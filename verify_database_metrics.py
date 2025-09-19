#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify that actual SMA metrics are stored in the database strategy_result table.
"""
import sqlite3
import json

def verify_database_metrics():
    """Check actual metrics data in the database."""
    print("=== Verifying Database Metrics Storage ===")
    print()
    
    try:
        # Connect to database
        conn = sqlite3.connect('at_data.sqlite')
        cursor = conn.cursor()
        
        # Get recent strategy results with metrics (join with strategy_run for strategy_code)
        cursor.execute("""
            SELECT sr.run_id, sr.ticker, sr.metrics_json, sr.created_at, srun.strategy_code
            FROM strategy_result sr
            JOIN strategy_run srun ON sr.run_id = srun.run_id
            WHERE sr.metrics_json IS NOT NULL
            AND sr.metrics_json != '{}'
            AND sr.metrics_json != ''
            ORDER BY sr.created_at DESC
            LIMIT 5
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("ERROR: No strategy results with metrics found in database")
            return False
        
        print(f"SUCCESS: Found {len(results)} recent strategy results with metrics:")
        print()
        
        sma_found = False
        for i, (run_id, ticker, metrics_json, created_at, strategy_code) in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Run ID: {run_id}")
            print(f"  Strategy: {strategy_code}")
            print(f"  Ticker: {ticker}")
            print(f"  Created: {created_at}")
            
            try:
                metrics = json.loads(metrics_json)
                print(f"  Metrics keys: {list(metrics.keys())}")
                
                # Check for SMA values
                sma_keys = [k for k in metrics.keys() if 'sma' in k.lower()]
                if sma_keys:
                    sma_found = True
                    print(f"  SUCCESS: SMA metrics found!")
                    for key in sma_keys:
                        print(f"     {key}: {metrics[key]}")
                else:
                    print(f"  WARNING: No SMA metrics in this result")
                    # Print all metrics for debugging
                    for key, value in metrics.items():
                        print(f"     {key}: {value}")
                    
            except json.JSONDecodeError:
                print(f"  ERROR: Invalid JSON in metrics_json: {metrics_json}")
            
            print()
        
        conn.close()
        
        if sma_found:
            print("SUCCESS: SMA metrics are properly stored in database!")
            return True
        else:
            print("ISSUE: No SMA metrics found in recent results")
            return False
            
    except Exception as e:
        print(f"ERROR: Database verification failed: {e}")
        return False

if __name__ == "__main__":
    verify_database_metrics()