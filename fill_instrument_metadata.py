import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'at_data.sqlite')

# Static defaults (no external lookup)
DEFAULT_SECTOR = 'Unknown'
DEFAULT_INDUSTRY = 'Unknown'
DEFAULT_COUNTRY = 'US'
DEFAULT_CURRENCY = 'USD'
DEFAULT_TYPE = 'stock'

UPDATE_SQL = """
UPDATE instruments
SET
    sector = COALESCE(NULLIF(sector, ''), :sector),
    industry = COALESCE(NULLIF(industry, ''), :industry),
    country = COALESCE(NULLIF(country, ''), :country),
    currency = COALESCE(NULLIF(currency, ''), :currency),
    instrument_type = COALESCE(NULLIF(instrument_type, ''), :itype),
    updated_at = datetime('now')
WHERE ticker IN (
    SELECT ticker FROM instruments
    WHERE (sector IS NULL OR sector = '')
       OR (industry IS NULL OR industry = '')
       OR (country IS NULL OR country = '')
       OR (currency IS NULL OR currency = '')
       OR (instrument_type IS NULL OR instrument_type = '')
)
"""

COUNT_GAPS = """
SELECT 
    SUM(CASE WHEN sector IS NULL OR sector = '' THEN 1 ELSE 0 END) AS missing_sector,
    SUM(CASE WHEN industry IS NULL OR industry = '' THEN 1 ELSE 0 END) AS missing_industry,
    SUM(CASE WHEN country IS NULL OR country = '' THEN 1 ELSE 0 END) AS missing_country,
    SUM(CASE WHEN currency IS NULL OR currency = '' THEN 1 ELSE 0 END) AS missing_currency,
    SUM(CASE WHEN instrument_type IS NULL OR instrument_type = '' THEN 1 ELSE 0 END) AS missing_type
FROM instruments
"""

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f'Database not found at {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(COUNT_GAPS)
        before = cur.fetchone()
        print('Before fill:', before)

        cur.execute(UPDATE_SQL, {
            'sector': DEFAULT_SECTOR,
            'industry': DEFAULT_INDUSTRY,
            'country': DEFAULT_COUNTRY,
            'currency': DEFAULT_CURRENCY,
            'itype': DEFAULT_TYPE,
        })
        affected = cur.rowcount
        conn.commit()

        cur.execute(COUNT_GAPS)
        after = cur.fetchone()
        print('After fill:', after)
        print(f'Rows updated: {affected}')
    finally:
        conn.close()

if __name__ == '__main__':
    main()
