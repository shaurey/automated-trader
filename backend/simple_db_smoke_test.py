from backend.database.connection import get_db_manager

dbm = get_db_manager()
print('single count row:', dbm.execute_one("SELECT COUNT(*) FROM holdings"))
print('first 3 holdings rows:')
for row in dbm.execute_query("SELECT ticker, quantity FROM holdings LIMIT 3"):
    print(dict(row))
