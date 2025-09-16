from __future__ import annotations

"""Assign style_category for instruments where it is missing/Unknown.

Heuristics (ordered):
    1. If instrument_type = 'etf' sector drives style (growth, income, commodity, crypto, real_estate, broad).
    2. If instrument_type = 'stock': sector maps to style buckets (growth/defensive/financial/core/energy/real_estate).
    3. Fallback = 'core' (stocks) or 'broad' (ETFs without recognizable sector).

The script only updates rows where style_category IS NULL/''/'Unknown'.
Idempotent and safe to re-run.
"""
import sqlite3, os, argparse

SELECT_TARGETS = """
SELECT ticker, instrument_type, COALESCE(sector,''), COALESCE(style_category,'')
FROM instruments
WHERE style_category IS NULL OR style_category='' OR style_category='Unknown'
ORDER BY ticker
"""

UPDATE_SQL = """UPDATE instruments
SET style_category = :style, updated_at = datetime('now')
WHERE ticker = :ticker AND (style_category IS NULL OR style_category='' OR style_category='Unknown')"""

def classify(inst_type: str, sector: str) -> str:
    inst_type = (inst_type or '').lower()
    s = sector.lower()
    if inst_type == 'etf':
        if 'technology' in s:
            return 'growth'
        if 'income' in s or 'dividend' in s:
            return 'income'
        if 'gold' in s or 'commod' in s:
            return 'commodity'
        if 'digital' in s or 'crypto' in s:
            return 'crypto'
        if 'real estate' in s:
            return 'real_estate'
        if 'broad' in s or not s:
            return 'broad'
        return 'broad'
    # Stocks
    if 'technology' in s:
        return 'growth'
    if 'consumer cyclical' in s or 'communication services' in s:
        return 'growth'
    if 'healthcare' in s:
        return 'defensive'
    if 'consumer defensive' in s or 'utilities' in s:
        return 'defensive'
    if 'financial' in s:
        return 'financial'
    if 'industrial' in s or 'basic materials' in s:
        return 'value'
    if 'energy' in s:
        return 'energy'
    if 'real estate' in s:
        return 'real_estate'
    if not s:
        return 'value'
    return 'value'

def main():
    ap = argparse.ArgumentParser(description='Assign style_category heuristically')
    default_db = 'at_data.sqlite'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, default_db)
    if os.path.exists(candidate):
        default_db = candidate
    ap.add_argument('--db', default=default_db, help='SQLite DB path')
    args = ap.parse_args()
    if not os.path.exists(args.db):
        print('DB not found:', args.db)
        return 1
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    rows = cur.execute(SELECT_TARGETS).fetchall()
    if not rows:
        print('No rows need style assignment.')
        return 0
    updated = 0
    for i, (ticker, inst_type, sector, existing) in enumerate(rows, 1):
        style = classify(inst_type, sector)
        cur.execute(UPDATE_SQL, {'ticker': ticker, 'style': style})
        if cur.rowcount:
            updated += 1
        print(f"{i}/{len(rows)} {ticker}: sector='{sector}' -> style='{style}' (updated={cur.rowcount})")
        if i % 100 == 0:
            conn.commit()
    conn.commit()
    print(f'Done. Rows updated: {updated}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
