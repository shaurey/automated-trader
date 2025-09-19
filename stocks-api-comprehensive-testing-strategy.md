# Stocks API Comprehensive Testing Strategy

## Executive Summary

This document outlines a comprehensive testing strategy for the Stocks API based on analysis of 13 core endpoints with current 90.9% test pass rate (10/11 tests passing). The strategy addresses critical gaps in error handling, input validation, schema validation, and external API dependency management through a prioritized implementation approach.

## Current State Analysis

### API Endpoints (13 Core Endpoints)
1. **Health & Status**
   - `GET /stocks/health` - Health check
   - `GET /stocks/test` - Simple test endpoint
   - `GET /stocks/market-status` - Market status with trading phases

2. **Stock Information & Analysis**
   - `GET /stocks/{symbol}/info` - Comprehensive stock information
   - `GET /stocks/{symbol}/analysis` - Duplicate path for comprehensive info
   - `GET /stocks/analysis` - Query-based stock analysis
   - `GET /stocks/{symbol}/technical` - Technical indicators
   - `GET /stocks/{symbol}/performance` - Performance metrics

3. **Symbol Validation**
   - `GET /stocks/{symbol}/validate` - Path-based symbol validation
   - `GET /stocks/validate` - Query-based symbol validation
   - `POST /stocks/validate-batch` - Batch validation ⚠️ **FAILING**
   - `GET /stocks/suggestions` - Symbol suggestions/autocomplete

4. **Data Management**
   - `GET /stocks/{symbol}/strategy-history` - Strategy execution history
   - `POST /stocks/add-instrument` - Add new instrument

### Critical Issues Identified

#### **PRIORITY 1: Failing Test**
- **`test_batch_validate`**: Sends incorrect payload format
  - **Current**: `json=[TEST_SYMBOL, ALT_SYMBOL]`
  - **Expected**: `json={"symbols": [TEST_SYMBOL, ALT_SYMBOL]}`
  - **Issue**: Missing [`BatchValidationRequest`](backend/api/stocks.py:52) wrapper structure

#### **PRIORITY 2: Missing Test Coverage**
- No tests for query-based endpoints (`/validate`, `/analysis`)
- Missing comprehensive error handling validation
- No schema validation using Pydantic models
- No mocking of external yfinance API calls
- No security testing for input sanitization

---

## Testing Strategy Implementation Plan

### Phase 1: Immediate Fixes (Critical Priority) ⚡

**Timeline**: 1-2 days  
**Success Criteria**: 100% test pass rate, all endpoints covered

#### 1.1 Fix Failing Test
```python
# Current failing test
def test_batch_validate():
    r = client.post("/api/stocks/validate-batch", 
                   params={"check_data_availability": True}, 
                   json=[TEST_SYMBOL, ALT_SYMBOL])  # ❌ Wrong format

# Fixed test
def test_batch_validate():
    payload = {"symbols": [TEST_SYMBOL, ALT_SYMBOL], "check_data_availability": True}
    r = client.post("/api/stocks/validate-batch", json=payload)  # ✅ Correct format
    assert r.status_code == 200
    data = r.json()
    assert "total_count" in data
    assert "valid_count" in data
    assert "results" in data
```

#### 1.2 Add Missing Endpoint Tests
```python
def test_validate_query_endpoint():
    """Test query-based validation endpoint"""
    r = client.get("/api/stocks/validate", params={"symbol": TEST_SYMBOL})
    assert r.status_code == 200
    data = r.json()
    assert "is_valid" in data

def test_analysis_query_endpoint():
    """Test query-based analysis endpoint"""
    r = client.get("/api/stocks/analysis", params={"symbol": TEST_SYMBOL})
    assert r.status_code in (200, 400, 500)
    _ = r.json()
```

### Phase 2: Enhanced Test Coverage (High Priority) 🎯

**Timeline**: 3-5 days  
**Success Criteria**: 90% code coverage, comprehensive error scenarios covered

#### 2.1 Comprehensive Error Handling Tests

**Invalid Symbol Testing**
```python
@pytest.mark.parametrize("invalid_symbol,expected_status", [
    ("", 422),           # Empty symbol
    ("INVALID123", 400), # Non-existent symbol
    ("TOO_LONG_SYMBOL_NAME", 400), # Oversized symbol
    ("special@chars", 400), # Special characters
    ("123", 400),        # Numeric only
])
def test_invalid_symbols(invalid_symbol, expected_status):
    r = client.get(f"/api/stocks/{invalid_symbol}/info")
    assert r.status_code == expected_status
    data = r.json()
    assert "error" in data
```

**Network Error Simulation**
```python
@patch('backend.services.stock_analysis_service.StockAnalysisService.get_comprehensive_stock_info')
def test_network_error_handling(mock_service):
    mock_service.side_effect = ConnectionError("Network timeout")
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/info")
    assert r.status_code == 503
    data = r.json()
    assert data["error"] == "ConnectionError"
```

#### 2.2 Input Validation Testing

**Boundary Condition Tests**
```python
def test_suggestions_limit_boundaries():
    # Test minimum limit
    r = client.get("/api/stocks/suggestions", params={"query": "AA", "limit": 1})
    assert r.status_code == 200
    
    # Test maximum limit
    r = client.get("/api/stocks/suggestions", params={"query": "AA", "limit": 50})
    assert r.status_code == 200
    
    # Test over maximum limit
    r = client.get("/api/stocks/suggestions", params={"query": "AA", "limit": 51})
    assert r.status_code == 422  # Validation error
```

**Malformed Request Testing**
```python
def test_batch_validate_malformed_requests():
    # Empty symbols array
    r = client.post("/api/stocks/validate-batch", json={"symbols": []})
    assert r.status_code == 400
    
    # Missing symbols field
    r = client.post("/api/stocks/validate-batch", json={"check_data_availability": True})
    assert r.status_code == 422
    
    # Invalid JSON structure
    r = client.post("/api/stocks/validate-batch", json="invalid")
    assert r.status_code == 422
```

#### 2.3 Schema Validation with Pydantic Models

```python
from backend.models.stock_models import (
    ComprehensiveStockInfo, 
    StockValidationResult,
    MarketStatusResponse
)

def test_comprehensive_info_schema_validation():
    """Validate response matches Pydantic schema"""
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/info")
    if r.status_code == 200:
        data = r.json()
        # Validate against Pydantic model
        validated_data = ComprehensiveStockInfo.model_validate(data)
        assert validated_data.ticker == TEST_SYMBOL
        assert validated_data.market_data is not None
        assert validated_data.company_info is not None

def test_validation_result_schema():
    """Validate validation response schema"""
    r = client.get(f"/api/stocks/{TEST_SYMBOL}/validate")
    if r.status_code == 200:
        data = r.json()
        validated_data = StockValidationResult.model_validate(data)
        assert validated_data.symbol == TEST_SYMBOL
```

#### 2.4 Edge Case Testing

```python
@pytest.mark.parametrize("symbol,expected_handling", [
    ("aapl", "case_insensitive"),     # Lowercase conversion
    ("AAPL.L", "international"),      # International symbols
    ("BRK.A", "class_shares"),        # Share classes
    ("SPY", "etf"),                   # ETFs
    ("^GSPC", "index"),               # Market indices
])
def test_symbol_edge_cases(symbol, expected_handling):
    r = client.get(f"/api/stocks/{symbol}/validate")
    assert r.status_code in (200, 400)
    data = r.json()
    if r.status_code == 200:
        assert data["normalized_symbol"] is not None
```

### Phase 3: Test Infrastructure Improvements (Medium Priority) 🏗️

**Timeline**: 4-6 days  
**Success Criteria**: Fast, reliable test execution with <2s total runtime

#### 3.1 Mock External API Dependencies

**yfinance API Mocking Strategy**
```python
# conftest.py
import pytest
from unittest.mock import Mock, patch
import yfinance as yf

@pytest.fixture
def mock_yfinance():
    """Mock yfinance responses for consistent testing"""
    with patch('yfinance.Ticker') as mock_ticker:
        # Setup mock data
        mock_instance = Mock()
        mock_instance.info = {
            'symbol': 'AAPL',
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'marketCap': 3000000000000,
            'regularMarketPrice': 150.0,
            'regularMarketChange': 2.5,
            'regularMarketChangePercent': 1.7
        }
        mock_instance.history.return_value = Mock()  # Historical data
        mock_ticker.return_value = mock_instance
        yield mock_instance

# Usage in tests
def test_stock_info_with_mock(mock_yfinance):
    r = client.get(f"/api/stocks/AAPL/info")
    assert r.status_code == 200
    data = r.json()
    assert data["company_info"]["company_name"] == "Apple Inc."
```

**Service Layer Mocking**
```python
@pytest.fixture
def mock_stock_services():
    """Mock stock service dependencies"""
    with patch('backend.api.stocks.get_analysis_service') as mock_analysis, \
         patch('backend.api.stocks.get_validation_service') as mock_validation:
        
        # Setup service mocks
        mock_analysis.return_value.get_comprehensive_stock_info.return_value = {
            "ticker": "AAPL",
            "market_data": {"price": 150.0},
            "company_info": {"company_name": "Apple Inc."}
        }
        
        mock_validation.return_value.validate_symbol.return_value = {
            "symbol": "AAPL",
            "is_valid": True,
            "normalized_symbol": "AAPL"
        }
        
        yield mock_analysis, mock_validation
```

#### 3.2 Test Fixtures and Data Management

```python
# fixtures.py
@pytest.fixture
def sample_stock_data():
    """Provide consistent test data"""
    return {
        "valid_symbols": ["AAPL", "MSFT", "GOOGL"],
        "invalid_symbols": ["INVALID", "123", ""],
        "international_symbols": ["AAPL.L", "SAP.DE"],
        "sample_responses": {
            "market_data": {
                "ticker": "AAPL",
                "price": 150.0,
                "change": 2.5,
                "volume": 50000000
            }
        }
    }

@pytest.fixture
def test_database():
    """Setup test database for strategy history tests"""
    # Setup test database with sample strategy results
    pass
```

#### 3.3 Performance Testing for Batch Operations

```python
import time
import pytest

def test_batch_validation_performance():
    """Test batch validation performance"""
    large_symbol_list = ["AAPL", "MSFT", "GOOGL"] * 10  # 30 symbols
    payload = {"symbols": large_symbol_list, "check_data_availability": False}
    
    start_time = time.time()
    r = client.post("/api/stocks/validate-batch", json=payload)
    end_time = time.time()
    
    assert r.status_code == 200
    assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
    
    data = r.json()
    assert data["total_count"] == 30

@pytest.mark.parametrize("symbol_count", [1, 5, 10, 25, 50])
def test_batch_validation_scaling(symbol_count):
    """Test how batch validation scales with input size"""
    symbols = [f"SYMBOL{i}" for i in range(symbol_count)]
    payload = {"symbols": symbols, "check_data_availability": False}
    
    start_time = time.time()
    r = client.post("/api/stocks/validate-batch", json=payload)
    execution_time = time.time() - start_time
    
    # Performance assertions
    assert execution_time < (symbol_count * 0.1)  # Max 100ms per symbol
```

#### 3.4 Security Testing

```python
def test_sql_injection_protection():
    """Test protection against SQL injection"""
    malicious_symbols = [
        "'; DROP TABLE instruments; --",
        "UNION SELECT * FROM users",
        "<script>alert('xss')</script>",
        "../../etc/passwd"
    ]
    
    for symbol in malicious_symbols:
        r = client.get(f"/api/stocks/{symbol}/info")
        # Should return 400 (bad request) not 500 (server error)
        assert r.status_code in (400, 422)
        data = r.json()
        assert "error" in data

def test_input_sanitization():
    """Test input sanitization for XSS protection"""
    xss_query = "<script>alert('xss')</script>"
    r = client.get("/api/stocks/suggestions", params={"query": xss_query})
    
    if r.status_code == 200:
        data = r.json()
        # Ensure no raw script tags in response
        response_str = str(data)
        assert "<script>" not in response_str
        assert "alert(" not in response_str
```

### Phase 4: Test Organization & Architecture (Medium Priority) 📁

**Timeline**: 2-3 days  
**Success Criteria**: Clean, maintainable test structure with clear separation of concerns

#### 4.1 Test File Organization

```
backend/tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests for individual components
│   ├── test_stock_models.py   # Pydantic model validation
│   ├── test_stock_services.py # Service layer unit tests
│   └── test_error_handling.py # Error handling logic
├── integration/                # Integration tests
│   ├── test_stocks_api.py     # Full API endpoint tests
│   ├── test_batch_operations.py # Batch processing tests
│   └── test_external_apis.py  # External API integration
├── performance/                # Performance and load tests
│   ├── test_response_times.py
│   └── test_batch_scaling.py
├── security/                   # Security-focused tests
│   ├── test_input_validation.py
│   └── test_injection_protection.py
└── fixtures/                   # Test data and utilities
    ├── sample_data.py
    └── mock_responses.py
```

#### 4.2 Parameterized Test Categories

```python
# test_categories.py
import pytest

# Test markers for categorization
pytestmark = [
    pytest.mark.stocks_api,
    pytest.mark.integration
]

class TestStockValidation:
    """Grouped validation tests"""
    
    @pytest.mark.parametrize("endpoint", [
        "/api/stocks/{symbol}/validate",
        "/api/stocks/validate"
    ])
    def test_validation_endpoints(self, endpoint, sample_stock_data):
        """Test both validation endpoint variants"""
        if "{symbol}" in endpoint:
            url = endpoint.format(symbol="AAPL")
            r = client.get(url)
        else:
            r = client.get(endpoint, params={"symbol": "AAPL"})
        
        assert r.status_code in (200, 400)

class TestStockAnalysis:
    """Grouped analysis tests"""
    
    @pytest.mark.parametrize("include_technical,include_performance", [
        (True, True),
        (True, False),
        (False, True),
        (False, False)
    ])
    def test_analysis_optional_sections(self, include_technical, include_performance):
        """Test analysis with different section combinations"""
        params = {
            "include_technical": include_technical,
            "include_performance": include_performance
        }
        r = client.get(f"/api/stocks/AAPL/info", params=params)
        
        if r.status_code == 200:
            data = r.json()
            if include_technical:
                assert "technical_indicators" in data
            if include_performance:
                assert "performance_metrics" in data
```

#### 4.3 Test Utilities and Helpers

```python
# test_utils.py
from typing import Dict, Any
import json

class StockAPITestHelper:
    """Helper class for stock API testing"""
    
    @staticmethod
    def assert_error_response(response, expected_status: int):
        """Assert response is a proper error with expected status"""
        assert response.status_code == expected_status
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
    
    @staticmethod
    def assert_successful_stock_info(response, symbol: str):
        """Assert response contains valid stock info"""
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == symbol
        assert "market_data" in data
        assert "company_info" in data
        assert "timestamp" in data
    
    @staticmethod
    def create_batch_validation_payload(symbols: list, check_data: bool = True):
        """Create properly formatted batch validation payload"""
        return {
            "symbols": symbols,
            "check_data_availability": check_data
        }

# Usage in tests
def test_with_helper():
    r = client.get("/api/stocks/AAPL/info")
    StockAPITestHelper.assert_successful_stock_info(r, "AAPL")
```

---

## Implementation Roadmap

### Week 1: Critical Fixes ⚡
- **Day 1**: Fix `test_batch_validate` payload format
- **Day 2**: Add missing endpoint tests (`/validate`, `/analysis`)
- **Day 3**: Validate 100% test pass rate

### Week 2: Enhanced Coverage 🎯
- **Days 1-2**: Implement comprehensive error handling tests
- **Days 3-4**: Add input validation and boundary testing
- **Day 5**: Implement Pydantic schema validation tests

### Week 3: Infrastructure & Mocking 🏗️
- **Days 1-2**: Implement yfinance API mocking
- **Days 3-4**: Add performance and security tests
- **Day 5**: Optimize test execution speed

### Week 4: Organization & Documentation 📁
- **Days 1-2**: Restructure test files and organization
- **Days 3-4**: Add test utilities and helpers
- **Day 5**: Documentation and CI/CD integration

---

## Success Criteria & Metrics

### **Critical Success Factors**
1. **✅ 100% Test Pass Rate**: All tests execute successfully
2. **🎯 90% Code Coverage**: Comprehensive coverage of API endpoints
3. **⚡ <2s Test Execution**: Fast feedback loop for development
4. **🔒 Security Validated**: Input sanitization and injection protection
5. **📊 Performance Benchmarked**: Batch operations meet SLA requirements

### **Quality Gates**
- **Phase 1**: 100% endpoint coverage, failing test fixed
- **Phase 2**: Error scenarios covered, schema validation implemented
- **Phase 3**: External dependencies mocked, performance benchmarks met
- **Phase 4**: Clean test architecture, comprehensive documentation

### **Monitoring & Reporting**
```python
# pytest configuration for coverage reporting
# pytest.ini
[tool:pytest]
addopts = 
    --cov=backend.api.stocks
    --cov=backend.services.stock_analysis_service
    --cov=backend.services.stock_validation_service
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
    --tb=short

markers =
    unit: Unit tests
    integration: Integration tests  
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
```

---

## Risk Mitigation

### **High-Risk Areas**
1. **External API Dependencies**: yfinance API rate limits and availability
   - **Mitigation**: Comprehensive mocking strategy, fallback mechanisms
2. **Database Dependencies**: Strategy history tests require DB state
   - **Mitigation**: Test database fixtures, transaction rollback
3. **Performance Degradation**: Adding comprehensive tests may slow CI/CD
   - **Mitigation**: Parallel test execution, test categorization

### **Fallback Strategies**
- **Graceful Degradation**: Tests continue even if external APIs fail
- **Mock Fallbacks**: Always provide mocked alternatives
- **Progressive Enhancement**: Implement testing in phases to maintain stability

---

## Conclusion

This comprehensive testing strategy addresses all critical gaps identified in the current stocks API testing approach. By implementing this plan in phases, we'll achieve robust, reliable, and maintainable test coverage while ensuring the API meets enterprise-grade quality standards.

The strategy emphasizes immediate problem resolution, comprehensive coverage, and long-term maintainability through proper test organization and infrastructure improvements.