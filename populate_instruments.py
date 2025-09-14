"""Populate instruments table from a ticker list file, enriching with sector/industry/country/currency.

Data sources tried (in order):
- yfinance.Ticker.info or .get_info()
- fallback defaults if missing

Usage:
  python populate_instruments.py --db at_data.sqlite --tickers-file portfolio_66.txt

Idempotent: uses INSERT OR REPLACE to update metadata.
"""
from __future__ import annotations
import argparse, json, time, sys
import sqlite3
from typing import Dict, Any, Optional

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. Install requirements first.")
    sys.exit(1)

DEFAULT_CURRENCY = "USD"

FIELDS_MAP = [
    ("sector", "sector"),
    ("industry", "industry"),
    ("country", "country"),
    ("currency", "currency"),
    ("quoteType", "instrument_type"),  # map quoteType -> instrument_type
]

CREATE_INSTRUMENTS = """CREATE TABLE IF NOT EXISTS instruments (
  ticker TEXT PRIMARY KEY,
  instrument_type TEXT NOT NULL DEFAULT 'stock',
  style_category TEXT,
  sector TEXT,
  industry TEXT,
  country TEXT,
  currency TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT,
  notes TEXT
);"""

UPSERT_SQL = """
INSERT INTO instruments(ticker,instrument_type,style_category,sector,industry,country,currency,active,updated_at,notes)
VALUES(?,?,?,?,?,?,?,?,datetime('now'),?)
ON CONFLICT(ticker) DO UPDATE SET
  instrument_type=excluded.instrument_type,
  style_category=COALESCE(excluded.style_category,instruments.style_category),
  sector=COALESCE(excluded.sector,instruments.sector),
  industry=COALESCE(excluded.industry,instruments.industry),
  country=COALESCE(excluded.country,instruments.country),
  currency=COALESCE(excluded.currency,instruments.currency),
  active=excluded.active,
  updated_at=datetime('now'),
  notes=COALESCE(excluded.notes,instruments.notes);
"""

def read_tickers(path: str):
    out = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            t = line.strip().upper()
            if t and not t.startswith('#'):
                out.append(t)
    # de-dup preserving order
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq

def fetch_meta(ticker: str) -> Dict[str, Any]:
    info = {}
    try:
        tk = yf.Ticker(ticker)
        # Some versions: get_info may exist; else info attribute
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
            info = raw
    except Exception:
        pass
    meta: Dict[str, Any] = {}
    for src_key, dest_key in FIELDS_MAP:
        val = info.get(src_key)
        if isinstance(val, str) and val.strip():
            meta[dest_key] = val.strip()
    # Normalize instrument type
    qtype = meta.get("instrument_type", "stock").lower()
    if qtype in ("etf", "mutualfund", "fund"):
        inst_type = "etf"
    elif qtype in ("crypto", "cryptocurrency"):
        inst_type = "crypto"
    elif qtype in ("equity", "commonstock", "stock"):
        inst_type = "stock"
    else:
        inst_type = qtype[:16]
    meta["instrument_type"] = inst_type or "stock"
    # Currency default
    meta.setdefault("currency", DEFAULT_CURRENCY)
    return meta

def upsert(conn: sqlite3.Connection, ticker: str, meta: Dict[str, Any]):
    conn.execute(UPSERT_SQL, (
        ticker,
        meta.get("instrument_type", "stock"),
        meta.get("style_category"),
        meta.get("sector"),
        meta.get("industry"),
        meta.get("country"),
        meta.get("currency", DEFAULT_CURRENCY),
        1,
        meta.get("notes"),
    ))

def main():
    ap = argparse.ArgumentParser(description="Populate instruments table with metadata for tickers")
    ap.add_argument('--db', default='at_data.sqlite', help='SQLite DB path')
    ap.add_argument('--tickers-file', required=True, help='File containing tickers (one per line)')
    ap.add_argument('--sleep', type=float, default=0.4, help='Sleep between API calls to avoid rate limits')
    args = ap.parse_args()
    tickers = read_tickers(args.tickers_file)
    if not tickers:
        print('No tickers found.')
        return 1
    conn = sqlite3.connect(args.db)
    conn.execute('PRAGMA foreign_keys=ON')
    # Ensure table exists (in case db not at v4 yet)
    conn.execute(CREATE_INSTRUMENTS)
    total = len(tickers)
    for i, t in enumerate(tickers, 1):
        meta = fetch_meta(t)
        try:
            upsert(conn, t, meta)
            if i % 25 == 0:
                conn.commit()
        except Exception as e:
            print(f"[{t}] upsert failed: {e}")
        time.sleep(args.sleep)
        print(f"{i}/{total} {t} -> {meta.get('instrument_type')} sector={meta.get('sector')} industry={meta.get('industry')}")
    conn.commit()
    # Summary counts
    cur = conn.cursor()
    c = cur.execute('SELECT COUNT(*) FROM instruments').fetchone()[0]
    print(f"Done. instruments rows: {c}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
