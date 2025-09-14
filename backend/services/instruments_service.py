"""Instruments service providing business logic for instrument management.

This service manages instrument data and metadata from the database.
"""

import logging
from typing import List, Optional
import sqlite3

from ..database.connection import DatabaseManager
from ..database.models import Instrument
from ..models.schemas import InstrumentResponse, InstrumentsResponse
from .market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class InstrumentsService:
    """Service for managing instrument data and metadata."""
    
    def __init__(self, db_manager: DatabaseManager, market_service: MarketDataService):
        self.db_manager = db_manager
        self.market_service = market_service
    
    def get_instruments(
        self,
        instrument_type: Optional[str] = None,
        sector: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> InstrumentsResponse:
        """Get list of instruments with optional filtering.
        
        Args:
            instrument_type: Filter by instrument type (stock, etf, etc.)
            sector: Filter by sector
            active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            InstrumentsResponse with instrument data and pagination info
        """
        # Build WHERE clause conditions
        where_conditions = ["1=1"]
        params = []
        
        if instrument_type:
            where_conditions.append("instrument_type = ?")
            params.append(instrument_type)
        
        if sector:
            where_conditions.append("sector = ?")
            params.append(sector)
        
        if active is not None:
            where_conditions.append("active = ?")
            params.append(1 if active else 0)
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM instruments WHERE {where_clause}"
        total_count_row = self.db_manager.execute_one(count_query, tuple(params))
        total_count = int(total_count_row[0]) if total_count_row else 0
        
        # Build main query
        query = f"""
        SELECT ticker, instrument_type, style_category, sector, industry,
               country, currency, active, updated_at, notes
        FROM instruments
        WHERE {where_clause}
        """
        
        # Add ordering and pagination
        query += " ORDER BY ticker ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = self.db_manager.execute_query(query, tuple(params))
        
        # Convert to instrument responses
        instruments = [self._row_to_instrument_response(row) for row in rows]
        
        page = (offset // limit) + 1 if limit > 0 else 1
        
        return InstrumentsResponse(
            instruments=instruments,
            total_count=total_count,
            page=page,
            page_size=limit
        )
    
    def get_instrument(self, ticker: str) -> Optional[InstrumentResponse]:
        """Get a single instrument by ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            InstrumentResponse or None if not found
        """
        query = """
        SELECT ticker, instrument_type, style_category, sector, industry, 
               country, currency, active, updated_at, notes
        FROM instruments
        WHERE ticker = ?
        """
        
        row = self.db_manager.execute_one(query, (ticker,))
        
        if not row:
            return None
        
        return self._row_to_instrument_response(row)
    
    def get_instrument_with_market_data(self, ticker: str) -> Optional[dict]:
        """Get instrument data enriched with current market data.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Dictionary with instrument and market data or None if not found
        """
        instrument = self.get_instrument(ticker)
        
        if not instrument:
            return None
        
        # Get market data
        market_data = self.market_service.get_single_price(ticker)
        
        # Convert to dict and add market data
        result = instrument.model_dump()
        
        if market_data:
            result.update({
                'current_price': market_data.get('price'),
                'change': market_data.get('change'),
                'change_percent': market_data.get('change_percent'),
                'volume': market_data.get('volume'),
                'high': market_data.get('high'),
                'low': market_data.get('low'),
                'open': market_data.get('open'),
                'last_updated': market_data.get('timestamp')
            })
        
        return result
    
    def search_instruments(self, query: str, limit: int = 20) -> List[InstrumentResponse]:
        """Search instruments by ticker or name.
        
        Args:
            query: Search query (ticker or partial name)
            limit: Maximum number of results
            
        Returns:
            List of matching instruments
        """
        search_query = """
        SELECT ticker, instrument_type, style_category, sector, industry, 
               country, currency, active, updated_at, notes
        FROM instruments
        WHERE ticker LIKE ? OR sector LIKE ? OR industry LIKE ?
        ORDER BY 
            CASE WHEN ticker = ? THEN 1
                 WHEN ticker LIKE ? THEN 2
                 ELSE 3 END,
            ticker ASC
        LIMIT ?
        """
        
        search_term = f"%{query.upper()}%"
        exact_term = query.upper()
        prefix_term = f"{query.upper()}%"
        
        params = (search_term, search_term, search_term, exact_term, prefix_term, limit)
        
        rows = self.db_manager.execute_query(search_query, params)
        
        return [self._row_to_instrument_response(row) for row in rows]
    
    def get_sectors(self) -> List[str]:
        """Get list of all unique sectors.
        
        Returns:
            List of sector names
        """
        query = """
        SELECT DISTINCT sector
        FROM instruments
        WHERE sector IS NOT NULL AND sector != ''
        ORDER BY sector ASC
        """
        
        rows = self.db_manager.execute_query(query)
        
        return [row[0] for row in rows]
    
    def get_industries(self, sector: Optional[str] = None) -> List[str]:
        """Get list of all unique industries, optionally filtered by sector.
        
        Args:
            sector: Filter by sector
            
        Returns:
            List of industry names
        """
        query = """
        SELECT DISTINCT industry
        FROM instruments
        WHERE industry IS NOT NULL AND industry != ''
        """
        
        params = []
        
        if sector:
            query += " AND sector = ?"
            params.append(sector)
        
        query += " ORDER BY industry ASC"
        
        rows = self.db_manager.execute_query(query, tuple(params))
        
        return [row[0] for row in rows]
    
    def get_instrument_types(self) -> List[str]:
        """Get list of all unique instrument types.
        
        Returns:
            List of instrument type names
        """
        query = """
        SELECT DISTINCT instrument_type
        FROM instruments
        WHERE instrument_type IS NOT NULL AND instrument_type != ''
        ORDER BY instrument_type ASC
        """
        
        rows = self.db_manager.execute_query(query)
        
        return [row[0] for row in rows]
    
    def update_instrument_from_market_data(self, ticker: str) -> bool:
        """Update instrument metadata from market data source.
        
        Args:
            ticker: Ticker symbol to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get company info from market data service
            company_info = self.market_service.get_company_info(ticker)
            
            if not company_info:
                logger.warning(f"No company info found for {ticker}")
                return False
            
            # Update instrument record
            query = """
            UPDATE instruments 
            SET sector = COALESCE(?, sector),
                industry = COALESCE(?, industry),
                country = COALESCE(?, country),
                currency = COALESCE(?, currency),
                updated_at = datetime('now')
            WHERE ticker = ?
            """
            
            params = (
                company_info.get('sector'),
                company_info.get('industry'),
                company_info.get('country'),
                company_info.get('currency', 'USD'),
                ticker
            )
            
            rows_affected = self.db_manager.execute_update(query, params)
            
            if rows_affected > 0:
                logger.info(f"Updated instrument metadata for {ticker}")
                return True
            else:
                logger.warning(f"No instrument found with ticker {ticker}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update instrument {ticker}: {e}")
            return False
    
    def _row_to_instrument_response(self, row: sqlite3.Row) -> InstrumentResponse:
        """Convert database row to InstrumentResponse."""
        return InstrumentResponse(
            ticker=row['ticker'],
            instrument_type=row['instrument_type'] if 'instrument_type' in row.keys() else 'stock',
            style_category=row['style_category'] if 'style_category' in row.keys() else None,
            sector=row['sector'] if 'sector' in row.keys() else None,
            industry=row['industry'] if 'industry' in row.keys() else None,
            country=row['country'] if 'country' in row.keys() else None,
            currency=row['currency'] if 'currency' in row.keys() else 'USD',
            active=bool(row['active']) if 'active' in row.keys() else True,
            updated_at=row['updated_at'] if 'updated_at' in row.keys() else None,
            notes=row['notes'] if 'notes' in row.keys() else None
        )
    
    def get_instruments_stats(self) -> dict:
        """Get statistics about instruments in the database.
        
        Returns:
            Dictionary with various statistics
        """
        queries = {
            'total_instruments': "SELECT COUNT(*) FROM instruments",
            'active_instruments': "SELECT COUNT(*) FROM instruments WHERE active = 1",
            'stocks': "SELECT COUNT(*) FROM instruments WHERE instrument_type = 'stock'",
            'etfs': "SELECT COUNT(*) FROM instruments WHERE instrument_type = 'etf'",
            'sectors_count': "SELECT COUNT(DISTINCT sector) FROM instruments WHERE sector IS NOT NULL",
            'industries_count': "SELECT COUNT(DISTINCT industry) FROM instruments WHERE industry IS NOT NULL"
        }
        
        stats = {}
        
        for stat_name, query in queries.items():
            try:
                result = self.db_manager.execute_one(query)
                stats[stat_name] = result[0] if result else 0
            except Exception as e:
                logger.error(f"Failed to get {stat_name}: {e}")
                stats[stat_name] = 0
        
        return stats