"""Pydantic models for API request and response schemas.

This module defines the data schemas used for API input/output,
following the API endpoint design from the architecture plan.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    detail: Optional[str] = None
    status_code: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "healthy"
    timestamp: datetime
    database_connected: bool
    version: str = "1.0.0"


class InstrumentResponse(BaseModel):
    """Individual instrument response model."""
    ticker: str
    instrument_type: str = "stock"
    style_category: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    currency: str = "USD"
    active: bool = True
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class InstrumentsResponse(BaseModel):
    """List of instruments response model."""
    instruments: List[InstrumentResponse]
    total_count: int
    page: int = 1
    page_size: int = 50


class PositionResponse(BaseModel):
    """Individual position/holding response model."""
    holding_id: Optional[int] = None
    account: str
    subaccount: Optional[str] = None
    ticker: str
    company_name: Optional[str] = None
    quantity: float
    cost_basis: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_gain_loss: Optional[float] = None
    unrealized_gain_loss_percent: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: str = "USD"
    instrument_type: str = "stock"
    opened_at: Optional[str] = None
    last_update: Optional[str] = None
    weight: Optional[float] = None  # Portfolio weight percentage
    
    model_config = ConfigDict(from_attributes=True)


class PositionsResponse(BaseModel):
    """List of positions response model."""
    positions: List[PositionResponse]
    total_count: int
    page: int = 1
    page_size: int = 50


class AccountSummary(BaseModel):
    """Account summary data."""
    account: str
    value: Optional[float] = None
    cost_basis: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None
    positions_count: int = 0


class SectorAllocation(BaseModel):
    """Sector allocation data."""
    sector: str
    value: Optional[float] = None
    weight: Optional[float] = None  # Percentage of total portfolio
    positions_count: int = 0


class TopHolding(BaseModel):
    """Top holding data for portfolio summary."""
    ticker: str
    company_name: Optional[str] = None
    quantity: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None
    weight: Optional[float] = None  # Portfolio weight percentage
    sector: Optional[str] = None


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary response model matching architecture plan."""
    total_value: Optional[float] = None
    total_cost_basis: Optional[float] = None
    total_gain_loss: Optional[float] = None
    total_gain_loss_percent: Optional[float] = None
    accounts: List[AccountSummary] = Field(default_factory=list)
    top_holdings: List[TopHolding] = Field(default_factory=list)
    sector_allocation: List[SectorAllocation] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class DailyReturn(BaseModel):
    """Daily portfolio return data."""
    date: str
    portfolio_value: Optional[float] = None
    daily_change: Optional[float] = None
    daily_change_percent: Optional[float] = None


class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics."""
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None


class PerformanceResponse(BaseModel):
    """Portfolio performance response model."""
    daily_returns: List[DailyReturn] = Field(default_factory=list)
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)


class MarketPrice(BaseModel):
    """Market price data for a single ticker."""
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    timestamp: Optional[datetime] = None


class MarketPricesResponse(BaseModel):
    """Market prices response model."""
    prices: Dict[str, MarketPrice] = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


class StrategyRunResponse(BaseModel):
    """Strategy run response model."""
    run_id: str
    strategy_code: str
    started_at: str
    completed_at: Optional[str] = None
    universe_size: Optional[int] = None
    passed_count: Optional[int] = None
    min_score: Optional[int] = None
    exit_status: Optional[str] = None
    duration_ms: Optional[int] = None


class StrategyRunsResponse(BaseModel):
    """List of strategy runs response model."""
    runs: List[StrategyRunResponse]
    total_count: int
    page: int = 1
    page_size: int = 20


# Query parameter models
class HoldingsQueryParams(BaseModel):
    """Query parameters for holdings endpoints."""
    account: Optional[str] = None
    ticker: Optional[str] = None
    limit: Optional[int] = Field(default=50, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class InstrumentsQueryParams(BaseModel):
    """Query parameters for instruments endpoints."""
    instrument_type: Optional[str] = None
    sector: Optional[str] = None
    active: Optional[bool] = None
    limit: Optional[int] = Field(default=50, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class MarketDataQueryParams(BaseModel):
    """Query parameters for market data endpoints."""
    tickers: str = Field(description="Comma-separated list of tickers")