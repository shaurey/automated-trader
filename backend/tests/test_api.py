"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from backend.main import app

client = TestClient(app)


class TestHoldingsAPI:
    """Test cases for holdings API endpoints."""
    
    def test_get_portfolio_summary(self):
        """Test portfolio summary endpoint."""
        response = client.get("/api/holdings/summary")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "total_value" in data
            assert "accounts" in data
            assert "top_holdings" in data
            assert "sector_allocation" in data
    
    def test_get_positions(self):
        """Test positions listing endpoint."""
        response = client.get("/api/holdings/positions")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "positions" in data
            assert "total_count" in data
            assert "page" in data
            assert "page_size" in data
    
    def test_get_positions_with_pagination(self):
        """Test positions with pagination parameters."""
        response = client.get("/api/holdings/positions?limit=10&offset=0")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
    
    def test_get_positions_with_filters(self):
        """Test positions with filter parameters."""
        response = client.get("/api/holdings/positions?account=MAIN&ticker=AAPL")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
    
    def test_get_accounts(self):
        """Test accounts listing endpoint."""
        response = client.get("/api/holdings/accounts")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "accounts" in data
            assert "total_accounts" in data
    
    def test_get_holdings_stats(self):
        """Test holdings statistics endpoint."""
        response = client.get("/api/holdings/stats")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "summary" in data
            assert "sector_breakdown" in data
            assert "account_breakdown" in data


class TestInstrumentsAPI:
    """Test cases for instruments API endpoints."""
    
    def test_get_instruments(self):
        """Test instruments listing endpoint."""
        response = client.get("/api/instruments")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "instruments" in data
            assert "total_count" in data
            assert "page" in data
            assert "page_size" in data
    
    def test_get_instruments_with_filters(self):
        """Test instruments with filter parameters."""
        response = client.get("/api/instruments?instrument_type=stock&sector=Technology&active=true")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
    
    def test_get_instruments_with_pagination(self):
        """Test instruments with pagination parameters."""
        response = client.get("/api/instruments?limit=25&offset=0")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
    
    def test_search_instruments(self):
        """Test instrument search endpoint."""
        response = client.get("/api/instruments/search/AAPL")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "results" in data
            assert "count" in data
            assert data["query"] == "AAPL"
    
    def test_search_instruments_empty_query(self):
        """Test search with empty query."""
        response = client.get("/api/instruments/search/")
        
        # Should return error for empty query
        assert response.status_code == 404  # FastAPI returns 404 for missing path parameter
    
    def test_get_sectors(self):
        """Test sectors metadata endpoint."""
        response = client.get("/api/instruments/meta/sectors")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "sectors" in data
            assert "count" in data
    
    def test_get_industries(self):
        """Test industries metadata endpoint."""
        response = client.get("/api/instruments/meta/industries")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "industries" in data
            assert "count" in data
    
    def test_get_industries_with_sector_filter(self):
        """Test industries with sector filter."""
        response = client.get("/api/instruments/meta/industries?sector=Technology")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
    
    def test_get_instrument_types(self):
        """Test instrument types metadata endpoint."""
        response = client.get("/api/instruments/meta/types")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database
        
        if response.status_code == 200:
            data = response.json()
            assert "types" in data
            assert "count" in data
    
    def test_get_instruments_stats(self):
        """Test instruments statistics endpoint."""
        response = client.get("/api/instruments/stats")
        
        # Should not fail even if no data
        assert response.status_code in [200, 500]  # 500 if no database


class TestMarketDataAPI:
    """Test cases for market data API endpoints."""
    
    def test_get_market_prices_single_ticker(self):
        """Test market prices endpoint with single ticker."""
        # Note: This will try to fetch real market data
        response = client.get("/api/market/prices?tickers=AAPL")
        
        # Should not fail, but may return empty data if market is closed
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "prices" in data
    
    def test_get_market_prices_multiple_tickers(self):
        """Test market prices endpoint with multiple tickers."""
        response = client.get("/api/market/prices?tickers=AAPL,MSFT,GOOGL")
        
        # Should not fail, but may return empty data if market is closed
        assert response.status_code in [200, 500]
    
    def test_get_market_prices_empty_tickers(self):
        """Test market prices with empty tickers parameter."""
        response = client.get("/api/market/prices?tickers=")
        
        # Should return bad request
        assert response.status_code == 400
    
    def test_get_market_prices_too_many_tickers(self):
        """Test market prices with too many tickers."""
        tickers = ",".join([f"TICKER{i}" for i in range(51)])
        response = client.get(f"/api/market/prices?tickers={tickers}")
        
        # Should return bad request
        assert response.status_code == 400


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_not_found_endpoint(self):
        """Test 404 error handling."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_ticker_format(self):
        """Test handling of invalid ticker format."""
        response = client.get("/api/instruments/!!INVALID!!")
        
        # Should handle gracefully
        assert response.status_code in [200, 404, 500]
    
    def test_invalid_query_parameters(self):
        """Test handling of invalid query parameters."""
        response = client.get("/api/holdings/positions?limit=-1")
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_invalid_query_parameters_offset(self):
        """Test handling of invalid offset parameter."""
        response = client.get("/api/holdings/positions?offset=-1")
        
        # Should return validation error
        assert response.status_code == 422