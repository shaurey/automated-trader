"""
LEAP Entry Strategy Service

Implements the LEAP entry screener as an importable service for direct FastAPI integration.
This wraps the existing leap_entry_strategy functionality in the BaseStrategyService pattern.
"""

import time
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base_strategy_service import (
    BaseStrategyService, StrategyResult, StrategyExecutionSummary, ProgressCallback
)


@dataclass
class LeapEntryConfig:
    """Configuration for LEAP entry strategy."""
    period: str = "2y"
    interval: str = "1d"
    min_score: int = 60
    max_workers: int = 4
    lookup_names: bool = True
    rsi_lower: int = 45
    rsi_upper: int = 60
    avwap_ideal_max: float = 5.0
    avwap_soft_max: float = 8.0
    avwap_penalty_threshold: float = 15.0
    avwap_penalty_points: int = 5


@dataclass
class LeapTickerEvaluation:
    """Internal result of LEAP ticker evaluation."""
    ticker: str
    passed: bool
    score: int
    classification: str
    reasons: List[str]
    metrics: Dict[str, Any]


class LeapEntryService(BaseStrategyService):
    """LEAP Entry Strategy Service for direct FastAPI integration."""
    
    def get_strategy_code(self) -> str:
        return "leap_entry"
    
    def get_strategy_name(self) -> str:
        return "LEAP Call Entry Screener"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate strategy parameters."""
        # Basic validation - can be enhanced
        required_fields = ["tickers"]
        if not all(field in parameters for field in required_fields):
            return False
        
        if not isinstance(parameters.get("tickers"), list):
            return False
            
        return True
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Return default parameters."""
        return {
            "period": "2y",
            "interval": "1d",
            "min_score": 60,
            "max_workers": 4,
            "lookup_names": True,
            "rsi_lower": 45,
            "rsi_upper": 60,
            "avwap_ideal_max": 5.0,
            "avwap_soft_max": 8.0,
            "avwap_penalty_threshold": 15.0,
            "avwap_penalty_points": 5
        }
    
    def execute(self, tickers: List[str], parameters: Dict[str, Any], 
                progress_callback: ProgressCallback) -> StrategyExecutionSummary:
        """Execute LEAP entry strategy with progress reporting."""
        start_time = time.time()
        run_id = parameters.get("run_id", f"leap_{int(start_time)}")
        
        # Create configuration from parameters
        config = LeapEntryConfig(
            period=parameters.get("period", "2y"),
            interval=parameters.get("interval", "1d"),
            min_score=parameters.get("min_score", 60),
            max_workers=parameters.get("max_workers", 4),
            lookup_names=parameters.get("lookup_names", True),
            rsi_lower=parameters.get("rsi_lower", 45),
            rsi_upper=parameters.get("rsi_upper", 60),
            avwap_ideal_max=parameters.get("avwap_ideal_max", 5.0),
            avwap_soft_max=parameters.get("avwap_soft_max", 8.0),
            avwap_penalty_threshold=parameters.get("avwap_penalty_threshold", 15.0),
            avwap_penalty_points=parameters.get("avwap_penalty_points", 5)
        )
        
        # Clean and deduplicate tickers
        tickers = list(dict.fromkeys([t.strip().upper() for t in tickers if t and t.strip()]))
        if not tickers:
            return StrategyExecutionSummary(
                run_id=run_id,
                strategy_code=self.get_strategy_code(),
                total_evaluated=0,
                qualifying_count=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                qualifying_stocks=[],
                summary_metrics={}
            )
        
        progress_callback.report_setup(
            "Starting LEAP entry screener", 
            {"total_tickers": len(tickers)}
        )
        
        # Execute strategy
        results = self._evaluate_tickers(tickers, config, progress_callback)
        
        # Enrich with company names if requested
        if config.lookup_names and results:
            self._enrich_company_names(results, progress_callback)
        
        # Separate passed and failed results
        passed_results = [r for r in results if r.passed]
        failed_results = [r for r in results if not r.passed]
        
        # Sort by score
        passed_results.sort(key=lambda r: r.score, reverse=True)
        
        # Convert to StrategyResult objects
        qualifying_stocks = []
        for eval_result in passed_results:
            processing_time = eval_result.metrics.get("processing_time_ms", 0)
            strategy_result = StrategyResult(
                ticker=eval_result.ticker,
                passed=eval_result.passed,
                score=eval_result.score,
                classification=eval_result.classification,
                reasons=eval_result.reasons,
                metrics=eval_result.metrics,
                processed_at=datetime.utcnow(),
                processing_time_ms=processing_time
            )
            qualifying_stocks.append(strategy_result)
        
        # Report completion
        progress_callback.report_completion(
            total_evaluated=len(results),
            passed=len(passed_results),
            failed=len(failed_results)
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Create summary
        summary_metrics = {
            "pass_rate_percent": round((len(passed_results) / len(results)) * 100, 1) if results else 0,
            "top_scores": [
                {"ticker": r.ticker, "score": r.score, "classification": r.classification} 
                for r in passed_results[:5]
            ],
            "average_score": round(
                sum(r.score for r in passed_results) / len(passed_results), 1
            ) if passed_results else 0,
            "prime_candidates": len([r for r in passed_results if r.classification == "prime"]),
            "watch_candidates": len([r for r in passed_results if r.classification == "watch"])
        }
        
        return StrategyExecutionSummary(
            run_id=run_id,
            strategy_code=self.get_strategy_code(),
            total_evaluated=len(results),
            qualifying_count=len(passed_results),
            execution_time_ms=execution_time_ms,
            qualifying_stocks=qualifying_stocks,
            summary_metrics=summary_metrics
        )
    
    def _evaluate_tickers(self, tickers: List[str], config: LeapEntryConfig, 
                         progress_callback: ProgressCallback) -> List[LeapTickerEvaluation]:
        """Evaluate tickers using concurrent execution."""
        results: List[LeapTickerEvaluation] = []
        max_workers = max(1, min(config.max_workers, len(tickers)))
        
        processed_count = 0
        passed_count = 0
        
        def evaluate_with_progress(ticker: str) -> LeapTickerEvaluation:
            nonlocal processed_count, passed_count
            
            ticker_start_time = time.time()
            result = self._evaluate_single_ticker(ticker, config)
            processing_time_ms = int((time.time() - ticker_start_time) * 1000)
            
            # Add processing time to metrics
            result.metrics["processing_time_ms"] = processing_time_ms
            
            processed_count += 1
            if result.passed:
                passed_count += 1
            
            # Report ticker progress with additional context
            progress_callback.report_ticker_progress(
                ticker=ticker,
                passed=result.passed,
                score=result.score,
                classification=result.classification,
                sequence_number=processed_count
            )
            
            # Enhanced progress callback to pass reasons and metrics for database storage
            if hasattr(progress_callback.callback_func, '__call__'):
                progress_callback.callback_func(
                    stage="evaluation",
                    ticker=ticker,
                    passed=result.passed,
                    score=result.score,
                    classification=result.classification,
                    sequence_number=processed_count,
                    reasons=result.reasons,
                    metrics=result.metrics
                )
            
            # Report overall progress periodically
            if processed_count % 10 == 0 or processed_count == len(tickers):
                progress_callback.report_overall_progress(
                    processed=processed_count,
                    total=len(tickers),
                    passed_so_far=passed_count
                )
            
            return result
        
        # Execute with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(evaluate_with_progress, tickers):
                results.append(result)
        
        return results
    
    def _evaluate_single_ticker(self, ticker: str, config: LeapEntryConfig) -> LeapTickerEvaluation:
        """Evaluate a single ticker using the original LEAP entry logic."""
        try:
            # Import the original LEAP evaluation function
            from leap_entry_strategy import _evaluate_ticker, LeapConfig, LeapResult
            
            # Convert our config to the original LeapConfig
            leap_config = LeapConfig(
                period=config.period,
                interval=config.interval,
                min_score=config.min_score,
                max_workers=config.max_workers,
                rsi_lower=config.rsi_lower,
                rsi_upper=config.rsi_upper,
                avwap_ideal_max=config.avwap_ideal_max,
                avwap_soft_max=config.avwap_soft_max,
                avwap_penalty_threshold=config.avwap_penalty_threshold,
                avwap_penalty_points=config.avwap_penalty_points
            )
            
            # Call the original evaluation function
            result: LeapResult = _evaluate_ticker(ticker, leap_config)
            
            # Convert to our internal format
            return LeapTickerEvaluation(
                ticker=result.ticker,
                passed=result.passed,
                score=result.score,
                classification=result.classification,
                reasons=result.reasons,
                metrics=result.metrics
            )
            
        except ImportError:
            return LeapTickerEvaluation(
                ticker=ticker,
                passed=False,
                score=0,
                classification="error",
                reasons=["missing_dependencies"],
                metrics={}
            )
        except Exception as e:
            self.logger.error(f"Error evaluating {ticker}: {e}")
            return LeapTickerEvaluation(
                ticker=ticker,
                passed=False,
                score=0,
                classification="error",
                reasons=["evaluation_error"],
                metrics={"error": str(e)}
            )
    
    def _enrich_company_names(self, results: List[LeapTickerEvaluation], progress_callback: ProgressCallback):
        """Enrich results with company names for qualifying stocks."""
        qualifying_results = [r for r in results if r.passed]
        if not qualifying_results:
            return
        
        progress_callback.report_enrichment(
            "Looking up company names for qualifying LEAP candidates",
            len(qualifying_results)
        )
        
        try:
            import yfinance as yf
            for result in qualifying_results:
                if "company_name" not in result.metrics:
                    try:
                        ticker_obj = yf.Ticker(result.ticker)
                        info = None
                        if hasattr(ticker_obj, "get_info"):
                            info = ticker_obj.get_info()
                        elif hasattr(ticker_obj, "info"):
                            info = ticker_obj.info
                        
                        name = None
                        if isinstance(info, dict):
                            name = info.get("shortName") or info.get("longName")
                        result.metrics["company_name"] = name
                    except Exception:
                        result.metrics["company_name"] = None
        except Exception:
            # If enrichment fails, continue without names
            pass