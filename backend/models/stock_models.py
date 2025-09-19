"""Pydantic models for stock analysis API responses.

This module defines the data schemas used specifically for stock analysis
endpoints and individual stock information.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class TechnicalIndicators(BaseModel):
    """Technical indicators for a stock."""
    # Moving averages
    sma_10: Optional[float] = Field(None, description="10-day Simple Moving Average")
    sma_20: Optional[float] = Field(None, description="20-day Simple Moving Average") 
    sma_50: Optional[float] = Field(None, description="50-day Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-day Simple Moving Average")
    
    # Exponential moving averages
    ema_12: Optional[float] = Field(None, description="12-day Exponential Moving Average")
    ema_26: Optional[float] = Field(None, description="26-day Exponential Moving Average")
    
    # RSI
    rsi_14: Optional[float] = Field(None, description="14-day Relative Strength Index")
    
    # MACD
    macd_line: Optional[float] = Field(None, description="MACD Line")
    macd_signal: Optional[float] = Field(None, description="MACD Signal Line")
    macd_histogram: Optional[float] = Field(None, description="MACD Histogram")
    
    # Bollinger Bands
    bb_upper: Optional[float] = Field(None, description="Bollinger Band Upper")
    bb_middle: Optional[float] = Field(None, description="Bollinger Band Middle")
    bb_lower: Optional[float] = Field(None, description="Bollinger Band Lower")
    bb_position: Optional[float] = Field(None, description="Position within Bollinger Bands (0-1)")
    
    # Volume indicators
    volume_sma_20: Optional[float] = Field(None, description="20-day Volume SMA")
    volume_ratio: Optional[float] = Field(None, description="Current volume vs 20-day average")
    
    # Price position indicators
    price_vs_sma10: Optional[float] = Field(None, description="Price vs SMA10 percentage")
    price_vs_sma20: Optional[float] = Field(None, description="Price vs SMA20 percentage")
    price_vs_sma50: Optional[float] = Field(None, description="Price vs SMA50 percentage")
    price_vs_sma200: Optional[float] = Field(None, description="Price vs SMA200 percentage")
    
    # ATR
    atr_14: Optional[float] = Field(None, description="14-day Average True Range")
    
    model_config = ConfigDict(extra='allow')


class PerformanceMetrics(BaseModel):
    """Performance metrics for a stock."""
    # Basic performance
    total_return: Optional[float] = Field(None, description="Total return percentage")
    annualized_return: Optional[float] = Field(None, description="Annualized return percentage")
    
    # Volatility
    volatility: Optional[float] = Field(None, description="Annualized volatility percentage")
    daily_volatility: Optional[float] = Field(None, description="Daily volatility percentage")
    
    # Risk metrics
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown percentage")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    
    # Recent performance
    one_month_return: Optional[float] = Field(None, description="1-month return percentage", alias="1_month_return")
    three_month_return: Optional[float] = Field(None, description="3-month return percentage", alias="3_month_return")
    six_month_return: Optional[float] = Field(None, description="6-month return percentage", alias="6_month_return")
    
    # High/low metrics
    fifty_two_week_high: Optional[float] = Field(None, description="52-week high price", alias="52_week_high")
    fifty_two_week_low: Optional[float] = Field(None, description="52-week low price", alias="52_week_low")
    distance_from_52w_high: Optional[float] = Field(None, description="Distance from 52-week high percentage")
    distance_from_52w_low: Optional[float] = Field(None, description="Distance from 52-week low percentage")
    
    model_config = ConfigDict(extra='allow', populate_by_name=True)


class CompanyInfo(BaseModel):
    """Company information for a stock."""
    ticker: str = Field(description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    country: Optional[str] = Field(None, description="Country")
    currency: Optional[str] = Field(None, description="Currency")
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    description: Optional[str] = Field(None, description="Business description")
    website: Optional[str] = Field(None, description="Company website")
    employees: Optional[int] = Field(None, description="Number of employees")
    
    model_config = ConfigDict(extra='allow')


class MarketData(BaseModel):
    """Current market data for a stock."""
    ticker: str = Field(description="Stock ticker symbol")
    price: Optional[float] = Field(None, description="Current price")
    change: Optional[float] = Field(None, description="Daily price change")
    change_percent: Optional[float] = Field(None, description="Daily change percentage")
    volume: Optional[int] = Field(None, description="Current volume")
    high: Optional[float] = Field(None, description="Daily high")
    low: Optional[float] = Field(None, description="Daily low")
    open: Optional[float] = Field(None, description="Opening price")
    timestamp: Optional[datetime] = Field(None, description="Data timestamp")
    
    model_config = ConfigDict(extra='allow')


class DataQuality(BaseModel):
    """Data quality indicators for stock information."""
    has_market_data: bool = Field(description="Market data available")
    has_company_info: bool = Field(description="Company info available") 
    has_technical_data: bool = Field(description="Technical data available")
    has_performance_data: bool = Field(description="Performance data available")


class StrategyHistoryItem(BaseModel):
    """Individual strategy execution result from history."""
    run_id: str = Field(description="Strategy run ID")
    strategy_code: str = Field(description="Strategy code")
    ticker: str = Field(description="Stock ticker")
    passed: bool = Field(description="Whether stock passed strategy")
    score: Optional[float] = Field(None, description="Strategy score")
    classification: Optional[str] = Field(None, description="Strategy classification")
    reasons: List[str] = Field(default_factory=list, description="Strategy reasons")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Strategy metrics")
    created_at: str = Field(description="Result creation timestamp")
    run_started_at: str = Field(description="Strategy run start time")
    run_completed_at: Optional[str] = Field(None, description="Strategy run completion time")
    run_params: Dict[str, Any] = Field(default_factory=dict, description="Strategy run parameters")
    
    model_config = ConfigDict(extra='allow')


class ComprehensiveStockInfo(BaseModel):
    """Comprehensive stock information response."""
    ticker: str = Field(description="Stock ticker symbol")
    timestamp: datetime = Field(description="Data retrieval timestamp")
    
    # Core data sections
    market_data: MarketData = Field(description="Current market data")
    company_info: CompanyInfo = Field(description="Company information")
    technical_indicators: Optional[TechnicalIndicators] = Field(None, description="Technical analysis indicators")
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Performance metrics")
    
    # Data quality
    data_quality: DataQuality = Field(description="Data availability indicators")
    
    model_config = ConfigDict(extra='allow')


class StockValidationResult(BaseModel):
    """Result of stock symbol validation."""
    symbol: str = Field(description="Input symbol")
    normalized_symbol: str = Field(description="Normalized symbol")
    is_valid: bool = Field(description="Whether symbol is valid")
    symbol_type: Optional[str] = Field(None, description="Type of symbol (us_stock, international, etc.)")
    issues: List[str] = Field(default_factory=list, description="Validation issues")
    data_available: Optional[bool] = Field(None, description="Whether market data is available")
    data_issues: List[str] = Field(default_factory=list, description="Data availability issues")
    
    model_config = ConfigDict(extra='allow')


class StockValidationBatchResponse(BaseModel):
    """Response for batch stock validation."""
    results: Dict[str, StockValidationResult] = Field(description="Validation results by symbol")
    valid_count: int = Field(description="Number of valid symbols")
    invalid_count: int = Field(description="Number of invalid symbols")
    total_count: int = Field(description="Total symbols validated")


class SymbolSuggestion(BaseModel):
    """Symbol suggestion for autocomplete."""
    symbol: str = Field(description="Suggested symbol")
    match_type: str = Field(description="Type of match (prefix, contains, etc.)")
    confidence: float = Field(description="Confidence score (0-1)")
    company_name: Optional[str] = Field(None, description="Company name if available")


class SymbolSuggestionsResponse(BaseModel):
    """Response for symbol suggestions."""
    query: str = Field(description="Original search query")
    suggestions: List[SymbolSuggestion] = Field(description="Symbol suggestions")
    count: int = Field(description="Number of suggestions")


class MarketStatusResponse(BaseModel):
    """Market status information."""
    us_market_open: Optional[bool] = Field(None, description="Whether US market is open")
    current_time_et: Optional[str] = Field(None, description="Current Eastern Time")
    current_time_utc: Optional[str] = Field(None, description="Current UTC time")
    note: Optional[str] = Field(None, description="Market hours note")
    error: Optional[str] = Field(None, description="Error message if status check failed")


class StockStrategyHistoryResponse(BaseModel):
    """Response for stock strategy execution history."""
    ticker: str = Field(description="Stock ticker symbol")
    history: List[StrategyHistoryItem] = Field(description="Strategy execution history")
    total_executions: int = Field(description="Total number of executions")
    strategies_used: List[str] = Field(description="List of strategies that have been run")
    last_execution: Optional[str] = Field(None, description="Timestamp of last execution")


class StockAnalysisError(BaseModel):
    """Error response for stock analysis endpoints."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    ticker: Optional[str] = Field(None, description="Stock ticker if applicable")
    timestamp: datetime = Field(description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class AddInstrumentRequest(BaseModel):
    """Request to add new instrument to database."""
    ticker: str = Field(description="Stock ticker symbol")
    instrument_type: str = Field(default="stock", description="Instrument type")
    fetch_metadata: bool = Field(default=True, description="Whether to fetch metadata from yfinance")
    notes: Optional[str] = Field(None, description="Optional notes")


class AddInstrumentResponse(BaseModel):
    """Response for adding new instrument."""
    ticker: str = Field(description="Stock ticker symbol")
    status: str = Field(description="Operation status")
    message: str = Field(description="Status message")
    added: bool = Field(description="Whether instrument was added")
    metadata_fetched: bool = Field(description="Whether metadata was fetched")
    existing: bool = Field(description="Whether instrument already existed")