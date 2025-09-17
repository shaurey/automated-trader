# Strategy Service Classes Design

## Overview

This document outlines the design for strategy service classes that enable direct integration into FastAPI endpoints, eliminating the need for complex subprocess management and SSE streaming.

## Design Principles

1. **Direct Integration**: Strategy logic runs in-process within FastAPI
2. **Callback-Based Progress**: Use callback functions for progress reporting
3. **Database-Centric**: All progress and results stored directly in database
4. **Modular Design**: Each strategy is a self-contained service class
5. **Error Resilience**: Graceful handling of individual ticker failures

## Base Strategy Service Architecture

### 1. Abstract Base Strategy Class

```python
from abc import ABC, abstractmethod
from typing import List, Callable, Dict, Any, Optional
from dataclasses import dataclass
import time
from datetime import datetime

@dataclass
class StrategyConfig:
    """Base configuration for strategy execution"""
    min_score: int = 70
    max_workers: int = 4
    timeout_seconds: int = 300

@dataclass 
class TickerResult:
    """Result for individual ticker analysis"""
    ticker: str
    passed: bool
    score: Optional[float]
    classification: Optional[str]
    reasons: List[str]
    metrics: Dict[str, Any]
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None

@dataclass
class StrategyResults:
    """Complete strategy execution results"""
    run_id: str
    strategy_code: str
    total_evaluated: int
    qualifying_stocks: List[TickerResult]
    failed_stocks: List[TickerResult]
    execution_time_ms: int
    summary_metrics: Dict[str, Any]

class ProgressCallback:
    """Callback interface for progress reporting"""
    
    def __call__(self, 
                 current: int, 
                 total: int, 
                 ticker: str, 
                 result: Optional[TickerResult] = None,
                 stage: str = "processing") -> None:
        """
        Report progress during strategy execution
        
        Args:
            current: Current position (1-based)
            total: Total number of tickers
            ticker: Current ticker symbol
            result: Result of ticker analysis (if completed)
            stage: Current execution stage
        """
        pass

class BaseStrategyService(ABC):
    """Abstract base class for strategy services"""
    
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        
    @property
    @abstractmethod
    def strategy_code(self) -> str:
        """Strategy identifier code"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy version"""
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate strategy-specific parameters"""
        pass
    
    @abstractmethod
    def create_config(self, parameters: Dict[str, Any]) -> StrategyConfig:
        """Create strategy configuration from parameters"""
        pass
    
    @abstractmethod
    def evaluate_ticker(self, ticker: str, config: StrategyConfig) -> TickerResult:
        """Evaluate a single ticker"""
        pass
    
    def execute(self, 
                tickers: List[str], 
                parameters: Dict[str, Any],
                progress_callback: Optional[ProgressCallback] = None) -> StrategyResults:
        """
        Execute strategy on list of tickers
        
        Args:
            tickers: List of ticker symbols to analyze
            parameters: Strategy-specific parameters
            progress_callback: Optional progress reporting callback
            
        Returns:
            Complete strategy execution results
        """
        # Validate inputs
        self.validate_parameters(parameters)
        config = self.create_config(parameters)
        
        # Start database run
        run_id = self.db.start_run(
            strategy_code=self.strategy_code,
            version=self.version,
            params=parameters,
            universe_source="api",
            universe_size=len(tickers),
            min_score=config.min_score
        )
        
        # Initialize execution
        start_time = time.time()
        results = []
        
        if progress_callback:
            progress_callback(0, len(tickers), "", None, "initializing")
        
        # Process each ticker
        for i, ticker in enumerate(tickers):
            ticker_start = time.time()
            
            try:
                # Evaluate ticker
                result = self.evaluate_ticker(ticker, config)
                result.processing_time_ms = int((time.time() - ticker_start) * 1000)
                results.append(result)
                
                # Update database
                self._update_database_progress(run_id, i + 1, len(tickers), ticker, result)
                
                # Report progress
                if progress_callback:
                    progress_callback(i + 1, len(tickers), ticker, result, "processing")
                    
            except Exception as e:
                # Handle ticker error gracefully
                error_result = TickerResult(
                    ticker=ticker,
                    passed=False,
                    score=None,
                    classification="error",
                    reasons=[f"evaluation_error: {str(e)}"],
                    metrics={},
                    processing_time_ms=int((time.time() - ticker_start) * 1000),
                    error_message=str(e)
                )
                results.append(error_result)
                
                # Update database with error
                self._update_database_progress(run_id, i + 1, len(tickers), ticker, error_result)
                
                # Report error progress
                if progress_callback:
                    progress_callback(i + 1, len(tickers), ticker, error_result, "error")
        
        # Complete execution
        execution_time_ms = int((time.time() - start_time) * 1000)
        self.db.finalize_run(run_id)
        
        # Prepare results
        qualifying = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        
        summary_metrics = {
            "total_evaluated": len(results),
            "qualifying_count": len(qualifying),
            "failed_count": len(failed),
            "pass_rate": len(qualifying) / len(results) if results else 0,
            "avg_score": sum(r.score for r in qualifying if r.score) / len(qualifying) if qualifying else 0,
            "execution_time_ms": execution_time_ms
        }
        
        if progress_callback:
            progress_callback(len(tickers), len(tickers), "", None, "completed")
        
        return StrategyResults(
            run_id=run_id,
            strategy_code=self.strategy_code,
            total_evaluated=len(results),
            qualifying_stocks=qualifying,
            failed_stocks=failed,
            execution_time_ms=execution_time_ms,
            summary_metrics=summary_metrics
        )
    
    def _update_database_progress(self, run_id: str, current: int, total: int, 
                                 ticker: str, result: TickerResult) -> None:
        """Update database with current progress"""
        try:
            # Update run-level progress
            progress_percent = (current / total) * 100 if total > 0 else 0
            
            self.db.conn.execute("""
                UPDATE strategy_run 
                SET current_ticker = ?, 
                    processed_count = ?, 
                    progress_percent = ?,
                    last_progress_update = ?
                WHERE run_id = ?
            """, (ticker, current, progress_percent, Database._now_iso(), run_id))
            
            # Insert ticker-level progress
            self.db.conn.execute("""
                INSERT INTO strategy_execution_progress (
                    run_id, ticker, sequence_number, processed_at, 
                    passed, score, classification, error_message, processing_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, ticker, current, Database._now_iso(),
                  result.passed, result.score, result.classification,
                  result.error_message, result.processing_time_ms))
            
            # Log full result
            self.db.log_result(
                run_id=run_id,
                strategy_code=self.strategy_code,
                ticker=ticker,
                passed=result.passed,
                score=result.score or 0,
                classification=result.classification,
                reasons=result.reasons,
                metrics=result.metrics
            )
            
        except Exception as e:
            # Log error but don't fail execution
            print(f"Database update error for {ticker}: {e}")
```

### 2. Bullish Breakout Strategy Service

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class BullishBreakoutConfig(StrategyConfig):
    """Configuration for bullish breakout strategy"""
    min_volume_multiple: float = 1.0
    strict_macd_positive: bool = False
    allow_overbought: bool = False
    require_52w_high: bool = False
    period: str = "2y"
    interval: str = "1d"
    lookup_names: bool = True

class BullishBreakoutService(BaseStrategyService):
    """Bullish breakout strategy service"""
    
    @property
    def strategy_code(self) -> str:
        return "bullish_breakout"
    
    @property
    def version(self) -> str:
        return "2.0"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate bullish breakout parameters"""
        required_fields = ["tickers"]
        for field in required_fields:
            if field not in parameters:
                raise ValueError(f"Missing required parameter: {field}")
        
        if not isinstance(parameters["tickers"], list) or not parameters["tickers"]:
            raise ValueError("tickers must be a non-empty list")
        
        # Validate optional numeric parameters
        numeric_params = {
            "min_volume_multiple": (0.1, 10.0),
            "min_score": (0, 100)
        }
        
        for param, (min_val, max_val) in numeric_params.items():
            if param in parameters:
                value = parameters[param]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    raise ValueError(f"{param} must be between {min_val} and {max_val}")
    
    def create_config(self, parameters: Dict[str, Any]) -> BullishBreakoutConfig:
        """Create configuration from parameters"""
        return BullishBreakoutConfig(
            min_score=parameters.get("min_score", 70),
            max_workers=parameters.get("max_workers", 4),
            min_volume_multiple=parameters.get("min_volume_multiple", 1.0),
            strict_macd_positive=parameters.get("strict_macd_positive", False),
            allow_overbought=parameters.get("allow_overbought", False),
            require_52w_high=parameters.get("require_52w_high", False),
            period=parameters.get("period", "2y"),
            interval=parameters.get("interval", "1d"),
            lookup_names=parameters.get("lookup_names", True)
        )
    
    def evaluate_ticker(self, ticker: str, config: BullishBreakoutConfig) -> TickerResult:
        """Evaluate single ticker for bullish breakout"""
        # Import the existing evaluation logic from bullish_strategy.py
        from bullish_strategy import _evaluate_ticker, ScreenerConfig
        
        # Convert to legacy config format
        legacy_config = ScreenerConfig(
            period=config.period,
            interval=config.interval,
            min_volume_multiple=config.min_volume_multiple,
            strict_macd_positive=config.strict_macd_positive,
            allow_overbought=config.allow_overbought,
            require_52w_high=config.require_52w_high,
            min_score=config.min_score,
            lookup_names=config.lookup_names
        )
        
        # Execute evaluation
        legacy_result = _evaluate_ticker(ticker, legacy_config)
        
        # Convert to new format
        return TickerResult(
            ticker=legacy_result.ticker,
            passed=legacy_result.passed,
            score=legacy_result.metrics.get("score"),
            classification=legacy_result.metrics.get("recommendation"),
            reasons=legacy_result.reasons,
            metrics=legacy_result.metrics
        )
```

### 3. LEAP Entry Strategy Service

```python
@dataclass
class LeapEntryConfig(StrategyConfig):
    """Configuration for LEAP entry strategy"""
    min_dte: int = 300
    max_dte: int = 730
    min_open_interest: int = 100
    max_bid_ask_spread: float = 0.20
    min_iv_rank: float = 20.0
    max_iv_rank: float = 80.0

class LeapEntryService(BaseStrategyService):
    """LEAP entry strategy service"""
    
    @property
    def strategy_code(self) -> str:
        return "leap_entry"
    
    @property 
    def version(self) -> str:
        return "2.0"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate LEAP entry parameters"""
        required_fields = ["tickers"]
        for field in required_fields:
            if field not in parameters:
                raise ValueError(f"Missing required parameter: {field}")
        
        if not isinstance(parameters["tickers"], list) or not parameters["tickers"]:
            raise ValueError("tickers must be a non-empty list")
    
    def create_config(self, parameters: Dict[str, Any]) -> LeapEntryConfig:
        """Create configuration from parameters"""
        return LeapEntryConfig(
            min_score=parameters.get("min_score", 70),
            max_workers=parameters.get("max_workers", 4),
            min_dte=parameters.get("min_dte", 300),
            max_dte=parameters.get("max_dte", 730),
            min_open_interest=parameters.get("min_open_interest", 100),
            max_bid_ask_spread=parameters.get("max_bid_ask_spread", 0.20),
            min_iv_rank=parameters.get("min_iv_rank", 20.0),
            max_iv_rank=parameters.get("max_iv_rank", 80.0)
        )
    
    def evaluate_ticker(self, ticker: str, config: LeapEntryConfig) -> TickerResult:
        """Evaluate single ticker for LEAP entry opportunity"""
        # Import the existing evaluation logic from leap_entry_strategy.py
        from leap_entry_strategy import evaluate_leap_opportunity
        
        # Execute evaluation (this would need to be refactored from the existing script)
        result = evaluate_leap_opportunity(ticker, config)
        
        return TickerResult(
            ticker=ticker,
            passed=result.get("passed", False),
            score=result.get("score"),
            classification=result.get("classification"),
            reasons=result.get("reasons", []),
            metrics=result.get("metrics", {})
        )
```

## Strategy Service Registry

```python
from typing import Dict, Type

class StrategyServiceRegistry:
    """Registry for available strategy services"""
    
    _services: Dict[str, Type[BaseStrategyService]] = {}
    
    @classmethod
    def register(cls, strategy_code: str, service_class: Type[BaseStrategyService]):
        """Register a strategy service"""
        cls._services[strategy_code] = service_class
    
    @classmethod
    def get_service(cls, strategy_code: str, db_path: str) -> BaseStrategyService:
        """Get strategy service instance"""
        if strategy_code not in cls._services:
            raise ValueError(f"Unknown strategy code: {strategy_code}")
        
        service_class = cls._services[strategy_code]
        return service_class(db_path)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """List available strategy codes"""
        return list(cls._services.keys())

# Register available strategies
StrategyServiceRegistry.register("bullish_breakout", BullishBreakoutService)
StrategyServiceRegistry.register("leap_entry", LeapEntryService)
```

## FastAPI Integration

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

router = APIRouter()

def get_db_path() -> str:
    """Get database path from configuration"""
    return "at_data.sqlite"

@router.post("/api/strategies/execute")
async def execute_strategy_sync(
    request: StrategyExecutionRequest,
    db_path: str = Depends(get_db_path)
):
    """Execute strategy synchronously"""
    try:
        # Get strategy service
        strategy_service = StrategyServiceRegistry.get_service(
            request.strategy_code, 
            db_path
        )
        
        # Create progress callback for database updates
        def progress_callback(current: int, total: int, ticker: str, 
                            result: Optional[TickerResult] = None, 
                            stage: str = "processing"):
            # Progress is automatically handled by BaseStrategyService
            pass
        
        # Execute strategy
        results = strategy_service.execute(
            tickers=request.parameters["tickers"],
            parameters=request.parameters,
            progress_callback=progress_callback
        )
        
        # Return complete results
        return {
            "run_id": results.run_id,
            "status": "completed",
            "total_evaluated": results.total_evaluated,
            "qualifying_count": len(results.qualifying_stocks),
            "execution_time_ms": results.execution_time_ms,
            "qualifying_stocks": [
                {
                    "ticker": r.ticker,
                    "score": r.score,
                    "classification": r.classification,
                    "metrics": r.metrics
                }
                for r in results.qualifying_stocks
            ],
            "summary": results.summary_metrics
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@router.get("/api/strategies/runs/{run_id}/progress")
async def get_execution_progress(
    run_id: str,
    db_path: str = Depends(get_db_path)
):
    """Get execution progress via polling"""
    try:
        db = Database(db_path)
        db.connect()
        
        # Get run status
        cur = db.conn.cursor()
        cur.execute("""
            SELECT execution_status, current_ticker, progress_percent,
                   processed_count, total_count, last_progress_update
            FROM strategy_run 
            WHERE run_id = ?
        """, (run_id,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        
        status, current_ticker, progress_percent, processed_count, total_count, last_update = row
        
        # Get recent progress
        cur.execute("""
            SELECT ticker, passed, score, classification, processed_at, processing_time_ms
            FROM strategy_execution_progress 
            WHERE run_id = ? 
            ORDER BY sequence_number DESC 
            LIMIT 10
        """, (run_id,))
        
        recent_results = [
            {
                "ticker": r[0],
                "passed": bool(r[1]),
                "score": r[2],
                "classification": r[3],
                "processed_at": r[4],
                "processing_time_ms": r[5]
            }
            for r in cur.fetchall()
        ]
        
        return {
            "run_id": run_id,
            "status": status,
            "current_ticker": current_ticker,
            "progress_percent": progress_percent or 0,
            "processed_count": processed_count or 0,
            "total_count": total_count or 0,
            "last_update": last_update,
            "recent_results": recent_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")
```

## Benefits of This Design

### 1. **Simplified Architecture**
- No subprocess management or stdout parsing
- Direct in-process execution with immediate error handling
- Callback-based progress reporting vs complex event streaming

### 2. **Database-Centric Progress**
- All progress stored in database for persistence
- Simple polling-based progress updates
- Detailed execution history and metrics

### 3. **Modular Strategy Design**
- Each strategy is a self-contained service
- Easy to add new strategies by implementing BaseStrategyService
- Clear separation of concerns between strategy logic and execution framework

### 4. **Error Resilience**
- Graceful handling of individual ticker failures
- Partial results available even if some tickers fail
- Clear error reporting and logging

### 5. **Testing and Debugging**
- Direct testing of strategy services without subprocess complexity
- Easy mocking of dependencies for unit tests
- Clear stack traces and error handling

This design provides all the functionality of the current complex system while dramatically simplifying the architecture and improving reliability.