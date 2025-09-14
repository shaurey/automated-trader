#!/usr/bin/env python3

import os
import sys
sys.path.append('.')

from database.connection import get_database_connection, get_db_manager
import sqlite3

print("Testing health check database dependency...")

# Test get_db_manager directly
try:
    db_manager = get_db_manager()
    print(f"✅ get_db_manager() works: {db_manager.db_path}")
    
    # Test a query through the manager
    result = db_manager.execute_one("SELECT 1 as test")
    print(f"✅ Direct manager query works: {result}")
    
except Exception as e:
    print(f"❌ get_db_manager() failed: {e}")

# Test get_database_connection dependency (this is what health check uses)
try:
    print("\nTesting get_database_connection dependency...")
    for conn in get_database_connection():
        print(f"✅ get_database_connection() yielded connection: {type(conn)}")
        
        # Test the connection like the health check does
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        print(f"✅ Health check style query works: {result}")
        break  # Exit the generator
        
except Exception as e:
    print(f"❌ get_database_connection() failed: {e}")
    import traceback
    traceback.print_exc()

# Simulate what the health endpoint does exactly
print("\nSimulating exact health check logic...")
try:
    database_connected = True
    for db in get_database_connection():
        try:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            print("✅ Health check simulation: Database connected")
        except Exception as e:
            database_connected = False
            print(f"❌ Health check simulation failed: {e}")
        break
        
    print(f"Final result: database_connected = {database_connected}")
    
except Exception as e:
    print(f"❌ Health check simulation error: {e}")
    import traceback
    traceback.print_exc()