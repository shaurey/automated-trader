"""
LEAP Call Entry Screener

Identifies favorable underlying conditions for entering longer-dated (LEAP) call options.
Focus: capture early / actionable resumption of an uptrend or constructive basing pullback
while avoiding extended, late, or structurally weak situations.

Core Concepts Implemented:
- Trend Health: 200 SMA slope non-negative.
- Value Zone: Price proximity to SMA50 (controlled pullback) or near SMA200 support.
- Confluence: SMA50 within 3% of SMA200 (compression / base maturity).
- RSI Momentum Turn: RSI(14) crossing back above a lower bound (default 45) and still < upper bound (default 60).
- Accumulation: At least 2 accumulation days (up close with higher volume) last 10 sessions & balanced volume.
- Volatility Contraction: 20-day HV contracting vs prior window; ATR% acceptable.
- Relative Strength Turn: Stock/SPY ratio short EMA > long EMA.
- Bullish Divergence (optional bonus): Price lower low vs prior swing with higher RSI.
- AVWAP Distance: Anchored VWAP from initial breakout; distance influences score (bonus if controlled, penalty if extended).
- Suggested Stop: Structural (recent swing low) & ATR blend.

Scoring (max 100 after capping):
 Trend health (200 slope >=0)........15
 Value zone or near 200..............12
 Confluence (50 ~ 200)................8
 RSI turn............................15
 Accumulation + volume balance.......10
 Volatility contraction..............10
 Relative strength improving.........10
 Bullish divergence....................5
 ATR% acceptable......................8
 Value zone & RSI synergy.............7
 AVWAP distance (0-5%:+5,5-8%:+2,>15%:-5)

CLI Usage (examples):
 python leap_entry_strategy.py --tickers AAPL MSFT NVDA
 python leap_entry_strategy.py --tickers-file portfolio_66.txt --min-score 70

Outputs:
 - Text summary (default leap_entries.txt)
 - Detailed CSV (default leap_entries_details.csv)

Dependencies: pandas, numpy, yfinance (see requirements.txt)
"""
from __future__ import annotations

import argparse
import os
import sys
import math
import statistics
import time
import concurrent.futures
import traceback
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Iterable
from db import Database  # new import
import sqlite3
import time as _time  # for DB retry backoff

# Import ProgressReporter for real-time progress tracking
try:
    from backend.services.progress_reporter import ProgressReporter
except ImportError:
    # Fallback for when running standalone without backend
    class ProgressReporter:
        def __init__(self): pass
        def report_progress(self, *args, **kwargs): pass
        def report_ticker_progress(self, *args, **kwargs): pass
        def report_error(self, *args, **kwargs): pass

# ------------------------------- Data Classes -------------------------------

@dataclass
class LeapConfig:
    period: str = "2y"
    interval: str = "1d"
    min_score: int = 60
    max_workers: int = 4
    output_file: str = "leap_entries.txt"
    details_file: Optional[str] = "leap_entries_details.csv"
    lookup_names: bool = True
    rsi_lower: int = 45
    rsi_upper: int = 60
    # AVWAP thresholds
    avwap_ideal_max: float = 5.0
    avwap_soft_max: float = 8.0
    avwap_penalty_threshold: float = 15.0
    avwap_penalty_points: int = 5

@dataclass
class LeapResult:
    ticker: str
    score: int
    classification: str
    passed: bool
    metrics: Dict[str, Any]
    reasons: List[str]

# ------------------------------- Lazy Imports -------------------------------

def _lazy():
    import importlib
    pd = importlib.import_module("pandas")
    np = importlib.import_module("numpy")
    yf = importlib.import_module("yfinance")
    return pd, np, yf

# ------------------------------- Indicators ---------------------------------

def _ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def _rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    gain = up.ewm(alpha=1/period, adjust=False).mean()
    loss = down.ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, math.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def _slope(series, lookback=20):
    import numpy as np
    if len(series) < lookback:
        return None
    y = series.tail(lookback).values
    x = np.arange(len(y))
    num = (x - x.mean()) @ (y - y.mean())
    den = ((x - x.mean())**2).sum()
    if den == 0:
        return None
    return num / den

# ---------------------------- Data Acquisition ------------------------------

def _download_history(yf, pd, ticker: str, period: str, interval: str):
    import time, random
    def _normalize(df_raw):
        if df_raw is None or len(df_raw) == 0:
            return None
        df = df_raw.copy()
        df.columns = [c.lower() for c in df.columns]
        if "close" not in df.columns and "adj close" in df.columns:
            df["close"] = df["adj close"]
        needed = {"open", "high", "low", "close", "volume"}
        if not needed.issubset(df.columns):
            return None
        out = df[list(needed)].apply(pd.to_numeric, errors="coerce").dropna()
        return out if not out.empty else None
    for _ in range(3):
        try:
            raw = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            norm = _normalize(raw)
            if norm is not None:
                return norm
        except Exception:
            pass
        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            norm = _normalize(hist)
            if norm is not None:
                return norm
        except Exception:
            pass
        time.sleep(0.4 + random.random()*0.6)
    return None

# ---------------------------- Core Evaluation -------------------------------

def _evaluate_ticker(ticker: str, cfg: LeapConfig) -> LeapResult:
    try:
        pd, np, yf = _lazy()
    except Exception:
        return LeapResult(ticker, 0, "error", False, {}, ["missing_dependencies"])

    df = _download_history(yf, pd, ticker, cfg.period, cfg.interval)
    if df is None or len(df) < 220:  # need enough for SMA200 slope
        return LeapResult(ticker, 0, "insufficient", False, {}, ["insufficient_history"])

    # Moving averages
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma150"] = df["close"].rolling(150).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    if pd.isna(df["sma200"].iloc[-1]):
        return LeapResult(ticker, 0, "insufficient", False, {}, ["insufficient_history"])

    # RSI
    df["rsi14"] = _rsi(df["close"])

    # True ATR
    df["prev_close"] = df["close"].shift(1)
    tr_parts = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - df["prev_close"]).abs(),
        (df["low"] - df["prev_close"]).abs(),
    ], axis=1)
    df["true_range"] = tr_parts.max(axis=1)
    df["atr14"] = df["true_range"].rolling(14).mean()

    # Prior highs to anchor breakout determination
    df["high_126_prior"] = df["close"].shift(1).rolling(126).max()

    # Relative strength vs SPY
    try:
        spy = yf.download("SPY", period=cfg.period, interval=cfg.interval, auto_adjust=True, progress=False, threads=False)
        if not spy.empty:
            rs = (df["close"] / spy["Close"]).dropna()
            df.loc[rs.index, "rs"] = rs
            df["rs_ema10"] = _ema(df["rs"], 10)
            df["rs_ema20"] = _ema(df["rs"], 20)
    except Exception:
        pass

    last = df.iloc[-1]

    # Trend health
    slope_200 = _slope(df["sma200"], 20)
    trend_ok = slope_200 is not None and slope_200 >= 0

    # Distances
    dist_50_pct = ((last["close"] - last["sma50"]) / last["sma50"] * 100) if last["sma50"] and last["sma50"] > 0 else None
    dist_200_pct = ((last["close"] - last["sma200"]) / last["sma200"] * 100) if last["sma200"] and last["sma200"] > 0 else None
    value_zone = dist_50_pct is not None and -5 <= dist_50_pct <= 2
    near_200 = dist_200_pct is not None and -4 <= dist_200_pct <= 4
    confluence = (last["sma50"] and last["sma200"] and abs((last["sma50"] - last["sma200"]) / last["sma200"]) <= 0.03)

    # RSI turn
    rsi = float(last["rsi14"])
    recent_rsi_slice = df["rsi14"].iloc[-6:-1]
    rsi_turn = (rsi >= cfg.rsi_lower and rsi <= cfg.rsi_upper and (recent_rsi_slice.min() < cfg.rsi_lower))

    # Bullish divergence (simplified)
    divergence = False
    if len(df) >= 40:
        window = df.tail(35)
        low1_idx = window["close"].idxmin()
        prior_segment = window.loc[:low1_idx]
        if len(prior_segment) > 5:
            low2_idx = prior_segment["close"].idxmin()
            if low2_idx != low1_idx:
                if window.loc[low1_idx, "close"] < window.loc[low2_idx, "close"] and window.loc[low1_idx, "rsi14"] > window.loc[low2_idx, "rsi14"]:
                    divergence = True

    # Accumulation / volume balance
    acc_days = 0
    vol_up = 0
    vol_down = 0
    for i in range(1, 11):  # last 10 bars
        c0 = df["close"].iloc[-(i+1)]
        c1 = df["close"].iloc[-i]
        v1 = df["volume"].iloc[-i]
        if c1 > c0:
            vol_up += v1
            if v1 > df["volume"].iloc[-(i+1)]:
                acc_days += 1
        else:
            vol_down += v1
    vol_balance_ok = (vol_up > 0 and vol_down <= 1.3 * vol_up)
    accumulation_ok = acc_days >= 2

    # Volatility contraction (HV20 vs previous 20)
    ret = df["close"].pct_change()
    hv1 = ret.tail(20).std()
    hv2 = ret.tail(40).head(20).std() if len(ret) >= 40 else None
    vol_contract = (hv1 is not None and hv2 is not None and hv1 < hv2)

    atr = float(last["atr14"]) if not math.isnan(last["atr14"]) else None
    atr_pct = (atr / last["close"] * 100) if atr else None
    atr_ok = atr_pct is not None and atr_pct <= 6

    # Relative strength improvement
    rs_ok = False
    if "rs_ema10" in df.columns and "rs_ema20" in df.columns:
        rs_ok = last.get("rs_ema10") and last.get("rs_ema20") and last["rs_ema10"] > last["rs_ema20"]

    # Breakout anchor for AVWAP
    pivot_series = df["high_126_prior"]
    breakout_mask = df["close"] > pivot_series
    bk_idx = df.index[breakout_mask.fillna(False)]
    if len(bk_idx):
        anchor_date = bk_idx[0]
    else:
        anchor_date = df.index[-15] if len(df) > 15 else df.index[0]

    anchor_loc = df.index.get_loc(anchor_date)
    sub = df.iloc[anchor_loc:].copy()
    sub["typical_price"] = (sub["high"] + sub["low"] + sub["close"]) / 3.0
    sub["tpv"] = sub["typical_price"] * sub["volume"]
    cum_tpv = sub["tpv"].cumsum()
    cum_vol = sub["volume"].cumsum()
    anchored_vwap = (cum_tpv / cum_vol).iloc[-1] if cum_vol.iloc[-1] != 0 else None
    avwap_distance_pct = ((last["close"] - anchored_vwap) / anchored_vwap * 100.0) if anchored_vwap else None

    # Suggested stop (structure vs ATR)
    swing_low = df["close"].tail(8).min()
    suggested_stop = None
    if atr and atr_ok:
        candidate = last["close"] - 1.8 * atr
        suggested_stop = max(candidate, swing_low * 0.995)
        if suggested_stop >= last["close"]:
            suggested_stop = swing_low * 0.98
    else:
        suggested_stop = swing_low * 0.98

    # Scoring components
    score = 0
    if trend_ok: score += 15
    if value_zone or near_200: score += 12
    if confluence: score += 8
    if rsi_turn: score += 15
    if accumulation_ok and vol_balance_ok: score += 10
    if vol_contract: score += 10
    if rs_ok: score += 10
    if divergence: score += 5
    if atr_ok: score += 8
    if value_zone and rsi_turn: score += 7
    # AVWAP distance scoring
    avwap_points = 0
    if avwap_distance_pct is not None:
        if 0 <= avwap_distance_pct <= cfg.avwap_ideal_max:
            avwap_points = 5
        elif avwap_distance_pct <= cfg.avwap_soft_max:
            avwap_points = 2
        elif avwap_distance_pct > cfg.avwap_penalty_threshold:
            avwap_points = -cfg.avwap_penalty_points
    score += avwap_points

    # Cap and floor
    score = max(0, min(100, score))

    passed = score >= cfg.min_score
    classification = "prime" if score >= (cfg.min_score + 15) else ("watch" if passed else "reject")

    reasons: List[str] = []
    if not passed:
        if not trend_ok: reasons.append("trend_down")
        if not (value_zone or near_200): reasons.append("not_value_zone")
        if not rsi_turn: reasons.append("no_rsi_turn")
        if not (accumulation_ok and vol_balance_ok): reasons.append("weak_accumulation")

    metrics: Dict[str, Any] = {
        "close": round(float(last["close"]),2),
        "sma50": round(float(last["sma50"]),2) if not math.isnan(last["sma50"]) else None,
        "sma150": round(float(last["sma150"]),2) if not math.isnan(last["sma150"]) else None,
        "sma200": round(float(last["sma200"]) ,2) if not math.isnan(last["sma200"]) else None,
        "dist_50_pct": round(dist_50_pct,2) if dist_50_pct is not None else None,
        "dist_200_pct": round(dist_200_pct,2) if dist_200_pct is not None else None,
        "value_zone": value_zone,
        "near_200": near_200,
        "confluence": confluence,
        "rsi14": round(rsi,2),
        "rsi_turn": rsi_turn,
        "acc_days": acc_days,
        "vol_balance_ok": vol_balance_ok,
        "vol_contract": vol_contract,
        "rs_ok": rs_ok,
        "divergence": divergence,
        "atr14": round(atr,4) if atr else None,
        "atr_pct": round(atr_pct,2) if atr_pct else None,
        "slope_200": slope_200,
        "anchored_vwap": round(float(anchored_vwap),4) if anchored_vwap else None,
        "avwap_distance_pct": round(avwap_distance_pct,2) if avwap_distance_pct is not None else None,
        "anchor_date": anchor_date.strftime("%Y-%m-%d") if hasattr(anchor_date, "strftime") else None,
        "suggested_stop": round(suggested_stop,2) if suggested_stop else None,
        "avwap_points": avwap_points,
        "score": score,
        "classification": classification,
    }

    return LeapResult(ticker, score, classification, passed, metrics, reasons)

# ---------------------------- I/O & Reporting -------------------------------

def _read_tickers(path: Optional[str], tickers: Optional[List[str]]) -> List[str]:
    if tickers:
        return [t.strip().upper() for t in tickers if t.strip()]
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip().upper() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    return []

def _load_instruments_from_db(db_path: Optional[str]) -> List[str]:
    if not db_path:
        return []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        rows = cur.execute("SELECT ticker FROM instruments WHERE active=1 ORDER BY ticker").fetchall()
        conn.close()
        return [r[0].upper() for r in rows]
    except Exception:
        return []

def _write_text(results: List[LeapResult], path: str):
    def fmt(v, nd=2, prefix="", suffix=""):
        if v is None: return "n/a"
        try:
            return f"{prefix}{round(float(v), nd)}{suffix}"
        except Exception:
            return str(v)
    with open(path, "w", encoding="utf-8") as f:
        f.write("LEAP Entry Screener Results\n")
        f.write("============================\n\n")
        passed = [r for r in results if r.passed]
        if not passed:
            f.write("No qualifying candidates.\n")
            return
        for r in sorted(passed, key=lambda x: x.score, reverse=True):
            m = r.metrics
            f.write(
                f"{r.ticker}  Score:{r.score}  Class:{m.get('classification')}  Close:{fmt(m.get('close'),2,'$')}  "
                f"RSI:{fmt(m.get('rsi14'),2)}  RSI_Turn:{m.get('rsi_turn')}  ValueZone:{m.get('value_zone')}  Near200:{m.get('near_200')}\n"
            )
            f.write(
                f"  MAs: SMA50:{fmt(m.get('sma50'),2,'$')}  SMA150:{fmt(m.get('sma150'),2,'$')}  SMA200:{fmt(m.get('sma200'),2,'$')}  Slope200:{m.get('slope_200')}\n"
            )
            f.write(
                f"  Dist%: 50={fmt(m.get('dist_50_pct'))}%  200={fmt(m.get('dist_200_pct'))}%  Confluence:{m.get('confluence')}  RS_OK:{m.get('rs_ok')}  Divergence:{m.get('divergence')}\n"
            )
            f.write(
                f"  Acc:{m.get('acc_days')}  VolBal:{m.get('vol_balance_ok')}  VolContract:{m.get('vol_contract')}  ATR:{fmt(m.get('atr14'),4)}  ATR%:{fmt(m.get('atr_pct'))}\n"
            )
            f.write(
                f"  AVWAP:{fmt(m.get('anchored_vwap'),2,'$')}  Dist:{fmt(m.get('avwap_distance_pct'))}%  Anchor:{m.get('anchor_date')}  AVWAPpts:{m.get('avwap_points')}\n"
            )
            f.write(
                f"  Stop:{fmt(m.get('suggested_stop'),2,'$')}  ScoreComponents: value_zone={m.get('value_zone')} rsi_turn={m.get('rsi_turn')} avwap_pts={m.get('avwap_points')}\n\n"
            )

def _write_csv(pd, results: List[LeapResult], path: str):
    if not results:
        cols = [
            "ticker","score","classification","passed","reasons","close","sma50","sma150","sma200","dist_50_pct","dist_200_pct","value_zone","near_200","confluence","rsi14","rsi_turn","acc_days","vol_balance_ok","vol_contract","rs_ok","divergence","atr14","atr_pct","slope_200","anchored_vwap","avwap_distance_pct","anchor_date","suggested_stop","avwap_points"
        ]
        pd.DataFrame(columns=cols).to_csv(path, index=False)
        return
    # Sort by classification priority then descending score
    class_rank = {"prime": 0, "watch": 1, "reject": 2, "insufficient": 3, "error": 4}
    sorted_results = sorted(
        results,
        key=lambda r: (class_rank.get(r.classification, 99), -r.score, r.ticker)
    )
    rows = []
    for r in sorted_results:
        m = r.metrics
        rows.append({
            "ticker": r.ticker,
            "score": r.score,
            "classification": r.classification,
            "passed": r.passed,
            "reasons": "" if r.passed else ";".join(r.reasons),
            **m,
        })
    pd.DataFrame(rows).to_csv(path, index=False)

# ------------------------------ Runner --------------------------------------

def run_leap_screener(tickers: Iterable[str], cfg: Optional[LeapConfig] = None) -> List[LeapResult]:
    cfg = cfg or LeapConfig()
    
    # Initialize progress reporter
    progress_reporter = ProgressReporter()
    
    tickers = list(dict.fromkeys([t.strip().upper() for t in tickers if t and t.strip()]))
    if not tickers:
        return []
    
    progress_reporter.report_progress("setup", "Starting LEAP entry screener", {"total_tickers": len(tickers)})
    
    from concurrent.futures import ThreadPoolExecutor
    results: List[LeapResult] = []
    max_workers = max(1, min(cfg.max_workers, len(tickers)))
    
    # Track progress during ticker evaluation
    processed_count = 0
    passed_count = 0
    
    def evaluate_with_progress(ticker: str) -> LeapResult:
        nonlocal processed_count, passed_count
        result = _evaluate_ticker(ticker, cfg)
        processed_count += 1
        if result.passed:
            passed_count += 1
            
        # Report progress for each ticker
        progress_reporter.report_ticker_progress(
            ticker,
            result.passed,
            result.score,
            f"Score: {result.score}/100, Classification: {result.classification}"
        )
        
        # Report overall progress every 10 tickers or on completion
        if processed_count % 10 == 0 or processed_count == len(tickers):
            progress_pct = (processed_count / len(tickers)) * 100
            progress_reporter.report_progress(
                "evaluation",
                f"Evaluated {processed_count}/{len(tickers)} tickers",
                {
                    "processed": processed_count,
                    "total": len(tickers),
                    "progress_pct": round(progress_pct, 1),
                    "passed_so_far": passed_count
                }
            )
        
        return result
    
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in ex.map(evaluate_with_progress, tickers):
            results.append(res)
    
    # Report final results
    passed_results = [r for r in results if r.passed]
    progress_reporter.report_progress(
        "analysis_complete",
        f"LEAP analysis complete: {len(passed_results)} candidates found",
        {
            "total_evaluated": len(results),
            "passed": len(passed_results),
            "failed": len(results) - len(passed_results),
            "pass_rate_pct": round((len(passed_results) / len(results)) * 100, 1) if results else 0,
            "top_candidates": [{"ticker": r.ticker, "score": r.score, "classification": r.classification} for r in sorted(passed_results, key=lambda x: x.score, reverse=True)[:5]]
        }
    )
    
    # Optionally lookup names (can be added later similar to bullish strategy)
    return results

# ------------------------------ CLI -----------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="LEAP call entry screener")
    parser.add_argument("--tickers", nargs="*", help="Tickers (space separated)")
    parser.add_argument("--tickers-file", help="File with tickers (one per line)")
    parser.add_argument("--universe", choices=["sp500","dow30","nasdaq"], default="sp500", help="Universe if no tickers supplied")
    parser.add_argument("--period", default="2y", help="Data period (default 2y)")
    parser.add_argument("--interval", default="1d", help="Data interval (default 1d)")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum score to pass")
    parser.add_argument("--output", default="leap_entries.txt", help="Summary output path")
    parser.add_argument("--details", default="leap_entries_details.csv", help="Detailed CSV path (use 'none' to skip)")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--rsi-lower", type=int, default=45)
    parser.add_argument("--rsi-upper", type=int, default=60)
    parser.add_argument("--avwap-ideal-max", type=float, default=5.0)
    parser.add_argument("--avwap-soft-max", type=float, default=8.0)
    parser.add_argument("--avwap-penalty-threshold", type=float, default=15.0)
    parser.add_argument("--avwap-penalty-points", type=int, default=5)
    parser.add_argument("--db-path", help="Path to sqlite database file for logging runs")

    args = parser.parse_args(argv)

    tickers = _read_tickers(args.tickers_file, args.tickers)
    if not tickers:
        db_universe = _load_instruments_from_db(args.db_path)
        if db_universe:
            tickers = db_universe
            print(f"Loaded {len(tickers)} tickers from DB instruments table.")
        else:
            # Attempt universe load through yfinance helper lists
            try:
                pd, _, yf = _lazy()
                if args.universe == "sp500" and hasattr(yf, "tickers_sp500"):
                    tickers = list(yf.tickers_sp500())
                elif args.universe == "dow30" and hasattr(yf, "tickers_dow"):
                    tickers = list(yf.tickers_dow())
                elif args.universe == "nasdaq" and hasattr(yf, "tickers_nasdaq"):
                    tickers = list(yf.tickers_nasdaq())
                else:
                    print("Could not load universe; provide --tickers or --tickers-file.")
                    return 2
            except Exception:
                print("Failed to load universe list and DB instruments empty; provide tickers explicitly.")
                return 2

    cfg = LeapConfig(
        period=args.period,
        interval=args.interval,
        min_score=max(0, min(100, args.min_score)),
        max_workers=max(1, args.max_workers),
        output_file=args.output,
        details_file=(None if str(args.details).lower() == 'none' else args.details),
        rsi_lower=args.rsi_lower,
        rsi_upper=args.rsi_upper,
        avwap_ideal_max=args.avwap_ideal_max,
        avwap_soft_max=args.avwap_soft_max,
        avwap_penalty_threshold=args.avwap_penalty_threshold,
        avwap_penalty_points=args.avwap_penalty_points,
    )

    # Run evaluation
    results = run_leap_screener(tickers, cfg)

    # Optional DB logging (mirrors bullish strategy approach)
    run_id: Optional[str] = None
    if args.db_path:
        try:
            db = Database(args.db_path)
            # Skip schema DDL on each run to minimize lock contention
            db.connect(skip_schema=True)
            # Set busy timeout to mitigate locking if backend holds write locks briefly
            try:
                if db.conn:
                    db.conn.execute("PRAGMA busy_timeout=5000")
            except Exception:
                pass

            params_dict = {}
            for k, v in vars(args).items():
                if k not in ("db_path", "tickers_file"):
                    params_dict[k] = v

            # Retry wrapper for operations that can raise 'database is locked'
            def _retry(op_name, func, *f_args, **f_kwargs):
                attempts = 5
                delay = 0.4
                for attempt in range(1, attempts + 1):
                    try:
                        return func(*f_args, **f_kwargs)
                    except Exception as e:  # noqa: BLE001
                        msg = str(e).lower()
                        if 'database is locked' in msg and attempt < attempts:
                            print(f"[DB] {op_name} locked (attempt {attempt}/{attempts}) retrying in {delay:.1f}s")
                            _time.sleep(delay)
                            delay *= 1.6
                            continue
                        raise
                return None

            # Start run with retry
            try:
                run_id = _retry(
                    'start_run',
                    db.start_run,
                    strategy_code='leap_entry',
                    version='1.0',
                    params=params_dict,
                    universe_source=(args.tickers_file if args.tickers_file else 'list'),
                    universe_size=len(tickers),
                    min_score=cfg.min_score,
                )
            except Exception as e:  # noqa: BLE001
                # Fallback: attempt a one-off direct connection just for start_run
                print(f"[DB] start_run failed: {e}")
                try:
                    tmp = Database(args.db_path)
                    tmp.connect(skip_schema=True)
                    run_id = tmp.start_run(
                        strategy_code='leap_entry',
                        version='1.0',
                        params=params_dict,
                        universe_source=(args.tickers_file if args.tickers_file else 'list'),
                        universe_size=len(tickers),
                        min_score=cfg.min_score,
                    )
                    tmp.conn.close()
                    print(f"[DB] start_run fallback succeeded run_id={run_id}")
                except Exception as e2:  # noqa: BLE001
                    print(f"[DB] start_run fallback failed: {e2}")
                    run_id = None

            # Log results
            if run_id:
                for r in results:
                    try:
                        try:
                            _retry(
                                'log_result',
                                db.log_result,
                                run_id=run_id,
                                strategy_code='leap_entry',
                                ticker=r.ticker,
                                passed=r.passed,
                                score=r.score,
                                classification=r.classification,
                                reasons=r.reasons,
                                metrics=r.metrics,
                            )
                        except Exception as e_inner:  # noqa: BLE001
                            # Fallback per-row connection
                            if 'database is locked' in str(e_inner).lower():
                                try:
                                    tmp = Database(args.db_path)
                                    tmp.connect(skip_schema=True)
                                    tmp.log_result(
                                        run_id=run_id,
                                        strategy_code='leap_entry',
                                        ticker=r.ticker,
                                        passed=r.passed,
                                        score=r.score,
                                        classification=r.classification,
                                        reasons=r.reasons,
                                        metrics=r.metrics,
                                    )
                                    if tmp.conn:
                                        tmp.conn.close()
                                    print(f"[DB] log_result fallback {r.ticker} ok")
                                except Exception as e_f:  # noqa: BLE001
                                    print(f"[DB] log_result fallback failed {r.ticker}: {e_f}")
                            else:
                                raise
                    except Exception as e:  # noqa: BLE001
                        print(f"[DB] log_result error {r.ticker}: {e}")
                try:
                    try:
                        _retry('finalize_run', db.finalize_run, run_id)
                    except Exception as fin_e:  # noqa: BLE001
                        if 'database is locked' in str(fin_e).lower():
                            tmp = Database(args.db_path)
                            tmp.connect(skip_schema=True)
                            tmp.finalize_run(run_id)
                            if tmp.conn:
                                tmp.conn.close()
                            print("[DB] finalize_run fallback ok")
                        else:
                            raise
                except Exception as e:  # noqa: BLE001
                    print(f"[DB] finalize_run error: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[DB] run logging disabled: {e}")

    # Write text summary
    _write_text(results, cfg.output_file)
    # Write CSV details
    try:
        pd, _, _ = _lazy()
        if cfg.details_file:
            _write_csv(pd, results, cfg.details_file)
    except Exception:
        pass

    passed = sum(r.passed for r in results)
    print(f"Evaluated {len(results)} symbols. Passed: {passed}. Details -> {cfg.details_file or 'skipped'} RunID -> {run_id or 'n/a'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
