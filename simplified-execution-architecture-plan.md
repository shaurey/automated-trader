# Simplified Strategy Execution Architecture Plan

## Executive Summary

This document outlines the redesign of the automated-trader strategy execution system, replacing the complex SSE-streaming architecture with a simplified, synchronous FastAPI approach that maintains detailed progress tracking through database storage.

## Current Architecture Analysis

### Complex Components to Remove

#### 1. **Server-Sent Events (SSE) System**
- **File**: [`backend/api/strategy_execution.py`](backend/api/strategy_execution.py:98) - SSE endpoint
- **Complexity**: Real-time event streaming, connection management, error handling
- **Issues**: WebSocket-like complexity in HTTP, connection drops, browser compatibility
- **Replacement**: Simple HTTP polling for status updates

#### 2. **Complex Execution Manager**
- **File**: [`backend/services/execution_manager.py`](backend/services/execution_manager.py:38) - 737 lines of complex subprocess management
- **Complexity**: Queue management, subprocess orchestration, Windows/Unix compatibility layers
- **Issues**: Cross-platform subprocess issues, complex threading, resource management
- **Replacement**: Direct in-process strategy execution with simple database progress

#### 3. **Progress Service with Event Publishing**
- **File**: [`backend/services/progress_service.py`](backend/services/progress_service.py:1)
- **Complexity**: Event publishing, subscriber management, state tracking
- **Issues**: Memory overhead, connection management, real-time streaming complexity
- **Replacement**: Direct database writes for progress tracking

#### 4. **Complex Progress Reporter**
- **File**: [`backend/services/progress_reporter.py`](backend/services/progress_reporter.py:1)
- **Complexity**: Multiple output formats, subprocess communication via stdout parsing
- **Issues**: Parsing reliability, subprocess communication overhead
- **Replacement**: Direct callback-based progress reporting

### Strategy Execution Complexity

#### Current Subprocess Approach
```python
# Complex subprocess execution with stdout parsing
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=str(Path(__file__).parent.parent.parent),
    env={**os.environ, "STRATEGY_RUN_ID": run_id}
)
```

#### Current Progress Parsing
```python
# Parsing JSON progress from stdout
if line_str.startswith("PROGRESS:"):
    progress_json = line_str[9:]  # Remove "PROGRESS:" prefix
    progress_data = json.loads(progress_json)
```

## Simplified Architecture Design

### Core Principles

1. **Direct Integration**: Import and execute strategy functions directly in FastAPI
2. **Synchronous Execution**: Block API calls until completion with immediate results
3. **Database-Centric Progress**: Store all progress in database tables
4. **Simple HTTP Polling**: Replace SSE with standard GET endpoints
5. **Eliminated Complexity**: Remove subprocess management, SSE, complex queuing

### New Architecture Components

#### 1. **Strategy Service Classes**
```python
class BullishBreakoutStrategy:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        
    def execute(self, tickers: List[str], parameters: dict, 
               progress_callback: Callable) -> StrategyResults:
        """Direct execution with progress callbacks"""
        run_id = self.db.start_run(...)
        
        for i, ticker in enumerate(tickers):
            result = self._evaluate_ticker(ticker, parameters)
            progress_callback(i + 1, len(tickers), ticker, result)
            self.db.log_result(run_id, ticker, result)
            
        return StrategyResults(run_id=run_id, results=...)
```

#### 2. **Simplified FastAPI Endpoints**
```python
@router.post("/api/strategies/execute")
async def execute_strategy_sync(request: StrategyExecutionRequest):
    """Synchronous strategy execution with immediate results"""
    strategy = get_strategy_service(request.strategy_code)
    
    def progress_callback(current, total, ticker, result):
        # Update database progress directly
        update_execution_progress(run_id, current, total, ticker, result)
    
    # Execute synchronously and return complete results
    results = strategy.execute(
        tickers=request.parameters.tickers,
        parameters=request.parameters,
        progress_callback=progress_callback
    )
    
    return StrategyExecutionResults(
        run_id=results.run_id,
        status="completed",
        results=results.qualifying_stocks,
        progress={"current": len(tickers), "total": len(tickers)}
    )
```

#### 3. **Simple Progress Polling**
```python
@router.get("/api/strategies/runs/{run_id}/progress")
async def get_execution_progress(run_id: str):
    """Simple progress polling endpoint"""
    progress = db.get_execution_progress(run_id)
    return ExecutionProgress(
        run_id=run_id,
        current_ticker=progress.current_ticker,
        completed_count=progress.completed_count,
        total_count=progress.total_count,
        progress_percent=(progress.completed_count / progress.total_count) * 100,
        recent_results=progress.recent_results[-10:]  # Last 10 ticker results
    )
```

### Database Schema Extensions

#### New Progress Tracking Table
```sql
CREATE TABLE strategy_execution_progress (
    run_id TEXT NOT NULL,
    ticker TEXT,
    processed_at TEXT,
    passed BOOLEAN,
    score REAL,
    current_position INTEGER,
    total_tickers INTEGER,
    status TEXT,
    PRIMARY KEY (run_id, ticker)
);
```

#### Extended Strategy Run Table
```sql
-- Add columns to existing strategy_run table
ALTER TABLE strategy_run ADD COLUMN execution_status TEXT DEFAULT 'pending';
ALTER TABLE strategy_run ADD COLUMN current_ticker TEXT;
ALTER TABLE strategy_run ADD COLUMN progress_percent REAL DEFAULT 0.0;
```

### Refactored Strategy Structure

#### Modular Strategy Design
```python
# bullish_strategy.py - Refactored for direct import
from typing import List, Callable, Dict, Any
from dataclasses import dataclass

@dataclass
class StrategyConfig:
    min_volume_multiple: float = 1.0
    strict_macd_positive: bool = False
    allow_overbought: bool = False
    require_52w_high: bool = False
    min_score: int = 70

class BullishBreakoutStrategy:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        
    def execute(self, tickers: List[str], config: StrategyConfig, 
               progress_callback: Callable[[int, int, str, Any], None] = None):
        """
        Execute strategy with optional progress reporting
        
        Args:
            tickers: List of stock symbols to analyze
            config: Strategy configuration parameters
            progress_callback: Optional callback(current, total, ticker, result)
        """
        run_id = self.db.start_run(
            strategy_code="bullish_breakout",
            version="2.0",
            params=config.__dict__,
            universe_source="api",
            universe_size=len(tickers),
            min_score=config.min_score
        )
        
        results = []
        for i, ticker in enumerate(tickers):
            try:
                result = self._evaluate_ticker(ticker, config)
                results.append(result)
                
                # Log to database
                self.db.log_result(
                    run_id=run_id,
                    strategy_code="bullish_breakout",
                    ticker=ticker,
                    passed=result.passed,
                    score=result.metrics.get("score", 0),
                    classification=result.metrics.get("recommendation"),
                    reasons=result.reasons,
                    metrics=result.metrics
                )
                
                # Report progress via callback
                if progress_callback:
                    progress_callback(i + 1, len(tickers), ticker, result)
                    
            except Exception as e:
                # Handle individual ticker errors gracefully
                if progress_callback:
                    progress_callback(i + 1, len(tickers), ticker, 
                                    {"error": str(e), "passed": False})
        
        self.db.finalize_run(run_id)
        
        passed = [r for r in results if r.passed]
        return StrategyResults(
            run_id=run_id,
            total_evaluated=len(results),
            qualifying_stocks=passed,
            execution_time_ms=self.db.get_run_duration(run_id)
        )
```

## Migration Strategy

### Phase 1: Preparation
1. Create new simplified strategy service classes
2. Refactor existing strategy scripts to be importable modules
3. Design and implement new database progress schema
4. Create new simplified API endpoints alongside existing ones

### Phase 2: Implementation
1. Implement synchronous execution endpoints
2. Create database-based progress tracking
3. Build simple polling endpoints for frontend
4. Update frontend to use simplified execution calls

### Phase 3: Testing & Validation
1. Comprehensive testing of synchronous execution
2. Performance comparison with current system
3. Frontend integration testing
4. Load testing for blocking behavior

### Phase 4: Migration & Cleanup
1. Switch frontend to use new endpoints
2. Remove complex SSE/subprocess components
3. Clean up unused code and dependencies
4. Update documentation

## Benefits of Simplified Architecture

### Reliability Improvements
- **Eliminated subprocess management**: No cross-platform subprocess issues
- **Removed SSE complexity**: No connection drops or browser compatibility issues
- **Simplified error handling**: Direct exception handling vs subprocess error parsing
- **Reduced concurrency issues**: No complex queue management or threading

### Maintainability Improvements
- **Reduced codebase size**: ~1000+ lines of complex code removed
- **Direct debugging**: Strategy execution happens in same process
- **Simplified testing**: No need to mock subprocesses or SSE connections
- **Clear data flow**: Request → Execute → Store → Respond

### Performance Characteristics
- **Predictable execution**: No queue delays or subprocess overhead
- **Direct memory access**: No subprocess communication overhead
- **Efficient progress tracking**: Direct database writes vs event streaming
- **Simplified scaling**: Standard HTTP scaling vs SSE connection management

## Implementation Timeline

### Week 1: Foundation
- [ ] Refactor strategy scripts to importable modules
- [ ] Create strategy service classes
- [ ] Design database schema extensions

### Week 2: Backend Implementation
- [ ] Implement synchronous execution endpoints
- [ ] Create database progress tracking
- [ ] Build polling endpoints

### Week 3: Frontend Integration
- [ ] Update frontend execution provider
- [ ] Modify strategy execution screen
- [ ] Implement progress polling

### Week 4: Testing & Migration
- [ ] Comprehensive testing
- [ ] Performance validation
- [ ] Production migration
- [ ] Legacy system removal

## Risk Mitigation

### Blocking Request Concerns
- **Mitigation**: Set appropriate FastAPI timeout limits
- **Monitoring**: Track execution times and optimize slow strategies
- **Fallback**: Option to add background execution later if needed

### Database Concurrency
- **Solution**: Use SQLite WAL mode for improved concurrent access
- **Monitoring**: Track database lock times and connection pools
- **Scaling**: Consider PostgreSQL migration if scaling issues arise

### Frontend Responsiveness
- **Solution**: Implement periodic progress polling during execution
- **UX**: Show progress indicators and allow cancellation
- **Timeout**: Implement client-side timeouts with retry logic

## Success Metrics

### Technical Metrics
- **Codebase reduction**: >50% reduction in execution system code
- **Error rate improvement**: <1% execution failures
- **Performance consistency**: 95% of executions complete within expected time
- **Database efficiency**: <100ms average progress update time

### User Experience Metrics
- **Reliability**: 99%+ successful strategy executions
- **Responsiveness**: <2 second response time for progress updates
- **Simplicity**: Reduced support tickets related to execution issues

This simplified architecture maintains all the functionality of the current system while dramatically reducing complexity and improving reliability.