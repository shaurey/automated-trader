import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'at_data.sqlite')

OPTION_PREFIX = '-'  # tickers starting with dash considered options artifacts

REMOVE_SQL = """
DELETE FROM instruments
WHERE ticker LIKE '-%'
"""

MISSING_HOLDINGS_SQL = """
SELECT DISTINCT h.ticker
FROM holdings h
LEFT JOIN instruments i ON h.ticker = i.ticker
WHERE i.ticker IS NULL AND h.quantity > 0
"""

INSERT_INSTRUMENT_SQL = """
INSERT INTO instruments (ticker, instrument_type, currency, active, updated_at)
VALUES (?, 'stock', 'USD', 1, datetime('now'))
"""

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f'Database not found at {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        # Delete option-like tickers
        cur.execute("SELECT COUNT(*) FROM instruments WHERE ticker LIKE '-%'")
        to_delete = cur.fetchone()[0]
        cur.execute(REMOVE_SQL)
        deleted = to_delete

        # Find missing holdings
        cur.execute(MISSING_HOLDINGS_SQL)
        missing = [row[0] for row in cur.fetchall()]

        inserted = 0
        for t in missing:
            if not t or t.startswith(OPTION_PREFIX):
                continue
            cur.execute(INSERT_INSTRUMENT_SQL, (t,))
            inserted += 1

        conn.commit()
        print(f"Removed option-like instrument rows: {deleted}")
        print(f"Inserted missing instruments from holdings: {inserted}")
        if missing:
            print("Example inserted tickers:", ', '.join(missing[:10]))
    finally:
        conn.close()

if __name__ == '__main__':
    main()
