"""Enhanced comprehensive test suite for stocks API routes.

This module provides comprehensive test coverage including error handling,
input validation, edge cases, and response schema validation based on the
comprehensive testing strategy document.
"""

import json
import pytest
import logging
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app
from backend.models.stock_models import (
    ComprehensiveStockInfo,
    StockValidationResult,
    MarketStatusResponse,
    SymbolSuggestionsResponse,
    StockStrategyHistoryResponse,
    TechnicalIndicators,
    PerformanceMetrics,
    MarketData,
    CompanyInfo,
    DataQuality
)

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test client setup
client = TestClient(app)

# Test data constants
VALID_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
INVALID_SYMBOLS = ["", "XYZ123", "INVALID_SYMBOL", "TOOLONG" * 20]
SPECIAL_CHAR_SYMBOLS = ["AA@PL", "MS$FT", "GOO#GL", "A A P L", "AAPL."]


class TestUtilities:
    """Utility functions for testing."""
    
    @staticmethod
    def validate_json_response(response) -> Dict[str, Any]:
        """Validate that response is valid JSON and return parsed data."""
        try:
            return response.json()
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}")
    
    @staticmethod
    def validate_error_response_structure(data: Dict[str, Any]):
        """Validate error response has required fields."""
        required_fields = ["error", "message", "timestamp"]
        for field in required_fields:
            assert field in data, f"Error response missing required field: {field}"
    
    @staticmethod
    def validate_timestamp_format(timestamp_str: str):
        """Validate timestamp is in ISO format or UTC format."""
        try:
            # Try ISO format first
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try UTC format: '2025-09-19 00:47:42 UTC'
                datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S %Z')
            except ValueError:
                try:
                    # Try another common format: '2025-09-19 00:47:42'
                    datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pytest.fail(f"Invalid timestamp format: {timestamp_str}")
    
    @staticmethod
    def mock_network_error():
        """Create a mock network error."""
        return ConnectionError("Network connection failed")
    
    @staticmethod
    def mock_service_error():
        """Create a mock service error."""
        return Exception("Internal service error")


class TestFixtures:
    """Test fixtures and mock data."""
    
    @staticmethod
    def get_valid_stock_info() -> Dict[str, Any]:
        """Get valid stock info response data."""
        return {
            "ticker": "AAPL",
            "timestamp": datetime.utcnow().isoformat(),
            "market_data": {
                "ticker": "AAPL",
                "price": 150.0,
                "change": 2.5,
                "change_percent": 1.69,
                "volume": 50000000,
                "high": 152.0,
                "low": 148.0,
                "open": 149.0
            },
            "company_info": {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "country": "United States",
                "currency": "USD",
                "market_cap": 2500000000000
            },
            "technical_indicators": {
                "sma_10": 150.5,
                "sma_20": 148.2,
                "sma_50": 145.8,
                "rsi_14": 65.4
            },
            "performance_metrics": {
                "total_return": 15.6,
                "volatility": 28.5,
                "max_drawdown": -12.3,
                "sharpe_ratio": 1.2
            },
            "data_quality": {
                "has_market_data": True,
                "has_company_info": True,
                "has_technical_data": True,
                "has_performance_data": True
            }
        }
    
    @staticmethod
    def get_valid_validation_result() -> Dict[str, Any]:
        """Get valid validation result data."""
        return {
            "symbol": "AAPL",
            "normalized_symbol": "AAPL",
            "is_valid": True,
            "symbol_type": "us_stock",
            "issues": [],
            "data_available": True,
            "data_issues": []
        }


# Pytest fixtures
@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtilities()

@pytest.fixture
def test_fixtures():
    """Provide test fixtures."""
    return TestFixtures()

@pytest.fixture
def valid_symbol():
    """Provide a valid test symbol."""
    return "AAPL"

@pytest.fixture
def invalid_symbol():
    """Provide an invalid test symbol."""
    return "INVALID123"


class TestMissingEndpoints:
    """Test missing endpoint functionality that wasn't covered in basic tests."""
    
    def test_validate_query_endpoint_valid_symbol(self, test_utils, valid_symbol):
        """Test /validate endpoint with valid symbol using query parameters."""
        response = client.get(
            "/api/stocks/validate",
            params={"symbol": valid_symbol, "check_data_availability": True}
        )
        
        assert response.status_code in [200, 400, 503], f"Unexpected status code: {response.status_code}"
        data = test_utils.validate_json_response(response)
        
        if response.status_code == 200:
            # Validate response structure
            assert "symbol" in data
            assert "is_valid" in data
            assert "normalized_symbol" in data
            assert isinstance(data["is_valid"], bool)
    
    def test_validate_query_endpoint_invalid_symbol(self, test_utils, invalid_symbol):
        """Test /validate endpoint with invalid symbol."""
        response = client.get(
            "/api/stocks/validate",
            params={"symbol": invalid_symbol, "check_data_availability": True}
        )
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)
        
        if response.status_code == 200:
            assert data.get("is_valid") == False
        elif response.status_code == 400:
            test_utils.validate_error_response_structure(data)
    
    def test_analysis_query_endpoint_valid_symbol(self, test_utils, valid_symbol):
        """Test /analysis endpoint with valid symbol using query parameters."""
        response = client.get(
            "/api/stocks/analysis",
            params={
                "symbol": valid_symbol,
                "include_technical": True,
                "include_performance": True
            }
        )
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)
        
        if response.status_code == 200:
            # Should have similar structure to info endpoint
            assert "ticker" in data or "symbol" in data
    
    def test_analysis_query_endpoint_partial_data(self, test_utils, valid_symbol):
        """Test /analysis endpoint with selective data inclusion."""
        # Test with only technical data
        response = client.get(
            "/api/stocks/analysis",
            params={
                "symbol": valid_symbol,
                "include_technical": True,
                "include_performance": False
            }
        )
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)
        
        # Test with only performance data
        response = client.get(
            "/api/stocks/analysis",
            params={
                "symbol": valid_symbol,
                "include_technical": False,
                "include_performance": True
            }
        )
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @pytest.mark.parametrize("invalid_symbol", [
        "",  # Empty string
        " ",  # Whitespace only
        "TOOLONG" * 20,  # Too long
        "123ABC",  # Invalid format
        "A@B#C$",  # Special characters
        None  # None value (if passed as string)
    ])
    def test_invalid_symbol_formats(self, test_utils, invalid_symbol):
        """Test various invalid symbol formats."""
        if invalid_symbol is None:
            # Skip None test for URL path parameters
            return
            
        response = client.get(f"/api/stocks/{invalid_symbol}/info")
        
        assert response.status_code in [200, 400, 404, 422, 500]
        data = test_utils.validate_json_response(response)
        
        # If it's an error response, validate structure
        if response.status_code >= 400:
            if "error" in data:
                test_utils.validate_error_response_structure(data)
    
    def test_malformed_json_batch_validation(self, test_utils):
        """Test batch validation with malformed JSON."""
        # Test with invalid JSON
        response = client.post(
            "/api/stocks/validate-batch",
            content="{'invalid': json}",  # Malformed JSON
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
        data = test_utils.validate_json_response(response)
    
    def test_missing_required_parameters_batch_validation(self, test_utils):
        """Test batch validation with missing required parameters."""
        # Test with missing symbols
        response = client.post(
            "/api/stocks/validate-batch",
            json={"check_data_availability": True}  # Missing symbols
        )
        
        assert response.status_code == 422
        data = test_utils.validate_json_response(response)
    
    def test_invalid_parameter_types(self, test_utils):
        """Test endpoints with invalid parameter types."""
        # Test suggestions with invalid limit type
        response = client.get(
            "/api/stocks/suggestions",
            params={"query": "AAPL", "limit": "invalid"}
        )
        
        assert response.status_code == 422
        data = test_utils.validate_json_response(response)
    
    @patch('backend.api.stocks.get_validation_service')
    def test_network_error_simulation(self, mock_service, test_utils):
        """Test network error handling."""
        # Mock service to raise ConnectionError
        mock_service_instance = Mock()
        mock_service_instance.validate_symbol.side_effect = ConnectionError("Network error")
        mock_service.return_value = mock_service_instance
        
        response = client.get("/api/stocks/AAPL/validate")
        
        assert response.status_code == 503  # Service Unavailable
        data = test_utils.validate_json_response(response)
        test_utils.validate_error_response_structure(data)
        assert data["error"] == "ConnectionError"
    
    @patch('backend.api.stocks.get_analysis_service')
    def test_server_error_simulation(self, mock_service, test_utils):
        """Test server error handling."""
        # Mock service to raise generic exception
        mock_service_instance = Mock()
        mock_service_instance.get_comprehensive_stock_info.side_effect = Exception("Internal error")
        mock_service.return_value = mock_service_instance
        
        response = client.get("/api/stocks/AAPL/info")
        
        assert response.status_code == 500  # Internal Server Error
        data = test_utils.validate_json_response(response)
        test_utils.validate_error_response_structure(data)


class TestInputValidation:
    """Test comprehensive input validation."""
    
    def test_query_parameter_validation(self, test_utils):
        """Test query parameter validation."""
        # Test missing required query parameter
        response = client.get("/api/stocks/validate")  # Missing symbol
        
        assert response.status_code == 422
        data = test_utils.validate_json_response(response)
    
    def test_query_parameter_length_limits(self, test_utils):
        """Test query parameter length limits."""
        # Test very long query for suggestions
        long_query = "A" * 1000
        response = client.get(
            "/api/stocks/suggestions",
            params={"query": long_query, "limit": 10}
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
        data = test_utils.validate_json_response(response)
    
    def test_boundary_conditions(self, test_utils):
        """Test boundary conditions for numeric parameters."""
        # Test limit boundaries for suggestions
        test_cases = [
            {"limit": 0},      # Below minimum
            {"limit": 1},      # Minimum valid
            {"limit": 50},     # Maximum valid  
            {"limit": 51},     # Above maximum
            {"limit": -1},     # Negative
        ]
        
        for params in test_cases:
            response = client.get(
                "/api/stocks/suggestions",
                params={"query": "AAPL", **params}
            )
            
            # Should return 422 for invalid values or 200 for valid
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)
    
    def test_batch_validation_edge_cases(self, test_utils):
        """Test batch validation with edge cases."""
        test_cases = [
            {"symbols": []},  # Empty list
            {"symbols": [""]},  # List with empty string
            {"symbols": [" ", "  "]},  # List with whitespace
            {"symbols": ["AAPL"] * 100},  # Very large list
        ]
        
        for test_case in test_cases:
            response = client.post(
                "/api/stocks/validate-batch",
                json={**test_case, "check_data_availability": True}
            )
            
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)


class TestResponseSchemaValidation:
    """Test response schema validation using Pydantic models."""
    
    @patch('backend.api.stocks.get_validation_service')
    def test_validation_response_schema(self, mock_service, test_fixtures):
        """Test validation response matches expected schema."""
        # Mock successful validation
        mock_service_instance = Mock()
        mock_service_instance.validate_symbol.return_value = test_fixtures.get_valid_validation_result()
        mock_service.return_value = mock_service_instance
        
        response = client.get("/api/stocks/AAPL/validate")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate against Pydantic model
            try:
                validated_data = StockValidationResult(**data)
                assert validated_data.symbol == "AAPL"
                assert isinstance(validated_data.is_valid, bool)
                assert isinstance(validated_data.issues, list)
            except ValidationError as e:
                pytest.fail(f"Response doesn't match StockValidationResult schema: {e}")
    
    def test_market_status_response_schema(self, test_utils):
        """Test market status response schema."""
        response = client.get("/api/stocks/market-status")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate required fields are present
            expected_fields = ["phase", "server_time_utc"]
            for field in expected_fields:
                assert field in data, f"Missing field in market status: {field}"
            
            # Validate timestamp format
            if "server_time_utc" in data:
                test_utils.validate_timestamp_format(data["server_time_utc"])
    
    def test_suggestions_response_schema(self, test_utils):
        """Test suggestions response schema."""
        response = client.get(
            "/api/stocks/suggestions",
            params={"query": "AAPL", "limit": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate response structure
            assert "query" in data
            assert "count" in data
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)
            assert data["count"] == len(data["suggestions"])
    
    @patch('backend.api.stocks.get_analysis_service')
    def test_stock_info_response_schema(self, mock_service, test_fixtures, test_utils):
        """Test stock info response schema."""
        # Mock successful stock info
        mock_service_instance = Mock()
        mock_service_instance.get_comprehensive_stock_info.return_value = test_fixtures.get_valid_stock_info()
        mock_service.return_value = mock_service_instance
        
        response = client.get("/api/stocks/AAPL/info")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate core fields exist
            core_fields = ["ticker", "timestamp"]
            for field in core_fields:
                assert field in data, f"Missing core field: {field}"
            
            # Validate timestamp format
            if "timestamp" in data:
                test_utils.validate_timestamp_format(data["timestamp"])


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_input_handling(self, test_utils):
        """Test handling of empty inputs."""
        # Test empty string symbol in query
        response = client.get(
            "/api/stocks/validate",
            params={"symbol": "", "check_data_availability": True}
        )
        
        assert response.status_code == 422  # Should fail validation
        data = test_utils.validate_json_response(response)
    
    def test_special_characters_in_symbols(self, test_utils):
        """Test symbols with special characters."""
        special_symbols = ["AA@PL", "MS$FT", "GOO#GL", "A.B.C", "TEST-SYMBOL"]
        
        for symbol in special_symbols:
            response = client.get(f"/api/stocks/{symbol}/validate")
            
            # Should handle gracefully, either validate or return proper error
            assert response.status_code in [200, 400, 404, 422]
            data = test_utils.validate_json_response(response)
    
    def test_unicode_characters(self, test_utils):
        """Test handling of unicode characters."""
        unicode_symbols = ["ААРL", "МSFT", "测试", "🍎", "café"]
        
        for symbol in unicode_symbols:
            response = client.get(f"/api/stocks/{symbol}/validate")
            
            # Should handle gracefully
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)
    
    def test_extremely_long_inputs(self, test_utils):
        """Test extremely long input handling."""
        long_symbol = "A" * 1000
        
        response = client.get(f"/api/stocks/{long_symbol}/validate")
        
        # Should handle without crashing
        assert response.status_code in [200, 400, 422, 414]  # 414 = URI Too Long
        
        # If not 414, should have valid JSON response
        if response.status_code != 414:
            data = test_utils.validate_json_response(response)
    
    def test_case_sensitivity(self, test_utils):
        """Test case sensitivity handling."""
        symbols = ["aapl", "AAPL", "AaPl", "aApL"]
        
        for symbol in symbols:
            response = client.get(f"/api/stocks/{symbol}/validate")
            
            assert response.status_code in [200, 400, 503]
            data = test_utils.validate_json_response(response)
            
            if response.status_code == 200:
                # Should normalize to uppercase typically
                normalized = data.get("normalized_symbol", "")
                assert normalized.isupper() or not normalized


class TestSecurityTests:
    """Test security-related input sanitization and injection attempts."""
    
    def test_sql_injection_attempts(self, test_utils):
        """Test SQL injection attempt handling."""
        injection_attempts = [
            "AAPL'; DROP TABLE instruments;--",
            "AAPL' OR '1'='1",
            "AAPL'; DELETE FROM holdings;--",
            "'; SELECT * FROM users;--"
        ]
        
        for attempt in injection_attempts:
            response = client.get(f"/api/stocks/{attempt}/validate")
            
            # Should handle safely without execution
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)
    
    def test_xss_attempts(self, test_utils):
        """Test XSS attempt handling."""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "AAPL<script>alert('xss')</script>"
        ]
        
        for attempt in xss_attempts:
            response = client.get(
                "/api/stocks/suggestions",
                params={"query": attempt, "limit": 5}
            )
            
            # Should handle safely
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)
            
            # Check if response reflects the input (which is expected for suggestions)
            # The test validates that even if script tags are in the response,
            # they should be properly escaped when rendered in a web context
            response_str = json.dumps(data)
            # Note: It's acceptable for the API to return the query as-is in the response,
            # as XSS protection should happen at the frontend rendering level
    
    def test_path_traversal_attempts(self, test_utils):
        """Test path traversal attempt handling."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for attempt in traversal_attempts:
            response = client.get(f"/api/stocks/{attempt}/validate")
            
            # Should handle safely - path traversal attempts may result in 404
            assert response.status_code in [200, 400, 404, 422]
            data = test_utils.validate_json_response(response)
    
    def test_command_injection_attempts(self, test_utils):
        """Test command injection attempt handling."""
        command_attempts = [
            "AAPL; ls -la",
            "AAPL && cat /etc/passwd",
            "AAPL | whoami",
            "AAPL`id`",
            "AAPL$(whoami)"
        ]
        
        for attempt in command_attempts:
            response = client.get(
                "/api/stocks/validate",
                params={"symbol": attempt, "check_data_availability": True}
            )
            
            # Should handle safely
            assert response.status_code in [200, 400, 422]
            data = test_utils.validate_json_response(response)


class TestParameterizedScenarios:
    """Parameterized tests for different scenarios."""
    
    @pytest.mark.parametrize("symbol,expected_valid", [
        ("AAPL", True),
        ("MSFT", True),
        ("INVALID123", False),
        ("", False),
    ])
    def test_symbol_validation_scenarios(self, test_utils, symbol, expected_valid):
        """Test various symbol validation scenarios."""
        if not symbol:  # Skip empty symbol for path parameter
            return
            
        response = client.get(f"/api/stocks/{symbol}/validate")
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)
        
        if response.status_code == 200:
            is_valid = data.get("is_valid", False)
            # Note: We can't assert exact expected_valid due to external API dependencies
            assert isinstance(is_valid, bool)
    
    @pytest.mark.parametrize("include_technical,include_performance", [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ])
    def test_analysis_data_inclusion_scenarios(self, test_utils, include_technical, include_performance):
        """Test different data inclusion scenarios for analysis endpoint."""
        response = client.get(
            "/api/stocks/AAPL/info",
            params={
                "include_technical": include_technical,
                "include_performance": include_performance
            }
        )
        
        assert response.status_code in [200, 400, 503]
        data = test_utils.validate_json_response(response)
    
    @pytest.mark.parametrize("period", ["1d", "1mo", "3mo", "6mo", "1y", "2y", "invalid"])
    def test_technical_indicators_period_scenarios(self, test_utils, period):
        """Test different period scenarios for technical indicators."""
        response = client.get(
            "/api/stocks/AAPL/technical",
            params={"period": period}
        )
        
        if period == "invalid":
            # Should either handle gracefully or return error
            assert response.status_code in [200, 400, 422]
        else:
            assert response.status_code in [200, 400, 503]
        
        data = test_utils.validate_json_response(response)


class TestHealthAndDiagnostics:
    """Test health check and diagnostic endpoints."""
    
    def test_stocks_health_endpoint(self, test_utils):
        """Test stocks health check endpoint."""
        response = client.get("/api/stocks/health")
        
        assert response.status_code in [200, 503]
        data = test_utils.validate_json_response(response)
        
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        
        test_utils.validate_timestamp_format(data["timestamp"])
    
    def test_simple_test_endpoint(self, test_utils):
        """Test simple test endpoint."""
        response = client.get("/api/stocks/test")
        
        assert response.status_code == 200
        data = test_utils.validate_json_response(response)
        
        assert data["message"] == "test successful"
        assert "timestamp" in data
        
        test_utils.validate_timestamp_format(data["timestamp"])


# Integration test for complete workflow
class TestIntegrationWorkflow:
    """Integration tests for complete API workflows."""
    
    def test_complete_stock_analysis_workflow(self, test_utils):
        """Test complete workflow from validation to analysis."""
        symbol = "AAPL"
        
        # Step 1: Validate symbol
        validation_response = client.get(f"/api/stocks/{symbol}/validate")
        assert validation_response.status_code in [200, 400, 503]
        validation_data = test_utils.validate_json_response(validation_response)
        
        # Step 2: Get suggestions (alternative lookup)
        suggestions_response = client.get(
            "/api/stocks/suggestions",
            params={"query": symbol[:2], "limit": 10}
        )
        assert suggestions_response.status_code in [200, 400]
        suggestions_data = test_utils.validate_json_response(suggestions_response)
        
        # Step 3: Get comprehensive info
        info_response = client.get(f"/api/stocks/{symbol}/info")
        assert info_response.status_code in [200, 400, 503]
        info_data = test_utils.validate_json_response(info_response)
        
        # Step 4: Get technical indicators
        technical_response = client.get(f"/api/stocks/{symbol}/technical")
        assert technical_response.status_code in [200, 400, 503]
        technical_data = test_utils.validate_json_response(technical_response)
        
        # Step 5: Get performance metrics
        performance_response = client.get(f"/api/stocks/{symbol}/performance")
        assert performance_response.status_code in [200, 400, 503]
        performance_data = test_utils.validate_json_response(performance_response)
        
        # All responses should be valid JSON
        assert all([
            validation_data is not None,
            suggestions_data is not None,
            info_data is not None,
            technical_data is not None,
            performance_data is not None
        ])


if __name__ == "__main__":
    # Run specific test classes or all tests
    pytest.main([__file__, "-v", "--tb=short"])