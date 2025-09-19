# Individual Stock Analysis Page Architecture

## Overview

This document outlines the comprehensive architecture for an individual stock analysis page that supports both analyzing existing strategy results AND researching new stocks, with real-time market data integration using the yfinance MCP server.

## System Context Analysis

### Existing Architecture
- **Backend**: FastAPI with SQLite database, comprehensive strategy execution system
- **Frontend**: Flutter web application with responsive navigation
- **Database Schema**: Instruments, holdings, strategy_run, strategy_result tables (v5)
- **APIs**: Instruments, strategies, holdings, market data endpoints
- **MCP Integration**: yfinance server available for real-time market data

### Core Requirements
1. **Mixed Use Case**: Analyze strategy results + research new stocks
2. **Real-time Integration**: Live market data, technical indicators, intraday charts
3. **Strategy Performance Tracking**: Historical results across multiple runs
4. **Stock Comparison**: Side-by-side analysis capabilities
5. **Instrument Management**: Add new stocks to database

## Architecture Components

## 1. API Specifications

### 1.1 Stock Analysis API Endpoints

#### GET `/api/stocks/{ticker}/analysis`
**Purpose**: Comprehensive stock analysis data aggregation
```typescript
interface StockAnalysisResponse {
  basic_info: StockBasicInfo;
  market_data: RealTimeMarketData;
  technical_indicators: TechnicalIndicators;
  fundamental_data: FundamentalData;
  strategy_history: StrategyHistoryData;
  comparison_metrics: ComparisonMetrics;
}

interface StockBasicInfo {
  ticker: string;
  company_name: string;
  sector: string;
  industry: string;
  market_cap: number;
  exchange: string;
  currency: string;
  description?: string;
  website?: string;
  employees?: number;
}

interface RealTimeMarketData {
  current_price: number;
  price_change: number;
  price_change_percent: number;
  volume: number;
  avg_volume: number;
  open: number;
  high: number;
  low: number;
  previous_close: number;
  market_cap: number;
  pe_ratio?: number;
  dividend_yield?: number;
  beta?: number;
  week_52_high: number;
  week_52_low: number;
  last_updated: string;
}

interface TechnicalIndicators {
  moving_averages: {
    sma_10: number;
    sma_20: number;
    sma_50: number;
    sma_200: number;
    ema_12: number;
    ema_26: number;
  };
  momentum_indicators: {
    rsi_14: number;
    macd: number;
    macd_signal: number;
    macd_histogram: number;
    stochastic_k: number;
    stochastic_d: number;
  };
  volatility_indicators: {
    atr_14: number;
    bollinger_upper: number;
    bollinger_middle: number;
    bollinger_lower: number;
  };
  trend_analysis: {
    trend_direction: 'up' | 'down' | 'sideways';
    support_levels: number[];
    resistance_levels: number[];
    trend_strength: number; // 0-100
  };
}

interface FundamentalData {
  valuation_metrics: {
    pe_ratio: number;
    peg_ratio: number;
    price_to_book: number;
    price_to_sales: number;
    ev_to_ebitda: number;
  };
  financial_health: {
    debt_to_equity: number;
    current_ratio: number;
    quick_ratio: number;
    return_on_equity: number;
    return_on_assets: number;
  };
  growth_metrics: {
    revenue_growth_yoy: number;
    earnings_growth_yoy: number;
    eps_growth_5y: number;
  };
  dividend_info: {
    dividend_yield: number;
    payout_ratio: number;
    dividend_growth_5y: number;
    last_dividend_date: string;
  };
}
```

#### GET `/api/stocks/{ticker}/strategy-history`
**Purpose**: Historical strategy performance for specific stock
```typescript
interface StrategyHistoryResponse {
  ticker: string;
  total_appearances: number;
  strategy_runs: StrategyRunSummary[];
  performance_timeline: PerformanceTimelineEntry[];
  score_distribution: ScoreDistribution;
  success_patterns: SuccessPattern[];
}

interface StrategyRunSummary {
  run_id: string;
  strategy_code: string;
  run_date: string;
  passed: boolean;
  score: number;
  classification: string;
  rank_in_run: number;
  total_in_run: number;
  reasons: string[];
  metrics: StrategyMetrics;
}

interface PerformanceTimelineEntry {
  date: string;
  strategy_code: string;
  score: number;
  classification: string;
  market_price_at_time: number;
  subsequent_performance?: {
    price_1w: number;
    price_1m: number;
    price_3m: number;
    return_1w: number;
    return_1m: number;
    return_3m: number;
  };
}
```

#### GET `/api/stocks/{ticker}/charts`
**Purpose**: Chart data for technical analysis
```typescript
interface ChartDataResponse {
  price_history: PriceHistoryEntry[];
  volume_history: VolumeEntry[];
  technical_overlays: TechnicalOverlay[];
  comparison_data?: ComparisonEntry[];
}

interface PriceHistoryEntry {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface TechnicalOverlay {
  name: string;
  type: 'line' | 'area' | 'band';
  data: Array<{
    timestamp: string;
    value: number | { upper: number; lower: number };
  }>;
}
```

#### POST `/api/stocks/{ticker}/compare`
**Purpose**: Compare multiple stocks side-by-side
```typescript
interface CompareRequest {
  base_ticker: string;
  compare_tickers: string[];
  comparison_metrics: string[];
  time_period: string;
}

interface CompareResponse {
  comparison_table: ComparisonRow[];
  relative_performance: RelativePerformanceData;
  correlation_matrix: CorrelationMatrix;
}
```

#### POST `/api/stocks/{ticker}/add-to-instruments`
**Purpose**: Add new stock to instruments database
```typescript
interface AddToInstrumentsRequest {
  ticker: string;
  validate_first: boolean;
  fetch_metadata: boolean;
}

interface AddToInstrumentsResponse {
  success: boolean;
  ticker: string;
  validation_result: {
    valid: boolean;
    company_name: string;
    exchange: string;
    currency: string;
  };
  instrument_created: boolean;
  metadata_enriched: boolean;
}
```

### 1.2 Real-time Data API Endpoints

#### GET `/api/stocks/{ticker}/live-price`
**Purpose**: WebSocket endpoint for real-time price updates
```typescript
interface LivePriceUpdate {
  ticker: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}
```

#### GET `/api/stocks/watchlist/live`
**Purpose**: Multi-ticker real-time updates
```typescript
interface MultiTickerLiveUpdate {
  updates: LivePriceUpdate[];
  timestamp: string;
}
```

## 2. Database Schema Extensions

### 2.1 New Tables

#### Stock Analysis Cache Table
```sql
CREATE TABLE IF NOT EXISTS stock_analysis_cache (
    ticker TEXT PRIMARY KEY,
    analysis_data TEXT NOT NULL, -- JSON blob
    market_data TEXT NOT NULL,   -- JSON blob  
    last_updated TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (ticker) REFERENCES instruments(ticker)
);

CREATE INDEX IF NOT EXISTS ix_analysis_cache_expires ON stock_analysis_cache(expires_at);
CREATE INDEX IF NOT EXISTS ix_analysis_cache_updated ON stock_analysis_cache(last_updated);
```

#### Stock Comparison Sessions Table
```sql
CREATE TABLE IF NOT EXISTS stock_comparison_sessions (
    session_id TEXT PRIMARY KEY,
    user_session TEXT,  -- For future user management
    base_ticker TEXT NOT NULL,
    compare_tickers TEXT NOT NULL, -- JSON array
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    FOREIGN KEY (base_ticker) REFERENCES instruments(ticker)
);

CREATE INDEX IF NOT EXISTS ix_comparison_user_session ON stock_comparison_sessions(user_session);
CREATE INDEX IF NOT EXISTS ix_comparison_accessed ON stock_comparison_sessions(last_accessed);
```

#### Stock Watchlist Table
```sql
CREATE TABLE IF NOT EXISTS stock_watchlists (
    watchlist_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    tickers TEXT NOT NULL, -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2.2 Enhanced Instruments Table
```sql
-- Add new columns to existing instruments table
ALTER TABLE instruments ADD COLUMN company_name TEXT;
ALTER TABLE instruments ADD COLUMN exchange TEXT;
ALTER TABLE instruments ADD COLUMN market_cap REAL;
ALTER TABLE instruments ADD COLUMN pe_ratio REAL;
ALTER TABLE instruments ADD COLUMN dividend_yield REAL;
ALTER TABLE instruments ADD COLUMN beta REAL;
ALTER TABLE instruments ADD COLUMN week_52_high REAL;
ALTER TABLE instruments ADD COLUMN week_52_low REAL;
ALTER TABLE instruments ADD COLUMN metadata_last_updated TEXT;
```

### 2.3 Strategy Result Enhancements
```sql
-- Add price context to strategy results for performance tracking
ALTER TABLE strategy_result ADD COLUMN market_price_at_time REAL;
ALTER TABLE strategy_result ADD COLUMN price_1w_later REAL;
ALTER TABLE strategy_result ADD COLUMN price_1m_later REAL;
ALTER TABLE strategy_result ADD COLUMN price_3m_later REAL;
```

## 3. Backend Service Architecture

### 3.1 Stock Analysis Service
```python
class StockAnalysisService:
    def __init__(self, db_manager, market_service, yfinance_mcp):
        self.db = db_manager
        self.market = market_service
        self.yfinance = yfinance_mcp
        self.cache_ttl = 300  # 5 minutes for real-time data
        
    async def get_comprehensive_analysis(self, ticker: str) -> StockAnalysisResponse:
        """Get complete stock analysis with caching"""
        
    async def get_real_time_data(self, ticker: str) -> RealTimeMarketData:
        """Get fresh market data from yfinance MCP"""
        
    async def get_technical_indicators(self, ticker: str) -> TechnicalIndicators:
        """Calculate technical indicators from historical data"""
        
    async def get_strategy_history(self, ticker: str) -> StrategyHistoryData:
        """Analyze historical strategy performance"""
        
    async def compare_stocks(self, base_ticker: str, compare_tickers: List[str]) -> CompareResponse:
        """Multi-stock comparison analysis"""
```

### 3.2 Real-time Market Data Service
```python
class RealTimeMarketDataService:
    def __init__(self, yfinance_mcp):
        self.yfinance = yfinance_mcp
        self.price_cache = {}
        self.subscribers = {}  # WebSocket connections
        
    async def start_price_streaming(self, tickers: List[str]):
        """Start real-time price updates for tickers"""
        
    async def subscribe_ticker(self, ticker: str, websocket):
        """Subscribe WebSocket to ticker updates"""
        
    async def get_live_price(self, ticker: str) -> LivePriceUpdate:
        """Get current live price data"""
        
    async def get_historical_data(self, ticker: str, period: str) -> List[PriceHistoryEntry]:
        """Get historical data for charts"""
```

### 3.3 MCP Integration Service
```python
class YFinanceMCPService:
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        
    async def get_stock_price(self, ticker: str) -> dict:
        """Use yfinance MCP get_stock_price tool"""
        
    async def get_company_info(self, ticker: str) -> dict:
        """Use yfinance MCP get_company_info tool"""
        
    async def get_historical_data(self, ticker: str, period: str, interval: str) -> dict:
        """Use yfinance MCP get_historical_data tool"""
        
    async def get_financials(self, ticker: str, statement_type: str) -> dict:
        """Use yfinance MCP get_financials tool"""
        
    async def search_ticker(self, query: str) -> dict:
        """Use yfinance MCP search_ticker tool"""
```

## 4. Frontend UI/UX Architecture

### 4.1 Page Structure

```
Individual Stock Analysis Page
├── Header Section
│   ├── Stock Search/Selection Widget
│   ├── Quick Actions (Add to Watchlist, Compare, Export)
│   └── Real-time Price Ticker
├── Main Content Area
│   ├── Overview Dashboard (Left Panel)
│   │   ├── Price Chart with Technical Overlays
│   │   ├── Key Metrics Cards
│   │   └── News/Events Timeline
│   ├── Analysis Tabs (Center Panel)
│   │   ├── Technical Analysis Tab
│   │   ├── Fundamental Analysis Tab
│   │   ├── Strategy History Tab
│   │   └── Comparison Tab
│   └── Side Panel (Right)
│       ├── Related Stocks
│       ├── Sector Performance
│       └── Strategy Alerts
└── Footer
    ├── Data Sources Attribution
    └── Last Updated Timestamp
```

### 4.2 Flutter Widget Architecture

#### Main Stock Analysis Screen
```dart
class StockAnalysisScreen extends ConsumerStatefulWidget {
  final String? initialTicker;
  
  @override
  _StockAnalysisScreenState createState() => _StockAnalysisScreenState();
}

class _StockAnalysisScreenState extends ConsumerState<StockAnalysisScreen> 
    with TickerProviderStateMixin {
  late TabController _tabController;
  String? _selectedTicker;
  Timer? _priceUpdateTimer;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(),
      body: _selectedTicker == null 
        ? _buildStockSelector()
        : _buildAnalysisView(),
    );
  }
}
```

#### Stock Search Widget
```dart
class StockSearchWidget extends StatefulWidget {
  final Function(String) onTickerSelected;
  
  @override
  _StockSearchWidgetState createState() => _StockSearchWidgetState();
}

class _StockSearchWidgetState extends State<StockSearchWidget> {
  final TextEditingController _searchController = TextEditingController();
  List<StockSearchResult> _searchResults = [];
  bool _isSearching = false;
  
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildSearchField(),
        _buildSearchResults(),
        _buildRecentlyViewed(),
      ],
    );
  }
}
```

#### Technical Analysis Chart Widget
```dart
class TechnicalAnalysisChart extends StatefulWidget {
  final String ticker;
  final String timeframe;
  final List<TechnicalIndicator> indicators;
  
  @override
  _TechnicalAnalysisChartState createState() => _TechnicalAnalysisChartState();
}

class _TechnicalAnalysisChartState extends State<TechnicalAnalysisChart> {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          _buildChartHeader(),
          _buildInteractiveChart(),
          _buildIndicatorToggles(),
        ],
      ),
    );
  }
}
```

#### Strategy History Timeline Widget
```dart
class StrategyHistoryTimeline extends StatelessWidget {
  final String ticker;
  final List<StrategyRunSummary> strategyRuns;
  
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          _buildTimelineHeader(),
          _buildTimelineList(),
          _buildPerformanceMetrics(),
        ],
      ),
    );
  }
}
```

### 4.3 State Management (Riverpod)

#### Providers
```dart
// Stock analysis data provider
final stockAnalysisProvider = FutureProvider.autoDispose.family<StockAnalysisResponse, String>(
  (ref, ticker) async {
    final apiService = ref.read(apiServiceProvider);
    return await apiService.getStockAnalysis(ticker);
  },
);

// Real-time price provider
final realTimePriceProvider = StreamProvider.autoDispose.family<LivePriceUpdate, String>(
  (ref, ticker) {
    final realtimeService = ref.read(realtimeServiceProvider);
    return realtimeService.getPriceStream(ticker);
  },
);

// Strategy history provider
final strategyHistoryProvider = FutureProvider.autoDispose.family<StrategyHistoryResponse, String>(
  (ref, ticker) async {
    final apiService = ref.read(apiServiceProvider);
    return await apiService.getStrategyHistory(ticker);
  },
);

// Stock comparison provider
final stockComparisonProvider = StateNotifierProvider<StockComparisonNotifier, StockComparisonState>(
  (ref) => StockComparisonNotifier(),
);
```

### 4.4 Responsive Design

#### Layout Breakpoints
```dart
class LayoutConstants {
  static const double mobileBreakpoint = 600;
  static const double tabletBreakpoint = 900;
  static const double desktopBreakpoint = 1200;
}

class ResponsiveStockAnalysisLayout extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < LayoutConstants.mobileBreakpoint) {
          return _buildMobileLayout();
        } else if (constraints.maxWidth < LayoutConstants.tabletBreakpoint) {
          return _buildTabletLayout();
        } else {
          return _buildDesktopLayout();
        }
      },
    );
  }
}
```

## 5. Navigation Integration

### 5.1 Route Configuration
```dart
// Add to existing router configuration
GoRoute(
  path: '/stocks',
  name: 'stocks',
  builder: (context, state) => const StockAnalysisScreen(),
  routes: [
    GoRoute(
      path: '/:ticker',
      name: 'stock-detail',
      builder: (context, state) => StockAnalysisScreen(
        initialTicker: state.pathParameters['ticker'],
      ),
    ),
    GoRoute(
      path: '/:ticker/compare/:compareTickers',
      name: 'stock-compare',
      builder: (context, state) => StockComparisonScreen(
        baseTicker: state.pathParameters['ticker']!,
        compareTickers: state.pathParameters['compareTickers']!.split(','),
      ),
    ),
  ],
),
```

### 5.2 Navigation Integration
```dart
// Update main navigation
NavigationRailDestination(
  icon: Icon(Icons.trending_up_outlined),
  selectedIcon: Icon(Icons.trending_up),
  label: Text('Stock Analysis'),
),

// Add navigation logic
case 5: // New index for Stock Analysis
  context.goNamed('stocks');
  break;
```

## 6. Real-time Data Flow Architecture

### 6.1 Data Flow Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend        │    │   yfinance MCP  │
│   Flutter App   │    │   FastAPI        │    │   Server        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. Request Analysis   │                       │
         ├──────────────────────►│                       │
         │                       │ 2. Check Cache       │
         │                       ├───────────────┐       │
         │                       │               │       │
         │                       │ 3. Get Market Data   │
         │                       │               │       │
         │                       │               └──────►│ 4. yfinance API
         │                       │                       │    call
         │                       │ 5. Receive Data       │
         │                       │◄──────────────────────┤
         │                       │ 6. Process & Cache    │
         │                       ├───────────────┐       │
         │ 7. Return Analysis    │               │       │
         │◄──────────────────────┤               │       │
         │                       │               │       │
         │ 8. Start Live Updates │               │       │
         ├──────────────────────►│               │       │
         │                       │ 9. WebSocket Stream   │
         │◄══════════════════════┤               │       │
         │                       │               │       │
```

### 6.2 WebSocket Implementation
```python
# Backend WebSocket endpoint
@router.websocket("/ws/stocks/{ticker}/live")
async def stock_live_updates(websocket: WebSocket, ticker: str):
    await websocket.accept()
    await realtime_service.subscribe_ticker(ticker, websocket)
    
    try:
        while True:
            # Keep connection alive and send updates
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await realtime_service.unsubscribe_ticker(ticker, websocket)
```

```dart
// Frontend WebSocket client
class RealtimeStockService {
  WebSocketChannel? _channel;
  StreamController<LivePriceUpdate> _priceController = StreamController.broadcast();
  
  Stream<LivePriceUpdate> subscribeTo(String ticker) {
    _channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8000/ws/stocks/$ticker/live'),
    );
    
    _channel!.stream.listen((data) {
      final update = LivePriceUpdate.fromJson(jsonDecode(data));
      _priceController.add(update);
    });
    
    return _priceController.stream;
  }
}
```

## 7. Caching and Performance Strategy

### 7.1 Multi-level Caching

#### L1 Cache: In-Memory (Backend)
```python
class StockDataCache:
    def __init__(self):
        self.price_cache = TTLCache(maxsize=1000, ttl=30)  # 30 seconds
        self.analysis_cache = TTLCache(maxsize=500, ttl=300)  # 5 minutes
        self.fundamental_cache = TTLCache(maxsize=500, ttl=3600)  # 1 hour
```

#### L2 Cache: Database
```sql
-- Stock analysis cache with TTL
SELECT analysis_data FROM stock_analysis_cache 
WHERE ticker = ? AND expires_at > datetime('now');
```

#### L3 Cache: Frontend (Flutter)
```dart
class StockDataRepository {
  final Map<String, CachedData<StockAnalysisResponse>> _analysisCache = {};
  final Duration _cacheExpiry = Duration(minutes: 5);
  
  Future<StockAnalysisResponse> getStockAnalysis(String ticker) async {
    final cached = _analysisCache[ticker];
    if (cached != null && !cached.isExpired) {
      return cached.data;
    }
    
    final fresh = await _apiService.getStockAnalysis(ticker);
    _analysisCache[ticker] = CachedData(fresh, DateTime.now().add(_cacheExpiry));
    return fresh;
  }
}
```

### 7.2 Performance Optimizations

#### Backend Optimizations
- **Connection pooling** for database and MCP connections
- **Batch processing** for multiple ticker requests
- **Async/await** for non-blocking I/O operations
- **Request deduplication** for simultaneous requests

#### Frontend Optimizations
- **Lazy loading** of analysis tabs
- **Virtual scrolling** for large datasets
- **Image caching** for charts and logos
- **State preservation** during navigation

## 8. Implementation Roadmap

### Phase 1: Core Foundation (Week 1-2)
- [ ] Database schema extensions
- [ ] Basic API endpoints for stock analysis
- [ ] yfinance MCP integration service
- [ ] Basic Flutter stock analysis screen

### Phase 2: Real-time Integration (Week 3-4)
- [ ] WebSocket implementation for live prices
- [ ] Real-time chart updates
- [ ] Price streaming optimization
- [ ] Error handling and reconnection logic

### Phase 3: Advanced Analysis (Week 5-6)
- [ ] Technical indicators calculation
- [ ] Strategy history analysis
- [ ] Performance metrics and trending
- [ ] Advanced charting features

### Phase 4: Comparison & Management (Week 7-8)
- [ ] Multi-stock comparison interface
- [ ] Watchlist management
- [ ] Export and reporting features
- [ ] Mobile responsive optimization

### Phase 5: Performance & Polish (Week 9-10)
- [ ] Caching optimization
- [ ] Performance monitoring
- [ ] Error handling refinement
- [ ] User experience improvements

## 9. Integration Points

### 9.1 Strategy Results Integration
- **Direct navigation** from strategy results to stock analysis
- **Context preservation** showing which strategy flagged the stock
- **Performance tracking** from strategy signal to current price

### 9.2 Instruments Database Integration
- **Automatic metadata enrichment** for new stocks
- **Validation pipeline** for symbol verification
- **Batch updates** for instrument metadata refresh

### 9.3 Portfolio Integration
- **Holdings analysis** for stocks in portfolio
- **Position sizing** recommendations based on analysis
- **Risk assessment** relative to current holdings

## Conclusion

This architecture provides a comprehensive, scalable foundation for individual stock analysis with real-time data integration. The design supports both power users doing deep analysis and casual users researching stocks, with seamless integration into the existing trading application ecosystem.

The phased implementation approach ensures rapid delivery of core functionality while building towards advanced features. The caching strategy and performance optimizations ensure the system remains responsive even with real-time data requirements.