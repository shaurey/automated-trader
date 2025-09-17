# Simplified Database Schema Design

## Overview

This document details the database schema modifications needed to support the simplified strategy execution system. The design eliminates complex real-time streaming in favor of simple database-centric progress tracking.

## Current Database Schema (v4)

Based on [`db.py`](db.py:29), the current schema includes:

```sql
-- Current tables
schema_meta(key, value)
instruments(ticker PK, instrument_type, style_category, sector, industry, country, currency, active, updated_at, notes)
holdings(holding_id PK, account, subaccount, ticker, quantity, cost_basis, opened_at, last_update, lot_tag, notes)
strategy_run(run_id PK, strategy_code, version, params_hash, params_json, started_at, completed_at, universe_source, universe_size, min_score, exit_status, duration_ms)
strategy_result(run_id+ticker PK, strategy_code, ticker, passed, score, classification, reasons, metrics_json, created_at)
```

## New Schema Extensions (v5)

### 1. Enhanced Strategy Run Table

Add new columns to support simplified execution tracking:

```sql
-- Extend existing strategy_run table
ALTER TABLE strategy_run ADD COLUMN execution_status TEXT DEFAULT 'pending';
ALTER TABLE strategy_run ADD COLUMN current_ticker TEXT;
ALTER TABLE strategy_run ADD COLUMN progress_percent REAL DEFAULT 0.0;
ALTER TABLE strategy_run ADD COLUMN processed_count INTEGER DEFAULT 0;
ALTER TABLE strategy_run ADD COLUMN total_count INTEGER DEFAULT 0;
ALTER TABLE strategy_run ADD COLUMN last_progress_update TEXT;
```

#### New Column Descriptions

- **execution_status**: `'pending'`, `'running'`, `'completed'`, `'failed'`, `'cancelled'`
- **current_ticker**: Currently processing ticker symbol (for real-time display)
- **progress_percent**: Current completion percentage (0.0-100.0)
- **processed_count**: Number of tickers processed so far
- **total_count**: Total number of tickers to process
- **last_progress_update**: Timestamp of last progress update

### 2. New Strategy Progress Table

Create a detailed progress tracking table for ticker-by-ticker progress:

```sql
CREATE TABLE IF NOT EXISTS strategy_execution_progress (
    run_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    processed_at TEXT NOT NULL,
    passed BOOLEAN,
    score REAL,
    classification TEXT,
    error_message TEXT,
    processing_time_ms INTEGER,
    PRIMARY KEY (run_id, ticker),
    FOREIGN KEY (run_id) REFERENCES strategy_run(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_progress_run_sequence ON strategy_execution_progress(run_id, sequence_number);
CREATE INDEX IF NOT EXISTS ix_progress_processed_at ON strategy_execution_progress(processed_at);
```

#### Progress Table Usage

This table enables:
- **Real-time progress tracking**: Query recent entries to show current status
- **Historical progress review**: Full audit trail of execution progress
- **Error tracking**: Specific error messages per ticker
- **Performance analysis**: Processing time per ticker for optimization

### 3. Migration Strategy (v4 → v5)

```python
# Migration code to be added to db.py ensure_schema()
def migrate_v4_to_v5(cur):
    """Migrate from v4 to v5 - Add simplified execution tracking"""
    
    # Add new columns to strategy_run if they don't exist
    if not column_exists("strategy_run", "execution_status"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN execution_status TEXT DEFAULT 'completed'")
        # Set existing runs to completed since they finished
        cur.execute("UPDATE strategy_run SET execution_status = 'completed' WHERE completed_at IS NOT NULL")
        cur.execute("UPDATE strategy_run SET execution_status = 'failed' WHERE completed_at IS NULL")
    
    if not column_exists("strategy_run", "current_ticker"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN current_ticker TEXT")
    
    if not column_exists("strategy_run", "progress_percent"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN progress_percent REAL DEFAULT 100.0")
        # Set completed runs to 100%
        cur.execute("UPDATE strategy_run SET progress_percent = 100.0 WHERE completed_at IS NOT NULL")
    
    if not column_exists("strategy_run", "processed_count"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN processed_count INTEGER DEFAULT 0")
        # Backfill from strategy_result counts
        cur.execute("""
            UPDATE strategy_run 
            SET processed_count = (
                SELECT COUNT(*) FROM strategy_result 
                WHERE strategy_result.run_id = strategy_run.run_id
            )
        """)
    
    if not column_exists("strategy_run", "total_count"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN total_count INTEGER")
        # Use universe_size as total_count
        cur.execute("UPDATE strategy_run SET total_count = universe_size")
    
    if not column_exists("strategy_run", "last_progress_update"):
        cur.execute("ALTER TABLE strategy_run ADD COLUMN last_progress_update TEXT")
        # Use completed_at or started_at as last update
        cur.execute("UPDATE strategy_run SET last_progress_update = COALESCE(completed_at, started_at)")
    
    # Create new progress table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS strategy_execution_progress (
            run_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            processed_at TEXT NOT NULL,
            passed BOOLEAN,
            score REAL,
            classification TEXT,
            error_message TEXT,
            processing_time_ms INTEGER,
            PRIMARY KEY (run_id, ticker),
            FOREIGN KEY (run_id) REFERENCES strategy_run(run_id) ON DELETE CASCADE
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS ix_progress_run_sequence ON strategy_execution_progress(run_id, sequence_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_progress_processed_at ON strategy_execution_progress(processed_at)")
    
    # Backfill progress table from existing strategy_result data
    cur.execute("""
        INSERT OR IGNORE INTO strategy_execution_progress 
        (run_id, ticker, sequence_number, processed_at, passed, score, classification)
        SELECT 
            run_id, 
            ticker, 
            ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY created_at) as sequence_number,
            created_at as processed_at,
            passed,
            score,
            classification
        FROM strategy_result
    """)
```

## Database Operation Patterns

### 1. Starting Execution

```sql
-- Create new run
INSERT INTO strategy_run (
    run_id, strategy_code, version, params_hash, params_json, 
    started_at, universe_source, universe_size, min_score, 
    execution_status, total_count, progress_percent
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, 0.0);
```

### 2. Progress Updates

```sql
-- Update run progress
UPDATE strategy_run 
SET current_ticker = ?, 
    processed_count = ?, 
    progress_percent = ?, 
    last_progress_update = ?
WHERE run_id = ?;

-- Insert ticker progress
INSERT INTO strategy_execution_progress (
    run_id, ticker, sequence_number, processed_at, 
    passed, score, classification, processing_time_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
```

### 3. Progress Queries

```sql
-- Get current execution status
SELECT 
    execution_status, current_ticker, progress_percent,
    processed_count, total_count, last_progress_update
FROM strategy_run 
WHERE run_id = ?;

-- Get recent progress (last 10 tickers)
SELECT ticker, passed, score, classification, processed_at
FROM strategy_execution_progress 
WHERE run_id = ? 
ORDER BY sequence_number DESC 
LIMIT 10;

-- Get detailed progress timeline
SELECT 
    ticker, sequence_number, processed_at, passed, 
    score, classification, processing_time_ms
FROM strategy_execution_progress 
WHERE run_id = ? 
ORDER BY sequence_number;
```

## API Response Models

### Execution Status Response

```python
@dataclass
class ExecutionStatus:
    run_id: str
    status: str  # pending, running, completed, failed, cancelled
    current_ticker: Optional[str]
    progress_percent: float
    processed_count: int
    total_count: int
    last_update: str
    estimated_completion: Optional[str]

@dataclass
class RecentProgress:
    ticker: str
    passed: bool
    score: Optional[float]
    classification: Optional[str]
    processed_at: str
    processing_time_ms: Optional[int]

@dataclass
class ExecutionProgress:
    status: ExecutionStatus
    recent_results: List[RecentProgress]
    summary: Dict[str, Any]  # passed_count, failed_count, etc.
```

## Database Performance Considerations

### 1. Indexing Strategy

```sql
-- Existing indexes for strategy_run
CREATE INDEX IF NOT EXISTS ix_run_status ON strategy_run(execution_status);
CREATE INDEX IF NOT EXISTS ix_run_progress_update ON strategy_run(last_progress_update);

-- Progress table indexes
CREATE INDEX IF NOT EXISTS ix_progress_run_sequence ON strategy_execution_progress(run_id, sequence_number);
CREATE INDEX IF NOT EXISTS ix_progress_status ON strategy_execution_progress(run_id, passed);
CREATE INDEX IF NOT EXISTS ix_progress_processed_at ON strategy_execution_progress(processed_at);
```

### 2. Cleanup Strategy

```sql
-- Clean up old progress data (keep last 30 days)
DELETE FROM strategy_execution_progress 
WHERE processed_at < datetime('now', '-30 days');

-- Archive completed runs older than 90 days
UPDATE strategy_run 
SET execution_status = 'archived' 
WHERE execution_status = 'completed' 
  AND completed_at < datetime('now', '-90 days');
```

### 3. Transaction Patterns

For atomic progress updates:

```python
def update_progress_atomic(self, run_id: str, ticker: str, result: TickerResult):
    """Atomically update both run progress and ticker progress"""
    with self.conn:  # Auto-commit transaction
        # Update run-level progress
        self.conn.execute("""
            UPDATE strategy_run 
            SET current_ticker = ?, 
                processed_count = processed_count + 1,
                progress_percent = (processed_count + 1) * 100.0 / total_count,
                last_progress_update = ?
            WHERE run_id = ?
        """, (ticker, self._now_iso(), run_id))
        
        # Insert ticker-level progress
        self.conn.execute("""
            INSERT INTO strategy_execution_progress (
                run_id, ticker, sequence_number, processed_at, 
                passed, score, classification, processing_time_ms
            ) VALUES (?, ?, 
                (SELECT COALESCE(MAX(sequence_number), 0) + 1 
                 FROM strategy_execution_progress WHERE run_id = ?), 
                ?, ?, ?, ?, ?)
        """, (run_id, ticker, run_id, self._now_iso(), 
              result.passed, result.metrics.get('score'), 
              result.metrics.get('classification'), 
              result.processing_time_ms))
```

## Benefits of New Schema

### 1. Simplified Progress Tracking
- **Direct database queries** instead of complex SSE event streams
- **Atomic updates** ensure data consistency
- **Historical tracking** for debugging and analysis

### 2. Better Performance
- **Efficient queries** with proper indexing
- **Reduced memory usage** compared to in-memory SSE state
- **Scalable storage** in database vs memory-limited queues

### 3. Improved Reliability
- **Persistent progress** survives server restarts
- **Transaction safety** prevents data loss
- **Simple recovery** from database state

### 4. Enhanced Monitoring
- **Detailed metrics** per ticker and per run
- **Performance tracking** with timing data
- **Error analysis** with specific error messages

This schema design provides all the functionality needed for the simplified execution system while maintaining data integrity and supporting future enhancements.