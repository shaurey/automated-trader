# Strategy Execution Implementation Guide

## Quick Start Summary

This guide provides the essential steps to implement real-time strategy execution with Server-Sent Events (SSE) progress tracking.

## Architecture Overview

```
Frontend (Flutter)          Backend (FastAPI)           Strategy Scripts
      │                           │                           │
   [Execute] ──────────────► [Queue Manager] ──────────► [Wrapped Scripts]
      │                           │                           │
   [SSE Client] ◄────────── [Progress Service] ◄─────── [Progress Hooks]
      │                           │                           │
   [Live UI] ◄──────────────── [Event Stream] ◄──────── [JSON Progress]
```

## Key Design Decisions

### ✅ **SSE (Server-Sent Events)** for Real-Time Communication
- **Why**: Simple, browser-native, perfect for one-way progress streaming
- **Benefits**: Automatic reconnection, real-time debug logs, no additional libraries
- **Implementation**: `/api/strategies/sse/{run_id}` endpoint

### ✅ **Minimal Script Modifications** 
- **Why**: Keep Python scripts independently executable
- **Approach**: Lightweight `ProgressReporter` class with JSON stdout
- **Fallback**: Scripts work unchanged when run standalone

### ✅ **Background Task Execution**
- **Why**: Non-blocking API responses, concurrent execution support
- **Implementation**: FastAPI BackgroundTasks + subprocess management
- **Features**: Queuing, cancellation, resource limits

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
**Goal**: Setup progress tracking and SSE streaming

#### Key Components:
1. **ProgressService** - Manages SSE connections and event broadcasting
2. **ExecutionManager** - Handles strategy lifecycle and queuing
3. **Progress Events** - Standardized event schema for real-time updates

#### Deliverables:
- [ ] `backend/services/progress_service.py`
- [ ] `backend/services/execution_manager.py` 
- [ ] `backend/models/execution_models.py`
- [ ] Basic SSE endpoint implementation

### Phase 2: Strategy Enhancement (Week 2-3)
**Goal**: Add progress reporting to existing scripts

#### Key Changes:
1. **ProgressReporter** class - Lightweight, optional progress tracking
2. **Minimal script modifications** - Add progress hooks at key points
3. **JSON progress format** - Structured progress data via stdout

#### Deliverables:
- [ ] Enhanced `bullish_strategy.py` with progress hooks
- [ ] Enhanced `leap_entry_strategy.py` with progress hooks
- [ ] `ProgressReporter` utility class
- [ ] Backward compatibility testing

### Phase 3: API Implementation (Week 3-4)
**Goal**: Complete backend API for strategy execution

#### Key Endpoints:
1. **POST /api/strategies/execute** - Start strategy execution
2. **GET /api/strategies/sse/{run_id}** - Progress SSE stream
3. **GET /api/strategies/runs/{run_id}/status** - Status polling fallback
4. **POST /api/strategies/runs/{run_id}/cancel** - Cancel execution

#### Deliverables:
- [ ] `backend/api/strategy_execution.py`
- [ ] Request/response models
- [ ] Error handling and validation
- [ ] Integration with existing database schema

### Phase 4: Frontend Integration (Week 4-5)
**Goal**: Real-time execution UI with live progress

#### Key Components:
1. **Strategy Execution Screen** - Parameter form and execution trigger
2. **Progress Stream Widget** - Real-time progress visualization
3. **SSE Service** - Connection management and event parsing
4. **Execution Queue UI** - View and manage queued executions

#### Deliverables:
- [ ] `frontend/lib/screens/strategy_execution_screen.dart`
- [ ] `frontend/lib/widgets/progress_stream_widget.dart`
- [ ] `frontend/lib/services/sse_service.dart`
- [ ] Integration with existing strategy results UI

### Phase 5: Testing & Polish (Week 5-6)
**Goal**: Comprehensive testing and optimization

#### Testing Areas:
1. **Unit Tests** - Core services and utilities
2. **Integration Tests** - End-to-end execution flows
3. **Load Tests** - Concurrent execution scenarios
4. **UI Tests** - Frontend SSE handling and responsiveness

#### Deliverables:
- [ ] Comprehensive test suite
- [ ] Performance optimization
- [ ] Documentation and user guides
- [ ] Production deployment configuration

## Critical Implementation Details

### SSE Progress Event Format
```json
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

### Script Progress Integration
```python
# Minimal changes to existing scripts
def run_screener(tickers, cfg, db_path=None, cli_args=None, progress_reporter=None):
    if progress_reporter is None:
        progress_reporter = ProgressReporter()  # No-op when run standalone
    
    progress_reporter.report_progress("initialization", 0, "Starting analysis")
    
    # Existing logic with strategic progress points
    for i, ticker in enumerate(tickers):
        result = _evaluate_ticker(ticker, cfg)
        progress = (i + 1) / len(tickers) * 100
        progress_reporter.report_progress("analysis", progress, f"Processed {ticker}")
```

### Frontend SSE Integration
```dart
// Simple SSE connection with automatic reconnection
Stream<ProgressEvent> connectToProgressStream(String runId) {
  return EventSource.connect(
    Uri.parse('$baseUrl/api/strategies/sse/$runId'),
  ).map((event) => ProgressEvent.fromJson(jsonDecode(event.data)));
}
```

## Risk Mitigation Strategies

### 🔧 **Technical Risks**
- **SSE browser compatibility**: Polling fallback for older browsers
- **Memory leaks**: Automatic cleanup of old progress events
- **Script errors**: Robust error handling and state recovery

### 📊 **Performance Risks**  
- **Concurrent execution limits**: Configurable max concurrent runs (default: 2)
- **Resource monitoring**: CPU/memory checks before execution
- **Connection limits**: Max SSE connections per run

### 👥 **User Experience Risks**
- **Progress accuracy**: Conservative progress estimates
- **UI responsiveness**: Efficient real-time updates
- **Clear feedback**: Detailed error messages and status indicators

## Success Criteria

### 📈 **Performance Targets**
- **Execution overhead**: <5% additional time vs CLI execution
- **Progress latency**: Updates within 1 second of actual progress
- **UI responsiveness**: <100ms SSE event processing
- **Concurrent capacity**: Support 2+ simultaneous executions

### 🎯 **User Experience Goals**
- **Real-time visibility**: Live progress for all execution stages
- **Debug information**: Complete log streaming to web interface
- **Execution control**: Start, monitor, cancel executions from web UI
- **Backward compatibility**: CLI scripts remain fully functional

### 🔒 **Reliability Requirements**
- **Error recovery**: Graceful handling of script failures
- **Data integrity**: Consistent results across execution modes
- **Connection stability**: Automatic SSE reconnection
- **State persistence**: Progress survives server restarts

## Next Steps

1. **Review and approve** this architecture plan
2. **Setup development environment** with enhanced backend structure
3. **Begin Phase 1** implementation with core infrastructure
4. **Establish testing framework** for continuous validation
5. **Create development milestones** for iterative delivery

## Additional Resources

- **Main Architecture Document**: `strategy-execution-architecture-plan.md`
- **Current Strategy Analysis**: Review of `bullish_strategy.py` and `leap_entry_strategy.py`
- **Database Schema**: Existing `db.py` logging infrastructure
- **API Patterns**: Current `backend/api/strategies.py` for reference

---

This implementation guide provides a clear roadmap for delivering real-time strategy execution while preserving the robustness and independence of the existing CLI-based strategy scripts.