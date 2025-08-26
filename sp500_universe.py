"""
Generate S&P 500 ticker list for use with screening strategies.

Usage (PowerShell):
  python .\sp500_universe.py --output sp500_tickers.txt --source auto

Sources tried:
  - yfinance.tickers_sp500() (fast, simple if available)
  - Wikipedia (pandas.read_html on the S&P 500 companies page)

Output:
  A text file with one ticker per line, uppercased, de-duplicated and sorted.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Set


def _lazy_imports():
    import importlib

    pd = importlib.import_module("pandas")
    try:
        yf = importlib.import_module("yfinance")
    except Exception:
        yf = None
    return pd, yf


def fetch_sp500_from_yfinance() -> List[str]:
    pd, yf = _lazy_imports()
    if yf is None:
        return []
    # Some yfinance versions expose tickers_sp500()
    try:
        fn = getattr(yf, "tickers_sp500", None)
        if callable(fn):
            data = list(fn())
            return [str(x).strip().upper() for x in data if str(x).strip()]
    except Exception:
        return []
    return []


def fetch_sp500_from_wikipedia() -> List[str]:
    pd, _ = _lazy_imports()
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
    except Exception:
        return []

    for df in tables:
        try:
            # Look for a column like 'Symbol' or 'Ticker'
            for col in df.columns:
                name = str(col).strip().lower()
                if name in {"symbol", "ticker", "ticker symbol"}:
                    syms = df[col].astype(str).str.strip().tolist()
                    # Wikipedia symbols use '.'; Yahoo uses '-'
                    syms = [s.upper().replace(".", "-") for s in syms if s]
                    if syms:
                        return syms
        except Exception:
            continue
    return []


def normalize_tickers(tickers: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for t in tickers:
        t = t.strip().upper()
        if not t or t.startswith("#"):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    out.sort()
    return out


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate S&P 500 ticker list")
    parser.add_argument("--output", default="sp500_tickers.txt", help="Output file path (txt)")
    parser.add_argument(
        "--source",
        choices=["auto", "yfinance", "wikipedia"],
        default="auto",
        help="Data source to use",
    )
    args = parser.parse_args(argv)

    order = [args.source] if args.source != "auto" else ["yfinance", "wikipedia"]
    tickers: List[str] = []
    for src in order:
        if src == "yfinance":
            tickers = fetch_sp500_from_yfinance()
        elif src == "wikipedia":
            tickers = fetch_sp500_from_wikipedia()
        if tickers:
            break

    if not tickers:
        print("Failed to fetch S&P 500 tickers from available sources.", file=sys.stderr)
        return 1

    tickers = normalize_tickers(tickers)
    with open(args.output, "w", encoding="utf-8") as f:
        for t in tickers:
            f.write(f"{t}\n")
    print(f"Wrote {len(tickers)} tickers to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
