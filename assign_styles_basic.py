"""Assign simple style categories (growth, value, income) to instruments.

Fast, offline classification (no API calls) using static lists + rules:
 - Explicit growth and income sets below.
 - Anything not matched defaults to value (per requirement).
 - ETFs with common dividend / income symbols treated as income.

Usage:
  python assign_styles_basic.py --db at_data.sqlite [--overwrite]
"""
from __future__ import annotations
import argparse, sqlite3, datetime

GROWTH = {
    # Large cap tech / high-growth
    "AMZN","AAPL","MSFT","GOOGL","META","NVDA","NFLX","TSLA","AMD","NET","SNOW","CRWD","SHOP","PLTR","UBER","ABNB","PANW","QCOM","AVGO","ANET","ADBE","MU","SMCI","INMB","INKT","QUBT","QBTS","MSTR","RBLX","UPST","SOFI","APLD","ARM","SMH","AIQ","NVTS","VRT","RIOT","CORZ","BTCM","MESA","OPEN","ZS","DDOG","DOCN","DOCU","HOOD","LQDA","QS","QCOM","PROK","SOUN","RIVN","QNTM","QUBT","NVTS"
}

INCOME = {
    # Dividend / income focused equities & ETFs
    "KO","PEP","PG","T","VZ","XOM","CVX","JNJ","HDV","VYM","DVY","SCHD","JEPI","JEPQ","O","VIG","SPYD","SPYV","MO","ENB","LTC","IAU","GLD","DVY","VYM","SCHD","HDV","SPYD"
}

# Additional ETF heuristics for income classification
INCOME_KEYWORDS = {"DIV","YLD","YIELD","INCOME"}

ETF_INCOME_EXPLICIT = {"SCHD","DVY","VYM","HDV","SPYD","JEPI","JEPQ","VIG"}


def classify(ticker: str) -> str:
    t = ticker.upper()
    if t in INCOME or t in ETF_INCOME_EXPLICIT:
        return "income"
    if any(k in t for k in INCOME_KEYWORDS):
        return "income"
    if t in GROWTH:
        return "growth"
    # default rule
    return "value"


def main():
    ap = argparse.ArgumentParser(description="Assign simple style categories to instruments")
    ap.add_argument("--db", default="at_data.sqlite", help="SQLite DB path")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing non-empty style_category")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    if args.overwrite:
        cur.execute("SELECT ticker, style_category FROM instruments ORDER BY ticker")
    else:
        cur.execute("SELECT ticker, style_category FROM instruments WHERE style_category IS NULL OR style_category='' ORDER BY ticker")
    rows = cur.fetchall()
    if not rows:
        print("Nothing to classify.")
        return 0

    updated = 0
    for ticker, existing in rows:
        style = classify(ticker)
        if args.overwrite and (existing and existing.strip() and existing == style):
            continue
        if args.dry_run:
            print(f"{ticker}: {existing or '-'} -> {style}")
        else:
            cur.execute("UPDATE instruments SET style_category=?, updated_at=datetime('now') WHERE ticker=?", (style, ticker))
            updated += 1

    if not args.dry_run:
        con.commit()
        print(f"Updated {updated} instrument rows.")

    # Distribution
    print("\nStyle distribution:")
    for cat, cnt in cur.execute("SELECT style_category, COUNT(*) FROM instruments GROUP BY style_category ORDER BY COUNT(*) DESC"):
        print(f"  {cat or '(none)'}: {cnt}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
