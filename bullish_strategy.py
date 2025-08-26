"""
Bullish Breakout Screener

Implements a technical analysis screener for bullish breakouts based on:
1) Price above SMA10, SMA50, SMA200.
2) MACD bullish crossover today and histogram > 0 (optionally require MACD > 0).
3) RSI(14) > 60 (and <= 80 unless --allow-overbought).
4) Volume confirmation: today's volume >= min_volume_multiple * 20d average.
5) Recent high breakout: close > prior 6-month high (optionally 52-week high).

Notes:
- Uses daily data over a 2y period to ensure sufficient history for SMA200 and highs.
- Fetches data via yfinance at runtime. Install dependencies from requirements.txt.
- Imports for heavy deps (pandas, numpy, yfinance) are performed lazily so `--help` works without them installed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ScreenerConfig:
    period: str = "2y"
    interval: str = "1d"
    min_volume_multiple: float = 1.0
    strict_macd_positive: bool = False
    allow_overbought: bool = False
    require_52w_high: bool = False
    max_workers: int = 4
    output_file: str = "bullish_breakouts.txt"
    details_file: Optional[str] = "bullish_breakouts_details.csv"


@dataclass
class TickerResult:
    ticker: str
    passed: bool
    reasons: List[str]
    metrics: Dict[str, Any]


def _lazy_imports():
    """Import heavy dependencies lazily to keep CLI responsive without installs."""
    import importlib

    pd = importlib.import_module("pandas")
    np = importlib.import_module("numpy")
    yf = importlib.import_module("yfinance")
    return pd, np, yf


def _ema(pd, series, span: int):
    return series.ewm(span=span, adjust=False).mean()


def _rsi(pd, np, series, period: int = 14):
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    gain = up.ewm(alpha=1 / period, adjust=False).mean()
    loss = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _macd(pd, series):
    ema12 = _ema(pd, series, 12)
    ema26 = _ema(pd, series, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def _crossed_above(a, b) -> bool:
    if len(a) < 2 or len(b) < 2:
        return False
    prev_a, prev_b = a.iloc[-2], b.iloc[-2]
    curr_a, curr_b = a.iloc[-1], b.iloc[-1]
    if any(map(lambda x: x != x, [prev_a, prev_b, curr_a, curr_b])):  # NaN checks
        return False
    return prev_a <= prev_b and curr_a > curr_b


def _download_history(yf, pd, ticker: str, period: str, interval: str):
    import time, random

    def _normalize(df_raw):
        if df_raw is None or len(df_raw) == 0:
            return None
        df = df_raw.copy()
        cols = [str(c) for c in df.columns]
        lower = {c.lower(): c for c in cols}
        # Pick close
        for c in ("close", "adj close", "adj_close"):
            if c in lower:
                close_col = lower[c]
                break
        else:
            return None
        # Pick volume
        for v in ("volume",):
            if v in lower:
                vol_col = lower[v]
                break
        else:
            return None
        out = pd.DataFrame({
            "close": pd.to_numeric(df[close_col], errors="coerce"),
            "volume": pd.to_numeric(df[vol_col], errors="coerce"),
        })
        out = out.dropna()
        if out.empty:
            return None
        return out

    attempts = 3
    for i in range(attempts):
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            norm = _normalize(df)
            if norm is not None:
                return norm
        except Exception:
            pass
        # Fallback: Ticker.history
        try:
            hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            norm = _normalize(hist)
            if norm is not None:
                return norm
        except Exception:
            pass
        # Backoff before next attempt
        time.sleep(0.4 + random.random() * 0.6)
    return None


def _evaluate_ticker(ticker: str, cfg: ScreenerConfig) -> TickerResult:
    try:
        pd, np, yf = _lazy_imports()
    except Exception:
        return TickerResult(ticker, False, ["missing_dependencies"], {})

    reasons: List[str] = []
    metrics: Dict[str, Any] = {}

    df = _download_history(yf, pd, ticker, cfg.period, cfg.interval)
    if df is None or df.empty:
        return TickerResult(ticker, False, ["no_data"], metrics)

    # Indicators
    df["sma10"] = df["close"].rolling(10).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    macd, signal, hist = _macd(pd, df["close"])
    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_hist"] = hist

    df["rsi14"] = _rsi(pd, np, df["close"], 14)
    df["vol_avg20"] = df["volume"].rolling(20).mean()

    # Prior highs (exclude today)
    df["high_126_prior"] = df["close"].shift(1).rolling(126).max()
    df["high_252_prior"] = df["close"].shift(1).rolling(252).max()

    # Need sufficient history for SMA200
    if len(df) < 200 or pd.isna(df["sma200"].iloc[-1]):
        return TickerResult(ticker, False, ["insufficient_history"], metrics)

    last = df.iloc[-1]

    # 1) Price above SMAs
    sma_ok = (
        last["close"] > last["sma10"]
        and last["close"] > last["sma50"]
        and last["close"] > last["sma200"]
    )
    if not sma_ok:
        reasons.append("price_not_above_all_smas")

    # 2) MACD crossover today + histogram positive (+ optional above zero)
    macd_cross = _crossed_above(df["macd"], df["macd_signal"])
    macd_hist_pos = last["macd_hist"] > 0
    macd_above_zero = last["macd"] > 0
    macd_ok = macd_cross and macd_hist_pos and (macd_above_zero if cfg.strict_macd_positive else True)
    if not macd_ok:
        reasons.append("macd_not_bullish_cross")

    # 3) RSI momentum
    rsi = float(last["rsi14"])
    rsi_ok = rsi > 60 and (cfg.allow_overbought or rsi <= 80)
    if not rsi_ok:
        reasons.append("rsi_not_in_range")

    # 4) Volume confirmation
    vol = float(last["volume"])
    volavg20 = float(last["vol_avg20"]) if not pd.isna(last["vol_avg20"]) else 0.0
    vol_ok = volavg20 > 0 and (vol >= cfg.min_volume_multiple * volavg20)
    if not vol_ok:
        reasons.append("volume_below_threshold")

    # 5) Recent high breakout (6m or 52w)
    ref_high = last["high_252_prior"] if cfg.require_52w_high else last["high_126_prior"]
    high_ok = not pd.isna(ref_high) and (last["close"] > ref_high)
    if not high_ok:
        reasons.append("not_breaking_recent_high")

    passed = sma_ok and macd_ok and rsi_ok and vol_ok and high_ok

    metrics.update(
        {
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
            "volume_multiple": round(vol / volavg20, 2) if volavg20 else None,
            "ref_high": round(float(ref_high), 4) if ref_high == ref_high else None,
            "require_52w_high": cfg.require_52w_high,
        }
    )

    return TickerResult(ticker, passed, ([] if passed else reasons), metrics)


def _read_tickers(path: Optional[str], tickers: Optional[List[str]]) -> List[str]:
    if tickers:
        return [t.strip().upper() for t in tickers if t.strip()]
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().upper() for line in f if line.strip() and not line.strip().startswith("#")]
    return []


def _write_results_txt(passed: List[TickerResult], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        for r in passed:
            f.write(f"{r.ticker}\n")


def _write_details_csv(pd, results: List[TickerResult], path: str) -> None:
    if not results:
        # create empty with header
        cols = [
            "ticker",
            "passed",
            "reason",
            "close",
            "sma10",
            "sma50",
            "sma200",
            "macd",
            "macd_signal",
            "macd_hist",
            "rsi14",
            "volume",
            "vol_avg20",
            "volume_multiple",
            "ref_high",
            "require_52w_high",
        ]
        pd.DataFrame(columns=cols).to_csv(path, index=False)
        return
    rows = []
    for r in results:
        m = r.metrics
        rows.append(
            {
                "ticker": r.ticker,
                "passed": r.passed,
                "reason": "" if r.passed else ";".join(r.reasons),
                **m,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def run_screener(
    tickers: Iterable[str],
    cfg: Optional[ScreenerConfig] = None,
) -> Tuple[List[TickerResult], List[TickerResult]]:
    cfg = cfg or ScreenerConfig()
    # Concurrency for I/O-bound downloads
    from concurrent.futures import ThreadPoolExecutor

    tickers = list(dict.fromkeys([t.strip().upper() for t in tickers if t and t.strip()]))
    results: List[TickerResult] = []
    if not tickers:
        return [], []

    max_workers = max(1, min(cfg.max_workers, len(tickers)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in ex.map(lambda sym: _evaluate_ticker(sym, cfg), tickers):
            results.append(res)
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    return passed, failed


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bullish breakout screener")
    parser.add_argument("--tickers", nargs="*", help="Tickers to screen (space-separated)")
    parser.add_argument("--tickers-file", help="Path to a text file with one ticker per line", default=None)
    parser.add_argument("--output", help="Output file for passed tickers", default="bullish_breakouts.txt")
    parser.add_argument("--details", help="CSV path for detailed metrics (set to 'none' to skip)", default="bullish_breakouts_details.csv")
    parser.add_argument("--universe", choices=["sp500", "dow30", "nasdaq"], default="sp500", help="Universe to scan when no tickers provided")
    parser.add_argument("--max-workers", type=int, default=4, help="Max concurrent downloads (reduce if you hit 401/429)")

    parser.add_argument("--min-volume-multiple", type=float, default=1.0, help="Minimum multiple of 20d avg volume (e.g., 1.0, 1.5)")
    parser.add_argument("--strict-macd", action="store_true", help="Require MACD > 0 in addition to crossover + positive histogram")
    parser.add_argument("--allow-overbought", action="store_true", help="Allow RSI > 80")
    parser.add_argument("--require-52w-high", action="store_true", help="Require 52-week high breakout instead of prior 6-month high")
    parser.add_argument("--period", default="2y", help="Data period for yfinance (default 2y)")
    parser.add_argument("--interval", default="1d", help="Data interval for yfinance (default 1d)")

    args = parser.parse_args(argv)

    tickers = _read_tickers(args.tickers_file, args.tickers)
    if not tickers:
        # Load a predefined universe
        try:
            pd, _, yf = _lazy_imports()
            if args.universe == "sp500" and hasattr(yf, "tickers_sp500"):
                tickers = list(yf.tickers_sp500())
            elif args.universe == "dow30" and hasattr(yf, "tickers_dow"):
                tickers = list(yf.tickers_dow())
            elif args.universe == "nasdaq" and hasattr(yf, "tickers_nasdaq"):
                # Warning: this is very large and may be slow
                tickers = list(yf.tickers_nasdaq())
            else:
                print("Could not load universe tickers. Please provide --tickers or --tickers-file.")
                return 2
        except Exception:
            print("Failed to load universe list. Provide --tickers or --tickers-file.")
            return 2

    cfg = ScreenerConfig(
        period=args.period,
        interval=args.interval,
        min_volume_multiple=args.min_volume_multiple,
        strict_macd_positive=args.strict_macd,
        allow_overbought=args.allow_overbought,
        require_52w_high=args.require_52w_high,
        max_workers=max(1, args.max_workers),
        output_file=args.output,
        details_file=(None if (str(args.details).lower() == "none") else args.details),
    )

    passed, failed = run_screener(tickers, cfg)

    # Write outputs
    _write_results_txt(passed, cfg.output_file)
    try:
        pd, _, _ = _lazy_imports()
        if cfg.details_file:
            _write_details_csv(pd, passed + failed, cfg.details_file)
    except Exception:
        # If pandas not installed, silently skip details
        pass

    print(f"Evaluated {len(tickers)} tickers. Passed: {len(passed)}. Details -> {cfg.details_file or 'skipped'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
