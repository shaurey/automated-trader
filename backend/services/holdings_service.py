"""Holdings service providing business logic for portfolio and holdings management.

This service integrates with the existing database and provides
data processing for holdings-related API endpoints.
"""

import logging
import csv
import io
from typing import List, Optional, Dict, Any
import sqlite3
from datetime import datetime

from ..database.connection import DatabaseManager
from ..database.models import HoldingWithInstrument
from ..models.schemas import (
    PositionResponse, PortfolioSummaryResponse, AccountSummary,
    SectorAllocation, StyleAllocation, TopHolding, PositionsResponse,
    HoldingsImportResponse, HoldingsImportSummary, ImportedHoldingRecord,
    DetectedAccount, AccountImportSummary
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
                    # cost_basis stored as TOTAL (not per share)
                    if holding.cost_basis:
                        total_cost = holding.cost_basis
                        holding.unrealized_gain_loss = holding.market_value - total_cost
                        if total_cost > 0:
                            holding.unrealized_gain_loss_percent = (holding.unrealized_gain_loss / total_cost) * 100
            enriched_holdings.append(holding)
        
        # Calculate portfolio metrics
        total_value = sum((h.market_value or 0) for h in enriched_holdings)
        # Treat cost_basis as already TOTAL
        total_cost_basis = sum((h.cost_basis or 0) for h in enriched_holdings if h.cost_basis)
        total_gain_loss = total_value - total_cost_basis if total_cost_basis > 0 else None
        total_gain_loss_percent = ((total_gain_loss / total_cost_basis) * 100) if total_cost_basis > 0 and total_gain_loss else None

        # Calculate account summaries
        accounts = self._calculate_account_summaries(enriched_holdings)

        # Calculate sector allocations
        sector_allocations = self._calculate_sector_allocations(enriched_holdings, total_value)

        # Calculate style allocations
        style_allocations = self._calculate_style_allocations(enriched_holdings, total_value)

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
            style_allocation=style_allocations,
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
            style_category=holding.style_category,
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
                        total_cost = position.cost_basis  # total cost already
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
                account_data[account]['cost_basis'] += holding.cost_basis  # total cost
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
    
    def _calculate_style_allocations(self, holdings: List[HoldingWithInstrument], total_value: float) -> List[StyleAllocation]:
        """Calculate style allocation breakdown."""
        style_data = {}
        
        for holding in holdings:
            style_category = holding.style_category or 'Unknown'
            if style_category not in style_data:
                style_data[style_category] = {
                    'value': 0.0,
                    'count': 0
                }
            
            style_data[style_category]['value'] += holding.market_value or 0.0
            style_data[style_category]['count'] += 1
        
        allocations = []
        for style_category, data in style_data.items():
            weight = (data['value'] / total_value * 100) if total_value > 0 else 0.0
            
            allocations.append(StyleAllocation(
                style_category=style_category,
                value=data['value'] if data['value'] > 0 else None,
                weight=weight if weight > 0 else None,
                positions_count=data['count']
            ))
        
        # Sort by value descending
        allocations.sort(key=lambda x: x.value or 0, reverse=True)
        return allocations
    
    def _get_top_holdings(self, holdings: List[HoldingWithInstrument], total_value: float, limit: int = 10) -> List[TopHolding]:
        """Get top holdings by market value, aggregated by ticker across accounts."""
        from collections import defaultdict
        
        # Group holdings by ticker
        ticker_holdings = defaultdict(list)
        for holding in holdings:
            ticker_holdings[holding.ticker].append(holding)
        
        # Aggregate holdings by ticker
        aggregated_holdings = []
        for ticker, ticker_positions in ticker_holdings.items():
            # Use the first position for non-aggregatable fields
            first_position = ticker_positions[0]
            
            # Aggregate quantities and values
            total_quantity = sum(pos.quantity for pos in ticker_positions)
            total_market_value = sum(pos.market_value or 0 for pos in ticker_positions)
            total_cost_basis = sum(pos.cost_basis or 0 for pos in ticker_positions if pos.cost_basis)  # cost_basis is already total cost
            
            # Calculate weighted average cost basis per share
            avg_cost_basis_per_share = total_cost_basis / total_quantity if total_quantity > 0 and total_cost_basis > 0 else None
            
            # Calculate current price (use first position's price)
            current_price = first_position.current_price
            
            # Calculate gain/loss
            gain_loss = None
            gain_loss_percent = None
            if total_cost_basis > 0 and total_market_value > 0:
                gain_loss = total_market_value - total_cost_basis
                gain_loss_percent = (gain_loss / total_cost_basis) * 100
            
            aggregated_holdings.append({
                'ticker': ticker,
                'company_name': first_position.company_name,
                'quantity': total_quantity,
                'current_price': current_price,
                'market_value': total_market_value,
                'cost_basis': total_cost_basis,  # Total cost basis across all accounts
                'avg_cost_basis_per_share': avg_cost_basis_per_share,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent,
                'sector': first_position.sector,
                'account_count': len(ticker_positions)  # Track how many accounts have this ticker
            })
        
        # Sort by total market value descending
        sorted_aggregated = sorted(aggregated_holdings, key=lambda x: x['market_value'] or 0, reverse=True)
        
        # Create TopHolding objects for the top holdings
        top_holdings = []
        for holding_data in sorted_aggregated[:limit]:
            weight = ((holding_data['market_value'] or 0) / total_value * 100) if total_value > 0 else 0.0
            
            top_holdings.append(TopHolding(
                ticker=holding_data['ticker'],
                company_name=holding_data['company_name'],
                quantity=holding_data['quantity'],
                current_price=holding_data['current_price'],
                market_value=holding_data['market_value'],
                cost_basis=holding_data['cost_basis'],  # Use total cost basis (same as original implementation)
                gain_loss=holding_data['gain_loss'],
                gain_loss_percent=holding_data['gain_loss_percent'],
                weight=weight if weight > 0 else None,
                sector=holding_data['sector']
            ))
        
        return top_holdings
    
    def import_holdings_from_csv(
        self,
        csv_content: str,
        replace_existing: bool = True
    ) -> HoldingsImportResponse:
        """Import holdings from CSV content with automatic account detection.
        
        Args:
            csv_content: CSV file content as string
            replace_existing: Whether to replace all existing holdings for detected accounts
            
        Returns:
            HoldingsImportResponse with import results and summary
        """
        logger.info("Starting CSV import with automatic account detection")
        
        imported_records = []
        errors = []
        warnings = []
        total_rows_processed = 0
        total_records_imported = 0
        total_records_skipped = 0
        total_records_failed = 0
        total_existing_holdings_deleted = 0
        
        # Account tracking
        detected_accounts = {}  # account_number -> DetectedAccount
        account_summaries = {}  # account_number -> AccountImportSummary
        
        try:
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            csv_reader = csv.DictReader(csv_file)
            
            # Validate CSV headers
            expected_headers = {'Account Number', 'Symbol', 'Quantity', 'Current Value', 'Cost Basis Total', 'Type'}
            if not expected_headers.issubset(set(csv_reader.fieldnames or [])):
                missing_headers = expected_headers - set(csv_reader.fieldnames or [])
                raise ValueError(f"Missing required CSV headers: {missing_headers}")
            
            # First pass: detect accounts and preview data
            first_pass_rows = []
            for row_number, row in enumerate(csv_reader, start=2):
                first_pass_rows.append((row_number, row))
                
                # Skip empty rows and disclaimer lines
                row_values = list(row.values())
                if not any(value and str(value).strip() for value in row_values):
                    continue
                    
                if any(str(value).strip().startswith('"') for value in row_values if value and str(value).strip()):
                    continue
                
                # Skip pending activity entries
                description = row.get('Description', '') or ''
                if 'Pending activity' in str(description):
                    continue
                
                # Skip cash entries
                entry_type = row.get('Type', '').strip()
                if entry_type.lower() == 'cash':
                    continue
                
                # Skip options
                symbol = (row.get('Symbol') or '').strip()
                if symbol.startswith(' -') or symbol.startswith('-') or not symbol:
                    continue
                
                # Extract account information
                account_number = (row.get('Account Number') or '').strip()
                account_name = (row.get('Account Name') or '').strip() or None
                
                if account_number:
                    if account_number not in detected_accounts:
                        detected_accounts[account_number] = DetectedAccount(
                            account_number=account_number,
                            account_name=account_name,
                            record_count=0,
                            sample_tickers=[]
                        )
                    
                    detected_accounts[account_number].record_count += 1
                    if len(detected_accounts[account_number].sample_tickers) < 3:
                        detected_accounts[account_number].sample_tickers.append(symbol.upper())
            
            if not detected_accounts:
                raise ValueError("No valid account data found in CSV file")
            
            logger.info(f"Detected {len(detected_accounts)} accounts: {list(detected_accounts.keys())}")
            
            # Start database transaction
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Initialize account summaries
                for account_number, account_info in detected_accounts.items():
                    account_summaries[account_number] = AccountImportSummary(
                        account_number=account_number,
                        account_name=account_info.account_name,
                        total_rows_processed=0,
                        records_imported=0,
                        records_skipped=0,
                        records_failed=0,
                        existing_holdings_deleted=0,
                        import_successful=False
                    )
                
                # Replace existing holdings for detected accounts if requested
                if replace_existing:
                    for account_number in detected_accounts.keys():
                        delete_query = "DELETE FROM holdings WHERE account = ?"
                        cursor.execute(delete_query, (account_number,))
                        deleted_count = cursor.rowcount
                        account_summaries[account_number].existing_holdings_deleted = deleted_count
                        total_existing_holdings_deleted += deleted_count
                        logger.info(f"Deleted {deleted_count} existing holdings for account {account_number}")
                
                # Second pass: process and import data
                for row_number, row in first_pass_rows:
                    total_rows_processed += 1
                    
                    try:
                        # Skip disclaimer lines and empty rows
                        row_values = list(row.values())
                        if not any(value and str(value).strip() for value in row_values):
                            total_records_skipped += 1
                            continue
                        
                        if any(str(value).strip().startswith('"') for value in row_values if value and str(value).strip()):
                            total_records_skipped += 1
                            continue
                        
                        # Skip pending activity entries
                        description = row.get('Description', '') or ''
                        if 'Pending activity' in str(description):
                            total_records_skipped += 1
                            continue
                        
                        # Skip cash entries
                        entry_type = row.get('Type', '').strip()
                        if entry_type.lower() == 'cash':
                            total_records_skipped += 1
                            continue
                        
                        # Skip options
                        symbol = (row.get('Symbol') or '').strip()
                        if symbol.startswith(' -') or symbol.startswith('-'):
                            total_records_skipped += 1
                            continue
                        
                        # Skip empty symbols
                        if not symbol:
                            total_records_skipped += 1
                            continue
                        
                        # Extract data
                        account_number = (row.get('Account Number') or '').strip()
                        account_name = (row.get('Account Name') or '').strip() or None
                        quantity_str = (row.get('Quantity') or '').strip()
                        current_value_str = (row.get('Current Value') or '').strip()
                        cost_basis_str = (row.get('Cost Basis Total') or '').strip()
                        
                        # Update account processing count
                        if account_number in account_summaries:
                            account_summaries[account_number].total_rows_processed += 1
                        
                        # Parse numeric values
                        try:
                            quantity = float(quantity_str.replace(',', '')) if quantity_str else 0.0
                            current_value = float(current_value_str.replace(',', '').replace('$', '')) if current_value_str else None
                            cost_basis = float(cost_basis_str.replace(',', '').replace('$', '')) if cost_basis_str else None
                        except ValueError as e:
                            error_msg = f"Row {row_number}: Invalid numeric data - {str(e)}"
                            errors.append(error_msg)
                            imported_records.append(ImportedHoldingRecord(
                                ticker=symbol,
                                account_number=account_number,
                                account_name=account_name,
                                quantity=0.0,
                                cost_basis=0.0,
                                current_value=current_value,
                                row_number=row_number,
                                status="error",
                                error_message=error_msg
                            ))
                            total_records_failed += 1
                            if account_number in account_summaries:
                                account_summaries[account_number].records_failed += 1
                            continue
                        
                        # Skip zero quantity holdings
                        if quantity <= 0:
                            total_records_skipped += 1
                            if account_number in account_summaries:
                                account_summaries[account_number].records_skipped += 1
                            continue
                        
                        # Insert holding into database
                        insert_query = """
                        INSERT INTO holdings (account, ticker, quantity, cost_basis, last_update)
                        VALUES (?, ?, ?, ?, ?)
                        """
                        
                        cursor.execute(insert_query, (
                            account_number,
                            symbol.upper(),
                            quantity,
                            cost_basis,
                            datetime.utcnow().isoformat()
                        ))
                        
                        # Record successful import
                        imported_records.append(ImportedHoldingRecord(
                            ticker=symbol.upper(),
                            account_number=account_number,
                            account_name=account_name,
                            quantity=quantity,
                            cost_basis=cost_basis or 0.0,
                            current_value=current_value,
                            row_number=row_number,
                            status="success"
                        ))
                        total_records_imported += 1
                        if account_number in account_summaries:
                            account_summaries[account_number].records_imported += 1
                        
                    except Exception as e:
                        error_msg = f"Row {row_number}: {str(e)}"
                        logger.error(f"Error processing row {row_number}: {e}")
                        errors.append(error_msg)
                        total_records_failed += 1
                        
                        # Extract account for error tracking
                        account_number = (row.get('Account Number', '') or '').strip()
                        if account_number in account_summaries:
                            account_summaries[account_number].records_failed += 1
                
                # Commit transaction
                conn.commit()
                logger.info(f"CSV import completed: {total_records_imported} imported, {total_records_skipped} skipped, {total_records_failed} failed")
        
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            errors.append(f"Import failed: {str(e)}")
            return HoldingsImportResponse(
                detected_accounts=[],
                import_summary=HoldingsImportSummary(
                    total_rows_processed=total_rows_processed,
                    total_accounts_detected=0,
                    total_records_imported=0,
                    total_records_skipped=0,
                    total_records_failed=total_rows_processed,
                    total_existing_holdings_deleted=0,
                    import_successful=False,
                    account_summaries=[]
                ),
                imported_records=[],
                errors=errors,
                warnings=warnings
            )
        
        # Update account summaries success status
        for account_summary in account_summaries.values():
            account_summary.import_successful = account_summary.records_imported > 0
        
        # Create overall import summary
        import_summary = HoldingsImportSummary(
            total_rows_processed=total_rows_processed,
            total_accounts_detected=len(detected_accounts),
            total_records_imported=total_records_imported,
            total_records_skipped=total_records_skipped,
            total_records_failed=total_records_failed,
            total_existing_holdings_deleted=total_existing_holdings_deleted,
            import_successful=total_records_imported > 0,
            account_summaries=list(account_summaries.values())
        )
        
        # Add warnings for any issues
        if total_records_skipped > 0:
            warnings.append(f"Skipped {total_records_skipped} non-stock entries (cash, options, pending activity)")
        
        if total_records_failed > 0:
            warnings.append(f"Failed to import {total_records_failed} records due to data errors")
        
        return HoldingsImportResponse(
            detected_accounts=list(detected_accounts.values()),
            import_summary=import_summary,
            imported_records=imported_records,
            errors=errors,
            warnings=warnings
        )