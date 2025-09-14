#!/usr/bin/env python3
"""Simple test for backend components without Unicode characters."""

import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_all():
    """Test all backend components."""
    print("Testing Automated Trading Backend Components")
    print("=" * 50)
    
    # Test 1: Database Connection
    print("\n1. Testing Database Connection...")
    try:
        from database.connection import get_db_manager
        
        db_manager = get_db_manager()
        print(f"   Database path: {db_manager.db_path}")
        
        result = db_manager.execute_query("SELECT COUNT(*) FROM holdings")
        holdings_count = result[0][0] if result else 0
        
        result = db_manager.execute_query("SELECT COUNT(*) FROM instruments") 
        instruments_count = result[0][0] if result else 0
        
        print(f"   Holdings count: {holdings_count}")
        print(f"   Instruments count: {instruments_count}")
        print("   [PASS] Database connection successful")
        
    except Exception as e:
        print(f"   [FAIL] Database connection failed: {e}")
        return False
    
    # Test 2: Holdings Service
    print("\n2. Testing Holdings Service...")
    try:
        from database.connection import get_db_manager
        from services.market_data_service import MarketDataService
        from services.holdings_service import HoldingsService
        
        db_manager = get_db_manager()
        market_service = MarketDataService()
        holdings_service = HoldingsService(db_manager, market_service)
        
        # Test portfolio summary
        summary = holdings_service.get_portfolio_summary()
        print(f"   Portfolio total value: {getattr(summary, 'total_value', 'N/A')}")
        
        # Test positions 
        positions = holdings_service.get_positions(limit=3)
        positions_count = len(getattr(positions, 'positions', []))
        print(f"   Positions retrieved: {positions_count}")
        print("   [PASS] Holdings service working")
        
    except Exception as e:
        print(f"   [FAIL] Holdings service failed: {e}")
        return False
    
    # Test 3: API Creation
    print("\n3. Testing FastAPI App Creation...")
    try:
        from main import create_app
        
        app = create_app()
        print(f"   App title: {app.title}")
        print(f"   App version: {app.version}")
        print("   [PASS] FastAPI app created successfully")
        
    except Exception as e:
        print(f"   [FAIL] FastAPI app creation failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("All tests passed! Backend is ready.")
    return True

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)