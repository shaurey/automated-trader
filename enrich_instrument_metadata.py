"""Enrich instrument metadata for rows currently marked as 'Unknown'.

This script looks up sector, industry, country, currency, and instrument_type
for instruments whose fields are missing or set to the placeholder 'Unknown'.

Data Source: yfinance (network calls). Keep an eye on rate limits.

Behavior:
  - Only overwrites a column if the new fetched value is a non-empty string
    and the existing value is NULL, empty, or 'Unknown'.
  - Normalizes instrument_type from yfinance quoteType.
  - Leaves any already populated (non-Unknown) values untouched.
  - Skips tickers that raise errors or return no metadata.

Usage:
  python enrich_instrument_metadata.py            # uses default at_data.sqlite
  python enrich_instrument_metadata.py --db path/to/db.sqlite --sleep 0.35

Exit code 0 on success, 1 on fatal error.
"""
from __future__ import annotations
import argparse, sys, time, sqlite3
from typing import Dict, Any, List, Tuple

TRY_IMPORT_MSG = "yfinance not installed. Install requirements first (pip install -r requirements.txt)."

try:
    import yfinance as yf  # type: ignore
except ImportError:
    print(TRY_IMPORT_MSG)
    sys.exit(1)

# Columns we attempt to enrich (dest -> yfinance key)
FIELD_MAP = [
    ("sector", "sector"),
    ("industry", "industry"),
    ("country", "country"),
    ("currency", "currency"),
    ("instrument_type", "quoteType"),  # normalized later
]

DEFAULT_CURRENCY = "USD"

SELECT_TARGETS = """
SELECT ticker, COALESCE(sector,''), COALESCE(industry,''), COALESCE(country,''), COALESCE(currency,''), COALESCE(instrument_type,'')
FROM instruments
WHERE (sector IS NULL OR sector = '' OR sector = 'Unknown')
   OR (industry IS NULL OR industry = '' OR industry = 'Unknown')
   OR (country IS NULL OR country = '' OR country = 'Unknown')
   OR (currency IS NULL OR currency = '')
   OR (instrument_type IS NULL OR instrument_type = '')
ORDER BY ticker
"""

UPDATE_SQL = """
UPDATE instruments
SET 
  sector = CASE WHEN (:sector IS NOT NULL AND :sector <> '' AND (sector IS NULL OR sector='' OR sector='Unknown')) THEN :sector ELSE sector END,
  industry = CASE WHEN (:industry IS NOT NULL AND :industry <> '' AND (industry IS NULL OR industry='' OR industry='Unknown')) THEN :industry ELSE industry END,
  country = CASE WHEN (:country IS NOT NULL AND :country <> '' AND (country IS NULL OR country='' OR country='Unknown')) THEN :country ELSE country END,
  currency = CASE WHEN (:currency IS NOT NULL AND :currency <> '' AND (currency IS NULL OR currency='')) THEN :currency ELSE currency END,
  instrument_type = CASE WHEN (:itype IS NOT NULL AND :itype <> '' AND (instrument_type IS NULL OR instrument_type='')) THEN :itype ELSE instrument_type END,
  updated_at = datetime('now')
WHERE ticker = :ticker
"""

COUNT_UNKNOWN = """
SELECT 
  SUM(CASE WHEN sector IS NULL OR sector='' OR sector='Unknown' THEN 1 ELSE 0 END) AS unk_sector,
  SUM(CASE WHEN industry IS NULL OR industry='' OR industry='Unknown' THEN 1 ELSE 0 END) AS unk_industry,
  SUM(CASE WHEN country IS NULL OR country='' OR country='Unknown' THEN 1 ELSE 0 END) AS unk_country,
  SUM(CASE WHEN currency IS NULL OR currency='' THEN 1 ELSE 0 END) AS unk_currency,
  SUM(CASE WHEN instrument_type IS NULL OR instrument_type='' THEN 1 ELSE 0 END) AS unk_type
FROM instruments
"""

def normalize_instrument_type(raw: str | None) -> str:
    if not raw:
        return "stock"
    r = raw.lower()
    if r in ("etf", "mutualfund", "fund"):
        return "etf"
    if r in ("crypto", "cryptocurrency"):
        return "crypto"
    if r in ("equity", "commonstock", "stock"):
        return "stock"
    return r[:16] or "stock"

def fetch_meta(ticker: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    try:
        tk = yf.Ticker(ticker)
        raw = None
        for attr in ("get_info", "info"):
            if hasattr(tk, attr):
                try:
                    raw = getattr(tk, attr)()
                    if raw:
                        break
                except Exception:
                    pass
        if isinstance(raw, dict):
            for dest, src in FIELD_MAP:
                val = raw.get(src)
                if isinstance(val, str) and val.strip():
                    data[dest] = val.strip()
    except Exception:
        return {}
    # Normalize instrument type
    data["instrument_type"] = normalize_instrument_type(data.get("instrument_type"))
    # Currency fallback
    if not data.get("currency"):
        data["currency"] = DEFAULT_CURRENCY
    return data

def enrich(conn: sqlite3.Connection, sleep: float):
    cur = conn.cursor()
    targets = cur.execute(SELECT_TARGETS).fetchall()
    total = len(targets)
    if not total:
        print("No instruments require enrichment.")
        return 0, 0
    updated = 0
    skipped = 0
    for idx, (ticker, sector, industry, country, currency, itype) in enumerate(targets, 1):
        meta = fetch_meta(ticker)
        if not meta:
            skipped += 1
            print(f"{idx}/{total} {ticker}: no data (skip)")
            time.sleep(sleep)
            continue
        params = {
            "ticker": ticker,
            "sector": meta.get("sector"),
            "industry": meta.get("industry"),
            "country": meta.get("country"),
            "currency": meta.get("currency"),
            "itype": meta.get("instrument_type"),
        }
        try:
            cur.execute(UPDATE_SQL, params)
            if cur.rowcount > 0:
                updated += 1
            print(f"{idx}/{total} {ticker}: updated={cur.rowcount} sector={params['sector']} industry={params['industry']} country={params['country']} type={params['itype']}")
        except Exception as e:
            print(f"{idx}/{total} {ticker}: update failed: {e}")
        if idx % 25 == 0:
            conn.commit()
        time.sleep(sleep)
    conn.commit()
    return updated, skipped

def print_unknown_counts(conn: sqlite3.Connection, label: str):
    cur = conn.cursor()
    counts = cur.execute(COUNT_UNKNOWN).fetchone()
    print(label, counts)

def main():
    ap = argparse.ArgumentParser(description="Enrich 'Unknown' instrument metadata via yfinance")
    default_db = 'at_data.sqlite'
    script_dir_db = default_db
    # Resolve DB relative to script directory to avoid picking up a stray frontend copy
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, default_db)
    if os.path.exists(candidate):
        script_dir_db = candidate
    ap.add_argument('--db', default=script_dir_db, help='SQLite DB path')
    ap.add_argument('--sleep', type=float, default=0.35, help='Sleep between API calls (rate limit friendly)')
    args = ap.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except Exception as e:
        print(f"Failed to open database: {e}")
        return 1
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        print_unknown_counts(conn, 'Before:')
        updated, skipped = enrich(conn, args.sleep)
        print_unknown_counts(conn, 'After:')
        print(f"Summary: rows_changed={updated} skipped_no_data={skipped}")
    finally:
        conn.close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
