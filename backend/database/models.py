"""Database models and configuration for the application.

This module defines data models that correspond to the existing
SQLite database schema from db.py.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str
    foreign_keys: bool = True
    timeout: float = 30.0


@dataclass
class Instrument:
    """Instrument model corresponding to the instruments table."""
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


@dataclass
class Holding:
    """Holding model corresponding to the holdings table."""
    holding_id: Optional[int] = None
    account: str = "MAIN"
    subaccount: Optional[str] = None
    ticker: str = ""
    quantity: float = 0.0
    cost_basis: Optional[float] = None
    opened_at: Optional[str] = None
    last_update: Optional[str] = None
    lot_tag: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class StrategyRun:
    """Strategy run model corresponding to the strategy_run table."""
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


@dataclass
class StrategyResult:
    """Strategy result model corresponding to the strategy_result table."""
    run_id: str
    strategy_code: str
    ticker: str
    passed: bool
    score: Optional[float] = None
    classification: Optional[str] = None
    reasons: Optional[str] = None
    metrics_json: str = "{}"
    created_at: str = ""


@dataclass
class HoldingWithInstrument:
    """Combined holding and instrument data for API responses."""
    # Holding fields
    holding_id: Optional[int]
    account: str
    subaccount: Optional[str]
    ticker: str
    quantity: float
    cost_basis: Optional[float]
    opened_at: Optional[str]
    last_update: Optional[str]
    lot_tag: Optional[str]
    holding_notes: Optional[str]
    
    # Instrument fields
    instrument_type: str
    style_category: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    country: Optional[str]
    currency: str
    active: bool
    instrument_updated_at: Optional[str]
    instrument_notes: Optional[str]
    
    # Market data (to be populated by services)
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_gain_loss: Optional[float] = None
    unrealized_gain_loss_percent: Optional[float] = None
    company_name: Optional[str] = None