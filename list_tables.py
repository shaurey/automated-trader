import sqlite3, sys, os
path = sys.argv[1] if len(sys.argv)>1 else 'at_data.sqlite'
print('DB Path:', os.path.abspath(path), 'Exists:', os.path.exists(path))
if not os.path.exists(path):
    sys.exit(1)
con = sqlite3.connect(path)
print('Tables:')
for (name,) in con.execute("select name from sqlite_master where type='table' order by name"):
    print(' -', name)
