"""
Test script for the simplified strategy execution system.

This script tests the new synchronous strategy execution service
without requiring the full FastAPI server to be running.
"""

import sys
import time
import sqlite3
from pathlib import Path

# Add the current directory to the Python path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.strategy_execution_service import StrategyExecutionService
from backend.services.bullish_breakout_service import BullishBreakoutService


def create_test_database():
    """Create a simple in-memory database for testing."""
    # Use check_same_thread=False to allow cross-thread access
    db = sqlite3.connect(':memory:', check_same_thread=False)
    
    # Create simplified tables for testing
    db.execute('''
        CREATE TABLE strategy_run (
            run_id TEXT PRIMARY KEY,
            strategy_code TEXT,
            execution_status TEXT,
            total_count INTEGER,
            processed_count INTEGER DEFAULT 0,
            qualifying_count INTEGER DEFAULT 0,
            current_ticker TEXT,
            progress_percent REAL DEFAULT 0.0,
            execution_started_at TEXT,
            last_progress_update TEXT,
            execution_time_ms INTEGER,
            summary TEXT
        )
    ''')
    
    db.execute('''
        CREATE TABLE strategy_execution_progress (
            run_id TEXT,
            ticker TEXT,
            sequence_number INTEGER,
            processed_at TEXT,
            passed BOOLEAN,
            score REAL,
            classification TEXT,
            error_message TEXT,
            processing_time_ms INTEGER,
            PRIMARY KEY (run_id, ticker)
        )
    ''')
    
    db.commit()
    return db


def test_strategy_execution_service():
    """Test the strategy execution service with a small ticker list."""
    print("Testing Simplified Strategy Execution Service")
    print("=" * 50)
    
    # Create test database
    print("Creating test database...")
    db = create_test_database()
    
    # Create execution service
    print("Initializing strategy execution service...")
    service = StrategyExecutionService(db)
    
    # Test strategy listing
    print("\nTesting strategy listing...")
    strategies = service.list_available_strategies()
    print(f"Available strategies: {strategies}")
    
    # Test strategy info
    if strategies:
        strategy_code = strategies[0]['code']
        print(f"\nTesting strategy info for '{strategy_code}'...")
        info = service.get_strategy_info(strategy_code)
        print(f"Strategy info: {info}")
        
        # Test strategy execution
        print(f"\nTesting strategy execution for '{strategy_code}'...")
        test_tickers = ["AAPL", "MSFT", "GOOGL"]
        test_parameters = {
            "min_volume": 1000000,
            "min_price": 10.0
        }
        
        start_time = time.time()
        
        try:
            result = service.execute_strategy_sync(
                strategy_code=strategy_code,
                tickers=test_tickers,
                parameters=test_parameters
            )
            
            execution_time = time.time() - start_time
            
            print(f"\nExecution completed in {execution_time:.2f} seconds")
            print(f"Strategy: {strategy_code}")
            print(f"Total evaluated: {result.total_evaluated}")
            print(f"Qualifying count: {result.qualifying_count}")
            print(f"Execution time (ms): {result.execution_time_ms}")
            print(f"Summary metrics: {result.summary_metrics}")
            
            if result.qualifying_stocks:
                print(f"\nQualifying tickers:")
                for ticker_result in result.qualifying_stocks:
                    print(f"  - {ticker_result.ticker}: {ticker_result.score:.2f} ({ticker_result.classification})")
            else:
                print("\nNo qualifying tickers found")
                
            # Test progress retrieval (should show completed)
            print(f"\nTesting progress retrieval...")
            progress = service.get_execution_progress(result.run_id)
            if progress:
                print(f"Progress: {progress['progress_percent']:.1f}% - Status: {progress['status']}")
                print(f"Processed: {progress['processed_count']}/{progress['total_count']}")
            
            # Test results retrieval
            print(f"\nTesting results retrieval...")
            results = service.get_execution_results(result.run_id)
            if results:
                print(f"Results status: {results['status']}")
                print(f"Qualifying results: {len(results['qualifying_results'])}")
                print(f"Total results: {len(results['all_results'])}")
            
            return True
            
        except Exception as e:
            print(f"Execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    else:
        print("No strategies available for testing")
        return False


def test_bullish_service_directly():
    """Test the bullish breakout service directly."""
    print("\n" + "=" * 50)
    print("Testing BullishBreakoutService Directly")
    print("=" * 50)
    
    try:
        service = BullishBreakoutService()
        
        print(f"Strategy Code: {service.get_strategy_code()}")
        print(f"Strategy Name: {service.get_strategy_name()}")
        print(f"Default Parameters: {service.get_default_parameters()}")
        
        # Test validation
        test_params = {
            'tickers': ['AAPL'],
            'min_volume': 1000000
        }
        
        is_valid = service.validate_parameters(test_params)
        print(f"Parameter validation: {is_valid}")
        
        if is_valid:
            print("\nExecuting strategy directly...")
            
            def simple_progress_callback(**kwargs):
                stage = kwargs.get('stage', 'unknown')
                if stage == 'evaluation':
                    ticker = kwargs.get('ticker', '')
                    passed = kwargs.get('passed', False)
                    score = kwargs.get('score', 0)
                    print(f"  {ticker}: {'PASS' if passed else 'FAIL'} (Score: {score:.2f})")
            
            # Import the progress callback class
            from backend.services.base_strategy_service import ProgressCallback
            progress_callback = ProgressCallback(simple_progress_callback)
            
            result = service.execute(['AAPL', 'MSFT'], test_params, progress_callback)
            
            print(f"\nDirect execution result:")
            print(f"Total evaluated: {result.total_evaluated}")
            print(f"Qualifying count: {result.qualifying_count}")
            print(f"Execution time (ms): {result.execution_time_ms}")
            
            return True
        else:
            print("Parameter validation failed")
            return False
            
    except Exception as e:
        print(f"Direct service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Simplified Strategy Execution System Test")
    print("========================================")
    
    # Test the service directly first
    direct_success = test_bullish_service_directly()
    
    # Test the full execution service
    service_success = test_strategy_execution_service()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Direct service test: {'PASS' if direct_success else 'FAIL'}")
    print(f"Execution service test: {'PASS' if service_success else 'FAIL'}")
    
    if direct_success and service_success:
        print("\nAll tests passed! The simplified execution system is working correctly.")
    else:
        print("\nSome tests failed. Check the error messages above.")