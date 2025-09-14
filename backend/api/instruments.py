"""Instruments API endpoints for instrument and market data management."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
import sqlite3

from ..models.schemas import (
    InstrumentResponse, InstrumentsResponse, MarketPricesResponse,
    MarketPrice, MarketDataQueryParams
)
from ..database.connection import get_database_connection, get_db_manager
from ..services.instruments_service import InstrumentsService
from ..services.market_data_service import MarketDataService

router = APIRouter()

# Initialize services
market_service = MarketDataService()
instruments_service = InstrumentsService(get_db_manager(), market_service)


@router.get("/instruments", response_model=InstrumentsResponse)
async def get_instruments(
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type (stock, etf, etc.)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip for pagination")
):
    """Get list of instruments with optional filtering.
    
    Returns instrument metadata including:
    - Ticker symbol and instrument type
    - Sector and industry classification
    - Country and currency information
    - Active status and last update timestamp
    
    Supports pagination and filtering by type, sector, and active status.
    """
    try:
        return instruments_service.get_instruments(
            instrument_type=instrument_type,
            sector=sector,
            active=active,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve instruments: {str(e)}"
        )


@router.get("/instruments/{ticker}", response_model=InstrumentResponse)
async def get_instrument(ticker: str):
    """Get detailed information for a specific instrument.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns comprehensive instrument information including:
    - Basic metadata (type, sector, industry)
    - Geographic information (country, currency)
    - Status and update information
    """
    try:
        instrument = instruments_service.get_instrument(ticker.upper())
        
        if not instrument:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found"
            )
        
        return instrument
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve instrument {ticker}: {str(e)}"
        )


@router.get("/instruments/{ticker}/market-data")
async def get_instrument_with_market_data(ticker: str):
    """Get instrument information enriched with current market data.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns instrument metadata combined with real-time market data:
    - All instrument metadata fields
    - Current price and daily change
    - Volume and OHLC data
    - Last update timestamp
    """
    try:
        data = instruments_service.get_instrument_with_market_data(ticker.upper())
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Instrument {ticker} not found"
            )
        
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve market data for {ticker}: {str(e)}"
        )


@router.get("/instruments/search/{query}")
async def search_instruments(
    query: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results")
):
    """Search instruments by ticker symbol or metadata.
    
    Args:
        query: Search term (ticker, sector, or industry)
        limit: Maximum number of results to return
        
    Returns list of matching instruments ranked by relevance:
    - Exact ticker matches first
    - Prefix matches second
    - Partial matches last
    """
    try:
        if len(query.strip()) < 1:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 1 character"
            )
        
        results = instruments_service.search_instruments(query, limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search instruments: {str(e)}"
        )


@router.get("/market/prices", response_model=MarketPricesResponse)
async def get_market_prices(
    tickers: str = Query(..., description="Comma-separated list of ticker symbols")
):
    """Get current market prices for multiple tickers.
    
    Args:
        tickers: Comma-separated list of ticker symbols (e.g., "AAPL,MSFT,GOOGL")
        
    Returns current market data for requested tickers:
    - Current price and daily change information
    - Volume and timestamp data
    - Error handling for invalid or unavailable tickers
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if not ticker_list:
            raise HTTPException(
                status_code=400,
                detail="At least one ticker must be provided"
            )
        
        if len(ticker_list) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 tickers allowed per request"
            )
        
        market_data = market_service.get_current_prices(ticker_list)
        
        # Convert to response format
        prices = {}
        for ticker, data in market_data.items():
            prices[ticker] = MarketPrice(
                price=data.get('price'),
                change=data.get('change'),
                change_percent=data.get('change_percent'),
                timestamp=data.get('timestamp')
            )
        
        return MarketPricesResponse(
            prices=prices,
            last_updated=max(
                (data.get('timestamp') for data in market_data.values() if data.get('timestamp')),
                default=None
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve market prices: {str(e)}"
        )


@router.get("/instruments/meta/sectors")
async def get_sectors():
    """Get list of all unique sectors in the instruments database.
    
    Returns sorted list of sector names for filtering and categorization.
    """
    try:
        sectors = instruments_service.get_sectors()
        return {
            "sectors": sectors,
            "count": len(sectors)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sectors: {str(e)}"
        )


@router.get("/instruments/meta/industries")
async def get_industries(
    sector: Optional[str] = Query(None, description="Filter industries by sector")
):
    """Get list of all unique industries, optionally filtered by sector.
    
    Args:
        sector: Optional sector filter
        
    Returns sorted list of industry names for filtering and categorization.
    """
    try:
        industries = instruments_service.get_industries(sector)
        return {
            "industries": industries,
            "count": len(industries),
            "sector_filter": sector
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve industries: {str(e)}"
        )


@router.get("/instruments/meta/types")
async def get_instrument_types():
    """Get list of all unique instrument types in the database.
    
    Returns sorted list of instrument types (stock, etf, etc.) for filtering.
    """
    try:
        types = instruments_service.get_instrument_types()
        return {
            "types": types,
            "count": len(types)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve instrument types: {str(e)}"
        )


@router.get("/instruments/stats")
async def get_instruments_stats():
    """Get statistical information about the instruments database.
    
    Returns comprehensive statistics including:
    - Total number of instruments
    - Breakdown by type, sector, and status
    - Data quality metrics
    """
    try:
        stats = instruments_service.get_instruments_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve instrument statistics: {str(e)}"
        )


@router.post("/instruments/{ticker}/refresh")
async def refresh_instrument_metadata(ticker: str):
    """Refresh instrument metadata from external market data sources.
    
    Args:
        ticker: Stock ticker symbol to refresh
        
    Updates instrument record with latest metadata from market data provider.
    Useful for keeping sector, industry, and other metadata current.
    """
    try:
        success = instruments_service.update_instrument_from_market_data(ticker.upper())
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Could not refresh metadata for {ticker} - instrument not found or data unavailable"
            )
        
        return {
            "ticker": ticker.upper(),
            "status": "refreshed",
            "message": "Instrument metadata updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh instrument metadata for {ticker}: {str(e)}"
        )