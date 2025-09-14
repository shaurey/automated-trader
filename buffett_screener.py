#!/usr/bin/env python3
"""
Buffett-Style Stock Screener (Python)
------------------------------------
Fetches fundamentals with yfinance (and optionally Wikipedia for S&P500 universe)
and filters for Buffett-aligned criteria: quality, financial strength, valuation,
stability, and margin-of-safety proxies.

Usage examples:
  # Screen S&P 500 with default filters
  python buffett_screener.py --universe sp500

  # Screen a custom list
  python buffett_screener.py --universe-file tickers.txt

  # Relax some thresholds
  python buffett_screener.py --universe sp500 --min_roe 12 --max_de 0.8 --max_pe 22 --output results.csv

Notes:
- yfinance data quality can vary across tickers (missing/None). The script handles
  missing fields gracefully (filters will fail safe).
- Intrinsic value is NOT computed here. Margin-of-safety is approximated using
  historical multiples vs current and optional external fair-value if present.
- For best results, manually review surviving tickers (annual reports, moat, management).

Requirements:
  pip install yfinance pandas numpy requests lxml beautifulsoup4

Author: Rohit Gupta
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import math
import sqlite3
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import yfinance as yf

# --------- Helpers ---------
def safe_div(a, b):
    try:
        if b is None or b == 0 or (isinstance(b, (int, float)) and math.isclose(b, 0.0)):
            return None
        return a / b
    except Exception:
        return None

def get_info_dict(t: yf.Ticker) -> Dict[str, Any]:
    try:
        if hasattr(t, 'get_info'):
            data = t.get_info()
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    try:
        data = t.info
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def pick_row(frame: Optional[pd.DataFrame], candidates: List[str]) -> Optional[pd.Series]:
    if frame is None or frame.empty:
        return None
    for name in candidates:
        if name in frame.index:
            return frame.loc[name].dropna().sort_index()
    # Try case-insensitive matches
    lower_map = {str(idx).lower(): idx for idx in frame.index}
    for name in candidates:
        key = name.lower()
        if key in lower_map:
            return frame.loc[lower_map[key]].dropna().sort_index()
    return None

def ttm_from_quarterly(series: Optional[pd.Series], n: int = 4) -> Optional[float]:
    if series is None or series.empty:
        return None
    s = series.dropna().sort_index(ascending=False)
    if len(s) < n:
        return None
    return float(s.iloc[:n].sum())

def average_from_quarterly(series: Optional[pd.Series], n: int = 4) -> Optional[float]:
    if series is None or series.empty:
        return None
    s = series.dropna().sort_index(ascending=False)
    if len(s) < n:
        return None
    return float(s.iloc[:n].mean())

def ttm_dividend_yield(ticker: yf.Ticker, price: Optional[float]) -> Optional[float]:
    try:
        div = ticker.dividends
        if div is None or div.empty or price in (None, 0):
            return None
        last_year = (dt.datetime.utcnow() - dt.timedelta(days=365)).tz_localize(None)
        ttm = div[div.index.tz_localize(None) >= last_year].sum()
        return (ttm / price) * 100.0 if price else None
    except Exception:
        return None

def years_of_dividend_growth(ticker: yf.Ticker) -> Optional[int]:
    """Rough proxy: count years since first dividend with no obvious gaps > 18 months recently."""
    try:
        div = ticker.dividends
        if div is None or div.empty:
            return 0
        # find the longest recent streak with no gap > 18 months
        idx = div.index.tz_localize(None).sort_values()
        gaps = (idx[1:] - idx[:-1]).days
        max_gap_days = gaps.max() if len(gaps) else 0
        # very rough heuristic
        first_year = idx[0].year
        last_year = idx[-1].year
        # If recent large gaps, return small streak
        if max_gap_days and max_gap_days > 550:  # ~18 months
            return max(0, (last_year - first_year) // 2)  # conservative
        return last_year - first_year
    except Exception:
        return None

def rolling_multiple_discount(series: pd.Series, current: Optional[float], window: int = 60) -> Optional[float]:
    """Return how far current multiple is below its rolling median (%) over window observations.
       Expects monthly or daily series; we will downsample to ~monthly to avoid noise."""
    try:
        if current is None or math.isnan(current):
            return None
        if series is None or len(series) == 0:
            return None
        # downsample by month
        s = series.dropna().copy()
        if s.empty:
            return None
        s = s.resample('M').last()
        med = s.tail(window).median()
        if med is None or med == 0 or math.isnan(med):
            return None
        return (med - current) / med * 100.0
    except Exception:
        return None

def fetch_sp500_universe() -> List[str]:
    """Scrape S&P500 tickers from Wikipedia. Falls back to yfinance Tickers if needed."""
    try:
        tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tables[0]
        return sorted(df['Symbol'].astype(str).str.replace('.', '-', regex=False).unique().tolist())
    except Exception:
        # last resort tiny fallback
        return ['AAPL', 'MSFT', 'BRK-B', 'KO', 'PG', 'JNJ', 'WMT', 'XOM', 'NVDA', 'PEP']

# --------- Config Dataclass ---------
@dataclass
class ScreenerConfig:
    # Business quality
    min_rev_5y_cagr: float = 5.0
    min_net_margin: float = 10.0
    min_roe: float = 15.0
    min_fcf_positive_years: int = 5
    min_gross_margin: float = 35.0

    # Financial strength
    max_de: float = 0.5
    min_current_ratio: float = 1.5
    min_interest_coverage: float = 5.0

    # Valuation
    max_pe: float = 20.0
    max_peg: float = 1.5
    max_pb: float = 3.0
    max_ev_ebit: float = 12.0
    min_div_yield: float = 2.0  # optional

    # Stability proxies
    max_beta: float = 1.2
    min_div_growth_years: int = 10

    # Margin-of-safety proxy
    min_mult_discount_pct: float = 10.0  # current P/E vs 5y median discount

    # Added Buffett-aligned extras
    min_fcf_yield_pct: float = 5.0
    max_debt_to_fcf: float = 3.0
    use_peg_as_hint: bool = True  # don't fail if PEG missing; if present and > max_peg then fail

# --------- Core Fetch ---------
def fetch_metrics(symbol: str) -> Dict[str, Any]:
    t = yf.Ticker(symbol)
    info = get_info_dict(t)
    try:
        # price & fast fields
        fast = t.fast_info if hasattr(t, 'fast_info') else {}
        price = fast.get('last_price') if fast else None
        if price is None:
            price = info.get('currentPrice')

        # Financial statements
        bs_a = t.balance_sheet
        is_a = t.income_stmt
        cf_a = t.cashflow
        bs_q = t.quarterly_balance_sheet
        is_q = t.quarterly_income_stmt
        cf_q = t.quarterly_cashflow

        # Trailing and valuation
        try:
            hist = t.history(period="10y", auto_adjust=False)
        except Exception:
            hist = pd.DataFrame()
        beta = info.get('beta')  # yfinance's beta may be None

        # Revenue CAGR (5y): use annual income statement 'Total Revenue'
        rev_cagr = None
        try:
            frame = is_a if is_a is not None else pd.DataFrame()
            row = pick_row(frame, ['Total Revenue', 'Revenue'])
            rev = row.dropna() if row is not None else pd.Series(dtype=float)
            rev = rev.sort_index()
            if len(rev) >= 6:  # need at least 6 annual points (5 full years)
                rev5 = rev.iloc[-6:]
                begin, end = rev5.iloc[0], rev5.iloc[-1]
                if begin and begin > 0 and end and end > 0:
                    years = (rev5.index[-1].year - rev5.index[0].year)
                    if years > 0:
                        rev_cagr = ((end / begin) ** (1/years) - 1) * 100.0
        except Exception:
            pass

        # TTM metrics from quarterly statements
        ni_ttm = ttm_from_quarterly(pick_row(is_q, ['Net Income', 'Net Income Applicable To Common Shares']))
        rev_ttm = ttm_from_quarterly(pick_row(is_q, ['Total Revenue', 'Revenue']))
        ebit_ttm = ttm_from_quarterly(pick_row(is_q, ['EBIT', 'Ebit', 'Operating Income']))
        int_exp_ttm = ttm_from_quarterly(pick_row(is_q, ['Interest Expense']))
        int_exp_ttm = abs(int_exp_ttm) if int_exp_ttm is not None else None
        net_margin = (safe_div(ni_ttm, rev_ttm) * 100.0) if (ni_ttm is not None and rev_ttm) else None

        # ROE = Net Income (TTM) / Average Equity (last 4 quarters)
        roe = None
        try:
            equity_avg = average_from_quarterly(pick_row(bs_q, ["Total Stockholder Equity"]))
            if equity_avg not in (None, 0) and ni_ttm is not None:
                roe = (ni_ttm / equity_avg) * 100.0
        except Exception:
            pass

        # Free cash flow positive years (last 5)
        fcf_pos_years = 0
        try:
            ocf = cf_a.loc['Total Cash From Operating Activities'].dropna().sort_index()
            capex = cf_a.loc['Capital Expenditures'].dropna().sort_index()
            common_index = ocf.index.intersection(capex.index)
            if len(common_index) >= 5:
                last5 = common_index[-5:]
                for d in last5:
                    fcf = ocf.loc[d] + capex.loc[d]  # capex is negative
                    if fcf and fcf > 0:
                        fcf_pos_years += 1
        except Exception:
            pass

        # Gross margin (TTM proxy)
        gross_margin = None
        try:
            # gross profit (annual latest) / revenue (annual latest) as proxy
            gp = pick_row(is_a, ['Gross Profit'])
            revv = pick_row(is_a, ['Total Revenue', 'Revenue'])
            gpv = gp.sort_index().iloc[-1] if gp is not None and not gp.empty else None
            rrv = revv.sort_index().iloc[-1] if revv is not None and not revv.empty else None
            if gp and revv:
                gross_margin = (gpv / rrv) * 100.0
        except Exception:
            pass

        # Debt-to-equity
        de = None
        try:
            total_debt = info.get('totalDebt')
            if total_debt is None and bs_a is not None and 'Total Debt' in bs_a.index:
                total_debt = bs_a.loc['Total Debt'].dropna().sort_index().iloc[-1]
            equity_latest = None
            if bs_a is not None and 'Total Stockholder Equity' in bs_a.index:
                equity_latest = bs_a.loc['Total Stockholder Equity'].dropna().sort_index().iloc[-1]
            if total_debt is not None and equity_latest not in (None, 0):
                de = total_debt / equity_latest
        except Exception:
            pass

        # Current ratio
        current_ratio = None
        try:
            ca = bs_a.loc['Total Current Assets'].dropna().sort_index().iloc[-1]
            cl = bs_a.loc['Total Current Liabilities'].dropna().sort_index().iloc[-1]
            current_ratio = safe_div(ca, cl)
        except Exception:
            pass

        # Interest coverage = EBIT / Interest Expense (TTM)
        interest_coverage = None
        try:
            interest_coverage = safe_div(ebit_ttm, int_exp_ttm)
        except Exception:
            pass

        # Valuation multiples (current)
        pe = info.get('trailingPE') or info.get('forwardPE')
        peg = info.get('pegRatio')
        pb = info.get('priceToBook')
        market_cap = info.get('marketCap')
        total_debt_info = info.get('totalDebt') or 0
        cash = info.get('totalCash') or 0
        ev = info.get('enterpriseValue')
        if ev is None and market_cap is not None:
            ev = market_cap + (total_debt_info or 0) - (cash or 0)
        ev_ebit = safe_div(ev, ebit_ttm) if (ev and ebit_ttm) else None

        # Dividend yield (TTM)
        div_yield = ttm_dividend_yield(t, price)

        # Dividend growth years (rough proxy)
        div_growth_years = years_of_dividend_growth(t)

    # P/E historical series to compute discount vs median (not available reliably)
        pe_discount_pct = None
        try:
            # Approximate P/E time series: price / (TTM EPS), but we don't have TTM EPS easily.
            # As a proxy, use yfinance's trailingPE over time is unavailable. We'll instead
            # approximate using price vs operating income margin stability by comparing current P/E to sector cap.
            # Simpler: use current P/E relative to last 5y price-to-sales (P/S) median if available.
            # yfinance doesn't provide historical P/S either, so we'll fallback to None.
            pe_discount_pct = None
        except Exception:
            pass

        # Company name & sector
        company_name = info.get('shortName') or info.get('longName')
        sector = info.get('sector')

        # FCF TTM and yield
        ocf_ttm = ttm_from_quarterly(pick_row(cf_q, ['Total Cash From Operating Activities']))
        capex_ttm = ttm_from_quarterly(pick_row(cf_q, ['Capital Expenditures']))
        fcf_ttm = (ocf_ttm + capex_ttm) if (ocf_ttm is not None and capex_ttm is not None) else None
        fcf_yield_pct = (safe_div(fcf_ttm, market_cap) * 100.0) if (fcf_ttm is not None and market_cap) else None
        net_debt = (total_debt_info or 0) - (cash or 0)
        debt_to_fcf = safe_div(net_debt, fcf_ttm) if (fcf_ttm not in (None, 0)) else None

        return {
            'symbol': symbol,
            'company_name': company_name,
            'sector': sector,
            'price': price,
            'rev_5y_cagr_pct': rev_cagr,
            'net_margin_pct': net_margin,
            'roe_pct': roe,
            'fcf_pos_years_5': fcf_pos_years,
            'gross_margin_pct': gross_margin,
            'de_ratio': de,
            'current_ratio': current_ratio,
            'interest_coverage': interest_coverage,
            'pe': pe,
            'peg': peg,
            'pb': pb,
            'ev_ebit': ev_ebit,
            'div_yield_pct': div_yield,
            'beta': beta,
            'div_growth_years': div_growth_years,
            'pe_discount_pct_vs_5y_median': pe_discount_pct,  # may be None
            'fcf_ttm': fcf_ttm,
            'fcf_yield_pct': fcf_yield_pct,
            'debt_to_fcf': debt_to_fcf,
        }
    except Exception as e:
        return {'symbol': symbol, 'error': str(e)}

def passes_filters(row: pd.Series, cfg: ScreenerConfig) -> bool:
    # Business quality
    if row.get('rev_5y_cagr_pct') is None or row['rev_5y_cagr_pct'] < cfg.min_rev_5y_cagr: return False
    if row.get('net_margin_pct') is None or row['net_margin_pct'] < cfg.min_net_margin: return False
    if row.get('roe_pct') is None or row['roe_pct'] < cfg.min_roe: return False
    if row.get('fcf_pos_years_5') is None or row['fcf_pos_years_5'] < cfg.min_fcf_positive_years: return False
    if row.get('gross_margin_pct') is None or row['gross_margin_pct'] < cfg.min_gross_margin: return False

    # Financial strength
    if row.get('de_ratio') is None or row['de_ratio'] > cfg.max_de: return False
    if row.get('current_ratio') is None or row['current_ratio'] < cfg.min_current_ratio: return False
    if row.get('interest_coverage') is None or row['interest_coverage'] < cfg.min_interest_coverage: return False
    # Debt to FCF (prefer low)
    if row.get('debt_to_fcf') is not None and row['debt_to_fcf'] > cfg.max_debt_to_fcf: return False

    # Valuation
    if row.get('pe') is None or row['pe'] > cfg.max_pe: return False
    # PEG is optional; if present and configured, check
    if cfg.use_peg_as_hint and row.get('peg') is not None and row['peg'] > cfg.max_peg: return False
    if row.get('pb') is None or row['pb'] > cfg.max_pb: return False
    if row.get('ev_ebit') is None or row['ev_ebit'] > cfg.max_ev_ebit: return False
    if row.get('div_yield_pct') is not None and row['div_yield_pct'] < cfg.min_div_yield:
        return False
    if row.get('fcf_yield_pct') is not None and row['fcf_yield_pct'] < cfg.min_fcf_yield_pct:
        return False

    # Stability proxies
    if row.get('beta') is not None and row['beta'] > cfg.max_beta: return False
    if row.get('div_growth_years') is not None and row['div_growth_years'] < cfg.min_div_growth_years:
        return False

    # Margin-of-safety proxy (optional; often None). If present, require min discount.
    if row.get('pe_discount_pct_vs_5y_median') is not None:
        if row['pe_discount_pct_vs_5y_median'] < cfg.min_mult_discount_pct: return False

    return True

def first_failure_reason(row: pd.Series, cfg: ScreenerConfig) -> Optional[str]:
    checks = [
        ("Revenue CAGR", row.get('rev_5y_cagr_pct'), lambda v: v is not None and v >= cfg.min_rev_5y_cagr, f"CAGR<{cfg.min_rev_5y_cagr}%"),
        ("Net Margin", row.get('net_margin_pct'), lambda v: v is not None and v >= cfg.min_net_margin, f"NetMargin<{cfg.min_net_margin}%"),
        ("ROE", row.get('roe_pct'), lambda v: v is not None and v >= cfg.min_roe, f"ROE<{cfg.min_roe}%"),
        ("FCF Positive Years (5)", row.get('fcf_pos_years_5'), lambda v: v is not None and v >= cfg.min_fcf_positive_years, f"FCFYears<{cfg.min_fcf_positive_years}"),
        ("Gross Margin", row.get('gross_margin_pct'), lambda v: v is not None and v >= cfg.min_gross_margin, f"GrossMargin<{cfg.min_gross_margin}%"),
        ("Debt/Equity", row.get('de_ratio'), lambda v: v is not None and v <= cfg.max_de, f"D/E>{cfg.max_de}"),
        ("Current Ratio", row.get('current_ratio'), lambda v: v is not None and v >= cfg.min_current_ratio, f"CR<{cfg.min_current_ratio}"),
        ("Interest Coverage", row.get('interest_coverage'), lambda v: v is not None and v >= cfg.min_interest_coverage, f"IC<{cfg.min_interest_coverage}"),
        ("Debt/FCF", row.get('debt_to_fcf'), lambda v: v is None or v <= cfg.max_debt_to_fcf, f"Debt/FCF>{cfg.max_debt_to_fcf}"),
        ("P/E", row.get('pe'), lambda v: v is not None and v <= cfg.max_pe, f"PE>{cfg.max_pe}"),
        ("PEG", row.get('peg'), lambda v: (v is None) or (not cfg.use_peg_as_hint) or (v <= cfg.max_peg), f"PEG>{cfg.max_peg}"),
        ("P/B", row.get('pb'), lambda v: v is not None and v <= cfg.max_pb, f"PB>{cfg.max_pb}"),
        ("EV/EBIT", row.get('ev_ebit'), lambda v: v is not None and v <= cfg.max_ev_ebit, f"EV/EBIT>{cfg.max_ev_ebit}"),
        ("Div Yield", row.get('div_yield_pct'), lambda v: v is None or v >= cfg.min_div_yield, f"DivYield<{cfg.min_div_yield}%"),
        ("FCF Yield", row.get('fcf_yield_pct'), lambda v: v is None or v >= cfg.min_fcf_yield_pct, f"FCFYield<{cfg.min_fcf_yield_pct}%"),
        ("PE discount vs 5y", row.get('pe_discount_pct_vs_5y_median'), lambda v: v is None or v >= cfg.min_mult_discount_pct, f"PEdisc<{cfg.min_mult_discount_pct}%"),
    ]
    for label, val, ok_fn, msg in checks:
        try:
            if not ok_fn(val):
                return f"{label}: {msg} (got {val})"
        except Exception:
            return f"{label}: invalid"
    return None

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

def load_universe(args) -> List[str]:
    # New option: if user passes --universe db (or sp500 but DB available) we pull from instruments
    if args.universe == 'db':
        db_list = _load_instruments_from_db(args.db_path)
        if db_list:
            return db_list
        print("Warning: --universe db requested but instruments table empty; falling back to sp500 scrape")
        return fetch_sp500_universe()
    if args.universe == 'sp500':
        # Prefer DB instruments if present (user already populated) unless --no-db-universe flag provided
        if not getattr(args, 'no_db_universe', False):
            db_list = _load_instruments_from_db(args.db_path)
            if db_list:
                return db_list
        return fetch_sp500_universe()
    elif args.universe == 'custom' and args.universe_file:
        with open(args.universe_file, 'r') as f:
            syms = [line.strip() for line in f if line.strip()]
        return syms
    else:
        return ['AAPL', 'MSFT', 'KO', 'PG', 'WMT', 'BRK-B', 'JNJ']

def main():
    parser = argparse.ArgumentParser(description="Buffett-style stock screener")
    parser.add_argument('--universe', choices=['sp500', 'custom', 'db'], default='sp500')
    parser.add_argument('--db-path', help='SQLite DB path (used when universe=db or to prefer populated instruments)')
    parser.add_argument('--no-db-universe', action='store_true', help='Force ignoring DB instruments even if present when universe=sp500')
    parser.add_argument('--universe-file', help='Path to a text file of tickers (one per line)')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--output', default='buffett_screen_results.csv', help='Output CSV path')

    # Threshold overrides
    parser.add_argument('--min_rev_5y_cagr', type=float, default=None)
    parser.add_argument('--min_net_margin', type=float, default=None)
    parser.add_argument('--min_roe', type=float, default=None)
    parser.add_argument('--min_fcf_years', type=int, default=None)
    parser.add_argument('--min_gross_margin', type=float, default=None)

    parser.add_argument('--max_de', type=float, default=None)
    parser.add_argument('--min_current_ratio', type=float, default=None)
    parser.add_argument('--min_interest_coverage', type=float, default=None)

    parser.add_argument('--max_pe', type=float, default=None)
    parser.add_argument('--max_peg', type=float, default=None)
    parser.add_argument('--max_pb', type=float, default=None)
    parser.add_argument('--max_ev_ebit', type=float, default=None)
    parser.add_argument('--min_div_yield', type=float, default=None)
    parser.add_argument('--min_fcf_yield', type=float, default=None)
    parser.add_argument('--max_debt_to_fcf', type=float, default=None)
    parser.add_argument('--ignore_peg', action='store_true')

    parser.add_argument('--max_beta', type=float, default=None)
    parser.add_argument('--min_div_growth_years', type=int, default=None)

    parser.add_argument('--min_mult_discount_pct', type=float, default=None)

    args = parser.parse_args()

    # Build config with overrides
    cfg = ScreenerConfig()
    if args.min_rev_5y_cagr is not None: cfg.min_rev_5y_cagr = args.min_rev_5y_cagr
    if args.min_net_margin is not None: cfg.min_net_margin = args.min_net_margin
    if args.min_roe is not None: cfg.min_roe = args.min_roe
    if args.min_fcf_years is not None: cfg.min_fcf_positive_years = args.min_fcf_years
    if args.min_gross_margin is not None: cfg.min_gross_margin = args.min_gross_margin

    if args.max_de is not None: cfg.max_de = args.max_de
    if args.min_current_ratio is not None: cfg.min_current_ratio = args.min_current_ratio
    if args.min_interest_coverage is not None: cfg.min_interest_coverage = args.min_interest_coverage

    if args.max_pe is not None: cfg.max_pe = args.max_pe
    if args.max_peg is not None: cfg.max_peg = args.max_peg
    if args.max_pb is not None: cfg.max_pb = args.max_pb
    if args.max_ev_ebit is not None: cfg.max_ev_ebit = args.max_ev_ebit
    if args.min_div_yield is not None: cfg.min_div_yield = args.min_div_yield
    if args.min_fcf_yield is not None: cfg.min_fcf_yield_pct = args.min_fcf_yield
    if args.max_debt_to_fcf is not None: cfg.max_debt_to_fcf = args.max_debt_to_fcf
    if args.ignore_peg: cfg.use_peg_as_hint = False

    if args.max_beta is not None: cfg.max_beta = args.max_beta
    if args.min_div_growth_years is not None: cfg.min_div_growth_years = args.min_div_growth_years

    if args.min_mult_discount_pct is not None: cfg.min_mult_discount_pct = args.min_mult_discount_pct

    symbols = load_universe(args)
    print(f"Universe size: {len(symbols)} symbols", file=sys.stderr)

    # Fetch concurrently
    results: List[Dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=args.threads) as executor:
        for res in executor.map(fetch_metrics, symbols):
            results.append(res)

    df = pd.DataFrame(results)
    # Reorder columns
    cols = ['symbol','company_name','sector','price','rev_5y_cagr_pct','net_margin_pct','roe_pct','fcf_pos_years_5',
        'gross_margin_pct','de_ratio','current_ratio','interest_coverage','pe','peg','pb',
        'ev_ebit','div_yield_pct','fcf_ttm','fcf_yield_pct','debt_to_fcf','beta','div_growth_years','pe_discount_pct_vs_5y_median','error']
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    df = df[cols]

    # Apply filters
    mask = df.apply(lambda r: passes_filters(r, cfg), axis=1)
    df['why_failed'] = df.apply(lambda r: None if passes_filters(r, cfg) else first_failure_reason(r, cfg), axis=1)
    # Prefer higher FCF yield, then lower EV/EBIT, then lower PE
    survivors = df[mask].sort_values(['fcf_yield_pct','ev_ebit','pe'], ascending=[False, True, True]).reset_index(drop=True)

    # Save all + survivors
    df.to_csv(args.output.replace('.csv', '_raw.csv'), index=False)
    survivors.to_csv(args.output, index=False)

    print(f"\nSaved: {args.output} (survivors)")
    print(f"       {args.output.replace('.csv', '_raw.csv')} (raw metrics)")

    # Pretty print top 20
    with pd.option_context('display.max_columns', None):
        print("\nTop 20 survivors:\n", survivors.head(20))

if __name__ == '__main__':
    main()
