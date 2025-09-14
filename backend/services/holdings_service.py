"""Holdings service providing business logic for portfolio and holdings management.

This service integrates with the existing database and provides
data processing for holdings-related API endpoints.
"""

import logging
from typing import List, Optional, Dict, Any
import sqlite3
from datetime import datetime

from ..database.connection import DatabaseManager
from ..database.models import HoldingWithInstrument
from ..models.schemas import (
    PositionResponse, PortfolioSummaryResponse, AccountSummary,
    SectorAllocation, TopHolding, PositionsResponse
)
from .market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class HoldingsService:
    """Service for managing holdings and portfolio data."""
    
    def __init__(self, db_manager: DatabaseManager, market_service: MarketDataService):
        self.db_manager = db_manager
        self.market_service = market_service
    
    def get_positions(
        self, 
        account: Optional[str] = None, 
        ticker: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> PositionsResponse:
        """Get list of positions with optional filtering.
        
        Args:
            account: Filter by account name
            ticker: Filter by specific ticker
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            PositionsResponse with position data and pagination info
        """
        query = """
        SELECT 
            h.holding_id, h.account, h.subaccount, h.ticker, h.quantity, 
            h.cost_basis, h.opened_at, h.last_update, h.lot_tag, h.notes as holding_notes,
            i.instrument_type, i.style_category, i.sector, i.industry, 
            i.country, i.currency, i.active, i.updated_at as instrument_updated_at, 
            i.notes as instrument_notes
        FROM holdings h
        LEFT JOIN instruments i ON h.ticker = i.ticker
        WHERE 1=1
        """
        
        params = []
        
        if account:
            query += " AND h.account = ?"
            params.append(account)
        
        if ticker:
            query += " AND h.ticker = ?"
            params.append(ticker)
        
        # Get total count for pagination
        count_query = query.replace(
            "SELECT h.holding_id, h.account, h.subaccount, h.ticker, h.quantity, h.cost_basis, h.opened_at, h.last_update, h.lot_tag, h.notes as holding_notes, i.instrument_type, i.style_category, i.sector, i.industry, i.country, i.currency, i.active, i.updated_at as instrument_updated_at, i.notes as instrument_notes",
            "SELECT COUNT(*)"
        )
        
        total_count = self.db_manager.execute_one(count_query, tuple(params))
        total_count = total_count[0] if total_count else 0
        
        # Add ordering and pagination
        query += " ORDER BY h.ticker ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = self.db_manager.execute_query(query, tuple(params))
        
        # Convert to position responses
        positions = []
        tickers_for_prices = []
        
        for row in rows:
            holding = self._row_to_holding_with_instrument(row)
            position = self._holding_to_position_response(holding)
            positions.append(position)
            tickers_for_prices.append(row['ticker'])
        
        # Enrich with market data
        if tickers_for_prices:
            market_data = self.market_service.get_current_prices(tickers_for_prices)
            self._enrich_positions_with_market_data(positions, market_data)
        
        page = (offset // limit) + 1 if limit > 0 else 1
        
        return PositionsResponse(
            positions=positions,
            total_count=total_count,
            page=page,
            page_size=limit
        )
    
    def get_portfolio_summary(self) -> PortfolioSummaryResponse:
        """Get comprehensive portfolio summary with allocations and top holdings.
        
        Returns:
            PortfolioSummaryResponse with portfolio metrics and allocations
        """
        # Get all holdings with instrument data
        query = """
        SELECT 
            h.holding_id, h.account, h.subaccount, h.ticker, h.quantity, 
            h.cost_basis, h.opened_at, h.last_update, h.lot_tag, h.notes as holding_notes,
            i.instrument_type, i.style_category, i.sector, i.industry, 
            i.country, i.currency, i.active, i.updated_at as instrument_updated_at, 
            i.notes as instrument_notes
        FROM holdings h
        LEFT JOIN instruments i ON h.ticker = i.ticker
        WHERE h.quantity > 0
        ORDER BY h.ticker ASC
        """
        
        rows = self.db_manager.execute_query(query)
        
        if not rows:
            return PortfolioSummaryResponse(
                last_updated=datetime.utcnow()
            )
        
        # Convert to holdings and get market data
        holdings = [self._row_to_holding_with_instrument(row) for row in rows]
        tickers = [h.ticker for h in holdings]
        market_data = self.market_service.get_current_prices(tickers)
        
        # Enrich holdings with market data
        enriched_holdings = []
        for holding in holdings:
            if holding.ticker in market_data:
                price_data = market_data[holding.ticker]
                holding.current_price = price_data.get('price')
                if holding.current_price and holding.quantity:
                    holding.market_value = holding.current_price * holding.quantity
                    if holding.cost_basis:
                        total_cost = holding.cost_basis * holding.quantity
                        holding.unrealized_gain_loss = holding.market_value - total_cost
                        if total_cost > 0:
                            holding.unrealized_gain_loss_percent = (holding.unrealized_gain_loss / total_cost) * 100
            enriched_holdings.append(holding)
        
        # Calculate portfolio metrics
        total_value = sum((h.market_value or 0) for h in enriched_holdings)
        total_cost_basis = sum(((h.cost_basis or 0) * h.quantity) for h in enriched_holdings if h.cost_basis)
        total_gain_loss = total_value - total_cost_basis if total_cost_basis > 0 else None
        total_gain_loss_percent = ((total_gain_loss / total_cost_basis) * 100) if total_cost_basis > 0 and total_gain_loss else None
        
        # Calculate account summaries
        accounts = self._calculate_account_summaries(enriched_holdings)
        
        # Calculate sector allocations
        sector_allocations = self._calculate_sector_allocations(enriched_holdings, total_value)
        
        # Get top holdings (by market value)
        top_holdings = self._get_top_holdings(enriched_holdings, total_value, limit=10)
        
        return PortfolioSummaryResponse(
            total_value=total_value if total_value > 0 else None,
            total_cost_basis=total_cost_basis if total_cost_basis > 0 else None,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percent=total_gain_loss_percent,
            accounts=accounts,
            top_holdings=top_holdings,
            sector_allocation=sector_allocations,
            last_updated=datetime.utcnow()
        )
    
    def _row_to_holding_with_instrument(self, row: sqlite3.Row) -> HoldingWithInstrument:
        """Convert database row to HoldingWithInstrument object."""
        return HoldingWithInstrument(
            holding_id=row['holding_id'] if 'holding_id' in row.keys() else None,
            account=row['account'] if 'account' in row.keys() else 'MAIN',
            subaccount=row['subaccount'] if 'subaccount' in row.keys() else None,
            ticker=row['ticker'] if 'ticker' in row.keys() else '',
            quantity=row['quantity'] if 'quantity' in row.keys() else 0.0,
            cost_basis=row['cost_basis'] if 'cost_basis' in row.keys() else None,
            opened_at=row['opened_at'] if 'opened_at' in row.keys() else None,
            last_update=row['last_update'] if 'last_update' in row.keys() else None,
            lot_tag=row['lot_tag'] if 'lot_tag' in row.keys() else None,
            holding_notes=row['holding_notes'] if 'holding_notes' in row.keys() else None,
            instrument_type=row['instrument_type'] if 'instrument_type' in row.keys() else 'stock',
            style_category=row['style_category'] if 'style_category' in row.keys() else None,
            sector=row['sector'] if 'sector' in row.keys() else None,
            industry=row['industry'] if 'industry' in row.keys() else None,
            country=row['country'] if 'country' in row.keys() else None,
            currency=row['currency'] if 'currency' in row.keys() else 'USD',
            active=bool(row['active']) if 'active' in row.keys() else True,
            instrument_updated_at=row['instrument_updated_at'] if 'instrument_updated_at' in row.keys() else None,
            instrument_notes=row['instrument_notes'] if 'instrument_notes' in row.keys() else None
        )
    
    def _holding_to_position_response(self, holding: HoldingWithInstrument) -> PositionResponse:
        """Convert HoldingWithInstrument to PositionResponse."""
        return PositionResponse(
            holding_id=holding.holding_id,
            account=holding.account,
            subaccount=holding.subaccount,
            ticker=holding.ticker,
            company_name=holding.company_name,
            quantity=holding.quantity,
            cost_basis=holding.cost_basis,
            current_price=holding.current_price,
            market_value=holding.market_value,
            unrealized_gain_loss=holding.unrealized_gain_loss,
            unrealized_gain_loss_percent=holding.unrealized_gain_loss_percent,
            sector=holding.sector,
            industry=holding.industry,
            currency=holding.currency,
            instrument_type=holding.instrument_type,
            opened_at=holding.opened_at,
            last_update=holding.last_update
        )
    
    def _enrich_positions_with_market_data(self, positions: List[PositionResponse], market_data: Dict[str, Any]):
        """Enrich position responses with market data."""
        for position in positions:
            if position.ticker in market_data:
                price_data = market_data[position.ticker]
                position.current_price = price_data.get('price')
                if position.current_price and position.quantity:
                    position.market_value = position.current_price * position.quantity
                    if position.cost_basis:
                        total_cost = position.cost_basis * position.quantity
                        position.unrealized_gain_loss = position.market_value - total_cost
                        if total_cost > 0:
                            position.unrealized_gain_loss_percent = (position.unrealized_gain_loss / total_cost) * 100
    
    def _calculate_account_summaries(self, holdings: List[HoldingWithInstrument]) -> List[AccountSummary]:
        """Calculate account-level summaries."""
        account_data = {}
        
        for holding in holdings:
            account = holding.account
            if account not in account_data:
                account_data[account] = {
                    'value': 0.0,
                    'cost_basis': 0.0,
                    'count': 0
                }
            
            account_data[account]['value'] += holding.market_value or 0.0
            if holding.cost_basis:
                account_data[account]['cost_basis'] += holding.cost_basis * holding.quantity
            account_data[account]['count'] += 1
        
        summaries = []
        for account, data in account_data.items():
            gain_loss = data['value'] - data['cost_basis'] if data['cost_basis'] > 0 else None
            gain_loss_percent = ((gain_loss / data['cost_basis']) * 100) if data['cost_basis'] > 0 and gain_loss else None
            
            summaries.append(AccountSummary(
                account=account,
                value=data['value'] if data['value'] > 0 else None,
                cost_basis=data['cost_basis'] if data['cost_basis'] > 0 else None,
                gain_loss=gain_loss,
                gain_loss_percent=gain_loss_percent,
                positions_count=data['count']
            ))
        
        return summaries
    
    def _calculate_sector_allocations(self, holdings: List[HoldingWithInstrument], total_value: float) -> List[SectorAllocation]:
        """Calculate sector allocation breakdown."""
        sector_data = {}
        
        for holding in holdings:
            sector = holding.sector or 'Unknown'
            if sector not in sector_data:
                sector_data[sector] = {
                    'value': 0.0,
                    'count': 0
                }
            
            sector_data[sector]['value'] += holding.market_value or 0.0
            sector_data[sector]['count'] += 1
        
        allocations = []
        for sector, data in sector_data.items():
            weight = (data['value'] / total_value * 100) if total_value > 0 else 0.0
            
            allocations.append(SectorAllocation(
                sector=sector,
                value=data['value'] if data['value'] > 0 else None,
                weight=weight if weight > 0 else None,
                positions_count=data['count']
            ))
        
        # Sort by value descending
        allocations.sort(key=lambda x: x.value or 0, reverse=True)
        return allocations
    
    def _get_top_holdings(self, holdings: List[HoldingWithInstrument], total_value: float, limit: int = 10) -> List[TopHolding]:
        """Get top holdings by market value."""
        # Sort by market value descending
        sorted_holdings = sorted(holdings, key=lambda x: x.market_value or 0, reverse=True)
        
        top_holdings = []
        for holding in sorted_holdings[:limit]:
            weight = ((holding.market_value or 0) / total_value * 100) if total_value > 0 else 0.0
            
            gain_loss = None
            gain_loss_percent = None
            if holding.cost_basis and holding.market_value:
                total_cost = holding.cost_basis * holding.quantity
                gain_loss = holding.market_value - total_cost
                if total_cost > 0:
                    gain_loss_percent = (gain_loss / total_cost) * 100
            
            top_holdings.append(TopHolding(
                ticker=holding.ticker,
                company_name=holding.company_name,
                quantity=holding.quantity,
                current_price=holding.current_price,
                market_value=holding.market_value,
                cost_basis=holding.cost_basis,
                gain_loss=gain_loss,
                gain_loss_percent=gain_loss_percent,
                weight=weight if weight > 0 else None,
                sector=holding.sector
            ))
        
        return top_holdings