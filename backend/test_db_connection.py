#!/usr/bin/env python3
"""Test database connectivity and basic API functionality."""

import os
import sys
import traceback

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test direct database connection."""
    print("=== Testing Database Connection ===")
    try:
        from database.connection import get_db_manager
        
        db_manager = get_db_manager()
        print(f"Database path: {db_manager.db_path}")
        
        # Test basic query
        result = db_manager.execute_query("SELECT COUNT(*) FROM holdings")
        print(f"Holdings count: {result[0][0] if result else 'No result'}")
        
        result = db_manager.execute_query("SELECT COUNT(*) FROM instruments")
        print(f"Instruments count: {result[0][0] if result else 'No result'}")
        
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        traceback.print_exc()
        return False

def test_holdings_service():
    """Test holdings service functionality."""
    print("\n=== Testing Holdings Service ===")
    try:
        from database.connection import get_db_manager
        from services.market_data_service import MarketDataService
        from services.holdings_service import HoldingsService
        
        db_manager = get_db_manager()
        market_service = MarketDataService()
        holdings_service = HoldingsService(db_manager, market_service)
        
        # Test portfolio summary
        summary = holdings_service.get_portfolio_summary()
        print(f"Portfolio summary retrieved: {summary.total_value if hasattr(summary, 'total_value') else 'No value'}")
        
        # Test positions
        positions = holdings_service.get_positions(limit=5)
        print(f"Positions retrieved: {len(positions.positions) if hasattr(positions, 'positions') else 'No positions'}")
        
        print("✅ Holdings service test successful")
        return True
        
    except Exception as e:
        print(f"❌ Holdings service test failed: {e}")
        traceback.print_exc()
        return False

def test_api_imports():
    """Test that all API modules can be imported."""
    print("\n=== Testing API Imports ===")
    try:
        from main import create_app
        from api.holdings import router as holdings_router
        from api.health import router as health_router
        
        app = create_app()
        print(f"FastAPI app created: {app.title}")
        
        print("✅ API imports successful")
        return True
        
    except Exception as e:
        print(f"❌ API imports failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing Automated Trading Backend Components\n")
    
    tests = [
        test_database_connection,
        test_holdings_service,
        test_api_imports
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())