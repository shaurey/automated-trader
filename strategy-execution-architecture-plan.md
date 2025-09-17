# Strategy Execution with Real-Time Progress Tracking - Architecture Plan

## Executive Summary

This document outlines the architecture for adding real-time strategy execution capabilities to the automated trading application. The design preserves the existing CLI strategy scripts while adding web-based execution with live progress tracking using Server-Sent Events (SSE).

## Current State Analysis

### Existing Strategy Execution Patterns

#### 1. Strategy Scripts Analysis
- **bullish_strategy.py**: Comprehensive technical analysis screener
  - **Execution Flow**: CLI → Data download → Analysis → Database logging → File output
  - **Progress Points**: Ticker processing (concurrent), metrics calculation, results aggregation
  - **Database Integration**: Uses `Database` class for run tracking and result logging
  - **Key Bottlenecks**: yfinance API calls, concurrent processing limits

- **leap_entry_strategy.py**: LEAP call entry screener
  - **Execution Flow**: Similar to bullish strategy with specialized LEAP analysis
  - **Progress Points**: Market data fetching, indicator calculations, scoring
  - **Database Integration**: Enhanced with retry logic for database locking
  - **Key Bottlenecks**: Market data dependencies, calculation-intensive scoring

#### 2. Database Schema (Current)
```sql
-- strategy_run: Tracks execution metadata
-- strategy_result: Stores individual ticker results
-- Well-established logging pattern with run_id correlation
```

#### 3. Current Execution Challenges
- **No real-time feedback**: Scripts run in isolation
- **Limited visibility**: Progress only visible in terminal output
- **No cancellation**: Once started, runs must complete
- **No queuing**: Multiple runs can conflict

## Proposed Architecture

### 1. Real-Time Execution Architecture with SSE

```mermaid
graph TB
    subgraph "Frontend (Flutter Web)"
        A[Strategy Execution Form] --> B[Start Execution API Call]
        B --> C[SSE Connection Setup]
        C --> D[Real-time Progress Display]
        D --> E[Results Dashboard]
        F[Execution Queue UI] --> G[Run Management]
    end
    
    subgraph "Backend (FastAPI)"
        H[POST /api/strategies/execute] --> I[Background Task Manager]
        I --> J[Strategy Process Wrapper]
        J --> K[Progress Event Emitter]
        K --> L[GET /api/strategies/sse/{run_id}]
        
        M[Execution State Manager] --> N[Redis/Memory Store]
        O[Run Queue Manager] --> P[Concurrent Execution Control]
    end
    
    subgraph "Strategy Scripts (Existing)"
        Q[bullish_strategy.py] --> R[Enhanced with Progress Hooks]
        S[leap_entry_strategy.py] --> T[Enhanced with Progress Hooks]
        R --> U[Database Logging]
        T --> U
    end
    
    L --> C
    J --> Q
    J --> S
    I --> M
    I --> O
```

### 2. Progress Streaming Architecture

#### SSE Event Stream Design
```python
# Progress Event Types
class ProgressEventType(Enum):
    STARTED = "started"
    PROGRESS = "progress" 
    TICKER_COMPLETED = "ticker_completed"
    STAGE_COMPLETED = "stage_completed"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

# Progress Event Schema
{
    "event_type": "progress",
    "timestamp": "2024-01-15T10:30:00Z",
    "run_id": "uuid-string",
    "stage": "data_download",
    "progress_percent": 45.5,
    "current_item": "AAPL",
    "total_items": 500,
    "completed_items": 227,
    "message": "Processing AAPL - fetching market data",
    "metrics": {
        "tickers_per_second": 2.3,
        "estimated_remaining": "00:05:32"
    }
}
```

### 3. Strategy Process Wrapper Design

```python
class StrategyExecutionWrapper:
    """Wraps existing strategy scripts with progress tracking"""
    
    def __init__(self, strategy_code: str, run_id: str):
        self.strategy_code = strategy_code
        self.run_id = run_id
        self.progress_emitter = ProgressEmitter(run_id)
        
    async def execute_with_progress(self, params: dict):
        """Execute strategy with real-time progress tracking"""
        # 1. Setup progress tracking
        # 2. Launch strategy subprocess with modified environment
        # 3. Parse stdout/stderr for progress indicators
        # 4. Emit progress events via SSE
        # 5. Handle completion/error states
```

## API Design

### 1. Strategy Execution Endpoints

#### POST /api/strategies/execute
```python
# Request Schema
{
    "strategy_code": "bullish_breakout",
    "parameters": {
        "min_score": 70,
        "max_workers": 4,
        "universe_source": "sp500",
        "tickers": ["AAPL", "MSFT"],  # optional
        "min_volume_multiple": 1.0
    },
    "options": {
        "priority": "normal",  # low, normal, high
        "notify_on_completion": true
    }
}

# Response Schema
{
    "run_id": "uuid-string",
    "status": "queued",  # queued, running, completed, error, cancelled
    "position_in_queue": 2,
    "estimated_start_time": "2024-01-15T10:35:00Z",
    "sse_endpoint": "/api/strategies/sse/uuid-string"
}
```

#### GET /api/strategies/sse/{run_id}
```python
# Server-Sent Events endpoint for real-time progress
# Content-Type: text/event-stream
# Returns continuous stream of progress events
```

#### GET /api/strategies/runs/{run_id}/status
```python
# Real-time status endpoint (polling fallback)
{
    "run_id": "uuid-string",
    "status": "running",
    "progress_percent": 67.5,
    "current_stage": "analysis",
    "started_at": "2024-01-15T10:30:00Z",
    "estimated_completion": "2024-01-15T10:45:00Z",
    "can_cancel": true,
    "metrics": {
        "processed_tickers": 337,
        "total_tickers": 500,
        "tickers_per_second": 2.1,
        "passed_count": 23
    }
}
```

#### POST /api/strategies/runs/{run_id}/cancel
```python
# Cancel running execution
{
    "cancelled": true,
    "message": "Execution cancelled successfully"
}
```

#### GET /api/strategies/queue
```python
# View execution queue
{
    "queue": [
        {
            "run_id": "uuid-1",
            "strategy_code": "bullish_breakout",
            "status": "running",
            "position": 0,
            "started_at": "2024-01-15T10:30:00Z"
        },
        {
            "run_id": "uuid-2", 
            "strategy_code": "leap_entry",
            "status": "queued",
            "position": 1,
            "estimated_start": "2024-01-15T10:45:00Z"
        }
    ],
    "total_queued": 2,
    "max_concurrent": 2
}
```

### 2. Enhanced Data Models

```python
# Execution State Management
class ExecutionState(str, Enum):
    QUEUED = "queued"
    STARTING = "starting" 
    RUNNING = "running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"

class StrategyExecutionRequest(BaseModel):
    strategy_code: str
    parameters: Dict[str, Any]
    options: Optional[ExecutionOptions] = None

class ExecutionOptions(BaseModel):
    priority: str = "normal"
    notify_on_completion: bool = False
    max_execution_time: Optional[int] = None  # seconds

class ProgressEvent(BaseModel):
    event_type: ProgressEventType
    timestamp: datetime
    run_id: str
    stage: Optional[str] = None
    progress_percent: Optional[float] = None
    current_item: Optional[str] = None
    total_items: Optional[int] = None
    completed_items: Optional[int] = None
    message: str
    metrics: Optional[Dict[str, Any]] = None
```

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Progress Tracking System
```python
# backend/services/progress_service.py
class ProgressService:
    """Manages progress tracking and SSE streaming"""
    
    def __init__(self):
        self.active_streams: Dict[str, Queue] = {}
        self.execution_states: Dict[str, ExecutionState] = {}
    
    async def emit_progress(self, run_id: str, event: ProgressEvent):
        """Emit progress event to all subscribers"""
        
    async def subscribe_to_progress(self, run_id: str) -> AsyncGenerator[str, None]:
        """SSE stream generator for progress events"""
        
    def get_execution_state(self, run_id: str) -> Optional[ExecutionState]:
        """Get current execution state"""
```

#### 1.2 Execution Manager
```python
# backend/services/execution_manager.py
class StrategyExecutionManager:
    """Manages strategy execution lifecycle"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        self.active_executions: Dict[str, subprocess.Popen] = {}
    
    async def queue_execution(self, request: StrategyExecutionRequest) -> str:
        """Queue strategy for execution"""
        
    async def execute_strategy(self, run_id: str, request: StrategyExecutionRequest):
        """Execute strategy with progress tracking"""
        
    async def cancel_execution(self, run_id: str) -> bool:
        """Cancel running execution"""
```

### Phase 2: Strategy Script Enhancement (Week 2-3)

#### 2.1 Progress Injection Mechanism
```python
# Strategy scripts will be enhanced with progress hooks
# but remain fully functional as standalone CLI tools

class ProgressReporter:
    """Lightweight progress reporter for strategy scripts"""
    
    def __init__(self, run_id: str = None):
        self.run_id = run_id
        self.enabled = run_id is not None
        
    def report_progress(self, stage: str, progress: float, message: str):
        """Report progress if tracking is enabled"""
        if not self.enabled:
            return
            
        # Write progress to stdout in JSON format
        progress_data = {
            "type": "progress",
            "run_id": self.run_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
```

#### 2.2 Script Modifications (Minimal)
```python
# In bullish_strategy.py and leap_entry_strategy.py
# Add progress reporting at key points:

def run_screener(tickers: List[str], cfg: ScreenerConfig, 
                db_path: Optional[str] = None, 
                cli_args: Optional[argparse.Namespace] = None,
                progress_reporter: Optional[ProgressReporter] = None) -> Tuple[List[TickerResult], List[TickerResult]]:
    
    # Initialize progress reporter
    if progress_reporter is None:
        progress_reporter = ProgressReporter()
    
    progress_reporter.report_progress("initialization", 0, "Starting strategy execution")
    
    # Existing logic with progress reporting added
    for i, ticker in enumerate(tickers):
        result = _evaluate_ticker(ticker, cfg)
        results.append(result)
        
        # Report progress
        progress = (i + 1) / len(tickers) * 100
        progress_reporter.report_progress("analysis", progress, f"Processed {ticker}")
```

### Phase 3: API Implementation (Week 3-4)

#### 3.1 FastAPI Endpoints
```python
# backend/api/strategy_execution.py
@router.post("/strategies/execute")
async def execute_strategy(
    request: StrategyExecutionRequest,
    background_tasks: BackgroundTasks,
    execution_manager: StrategyExecutionManager = Depends(get_execution_manager)
):
    """Start strategy execution with real-time progress tracking"""
    
@router.get("/strategies/sse/{run_id}")
async def strategy_progress_stream(
    run_id: str,
    progress_service: ProgressService = Depends(get_progress_service)
):
    """Server-Sent Events endpoint for real-time progress"""
    
    async def event_generator():
        async for event in progress_service.subscribe_to_progress(run_id):
            yield f"data: {event}\n\n"
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### Phase 4: Frontend Integration (Week 4-5)

#### 4.1 Strategy Execution UI Components
```dart
// frontend/lib/screens/strategy_execution_screen.dart
class StrategyExecutionScreen extends ConsumerWidget {
  // Form for strategy parameters
  // Real-time progress display
  // Execution queue management
  // Results integration
}

// frontend/lib/widgets/progress_stream_widget.dart
class ProgressStreamWidget extends ConsumerWidget {
  // SSE connection management
  // Progress visualization
  // Log display
  // Error handling
}
```

#### 4.2 SSE Integration
```dart
// frontend/lib/services/sse_service.dart
class SSEService {
  Stream<ProgressEvent> connectToProgressStream(String runId) {
    // Setup EventSource connection
    // Parse SSE events
    // Handle reconnection
    // Error recovery
  }
}
```

### Phase 5: Testing & Optimization (Week 5-6)

#### 5.1 Testing Strategy
- **Unit Tests**: Progress tracking, execution management
- **Integration Tests**: End-to-end execution with progress
- **Load Tests**: Multiple concurrent executions
- **Frontend Tests**: SSE connection handling, UI responsiveness

#### 5.2 Performance Optimization
- **Connection pooling**: Efficient SSE connection management
- **Memory management**: Progress event cleanup
- **Database optimization**: Bulk result operations
- **Frontend optimization**: Efficient real-time UI updates

## Error Handling & Recovery

### 1. Execution Failures
```python
class ExecutionErrorHandler:
    """Handles various execution failure scenarios"""
    
    async def handle_script_error(self, run_id: str, error: Exception):
        """Handle strategy script errors"""
        
    async def handle_timeout(self, run_id: str):
        """Handle execution timeouts"""
        
    async def handle_cancellation(self, run_id: str):
        """Handle user-requested cancellation"""
```

### 2. SSE Connection Management
```dart
class SSEConnectionManager {
  // Automatic reconnection on disconnect
  // Fallback to polling if SSE fails
  // Error state management
  // Progress persistence across reconnections
}
```

### 3. Database Integrity
- **Transaction management**: Ensure consistent run state
- **Retry logic**: Handle database locks gracefully
- **Cleanup procedures**: Remove orphaned runs
- **State recovery**: Restore execution state on server restart

## Resource Management & Scalability

### 1. Concurrent Execution Limits
```python
# Configuration-based limits
MAX_CONCURRENT_EXECUTIONS = 2
MAX_QUEUE_SIZE = 10
EXECUTION_TIMEOUT = 1800  # 30 minutes

# Resource monitoring
class ResourceMonitor:
    def check_system_resources(self) -> bool:
        """Check if system can handle new execution"""
        # CPU, memory, disk space checks
```

### 2. Memory Management
- **Progress event cleanup**: Remove old events after completion
- **Connection management**: Limit SSE connections per run
- **Result caching**: Efficient storage of intermediate results

### 3. Scaling Considerations
- **Horizontal scaling**: Support for multiple backend instances
- **Load balancing**: Distribute executions across instances  
- **Shared state**: Redis/database for cross-instance coordination

## Deployment Strategy

### 1. Backend Deployment
```yaml
# docker-compose updates
services:
  api:
    environment:
      - MAX_CONCURRENT_EXECUTIONS=2
      - SSE_TIMEOUT=1800
      - EXECUTION_QUEUE_SIZE=10
    volumes:
      - ./strategy_scripts:/app/strategy_scripts
```

### 2. Frontend Deployment
```yaml
# Frontend configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_SSE_TIMEOUT=30000
VITE_POLLING_FALLBACK=true
```

### 3. Production Considerations
- **Process monitoring**: Supervisor for strategy executions
- **Log aggregation**: Centralized logging for debugging
- **Health checks**: Monitor execution manager health
- **Backup strategies**: Database backup during long runs

## Success Metrics

### 1. Performance Metrics
- **Execution time**: Track strategy execution duration
- **Throughput**: Tickers processed per second
- **Resource usage**: CPU, memory consumption
- **Error rates**: Execution failure percentage

### 2. User Experience Metrics  
- **Progress accuracy**: Real-time vs actual progress
- **UI responsiveness**: SSE event processing time
- **Connection stability**: SSE reconnection frequency
- **Feature adoption**: Usage of real-time execution vs CLI

### 3. System Reliability
- **Uptime**: API availability during executions
- **Data integrity**: Result consistency across execution modes
- **Recovery time**: System recovery after failures
- **Queue management**: Average wait time in execution queue

## Future Enhancements

### 1. Advanced Features
- **Scheduled executions**: Cron-like strategy scheduling
- **Execution templates**: Pre-configured parameter sets
- **Result comparison**: Compare runs across time periods
- **Notifications**: Email/webhook notifications on completion

### 2. Performance Optimizations
- **Incremental execution**: Resume from interruption points
- **Parallel processing**: Multi-strategy concurrent execution
- **Caching**: Market data caching across runs
- **Streaming results**: Real-time result streaming during execution

### 3. Analytics & Monitoring
- **Execution analytics**: Performance trending and optimization
- **Resource optimization**: Dynamic resource allocation
- **Predictive scheduling**: Optimal execution timing
- **A/B testing**: Strategy parameter optimization

## Risk Mitigation

### 1. Technical Risks
- **SSE browser limits**: Fallback to polling for older browsers
- **Memory leaks**: Comprehensive cleanup procedures
- **Database locks**: Enhanced retry and timeout logic
- **Script compatibility**: Extensive testing with existing scripts

### 2. Operational Risks
- **Long-running executions**: Timeout and cancellation mechanisms
- **System overload**: Resource monitoring and limits
- **Data corruption**: Transaction integrity and rollback
- **User confusion**: Clear UI feedback and documentation

### 3. Business Risks
- **Performance degradation**: Monitoring and alerting
- **User adoption**: Gradual rollout and training
- **Maintenance complexity**: Clear documentation and testing
- **Backward compatibility**: Support for existing workflows

---

## Conclusion

This architecture provides a robust foundation for real-time strategy execution while preserving the existing CLI workflow. The SSE-based progress streaming offers excellent user experience with minimal complexity, and the phased implementation approach ensures stable delivery with manageable risk.

The design prioritizes:
- **Minimal disruption** to existing strategy scripts
- **Real-time visibility** into execution progress  
- **Scalable architecture** for future growth
- **Robust error handling** and recovery
- **Excellent user experience** with live feedback

The implementation phases provide clear milestones and allow for iterative refinement based on user feedback and performance characteristics.