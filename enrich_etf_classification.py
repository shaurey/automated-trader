"""Heuristically classify ETFs and fill missing sector/industry/style_category.

Strategy:
  - Target rows where instrument_type='etf' AND (sector or industry is NULL/''/'Unknown').
  - Use ticker + (optional) existing notes/name heuristics via pattern matching.
  - Derive a broad thematic sector and an industry-style bucket.
  - Also set style_category if NULL/empty/Unknown using similar logic.
  - Fallback sector='Broad Market', industry='Broad', style_category='broad'.

Patterns (ordered, first match wins):
  Growth / Tech: QQQ, QQQM, QQQI, QQQ*, IGM, XLK, VGT, SMH, CIBR, AIQ, JEPQ
  Dividend / Income: VYM, SCHD, DVY, HDV, SPYD, VIG, JEPI, SPYI
  Gold / Metals: GLD, IAU
  Crypto / Blockchain: BTC, BTCI, ETH, QTUM, TOPT
  Real Estate: SCHH
  Total / Broad Market: VOO, SCHX, FSKAX, FXAIX, FZROX, FNILX, BND, BSV, SPY

Idempotent: Only updates columns when their existing values are NULL/''/'Unknown'.

Usage:
  python enrich_etf_classification.py --db at_data.sqlite
"""
from __future__ import annotations
import re, sqlite3, argparse, os, sys
from typing import Optional, Tuple, Dict

RULES = [
    (re.compile(r'^(QQQ|QQQM|QQQI|QQQ[I0-9]?)$'), ('Technology', 'Technology Growth', 'growth')),
    (re.compile(r'^(IGM|XLK|VGT|SMH|CIBR|AIQ|JEPQ)$'), ('Technology', 'Technology Thematic', 'growth')),
    (re.compile(r'^(VYM|SCHD|DVY|HDV|SPYD|VIG|JEPI|SPYI)$'), ('Equity Income', 'Dividend Focus', 'income')),
    (re.compile(r'^(GLD|IAU)$'), ('Commodities', 'Gold', 'commodity')),
    (re.compile(r'^(BTC|BTCI|ETH|QTUM|TOPT)$'), ('Digital Assets', 'Crypto Exposure', 'crypto')),
    (re.compile(r'^(SCHH)$'), ('Real Estate', 'REIT Exposure', 'real_estate')),
    (re.compile(r'^(VOO|SCHX|FSKAX|FXAIX|FZROX|FNILX|BND|BSV|SPY)$'), ('Broad Market', 'Broad', 'broad')),
]

FALLBACK = ('Broad Market', 'Broad', 'broad')

SELECT_ETFS = """
SELECT ticker, COALESCE(sector,''), COALESCE(industry,''), COALESCE(style_category,'')
FROM instruments
WHERE instrument_type='etf'
  AND (
        sector IS NULL OR sector='' OR sector='Unknown'
     OR industry IS NULL OR industry='' OR industry='Unknown'
     OR style_category IS NULL OR style_category='' OR style_category='Unknown'
  )
ORDER BY ticker
"""

UPDATE_SQL = """
UPDATE instruments SET
  sector = CASE WHEN (sector IS NULL OR sector='' OR sector='Unknown') THEN :sector ELSE sector END,
  industry = CASE WHEN (industry IS NULL OR industry='' OR industry='Unknown') THEN :industry ELSE industry END,
  style_category = CASE WHEN (style_category IS NULL OR style_category='' OR style_category='Unknown') THEN :style_category ELSE style_category END,
  updated_at = datetime('now')
WHERE ticker = :ticker
"""

def classify(ticker: str) -> Tuple[str, str, str]:
    t = ticker.upper()
    for pattern, triple in RULES:
        if pattern.match(t):
            return triple
    return FALLBACK

def main():
    ap = argparse.ArgumentParser(description='Heuristically classify ETFs (sector/industry/style_category)')
    default_db = 'at_data.sqlite'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(script_dir, default_db)
    if os.path.exists(candidate):
        default_db = candidate
    ap.add_argument('--db', default=default_db, help='SQLite DB path')
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print('Database not found:', args.db)
        return 1
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    rows = cur.execute(SELECT_ETFS).fetchall()
    if not rows:
        print('No ETF rows require classification.')
        return 0
    updated = 0
    for idx, (ticker, sector, industry, style_cat) in enumerate(rows, 1):
        new_sector, new_industry, new_style = classify(ticker)
        cur.execute(UPDATE_SQL, {
            'ticker': ticker,
            'sector': new_sector,
            'industry': new_industry,
            'style_category': new_style,
        })
        if cur.rowcount:
            updated += 1
        print(f"{idx}/{len(rows)} {ticker}: sector={new_sector} industry={new_industry} style={new_style} (updated={cur.rowcount})")
        if idx % 50 == 0:
            conn.commit()
    conn.commit()
    print(f"Done. ETF rows updated: {updated}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
