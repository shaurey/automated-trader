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
    style_category: Optional[str] = None
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


class StyleAllocation(BaseModel):
    """Style allocation data."""
    style_category: str
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
    style_allocation: List[StyleAllocation] = Field(default_factory=list)
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


class StrategyRunSummary(BaseModel):
    """Lightweight run summary for list views."""
    run_id: str
    strategy_code: str
    started_at: str
    completed_at: Optional[str] = None
    universe_size: Optional[int] = None
    passed_count: Optional[int] = None
    pass_rate: Optional[float] = None
    avg_score: Optional[float] = None
    duration_ms: Optional[int] = None
    exit_status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class StrategyRunsResponse(BaseModel):
    """List of strategy runs response model."""
    runs: List[StrategyRunSummary]
    total_count: int
    page: int = 1
    page_size: int = 20
    
    # Aggregated stats across runs
    strategy_stats: Optional[Dict[str, Any]] = None


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
    style_category: Optional[str] = None
    active: Optional[bool] = None
    limit: Optional[int] = Field(default=50, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class MarketDataQueryParams(BaseModel):
    """Query parameters for market data endpoints."""
    tickers: str = Field(description="Comma-separated list of tickers")


# Strategy Results Data Models

class StrategyMetrics(BaseModel):
    """Individual strategy metrics parsed from metrics_json."""
    # Core metrics (common across strategies)
    close: Optional[float] = None
    score: Optional[float] = None
    change_pct: Optional[float] = None
    
    # Technical indicators
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    
    # Moving averages
    sma10: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    sma10_above: Optional[bool] = None
    sma50_above: Optional[bool] = None
    sma200_above: Optional[bool] = None
    
    # Volume metrics
    volume: Optional[int] = None
    vol_avg20: Optional[int] = None
    volume_multiple: Optional[float] = None
    vol_continuity_ratio: Optional[float] = None
    
    # Breakout metrics
    ref_high: Optional[float] = None
    breakout_pct: Optional[float] = None
    extension_pct: Optional[float] = None
    breakout_move_atr: Optional[float] = None
    
    # Risk and entry metrics
    risk: Optional[str] = None
    recommendation: Optional[str] = None
    entry_quality: Optional[str] = None
    suggested_stop: Optional[float] = None
    atr14: Optional[float] = None
    
    # Scoring breakdown
    points_sma: Optional[int] = None
    points_macd: Optional[int] = None
    points_rsi: Optional[int] = None
    points_volume: Optional[int] = None
    points_high: Optional[int] = None
    extra_score: Optional[int] = None
    
    # Additional strategy-specific metrics
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra='allow')


class StrategyResultDetail(BaseModel):
    """Individual ticker result with full metrics."""
    run_id: str
    strategy_code: str
    ticker: str
    passed: bool
    score: Optional[float] = None
    classification: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    metrics: StrategyMetrics
    created_at: str
    
    # Enriched data (from instruments table)
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    instrument_type: str = "stock"
    
    model_config = ConfigDict(from_attributes=True)


class StrategyRunDetail(BaseModel):
    """Extended strategy run information with performance stats."""
    run_id: str
    strategy_code: str
    version: str
    params_hash: str
    params_json: str
    started_at: str
    completed_at: Optional[str] = None
    universe_source: Optional[str] = None
    universe_size: Optional[int] = None
    min_score: Optional[int] = None
    exit_status: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Performance summary
    passed_count: Optional[int] = None
    total_results: Optional[int] = None
    pass_rate: Optional[float] = None
    avg_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score_actual: Optional[float] = None
    
    # Score distribution
    score_ranges: Optional[Dict[str, int]] = None  # e.g., {"0-20": 5, "21-40": 10, ...}
    
    # Top performers preview
    top_results: List[StrategyResultDetail] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class StrategyResultsResponse(BaseModel):
    """Paginated results for a specific run."""
    run_id: str
    strategy_code: str
    results: List[StrategyResultDetail]
    total_count: int
    passed_count: int
    failed_count: int
    page: int = 1
    page_size: int = 50
    
    # Summary statistics
    summary: Dict[str, Any] = Field(default_factory=dict)


class StrategyLatestResponse(BaseModel):
    """Latest runs by strategy type."""
    latest_runs: List[StrategyRunDetail]
    strategies: List[str]  # Available strategy codes
    total_strategies: int


# Query parameter models for strategy endpoints

class StrategyRunsQueryParams(BaseModel):
    """Query parameters for strategy runs endpoints."""
    strategy_code: Optional[str] = Field(None, description="Filter by strategy code")
    status: Optional[str] = Field(None, description="Filter by exit status (ok, error, timeout)")
    date_from: Optional[str] = Field(None, description="Filter runs from date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter runs to date (ISO format)")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip for pagination")
    order_by: str = Field("started_at", description="Sort field (started_at, completed_at, passed_count)")
    order_desc: bool = Field(True, description="Sort in descending order")


class StrategyResultsQueryParams(BaseModel):
    """Query parameters for strategy results endpoints."""
    passed: Optional[bool] = Field(None, description="Filter by pass/fail status")
    min_score: Optional[float] = Field(None, description="Minimum score threshold")
    max_score: Optional[float] = Field(None, description="Maximum score threshold")
    classification: Optional[str] = Field(None, description="Filter by classification (Buy, Watch, Wait)")
    ticker: Optional[str] = Field(None, description="Filter by ticker symbol")
    sector: Optional[str] = Field(None, description="Filter by sector")
    limit: int = Field(50, ge=1, le=500, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip for pagination")
    order_by: str = Field("score", description="Sort field (score, ticker, created_at)")
    order_desc: bool = Field(True, description="Sort in descending order")