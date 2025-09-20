"""Holdings API endpoints for portfolio and position management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
import sqlite3

from ..models.schemas import (
    PositionsResponse, PortfolioSummaryResponse, ErrorResponse, HoldingsImportResponse
)
from ..database.connection import get_database_connection, get_db_manager
from ..services.holdings_service import HoldingsService
from ..services.market_data_service import MarketDataService

router = APIRouter()

# Initialize services
market_service = MarketDataService()
holdings_service = HoldingsService(get_db_manager(), market_service)


@router.get("/holdings/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary():
    """Get comprehensive portfolio summary with allocations and top holdings.
    
    Returns portfolio-level metrics including:
    - Total value and cost basis
    - Account summaries
    - Top holdings by value
    - Sector allocation breakdown
    """
    try:
        return holdings_service.get_portfolio_summary()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve portfolio summary: {str(e)}"
        )


@router.get("/holdings/positions", response_model=PositionsResponse)
async def get_positions(
    account: Optional[str] = Query(None, description="Filter by account name"),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip for pagination")
):
    """Get list of portfolio positions with optional filtering.
    
    Returns detailed position data including:
    - Holdings information (quantity, cost basis)
    - Instrument metadata (sector, industry, type)
    - Current market data (price, market value, P&L)
    - Portfolio weight calculations
    
    Supports pagination and filtering by account or ticker.
    """
    try:
        return holdings_service.get_positions(
            account=account,
            ticker=ticker,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve positions: {str(e)}"
        )


@router.get("/holdings/accounts")
async def get_accounts():
    """Get list of all account names with position counts.
    
    Returns summary information about each account including
    the number of positions held in each account.
    """
    try:
        query = """
        SELECT account, COUNT(*) as position_count, SUM(quantity) as total_quantity
        FROM holdings 
        WHERE quantity > 0
        GROUP BY account
        ORDER BY account
        """
        
        db_manager = get_db_manager()
        rows = db_manager.execute_query(query)
        
        accounts = []
        for row in rows:
            accounts.append({
                "account": row[0],
                "position_count": row[1],
                "total_quantity": float(row[2])
            })
        
        return {
            "accounts": accounts,
            "total_accounts": len(accounts)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


async def get_holdings_stats():
    """Get statistical information about the holdings portfolio.
    
    Returns various statistics about the portfolio including:
    - Total number of positions
    - Number of unique tickers
    - Account distribution
    - Sector/industry breakdown
    """
    try:
        db_manager = get_db_manager()
        
        # Basic stats
        stats_queries = {
            "total_positions": "SELECT COUNT(*) FROM holdings WHERE quantity > 0",
            "unique_tickers": "SELECT COUNT(DISTINCT ticker) FROM holdings WHERE quantity > 0",
            "total_accounts": "SELECT COUNT(DISTINCT account) FROM holdings WHERE quantity > 0",
            "total_quantity": "SELECT SUM(quantity) FROM holdings WHERE quantity > 0"
        }
        
        stats = {}
        for stat_name, query in stats_queries.items():
            result = db_manager.execute_one(query)
            stats[stat_name] = result[0] if result else 0
        
        # Sector breakdown
        sector_query = """
        SELECT i.sector, COUNT(*) as count, SUM(h.quantity) as total_quantity
        FROM holdings h
        LEFT JOIN instruments i ON h.ticker = i.ticker
        WHERE h.quantity > 0
        GROUP BY i.sector
        ORDER BY count DESC
        """
        
        sector_rows = db_manager.execute_query(sector_query)
        sector_breakdown = [
            {
                "sector": row[0] or "Unknown",
                "position_count": row[1],
                "total_quantity": float(row[2])
            }
            for row in sector_rows
        ]
        
        # Account breakdown
        account_query = """
        SELECT account, COUNT(*) as count, SUM(quantity) as total_quantity
        FROM holdings
        WHERE quantity > 0
        GROUP BY account
        ORDER BY count DESC
        """
        
        account_rows = db_manager.execute_query(account_query)
        account_breakdown = [
            {
                "account": row[0],
                "position_count": row[1],
                "total_quantity": float(row[2])
            }
            for row in account_rows
        ]
        
        return {
            "summary": stats,
            "sector_breakdown": sector_breakdown,
            "account_breakdown": account_breakdown
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve holdings statistics: {str(e)}"
        )


@router.get("/holdings/{ticker}")
async def get_holding_detail(ticker: str):
    """Get detailed information for a specific holding across all accounts.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns detailed holding information including:
    - Position details across all accounts
    - Instrument metadata
    - Current market data
    - Historical cost basis information
    """
    try:
        positions = holdings_service.get_positions(ticker=ticker.upper())
        
        if not positions.positions:
            raise HTTPException(
                status_code=404,
                detail=f"No holdings found for ticker {ticker}"
            )
        
        # Calculate aggregated metrics across accounts
        total_quantity = sum(pos.quantity for pos in positions.positions)
        total_market_value = sum(pos.market_value or 0 for pos in positions.positions)
        total_cost = sum((pos.cost_basis or 0) * pos.quantity for pos in positions.positions if pos.cost_basis)
        
        avg_cost_basis = total_cost / total_quantity if total_quantity > 0 and total_cost > 0 else None
        total_unrealized_pl = total_market_value - total_cost if total_cost > 0 else None
        total_unrealized_pl_percent = ((total_unrealized_pl / total_cost) * 100) if total_cost > 0 and total_unrealized_pl else None
        
        return {
            "ticker": ticker.upper(),
            "positions": positions.positions,
            "summary": {
                "total_quantity": total_quantity,
                "total_market_value": total_market_value if total_market_value > 0 else None,
                "average_cost_basis": avg_cost_basis,
                "total_unrealized_gain_loss": total_unrealized_pl,
                "total_unrealized_gain_loss_percent": total_unrealized_pl_percent,
                "account_count": len(positions.positions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve holding detail for {ticker}: {str(e)}"
        )


@router.post("/holdings/import", response_model=HoldingsImportResponse)
async def import_holdings_csv(
    file: UploadFile = File(..., description="CSV file containing holdings data"),
    replace_existing: bool = Form(True, description="Whether to replace all existing holdings for detected accounts")
):
    """Import holdings from a CSV file with automatic account detection.
    
    Accepts a CSV file with holdings data and automatically detects accounts from the file.
    The CSV should contain the following columns:
    - Account Number: Account identifier (automatically detected)
    - Account Name: Account name (optional, automatically detected)
    - Symbol: Stock ticker symbol
    - Quantity: Number of shares held
    - Current Value: Current market value of the position
    - Cost Basis Total: Total cost basis for the position
    - Type: Type of holding (stocks only, cash and options are skipped)
    
    The import process will:
    - Automatically detect all accounts present in the CSV
    - Skip non-stock entries (cash, options)
    - Skip pending activity entries
    - Skip disclaimer text at bottom of file
    - Optionally replace all existing holdings for detected accounts
    - Provide detailed import summary and error reporting per account
    
    Args:
        file: CSV file upload
        replace_existing: Whether to replace existing holdings for detected accounts (default: True)
        
    Returns:
        HoldingsImportResponse with detected accounts, import results and summary per account
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV file"
            )
        
        # Read file content
        content = await file.read()
        
        # Decode content as text
        try:
            csv_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                csv_content = content.decode('utf-8-sig')  # Try with BOM
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode CSV file. Please ensure it's saved as UTF-8."
                )
        
        # Call the holdings service to process the import with automatic account detection
        result = holdings_service.import_holdings_from_csv(
            csv_content=csv_content,
            replace_existing=replace_existing
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import holdings: {str(e)}"
        )