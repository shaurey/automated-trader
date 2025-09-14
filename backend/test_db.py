#!/usr/bin/env python3

import sqlite3
import os

# Test database connectivity
db_path = "../at_data.sqlite"
abs_path = os.path.abspath(db_path)

print(f"Testing database at: {abs_path}")
print(f"File exists: {os.path.exists(abs_path)}")

try:
    conn = sqlite3.connect(abs_path)
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print(f"Basic query result: {result}")
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    
    cursor.close()
    conn.close()
    print("Database connection successful!")
    
except Exception as e:
    print(f"Database error: {e}")