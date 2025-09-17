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
    min_volume_multiple: float = 1.0
    strict_macd_positive: bool = False
    allow_overbought: bool = False
    require_52w_high: bool = False
    max_workers: int = 4
    min_score: int = 70
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
            "min_volume_multiple": 1.0,
            "strict_macd_positive": False,
            "allow_overbought": False,
            "require_52w_high": False,
            "max_workers": 4,
            "min_score": 70,
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
            min_volume_multiple=parameters.get("min_volume_multiple", 1.0),
            strict_macd_positive=parameters.get("strict_macd_positive", False),
            allow_overbought=parameters.get("allow_overbought", False),
            require_52w_high=parameters.get("require_52w_high", False),
            max_workers=parameters.get("max_workers", 4),
            min_score=parameters.get("min_score", 70),
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
            
            # Report ticker progress
            progress_callback.report_ticker_progress(
                ticker=ticker,
                passed=result.passed,
                score=result.metrics.get("score", 0),
                classification=result.metrics.get("recommendation", "N/A"),
                sequence_number=processed_count
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
    
    def _apply_strategy_rules(self, df, last, config: BullishBreakoutConfig, pd, np):
        """Apply strategy rules and calculate score."""
        reasons: List[str] = []
        metrics: Dict[str, Any] = {}
        
        # 1) Price above SMAs
        sma_ok = (
            last["close"] > last["sma10"]
            and last["close"] > last["sma50"]
            and last["close"] > last["sma200"]
        )
        if not sma_ok:
            reasons.append("price_not_above_all_smas")
        
        # 2) MACD crossover today + histogram positive
        macd_cross = self._crossed_above(df["macd"], df["macd_signal"])
        macd_hist_pos = last["macd_hist"] > 0
        macd_above_zero = last["macd"] > 0
        macd_ok = macd_cross and macd_hist_pos and (
            macd_above_zero if config.strict_macd_positive else True
        )
        if not macd_ok:
            reasons.append("macd_not_bullish_cross")
        
        # 3) RSI momentum
        rsi = float(last["rsi14"])
        rsi_ok = rsi > 60 and (config.allow_overbought or rsi <= 80)
        if not rsi_ok:
            reasons.append("rsi_not_in_range")
        
        # 4) Volume confirmation
        vol = float(last["volume"])
        volavg20 = float(last["vol_avg20"]) if not pd.isna(last["vol_avg20"]) else 0.0
        vol_ok = volavg20 > 0 and (vol >= config.min_volume_multiple * volavg20)
        if not vol_ok:
            reasons.append("volume_below_threshold")
        
        # 5) Recent high breakout
        ref_high = last["high_252_prior"] if config.require_52w_high else last["high_126_prior"]
        high_ok = not pd.isna(ref_high) and (last["close"] > ref_high)
        if not high_ok:
            reasons.append("not_breaking_recent_high")
        
        # Calculate scoring
        points_sma = 25 if sma_ok else 0
        
        # Enhanced MACD scoring (recent crossover within 5 bars)
        cross_mask = (df["macd"].shift(1) <= df["macd_signal"].shift(1)) & (df["macd"] > df["macd_signal"])
        cross_dates = df.index[cross_mask.fillna(False)]
        recent_cross = False
        if len(cross_dates) > 0:
            last_cross_date = cross_dates[-1]
            try:
                recent_cross = df.index.get_loc(last_cross_date) >= (len(df.index) - 5)
            except Exception:
                recent_cross = False
        
        macd_scored_ok = (
            recent_cross and 
            (last["macd_hist"] > 0) and 
            (last["macd"] > 0 if config.strict_macd_positive else True)
        )
        points_macd = 20 if macd_scored_ok else 0
        points_rsi = 20 if rsi_ok else 0
        points_vol = 20 if vol_ok else 0
        points_high = 15 if high_ok else 0
        
        base_score = points_sma + points_macd + points_rsi + points_vol + points_high
        
        # Enhanced scoring metrics
        extra_score = self._calculate_extra_score(df, last, ref_high, vol, volavg20, pd)
        total_score = base_score + extra_score
        
        # Determine pass/fail
        passed = total_score >= config.min_score
        
        # Build comprehensive metrics
        metrics = self._build_comprehensive_metrics(
            df, last, ref_high, vol, volavg20, rsi, config,
            points_sma, points_macd, points_rsi, points_vol, points_high,
            total_score, extra_score, pd
        )
        
        return total_score, passed, ([] if passed else reasons), metrics
    
    def _calculate_extra_score(self, df, last, ref_high, vol, volavg20, pd):
        """Calculate additional scoring factors for entry quality."""
        extra_score = 0
        
        # Extension from SMA50
        ext_sma50 = ((last["close"] - last["sma50"]) / last["sma50"] * 100.0) if (
            last.get("sma50") and last["sma50"] > 0
        ) else None
        
        # ATR calculation (approximation using close-only)
        df["tr_close"] = (df["close"] - df["close"].shift(1)).abs()
        df["atr14"] = df["tr_close"].rolling(14).mean()
        atr = float(df["atr14"].iloc[-1]) if not pd.isna(df["atr14"].iloc[-1]) else None
        
        # Breakout move in ATR terms
        breakout_level = float(ref_high) if ref_high == ref_high else None
        breakout_move_atr = ((last["close"] - breakout_level) / atr) if (
            breakout_level and atr and atr > 0
        ) else None
        
        # Volume continuity
        vol_2day = df["volume"].tail(2).mean()
        vol_continuity_ratio = (vol_2day / volavg20) if (volavg20 and volavg20 > 0) else None
        
        # Scoring adjustments
        if ext_sma50 is not None and ext_sma50 < 12:
            extra_score += 5
        if breakout_move_atr is not None and breakout_move_atr <= 2:
            extra_score += 5
        if vol_continuity_ratio and vol_continuity_ratio >= 1.2:
            extra_score += 3
        
        return extra_score
    
    def _build_comprehensive_metrics(self, df, last, ref_high, vol, volavg20, rsi, config,
                                   points_sma, points_macd, points_rsi, points_vol, points_high,
                                   total_score, extra_score, pd):
        """Build comprehensive metrics dictionary."""
        # Previous close for change calculation
        prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else None
        change_pct = ((float(last["close"]) - prev_close) / prev_close * 100.0) if (
            prev_close is not None and prev_close != 0
        ) else None
        
        # Breakout metrics
        breakout_level = float(ref_high) if ref_high == ref_high else None
        breakout_pct = ((float(last["close"]) - breakout_level) / breakout_level * 100.0) if (
            breakout_level and breakout_level != 0
        ) else None
        
        volume_multiple = (vol / volavg20) if volavg20 else None
        
        # Risk assessment
        risk = "Low"
        if ((rsi and rsi > 75) or 
            (breakout_pct and breakout_pct > 5.0) or 
            (volume_multiple and volume_multiple > 2.5)):
            risk = "High"
        elif (rsi and rsi > 70) or (volume_multiple and volume_multiple > 1.8):
            risk = "Medium"
        
        # Recommendation
        if total_score >= 85 and risk in ("Low", "Medium"):
            recommendation = "Buy"
        elif total_score >= config.min_score:
            recommendation = "Watch"
        else:
            recommendation = "Wait"
        
        return {
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
            "ref_high": round(breakout_level, 4) if breakout_level else None,
            "require_52w_high": config.require_52w_high,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "breakout_pct": round(breakout_pct, 2) if breakout_pct is not None else None,
            "points_sma": points_sma,
            "points_macd": points_macd,
            "points_rsi": points_rsi,
            "points_volume": points_vol,
            "points_high": points_high,
            "score": total_score,
            "extra_score": extra_score,
            "risk": risk,
            "recommendation": recommendation,
            "sma10_above": bool(last["close"] > last["sma10"]) if not pd.isna(last["sma10"]) else None,
            "sma50_above": bool(last["close"] > last["sma50"]) if not pd.isna(last["sma50"]) else None,
            "sma200_above": bool(last["close"] > last["sma200"]) if not pd.isna(last["sma200"]) else None,
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