"""
Bullish Breakout Strategy Service

Implements the bullish breakout screener as an importable service for direct FastAPI integration.
This replaces the complex subprocess execution with in-process strategy execution.
"""

import time
import statistics
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base_strategy_service import (
    BaseStrategyService, StrategyResult, StrategyExecutionSummary, ProgressCallback
)


@dataclass
class BullishBreakoutConfig:
    """Configuration for bullish breakout strategy."""
    period: str = "2y"
    interval: str = "1d"
    volume_threshold_multiple: float = 1.5  # 150% of 20-day average
    max_workers: int = 4
    min_score: int = 5  # Changed from 70 to 5 for 7-point system
    lookup_names: bool = True


@dataclass
class TickerEvaluation:
    """Internal result of ticker evaluation."""
    ticker: str
    passed: bool
    reasons: List[str]
    metrics: Dict[str, Any]


class BullishBreakoutService(BaseStrategyService):
    """Bullish Breakout Strategy Service for direct FastAPI integration."""
    
    def get_strategy_code(self) -> str:
        return "bullish_breakout"
    
    def get_strategy_name(self) -> str:
        return "Bullish Breakout Screener"
    
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
            "volume_threshold_multiple": 1.5,
            "max_workers": 4,
            "min_score": 5,
            "lookup_names": True
        }
    
    def execute(self, tickers: List[str], parameters: Dict[str, Any], 
                progress_callback: ProgressCallback) -> StrategyExecutionSummary:
        """Execute bullish breakout strategy with progress reporting."""
        start_time = time.time()
        run_id = parameters.get("run_id", f"bullish_{int(start_time)}")
        
        # Create configuration from parameters
        config = BullishBreakoutConfig(
            period=parameters.get("period", "2y"),
            interval=parameters.get("interval", "1d"),
            volume_threshold_multiple=parameters.get("volume_threshold_multiple", 1.5),
            max_workers=parameters.get("max_workers", 4),
            min_score=parameters.get("min_score", 5),
            lookup_names=parameters.get("lookup_names", True)
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
            "Starting bullish breakout screener", 
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
        passed_results.sort(key=lambda r: r.metrics.get("score", 0), reverse=True)
        
        # Convert to StrategyResult objects
        qualifying_stocks = []
        for eval_result in passed_results:
            processing_time = eval_result.metrics.get("processing_time_ms", 0)
            strategy_result = StrategyResult(
                ticker=eval_result.ticker,
                passed=eval_result.passed,
                score=eval_result.metrics.get("score", 0),
                classification=eval_result.metrics.get("recommendation"),
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
                {"ticker": r.ticker, "score": r.metrics.get("score", 0)} 
                for r in passed_results[:5]
            ],
            "average_score": round(
                sum(r.metrics.get("score", 0) for r in passed_results) / len(passed_results), 1
            ) if passed_results else 0
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
    
    def _evaluate_tickers(self, tickers: List[str], config: BullishBreakoutConfig, 
                         progress_callback: ProgressCallback) -> List[TickerEvaluation]:
        """Evaluate tickers using concurrent execution."""
        results: List[TickerEvaluation] = []
        max_workers = max(1, min(config.max_workers, len(tickers)))
        
        processed_count = 0
        passed_count = 0
        
        def evaluate_with_progress(ticker: str) -> TickerEvaluation:
            nonlocal processed_count, passed_count
            
            ticker_start_time = time.time()
            result = self._evaluate_single_ticker(ticker, config)
            processing_time_ms = int((time.time() - ticker_start_time) * 1000)
            
            # Add processing time to metrics
            result.metrics["processing_time_ms"] = processing_time_ms
            
            processed_count += 1
            if result.passed:
                passed_count += 1
            
            # DEBUG: Log the calculated metrics with SMA values and slope
            self.logger.debug(f"[METRICS_DEBUG] Calculated metrics for {ticker}: {result.metrics}")
            self.logger.debug(f"[METRICS_DEBUG] SMA10: {result.metrics.get('sma10')}, SMA50: {result.metrics.get('sma50')}, SMA200: {result.metrics.get('sma200')}")
            self.logger.debug(f"[METRICS_DEBUG] MA200 Slope Up: {result.metrics.get('ma200_slope_upward')}, Points Trend: {result.metrics.get('points_trend_direction')}")
            
            # Report ticker progress
            progress_callback.report_ticker_progress(
                ticker=ticker,
                passed=result.passed,
                score=result.metrics.get("score", 0),
                classification=result.metrics.get("recommendation", "N/A"),
                sequence_number=processed_count,
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
    
    def _evaluate_single_ticker(self, ticker: str, config: BullishBreakoutConfig) -> TickerEvaluation:
        """Evaluate a single ticker. This is the core logic from the original script."""
        try:
            # Import heavy dependencies lazily
            import pandas as pd
            import numpy as np
            import yfinance as yf
        except ImportError:
            return TickerEvaluation(ticker, False, ["missing_dependencies"], {})
        
        reasons: List[str] = []
        metrics: Dict[str, Any] = {}
        
        # Download historical data
        df = self._download_history(yf, pd, ticker, config.period, config.interval)
        if df is None or df.empty:
            return TickerEvaluation(ticker, False, ["no_data"], metrics)
        
        # Calculate indicators
        df["sma10"] = df["close"].rolling(10).mean()
        df["sma50"] = df["close"].rolling(50).mean()
        df["sma200"] = df["close"].rolling(200).mean()
        
        macd, signal, hist = self._calculate_macd(pd, df["close"])
        df["macd"] = macd
        df["macd_signal"] = signal
        df["macd_hist"] = hist
        
        df["rsi14"] = self._calculate_rsi(pd, np, df["close"], 14)
        df["vol_avg20"] = df["volume"].rolling(20).mean()
        
        # Prior highs (exclude today)
        df["high_126_prior"] = df["close"].shift(1).rolling(126).max()
        df["high_252_prior"] = df["close"].shift(1).rolling(252).max()
        
        # Need sufficient history for SMA200
        if len(df) < 200 or pd.isna(df["sma200"].iloc[-1]):
            return TickerEvaluation(ticker, False, ["insufficient_history"], metrics)
        
        last = df.iloc[-1]
        
        # Apply strategy rules and scoring
        score, passed, reasons, metrics = self._apply_strategy_rules(
            df, last, config, pd, np
        )
        
        return TickerEvaluation(ticker, passed, reasons, metrics)
    
    def _download_history(self, yf, pd, ticker: str, period: str, interval: str):
        """Download historical data with retries."""
        import time
        import random
        
        def normalize_data(df_raw):
            if df_raw is None or len(df_raw) == 0:
                return None
            df = df_raw.copy()
            cols = [str(c) for c in df.columns]
            lower = {c.lower(): c for c in cols}
            
            # Find close column
            close_col = None
            for c in ("close", "adj close", "adj_close"):
                if c in lower:
                    close_col = lower[c]
                    break
            if not close_col:
                return None
            
            # Find volume column
            vol_col = None
            for v in ("volume",):
                if v in lower:
                    vol_col = lower[v]
                    break
            if not vol_col:
                return None
            
            out = pd.DataFrame({
                "close": pd.to_numeric(df[close_col], errors="coerce"),
                "volume": pd.to_numeric(df[vol_col], errors="coerce"),
            })
            out = out.dropna()
            return out if not out.empty else None
        
        # Try downloading with retries
        for attempt in range(3):
            try:
                df = yf.download(
                    ticker,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                normalized = normalize_data(df)
                if normalized is not None:
                    return normalized
            except Exception:
                pass
            
            # Fallback to Ticker.history
            try:
                hist = yf.Ticker(ticker).history(
                    period=period, interval=interval, auto_adjust=True
                )
                normalized = normalize_data(hist)
                if normalized is not None:
                    return normalized
            except Exception:
                pass
            
            # Backoff before retry
            time.sleep(0.4 + random.random() * 0.6)
        
        return None
    
    def _calculate_macd(self, pd, series):
        """Calculate MACD indicator."""
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def _calculate_rsi(self, pd, np, series, period: int = 14):
        """Calculate RSI indicator."""
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        gain = up.ewm(alpha=1 / period, adjust=False).mean()
        loss = down.ewm(alpha=1 / period, adjust=False).mean()
        rs = gain / (loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)
    
    def _crossed_above(self, a, b) -> bool:
        """Check if series a crossed above series b."""
        if len(a) < 2 or len(b) < 2:
            return False
        prev_a, prev_b = a.iloc[-2], b.iloc[-2]
        curr_a, curr_b = a.iloc[-1], b.iloc[-1]
        if any(map(lambda x: x != x, [prev_a, prev_b, curr_a, curr_b])):  # NaN checks
            return False
        return prev_a <= prev_b and curr_a > curr_b
    
    def _detect_golden_cross(self, df, lookback_days: int = 30) -> bool:
        """
        Detect if 50-day MA recently crossed above 200-day MA (Golden Cross).
        
        Args:
            df: DataFrame with sma50 and sma200 columns
            lookback_days: How many days back to look for the cross
            
        Returns:
            True if Golden Cross occurred within lookback period
        """
        if len(df) < max(50, 200, lookback_days + 1):
            return False
            
        # Check for the cross in the last lookback_days
        for i in range(1, min(lookback_days + 1, len(df))):
            prev_idx = -(i + 1)
            curr_idx = -i
            
            if (prev_idx < -len(df) or curr_idx < -len(df)):
                continue
                
            prev_sma50 = df["sma50"].iloc[prev_idx]
            prev_sma200 = df["sma200"].iloc[prev_idx]
            curr_sma50 = df["sma50"].iloc[curr_idx]
            curr_sma200 = df["sma200"].iloc[curr_idx]
            
            # Check for NaN values
            if any(map(lambda x: x != x, [prev_sma50, prev_sma200, curr_sma50, curr_sma200])):
                continue
                
            # Golden Cross: 50-day was below or equal to 200-day, now above
            if prev_sma50 <= prev_sma200 and curr_sma50 > curr_sma200:
                return True
                
        return False
    
    def _detect_ma200_slope_upward(self, df, pd, lookback_days: int = 10) -> bool:
        """
        Detect if 200-day MA is trending upward by comparing current to 10 days ago.
        
        Args:
            df: DataFrame with sma200 column
            pd: pandas module
            lookback_days: How many days back to compare (default 10)
            
        Returns:
            True if MA(200) is sloping upward (current > 10 days ago)
        """
        if len(df) < max(200, lookback_days + 1):
            return False
            
        # Get current MA(200) and MA(200) from lookback_days ago
        current_ma200 = df["sma200"].iloc[-1]
        past_ma200 = df["sma200"].iloc[-(lookback_days + 1)]
        
        # Check for NaN values
        if pd.isna(current_ma200) or pd.isna(past_ma200):
            return False
            
        # MA(200) is sloping upward if current > past
        return current_ma200 > past_ma200
    
    def _apply_strategy_rules(self, df, last, config: BullishBreakoutConfig, pd, np):
        """Apply new 7-point scoring system."""
        reasons: List[str] = []
        score = 0
        
        # **7-Point Entry Scoring System**
        
        # 1. Moving Averages (3 points max)
        points_ma = 0
        
        # +1 if price closes above 50-day MA
        ma50_above = last["close"] > last["sma50"] if not pd.isna(last["sma50"]) else False
        if ma50_above:
            points_ma += 1
        else:
            reasons.append("price_below_50ma")
            
        # +1 if price closes above 200-day MA
        ma200_above = last["close"] > last["sma200"] if not pd.isna(last["sma200"]) else False
        if ma200_above:
            points_ma += 1
        else:
            reasons.append("price_below_200ma")
            
        # +1 if 50-day MA crosses above 200-day MA (Golden Cross)
        golden_cross = self._detect_golden_cross(df)
        if golden_cross:
            points_ma += 1
        else:
            reasons.append("no_golden_cross")
            
        score += points_ma
        
        # 2. Volume (1 point max)
        points_volume = 0
        vol = float(last["volume"])
        volavg20 = float(last["vol_avg20"]) if not pd.isna(last["vol_avg20"]) else 0.0
        
        # +1 if breakout occurs on volume > 150% of 20-day average
        volume_threshold = config.volume_threshold_multiple * volavg20
        volume_confirmed = volavg20 > 0 and (vol >= volume_threshold)
        if volume_confirmed:
            points_volume = 1
        else:
            reasons.append("volume_below_150pct_threshold")
            
        score += points_volume
        
        # 3. Momentum (2 points max)
        points_momentum = 0
        rsi = float(last["rsi14"])
        
        # +1 if RSI(14) > 50 but < 70 (shows momentum without overbought risk)
        rsi_good = 50 < rsi < 70
        if rsi_good:
            points_momentum += 1
        else:
            if rsi <= 50:
                reasons.append("rsi_below_50")
            else:
                reasons.append("rsi_above_70_overbought")
                
        # +1 if MACD line > Signal line and both > 0
        macd_above_signal = last["macd"] > last["macd_signal"] if not pd.isna(last["macd"]) and not pd.isna(last["macd_signal"]) else False
        macd_both_positive = (last["macd"] > 0 and last["macd_signal"] > 0) if not pd.isna(last["macd"]) and not pd.isna(last["macd_signal"]) else False
        macd_good = macd_above_signal and macd_both_positive
        if macd_good:
            points_momentum += 1
        else:
            if not macd_above_signal:
                reasons.append("macd_below_signal")
            if not macd_both_positive:
                reasons.append("macd_not_both_positive")
                
        score += points_momentum
        
        # 4. Trend Direction (1 point max)
        points_trend = 0
        
        # +1 if MA(200) is sloping upward (current > 10 days ago)
        ma200_slope_up = self._detect_ma200_slope_upward(df, pd)
        if ma200_slope_up:
            points_trend = 1
        else:
            reasons.append("ma200_not_sloping_up")
            
        score += points_trend
        
        # **Entry Signal:** Score ≥ 5 signals a strong buy entry
        passed = score >= config.min_score
        
        # **Exit/Caution Signals**
        exit_signals = []
        
        # Full exit if price closes below 200-day MA
        if not ma200_above:
            exit_signals.append("exit_below_200ma")
            
        # Consider trimming if RSI > 75 (overheated)
        if rsi > 75:
            exit_signals.append("trim_rsi_overheated")
            
        # **Classification/Recommendation**
        if not ma200_above:
            classification = "Exit"
        elif rsi > 75:
            classification = "Trim"
        elif score >= 6:
            classification = "Strong Buy"
        elif score == 5:
            classification = "Buy"
        elif score == 4:
            classification = "Watch"
        else:  # score <= 3
            classification = "Reduce"
            
        # Build comprehensive metrics
        metrics = self._build_new_metrics(
            df, last, vol, volavg20, rsi, config,
            points_ma, points_volume, points_momentum, points_trend, score,
            ma50_above, ma200_above, golden_cross, volume_confirmed,
            rsi_good, macd_good, ma200_slope_up, classification, exit_signals, pd
        )
        
        return score, passed, ([] if passed else reasons), metrics
    
    def _build_new_metrics(self, df, last, vol, volavg20, rsi, config,
                          points_ma, points_volume, points_momentum, points_trend, score,
                          ma50_above, ma200_above, golden_cross, volume_confirmed,
                          rsi_good, macd_good, ma200_slope_up, classification, exit_signals, pd):
        """Build comprehensive metrics dictionary for new 7-point system."""
        # Previous close for change calculation
        prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else None
        change_pct = ((float(last["close"]) - prev_close) / prev_close * 100.0) if (
            prev_close is not None and prev_close != 0
        ) else None
        
        volume_multiple = (vol / volavg20) if volavg20 and volavg20 > 0 else None
        
        return {
            # Basic price and technical data
            "close": round(float(last["close"]), 4),
            "sma10": round(float(last["sma10"]), 4) if not pd.isna(last["sma10"]) else None,
            "sma50": round(float(last["sma50"]), 4) if not pd.isna(last["sma50"]) else None,
            "sma200": round(float(last["sma200"]), 4) if not pd.isna(last["sma200"]) else None,
            "macd": round(float(last["macd"]), 6) if not pd.isna(last["macd"]) else None,
            "macd_signal": round(float(last["macd_signal"]), 6) if not pd.isna(last["macd_signal"]) else None,
            "macd_hist": round(float(last["macd_hist"]), 6) if not pd.isna(last["macd_hist"]) else None,
            "rsi14": round(rsi, 2),
            "volume": int(vol),
            "vol_avg20": int(volavg20) if volavg20 else None,
            "volume_multiple": round(volume_multiple, 2) if volume_multiple else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            
            # New 7-point scoring components
            "points_moving_averages": points_ma,
            "points_volume": points_volume,
            "points_momentum": points_momentum,
            "points_trend_direction": points_trend,
            "score": score,
            "max_score": 7,
            
            # Individual component flags
            "ma50_above": ma50_above,
            "ma200_above": ma200_above,
            "golden_cross": golden_cross,
            "volume_confirmed": volume_confirmed,
            "rsi_good_range": rsi_good,
            "macd_bullish": macd_good,
            "ma200_slope_upward": ma200_slope_up,
            
            # Classification and signals
            "recommendation": classification,
            "exit_signals": exit_signals,
            
            # Volume threshold used
            "volume_threshold_multiple": config.volume_threshold_multiple,
            "volume_threshold": round(config.volume_threshold_multiple * volavg20, 0) if volavg20 else None,
            
            # Additional context
            "entry_threshold": config.min_score,
            "system_version": "7-point"
        }
    
    def _enrich_company_names(self, results: List[TickerEvaluation], progress_callback: ProgressCallback):
        """Enrich results with company names for qualifying stocks."""
        qualifying_results = [r for r in results if r.passed]
        if not qualifying_results:
            return
        
        progress_callback.report_enrichment(
            "Looking up company names for qualifying stocks",
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