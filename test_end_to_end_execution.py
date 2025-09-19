#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test end-to-end strategy execution to verify SMA metrics flow correctly.
"""
import sys
import os
import json
import sqlite3
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_small_strategy_execution():
    """Test a small strategy execution to verify metrics flow."""
    print("=== Testing End-to-End Strategy Execution ===")
    print()
    
    try:
        from backend.services.strategy_execution_service import StrategyExecutionService
        from backend.database.connection import get_db_connection
        
        # Get database connection
        db = get_db_connection()
        
        # Create execution service
        service = StrategyExecutionService(db)
        
        # Test with a very small set of tickers to minimize API calls
        test_tickers = ["AAPL", "MSFT"]  # Just 2 tickers for quick test
        
        test_params = {
            'period': '1y',      # Shorter period to speed up
            'interval': '1d',
            'min_score': 0,      # Lower threshold to get results
            'max_workers': 1,    # Single worker to avoid rate limits
            'test_mode': True    # If available
        }
        
        print(f"Testing strategy execution with {len(test_tickers)} tickers...")
        print(f"Parameters: {json.dumps(test_params, indent=2)}")
        print()
        
        # Store original metrics count
        cursor = db.execute("""
            SELECT COUNT(*) FROM strategy_result 
            WHERE metrics_json IS NOT NULL AND metrics_json != '{}'
        """)
        original_count = cursor.fetchone()[0]
        
        print(f"Original metrics count in database: {original_count}")
        print()
        
        # Execute strategy with small universe
        print("Starting strategy execution...")
        result = service.execute_bullish_breakout_strategy(
            universe=test_tickers,
            **test_params
        )
        
        print("Strategy execution completed!")
        print(f"Execution result: {result}")
        print()
        
        # Check for new metrics in database
        cursor = db.execute("""
            SELECT COUNT(*) FROM strategy_result 
            WHERE metrics_json IS NOT NULL AND metrics_json != '{}'
        """)
        new_count = cursor.fetchone()[0]
        
        print(f"New metrics count in database: {new_count}")
        added_metrics = new_count - original_count
        print(f"Metrics added during test: {added_metrics}")
        print()
        
        if added_metrics > 0:
            # Check the latest results for SMA metrics
            cursor = db.execute("""
                SELECT sr.ticker, sr.score, sr.classification, sr.metrics_json, srun.strategy_code
                FROM strategy_result sr
                JOIN strategy_run srun ON sr.run_id = srun.run_id
                WHERE sr.metrics_json IS NOT NULL 
                AND sr.metrics_json != '{}' 
                ORDER BY sr.created_at DESC 
                LIMIT 3
            """)
            
            latest_results = cursor.fetchall()
            print("Latest results with metrics:")
            
            sma_found = False
            for ticker, score, classification, metrics_json, strategy_code in latest_results:
                print(f"  Ticker: {ticker}")
                print(f"  Strategy: {strategy_code}")
                print(f"  Score: {score}")
                print(f"  Classification: {classification}")
                
                try:
                    metrics = json.loads(metrics_json)
                    sma_keys = [k for k in metrics.keys() if 'sma' in k.lower()]
                    if sma_keys:
                        sma_found = True
                        print(f"  SUCCESS: SMA metrics found!")
                        for key in ['sma10', 'sma50', 'sma200']:
                            if key in metrics:
                                print(f"     {key}: {metrics[key]}")
                    else:
                        print(f"  WARNING: No SMA metrics found")
                        print(f"  Available metrics: {list(metrics.keys())[:5]}...")
                        
                except json.JSONDecodeError:
                    print(f"  ERROR: Invalid JSON in metrics")
                
                print()
            
            if sma_found:
                print("SUCCESS: End-to-end test passed! SMA metrics are properly flowing through the system.")
                return True
            else:
                print("ISSUE: No SMA metrics found in latest results")
                return False
        else:
            print("WARNING: No new metrics were added during the test")
            print("This could indicate:")
            print("1. Strategy execution failed")
            print("2. Metrics are not being stored properly")
            print("3. Test tickers didn't pass the strategy criteria")
            return False
            
    except Exception as e:
        print(f"ERROR: End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    print("WARNING: This test will make real API calls and may take a few minutes.")
    print("It will test the complete data flow: strategy execution → metrics calculation → database storage")
    print()
    
    # Ask for confirmation
    import time
    print("Starting in 3 seconds... (Ctrl+C to cancel)")
    time.sleep(3)
    
    success = test_small_strategy_execution()
    if success:
        print("\n✅ END-TO-END TEST PASSED!")
    else:
        print("\n❌ END-TO-END TEST FAILED!")