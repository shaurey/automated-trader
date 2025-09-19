"""Stock analysis API endpoints.

This module provides comprehensive endpoints for individual stock analysis,
validation, and data retrieval using real-time market data.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ..models.stock_models import (
    ComprehensiveStockInfo,
    StockValidationResult,
    StockValidationBatchResponse,
    SymbolSuggestionsResponse,
    MarketStatusResponse,
    StockStrategyHistoryResponse,
    StockAnalysisError,
    AddInstrumentRequest,
    AddInstrumentResponse
)
from ..services.stock_analysis_service import StockAnalysisService
from ..services.stock_validation_service import StockValidationService
from ..database.connection import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])

# Services will be initialized on demand to avoid import-time issues
analysis_service = None
validation_service = None

def get_analysis_service():
    global analysis_service
    if analysis_service is None:
        analysis_service = StockAnalysisService()
    return analysis_service

def get_validation_service():
    global validation_service
    if validation_service is None:
        validation_service = StockValidationService()
    return validation_service


class BatchValidationRequest(BaseModel):
    """Request payload for validating multiple stock symbols."""
    symbols: List[str]
    check_data_availability: bool = True


def _fetch_stock_analysis(symbol: str, include_technical: bool, include_performance: bool) -> Dict[str, Any]:
    """Retrieve stock analysis payload with optional section filtering."""
    service = get_analysis_service()
    stock_info = service.get_comprehensive_stock_info(symbol)
    if not stock_info:
        raise ValueError(f"No data available for symbol {symbol}")
    if not include_technical:
        stock_info.pop('technical_indicators', None)
    if not include_performance:
        stock_info.pop('performance_metrics', None)
    return stock_info


def _validate_symbol(symbol: str, check_data_availability: bool) -> Dict[str, Any]:
    """Validate a single symbol using the shared validation service."""
    service = get_validation_service()
    return service.validate_symbol(symbol, check_data_availability)


def handle_stock_error(error: Exception, ticker: str = None) -> JSONResponse:
    """Handle stock-related errors and return appropriate JSON response."""
    
    # Create error response avoiding any datetime serialization issues
    import json
    
    error_content = {
        'error': type(error).__name__,
        'message': str(error),
        'ticker': ticker,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Ensure content is JSON serializable
    try:
        json.dumps(error_content)
    except (TypeError, ValueError):
        # Fallback to safe content
        error_content = {
            'error': 'SerializationError',
            'message': 'Error response could not be serialized',
            'ticker': str(ticker) if ticker else None,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    
    if isinstance(error, ValueError):
        return JSONResponse(
            status_code=400,
            content=error_content
        )
    elif isinstance(error, ConnectionError):
        return JSONResponse(
            status_code=503,
            content=error_content
        )
    else:
        logger.error(f"Unexpected error for ticker {ticker}: {error}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_content
        )


@router.get("/{symbol}/info", response_model=Dict[str, Any])
@router.get("/{symbol}/analysis", response_model=Dict[str, Any])
def get_stock_info(
    symbol: str,
    include_technical: bool = Query(True, description="Include technical indicators"),
    include_performance: bool = Query(True, description="Include performance metrics")
):
    """
    Get comprehensive stock information including market data, company info,
    technical indicators, and performance metrics.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        include_technical: Whether to include technical indicators
        include_performance: Whether to include performance metrics
    
    Returns:
        Comprehensive stock information with all requested data sections
    """
    try:
        logger.info(f"Fetching comprehensive stock info for {symbol}")

        stock_info = _fetch_stock_analysis(symbol, include_technical, include_performance)

        logger.info(f"Successfully retrieved stock info for {symbol}")
        return stock_info

    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {e}")
        return handle_stock_error(e, symbol)


@router.get("/validate", response_model=Dict[str, Any])
def validate_stock_symbol_query(
    symbol: str = Query(..., min_length=1, description="Stock ticker symbol to validate"),
    check_data_availability: bool = Query(True, description="Check if market data is available")
):
    """Query variant for validating a stock symbol."""
    return validate_stock_symbol(
        symbol=symbol,
        check_data_availability=check_data_availability
    )


@router.get("/analysis", response_model=Dict[str, Any])
def get_stock_info_by_query(
    symbol: str = Query(..., min_length=1, description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')"),
    include_technical: bool = Query(True, description="Include technical indicators"),
    include_performance: bool = Query(True, description="Include performance metrics")
):
    """Query-based endpoint variant for stock analysis lookup."""
    return get_stock_info(
        symbol=symbol,
        include_technical=include_technical,
        include_performance=include_performance
    )


@router.get("/{symbol}/validate", response_model=Dict[str, Any])
def validate_stock_symbol(
    symbol: str,
    check_data_availability: bool = Query(True, description="Check if market data is available")
):
    """
    Validate a stock symbol and check data availability.
    
    Args:
        symbol: Stock ticker symbol to validate
        check_data_availability: Whether to check if market data is available
    
    Returns:
        Validation result with symbol status and any issues found
    """
    try:
        logger.info(f"Validating stock symbol: {symbol}")

        validation_result = _validate_symbol(symbol, check_data_availability)

        logger.info(f"Validation completed for {symbol}: valid={validation_result['is_valid']}")
        return validation_result

    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {e}")
        return handle_stock_error(e, symbol)


@router.post("/validate-batch", response_model=Dict[str, Any])
def validate_stock_symbols_batch(
    request: BatchValidationRequest
):
    """
    Validate multiple stock symbols in batch.

    Args:
        request: Request payload containing symbols and options

    Returns:
        Batch validation results with counts and individual results
    """
    try:
        symbols = [symbol.upper().strip() for symbol in request.symbols if symbol]
        if not symbols:
            raise ValueError("At least one symbol is required for validation")

        logger.info(f"Batch validating {len(symbols)} symbols")

        batch_results = get_validation_service().validate_multiple_symbols(symbols, request.check_data_availability)

        valid_count = sum(1 for result in batch_results.values() if result['is_valid'])
        total_count = len(batch_results)

        response = {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': total_count - valid_count,
            'results': batch_results
        }

        logger.info(f"Batch validation completed: {valid_count}/{total_count} valid")
        return response

    except Exception as e:
        logger.error(f"Error in batch validation: {e}")
        return handle_stock_error(e)


@router.get("/suggestions", response_model=Dict[str, Any])
def get_symbol_suggestions(
    query: str = Query(..., min_length=1, description="Search query for symbol suggestions"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions")
):
    """
    Get symbol suggestions for autocomplete functionality.
    
    Args:
        query: Search query (partial symbol or company name)
        limit: Maximum number of suggestions to return
    
    Returns:
        List of symbol suggestions with confidence scores
    """
    try:
        logger.info(f"Getting symbol suggestions for query: '{query}'")
        
        service = get_validation_service()
        suggestions = service.get_symbol_suggestions(query, limit)
        
        response = {
            'query': query,
            'count': len(suggestions),
            'suggestions': suggestions
        }
        
        logger.info(f"Found {len(suggestions)} suggestions for '{query}'")
        return response
        
    except Exception as e:
        logger.error(f"Error getting suggestions for '{query}': {e}")
        return handle_stock_error(e)


@router.get("/market-status", response_model=Dict[str, Any])
def get_market_status():
    """Return current market status with extended metadata and graceful fallbacks.

    Adds:
      - Explicit trading session phase (pre, regular, post, closed)
      - Server time (UTC)
      - Next session open/close estimates
      - Safe fallback if timezone library unavailable
    """
    try:
        logger.info("Fetching market status")

        # Try native implementation first
        service = get_validation_service()
        base_status = service.is_market_open() or {}

        # Augment with additional derived fields (avoid failing if pytz missing)
        from datetime import datetime, time, timedelta
        server_utc = datetime.utcnow()
        phase = 'unknown'
        next_open = None
        next_close = None
        try:
            import pytz
            et_tz = pytz.timezone('America/New_York')
            now_et = server_utc.replace(tzinfo=pytz.UTC).astimezone(et_tz)
            hm = now_et.hour + now_et.minute/60
            # Define phases
            if now_et.weekday() >= 5:  # Weekend
                phase = 'closed'
                # Next open: upcoming Monday 9:30 ET
                days_ahead = 7 - now_et.weekday()  # 6 or 7? if Sat(5)->2 days, Sun(6)->1 day
                if now_et.weekday() == 5:
                    days_ahead = 2
                elif now_et.weekday() == 6:
                    days_ahead = 1
                next_open_dt = (now_et + timedelta(days=days_ahead)).replace(hour=9, minute=30, second=0, microsecond=0)
                next_open = next_open_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                if hm < 9.5:
                    phase = 'pre'
                    # open today
                    next_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
                    next_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
                elif 9.5 <= hm <= 16:
                    phase = 'regular'
                    next_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
                elif 16 < hm <= 20:  # treat up to 8PM as post-market
                    phase = 'post'
                    # next open tomorrow (or Monday if Friday)
                    add_days = 1
                    if now_et.weekday() == 4:  # Friday
                        add_days = 3
                    next_open_dt = (now_et + timedelta(days=add_days)).replace(hour=9, minute=30, second=0, microsecond=0)
                    next_open = next_open_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                else:
                    phase = 'closed'
                    # Determine next open (next weekday or Monday)
                    add_days = 1
                    if now_et.weekday() == 4:  # Friday night
                        add_days = 3
                    elif now_et.weekday() >= 5:  # Weekend handled above but keep safe
                        add_days = (7 - now_et.weekday()) % 7 or 1
                    next_open_dt = (now_et + timedelta(days=add_days)).replace(hour=9, minute=30, second=0, microsecond=0)
                    next_open = next_open_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception as tz_err:
            logger.warning(f"Extended market phase calculation skipped: {tz_err}")
            phase = base_status.get('us_market_open') and 'regular' or 'closed'

        enriched = {
            **base_status,
            'phase': phase,
            'server_time_utc': server_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'next_open_et': next_open,
            'next_close_et': next_close,
        }

        logger.info(f"Market status phase={phase} open={base_status.get('us_market_open')}")
        return enriched
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        return handle_stock_error(e)


@router.get("/{symbol}/strategy-history", response_model=Dict[str, Any])
def get_stock_strategy_history(
    symbol: str,
    limit: Optional[int] = Query(10, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get strategy execution history for a specific stock.
    
    Args:
        symbol: Stock ticker symbol
        limit: Maximum number of results to return
    
    Returns:
        Strategy execution history with metadata
    """
    try:
        logger.info(f"Fetching strategy history for {symbol}")
        
        # Get database manager (handles connection lifecycle)
        db_manager = get_db_manager()

        service = get_analysis_service()
        try:
            history_results = service.get_strategy_history(symbol, db_manager, limit)
        finally:
            close_fn = getattr(db_manager, "close", None)
            if callable(close_fn):
                close_fn()

        response = {
            'symbol': symbol,
            'total_executions': len(history_results),
            'executions': history_results
        }
        
        logger.info(f"Retrieved {len(history_results)} strategy executions for {symbol}")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching strategy history for {symbol}: {e}")
        return handle_stock_error(e, symbol)


@router.get("/{symbol}/technical", response_model=Dict[str, Any])
def get_stock_technical_indicators(
    symbol: str,
    period: Optional[str] = Query("3mo", description="Data period for calculations")
):
    """
    Get technical indicators for a stock.
    
    Args:
        symbol: Stock ticker symbol
        period: Data period for calculations
    
    Returns:
        Technical indicators data
    """
    try:
        logger.info(f"Fetching technical indicators for {symbol}")
        
        service = get_analysis_service()
        technical_data = service.get_technical_indicators(symbol, period)
        
        logger.info(f"Retrieved technical indicators for {symbol}")
        return technical_data or {}
        
    except Exception as e:
        logger.error(f"Error fetching technical indicators for {symbol}: {e}")
        return handle_stock_error(e, symbol)


@router.get("/{symbol}/performance", response_model=Dict[str, Any])
def get_stock_performance_metrics(
    symbol: str,
    period: Optional[str] = Query("1y", description="Data period for calculations")
):
    """
    Get performance metrics for a stock.
    
    Args:
        symbol: Stock ticker symbol
        period: Data period for calculations
    
    Returns:
        Performance metrics data
    """
    try:
        logger.info(f"Fetching performance metrics for {symbol}")
        
        service = get_analysis_service()
        performance_data = service.get_performance_metrics(symbol, period)
        
        logger.info(f"Retrieved performance metrics for {symbol}")
        return performance_data or {}
        
    except Exception as e:
        logger.error(f"Error fetching performance metrics for {symbol}: {e}")
        return handle_stock_error(e, symbol)


@router.post("/add-instrument", response_model=Dict[str, Any])
def add_new_instrument(request: Dict[str, Any]):
    """
    Add a new instrument to the database.
    
    Args:
        request: Request containing ticker and options for adding instrument
    
    Returns:
        Response indicating success/failure and metadata about the operation
    """
    try:
        ticker = request.get('ticker')
        if not ticker:
            raise ValueError("Ticker is required")
            
        logger.info(f"Adding new instrument: {ticker}")
        
        # For now, return a simple response - this would be implemented later
        response = {
            'status': 'success',
            'ticker': ticker,
            'message': f'Instrument {ticker} added successfully',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Instrument addition result for {ticker}: success")
        return response
        
    except Exception as e:
        logger.error(f"Error adding instrument: {e}")
        return handle_stock_error(e)


# Health check endpoint for the stocks API
@router.get("/health")
def stocks_health_check():
    """
    Health check endpoint for stocks API.
    
    Returns:
        Status information about the stocks API services
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Stock API endpoints are available"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

# Simple test endpoint
@router.get("/test")
def simple_test():
    """Simple test endpoint with no dependencies."""
    return {"message": "test successful", "timestamp": datetime.utcnow().isoformat()}