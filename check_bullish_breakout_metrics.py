#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check specifically for bullish_breakout strategy results with SMA metrics.
"""
import sqlite3
import json

def check_bullish_breakout_metrics():
    """Check bullish_breakout strategy results for SMA metrics."""
    print("=== Checking Bullish Breakout Strategy Metrics ===")
    print()
    
    try:
        # Connect to database
        conn = sqlite3.connect('at_data.sqlite')
        cursor = conn.cursor()
        
        # Check for bullish_breakout strategy results
        cursor.execute("""
            SELECT sr.run_id, sr.ticker, sr.metrics_json, sr.created_at, sr.score, sr.classification
            FROM strategy_result sr
            JOIN strategy_run srun ON sr.run_id = srun.run_id
            WHERE srun.strategy_code = 'bullish_breakout'
            AND sr.metrics_json IS NOT NULL 
            AND sr.metrics_json != '{}' 
            AND sr.metrics_json != ''
            ORDER BY sr.created_at DESC 
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("WARNING: No bullish_breakout strategy results with metrics found")
            
            # Check if there are any bullish_breakout results at all
            cursor.execute("""
                SELECT COUNT(*) FROM strategy_result sr
                JOIN strategy_run srun ON sr.run_id = srun.run_id
                WHERE srun.strategy_code = 'bullish_breakout'
            """)
            count = cursor.fetchone()[0]
            print(f"Total bullish_breakout results in database: {count}")
            
            if count > 0:
                # Check what metrics they have
                cursor.execute("""
                    SELECT sr.ticker, sr.metrics_json, sr.score
                    FROM strategy_result sr
                    JOIN strategy_run srun ON sr.run_id = srun.run_id
                    WHERE srun.strategy_code = 'bullish_breakout'
                    ORDER BY sr.created_at DESC 
                    LIMIT 5
                """)
                
                sample_results = cursor.fetchall()
                print("\nSample bullish_breakout results:")
                for ticker, metrics_json, score in sample_results:
                    print(f"  Ticker: {ticker}")
                    print(f"  Score: {score}")
                    print(f"  Metrics JSON: {metrics_json}")
                    print()
            
            return False
        
        print(f"SUCCESS: Found {len(results)} bullish_breakout strategy results with metrics:")
        print()
        
        sma_found = False
        for i, (run_id, ticker, metrics_json, created_at, score, classification) in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Run ID: {run_id}")
            print(f"  Ticker: {ticker}")
            print(f"  Score: {score}")
            print(f"  Classification: {classification}")
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
                    # Print first few metrics for debugging
                    metric_items = list(metrics.items())[:5]
                    for key, value in metric_items:
                        print(f"     {key}: {value}")
                    if len(metrics) > 5:
                        print(f"     ... and {len(metrics) - 5} more metrics")
                    
            except json.JSONDecodeError:
                print(f"  ERROR: Invalid JSON in metrics_json: {metrics_json}")
            
            print()
        
        conn.close()
        
        if sma_found:
            print("SUCCESS: SMA metrics found in bullish_breakout results!")
            return True
        else:
            print("ISSUE: No SMA metrics found in bullish_breakout results")
            return False
            
    except Exception as e:
        print(f"ERROR: Database verification failed: {e}")
        return False

if __name__ == "__main__":
    check_bullish_breakout_metrics()