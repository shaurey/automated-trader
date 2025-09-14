#!/usr/bin/env python3

import os
import sys
sys.path.append('.')

# Test the database manager import and initialization
from database.connection import DatabaseManager, get_db_manager

print("Testing FastAPI database configuration...")

# Test the default path calculation
print(f"Current working directory: {os.getcwd()}")
print(f"__file__ would be: database/connection.py")

# Simulate the path calculation from DatabaseManager.__init__
default_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    "at_data.sqlite"
)
print(f"Calculated default path: {default_path}")
print(f"Absolute default path: {os.path.abspath(default_path)}")
print(f"Default path exists: {os.path.exists(default_path)}")

# Test environment variable
env_path = os.getenv("DATABASE_PATH", default_path)
print(f"Environment DATABASE_PATH: {os.getenv('DATABASE_PATH', 'Not set')}")
print(f"Final path used: {env_path}")
print(f"Final path exists: {os.path.exists(env_path)}")

# Test DatabaseManager initialization
try:
    db_manager = DatabaseManager()
    print(f"DatabaseManager initialized successfully")
    print(f"DatabaseManager.db_path: {db_manager.db_path}")
    
    # Test a simple query
    result = db_manager.execute_one("SELECT 1")
    print(f"Database query result: {result}")
    
except Exception as e:
    print(f"DatabaseManager error: {e}")

# Test get_db_manager
try:
    global_manager = get_db_manager()
    print(f"Global manager path: {global_manager.db_path}")
except Exception as e:
    print(f"Global manager error: {e}")