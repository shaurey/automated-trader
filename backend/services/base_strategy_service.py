"""
Base Strategy Service Classes

This module provides the foundation for strategy services that can be executed
directly within FastAPI endpoints, replacing the complex subprocess execution system.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Result of strategy execution for a single ticker."""
    ticker: str
    passed: bool
    score: float
    classification: Optional[str]
    reasons: List[str]
    metrics: Dict[str, Any]
    processed_at: datetime
    processing_time_ms: int


@dataclass
class StrategyExecutionSummary:
    """Summary of complete strategy execution."""
    run_id: str
    strategy_code: str
    total_evaluated: int
    qualifying_count: int
    execution_time_ms: int
    qualifying_stocks: List[StrategyResult]
    summary_metrics: Dict[str, Any]
    status: str = "completed"


class ProgressCallback:
    """Progress callback handler for strategy execution."""
    
    def __init__(self, callback_func: Optional[Callable] = None):
        self.callback_func = callback_func or self._default_callback
    
    def _default_callback(self, **kwargs):
        """Default no-op callback."""
        pass
    
    def report_setup(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Report setup/initialization progress."""
        self.callback_func(
            stage="setup",
            message=message,
            metadata=metadata or {}
        )
    
    def report_ticker_progress(self, ticker: str, passed: bool, score: float,
                             classification: str, sequence_number: int = 0,
                             metrics: Optional[Dict[str, Any]] = None):
        """Report progress for individual ticker evaluation."""
        self.callback_func(
            stage="evaluation",
            ticker=ticker,
            passed=passed,
            score=score,
            classification=classification,
            sequence_number=sequence_number,
            metrics=metrics or {}
        )
    
    def report_overall_progress(self, processed: int, total: int, passed_so_far: int):
        """Report overall evaluation progress."""
        progress_pct = (processed / total * 100) if total > 0 else 0
        self.callback_func(
            stage="progress",
            processed=processed,
            total=total,
            progress_percent=round(progress_pct, 1),
            passed_so_far=passed_so_far
        )
    
    def report_enrichment(self, message: str, count: int):
        """Report name enrichment progress."""
        self.callback_func(
            stage="enrichment",
            message=message,
            count=count
        )
    
    def report_completion(self, total_evaluated: int, passed: int, failed: int):
        """Report final completion with summary."""
        pass_rate = (passed / total_evaluated * 100) if total_evaluated > 0 else 0
        self.callback_func(
            stage="completed",
            message=f"Analysis complete: {passed} qualifying stocks found",
            total_evaluated=total_evaluated,
            passed=passed,
            failed=failed,
            pass_rate_percent=round(pass_rate, 1)
        )
    
    def report_error(self, message: str, error_details: Optional[Dict[str, Any]] = None):
        """Report error during execution."""
        self.callback_func(
            stage="error",
            message=message,
            error_details=error_details or {}
        )


class BaseStrategyService(ABC):
    """Abstract base class for strategy services."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_strategy_code(self) -> str:
        """Return the strategy code identifier."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the human-readable strategy name."""
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate strategy parameters."""
        pass
    
    @abstractmethod
    def execute(self, tickers: List[str], parameters: Dict[str, Any], 
                progress_callback: ProgressCallback) -> StrategyExecutionSummary:
        """Execute strategy on given tickers with progress reporting."""
        pass
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Return default parameters for this strategy."""
        return {}
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Return JSON schema for strategy parameters."""
        return {}


class StrategyServiceRegistry:
    """Registry for strategy services."""
    
    def __init__(self):
        self._services: Dict[str, BaseStrategyService] = {}
    
    def register(self, service: BaseStrategyService):
        """Register a strategy service."""
        strategy_code = service.get_strategy_code()
        self._services[strategy_code] = service
        logger.info(f"Registered strategy service: {strategy_code}")
    
    def get(self, strategy_code: str) -> Optional[BaseStrategyService]:
        """Get strategy service by code."""
        return self._services.get(strategy_code)
    
    def list_strategies(self) -> List[Dict[str, str]]:
        """List all registered strategies."""
        return [
            {
                "code": service.get_strategy_code(),
                "name": service.get_strategy_name()
            }
            for service in self._services.values()
        ]
    
    def is_registered(self, strategy_code: str) -> bool:
        """Check if strategy is registered."""
        return strategy_code in self._services


# Global registry instance
_strategy_registry: Optional[StrategyServiceRegistry] = None


def get_strategy_registry() -> StrategyServiceRegistry:
    """Get or create global strategy registry."""
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = StrategyServiceRegistry()
    return _strategy_registry