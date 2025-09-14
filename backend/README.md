# Automated Trading Backend API

FastAPI-based backend for the automated trading application, providing RESTful API endpoints for holdings visualization and portfolio management.

## Features

- **Holdings Management**: Portfolio summary, position details, and account breakdowns
- **Instrument Data**: Metadata management for stocks, ETFs, and other securities
- **Market Data Integration**: Real-time price data using yfinance
- **Database Integration**: Built on existing SQLite database structure
- **API Documentation**: Automatic OpenAPI/Swagger documentation
- **Error Handling**: Comprehensive error handling and logging
- **Testing**: Unit tests for all endpoints

## Architecture

```
backend/
├── api/                    # FastAPI route handlers
│   ├── holdings.py        # Holdings and portfolio endpoints
│   ├── instruments.py     # Instrument and market data endpoints
│   └── health.py          # Health check endpoint
├── services/               # Business logic layer
│   ├── holdings_service.py     # Portfolio calculations and data
│   ├── instruments_service.py  # Instrument metadata management
│   └── market_data_service.py  # Real-time market data
├── models/                 # Pydantic response models
│   └── schemas.py         # API request/response schemas
├── database/               # Database layer
│   ├── connection.py      # SQLite connection management
│   └── models.py          # Database model definitions
├── tests/                 # Test suite
│   ├── test_main.py       # Main application tests
│   └── test_api.py        # API endpoint tests
├── main.py                # FastAPI application setup
└── requirements.txt       # Python dependencies
```

## Installation

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   Set the database path (optional):
   ```bash
   export DATABASE_PATH=/path/to/at_data.sqlite
   ```
   Default: `../at_data.sqlite` (relative to backend directory)

3. **Run the API Server**
   ```bash
   # Development server with auto-reload
   python main.py
   
   # Or using uvicorn directly
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - OpenAPI Schema: http://localhost:8000/openapi.json

## API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /api/health` - Health check

### Holdings & Portfolio

- `GET /api/holdings/summary` - Portfolio summary with allocations
- `GET /api/holdings/positions` - List positions with filtering
- `GET /api/holdings/accounts` - List accounts
- `GET /api/holdings/{ticker}` - Specific holding details
- `GET /api/holdings/stats` - Portfolio statistics

### Instruments & Market Data

- `GET /api/instruments` - List instruments with filtering
- `GET /api/instruments/{ticker}` - Instrument details
- `GET /api/instruments/{ticker}/market-data` - Instrument with market data
- `GET /api/instruments/search/{query}` - Search instruments
- `GET /api/market/prices?tickers=AAPL,MSFT` - Current market prices

### Metadata

- `GET /api/instruments/meta/sectors` - List sectors
- `GET /api/instruments/meta/industries` - List industries
- `GET /api/instruments/meta/types` - List instrument types
- `GET /api/instruments/stats` - Instrument statistics

## Database Integration

The API integrates with the existing SQLite database structure:

- **instruments**: Ticker metadata (sector, industry, type, etc.)
- **holdings**: Portfolio positions (account, ticker, quantity, cost basis)
- **strategy_run**: Strategy execution metadata
- **strategy_result**: Individual ticker strategy results

## Market Data

Real-time market data is provided through yfinance integration:

- **Price Caching**: 5-minute cache to reduce API calls
- **Batch Requests**: Efficient multi-ticker price fetching
- **Error Handling**: Graceful handling of unavailable data
- **Rate Limiting**: Built-in request throttling

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest backend/tests/

# Run with coverage
pytest backend/tests/ --cov=backend

# Run specific test file
pytest backend/tests/test_api.py -v
```

## Configuration

### Environment Variables

- `DATABASE_PATH`: Path to SQLite database file
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### CORS Configuration

The API is configured to allow cross-origin requests from common development servers:
- http://localhost:3000 (React)
- http://localhost:5173 (Vite)
- http://localhost:8080 (Generic)

## Development

### Adding New Endpoints

1. Create route handler in appropriate `api/` module
2. Add business logic to relevant service in `services/`
3. Define request/response models in `models/schemas.py`
4. Add tests in `tests/test_api.py`

### Database Schema Changes

The API uses the existing database schema from `db.py`. Any schema changes should be coordinated with the main application.

### Market Data Sources

Currently uses yfinance for market data. To add additional sources:
1. Extend `MarketDataService` in `services/market_data_service.py`
2. Add fallback mechanisms for data unavailability
3. Update caching strategy as needed

## Production Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY at_data.sqlite .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables for Production

```bash
DATABASE_PATH=/app/at_data.sqlite
LOG_LEVEL=INFO
```

### Reverse Proxy Configuration

Example nginx configuration:

```nginx
location /api/ {
    proxy_pass http://localhost:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Performance Considerations

- **Database Connection Pooling**: SQLite with WAL mode for better concurrency
- **Market Data Caching**: 5-minute cache reduces external API calls
- **Response Compression**: Enable gzip compression in production
- **Request Limiting**: Consider rate limiting for public deployments

## Monitoring

The API provides several monitoring endpoints:

- `/api/health` - Application health status
- `/api/holdings/stats` - Portfolio data statistics
- `/api/instruments/stats` - Instrument database statistics

Consider adding:
- Prometheus metrics endpoint
- Structured logging for analysis
- Database performance monitoring

## Integration with Frontend

This backend is designed to serve multiple frontend applications:

- **Flutter Web/Mobile**: Cross-platform applications
- **React/Vue Web Apps**: Traditional web applications
- **Data Analysis Tools**: Jupyter notebooks, Python scripts

All endpoints return JSON and follow REST conventions for easy integration.