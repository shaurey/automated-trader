"""
Database Connection Module for Simplified Execution System

This module provides database connection utilities for the simplified
strategy execution system.
"""

import sqlite3
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Database path - default to existing database location
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "at_data.sqlite")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


def get_db_connection() -> sqlite3.Connection:
    """
    Get database connection for strategy execution.
    
    Returns:
        SQLite connection with row factory enabled
    """
    try:
        # Use check_same_thread=False to allow cross-thread access
        db = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.row_factory = sqlite3.Row  # Enable column access by name
        return db
    except Exception as e:
        logger.error(f"Failed to connect to database at {DB_PATH}: {e}")
        raise


def initialize_execution_tables(db_connection: sqlite3.Connection):
    """
    Initialize tables required for simplified execution tracking.
    
    Args:
        db_connection: SQLite database connection
    """
    try:
        # Create simplified execution tracking tables for the new system
        # Note: We keep the existing strategy_run table as-is and add new tables
        
        # Create strategy_execution_status table for simplified execution tracking
        db_connection.execute('''
            CREATE TABLE IF NOT EXISTS strategy_execution_status (
                run_id TEXT PRIMARY KEY,
                strategy_code TEXT NOT NULL,
                execution_status TEXT DEFAULT 'queued',
                total_count INTEGER DEFAULT 0,
                processed_count INTEGER DEFAULT 0,
                qualifying_count INTEGER DEFAULT 0,
                current_ticker TEXT,
                progress_percent REAL DEFAULT 0.0,
                execution_started_at TEXT,
                last_progress_update TEXT,
                execution_time_ms INTEGER,
                summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create strategy_execution_progress table if it doesn't exist
        db_connection.execute('''
            CREATE TABLE IF NOT EXISTS strategy_execution_progress (
                run_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                sequence_number INTEGER DEFAULT 0,
                processed_at TEXT,
                passed BOOLEAN DEFAULT 0,
                score REAL DEFAULT 0.0,
                classification TEXT,
                error_message TEXT,
                processing_time_ms INTEGER DEFAULT 0,
                PRIMARY KEY (run_id, ticker),
                FOREIGN KEY (run_id) REFERENCES strategy_execution_status (run_id)
            )
        ''')
        
        # Create indexes for performance
        db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_strategy_execution_status
            ON strategy_execution_status (execution_status)
        ''')
        
        db_connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_execution_progress_run_sequence
            ON strategy_execution_progress (run_id, sequence_number)
        ''')
        
        db_connection.commit()
        logger.info("Execution tracking tables initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize execution tables: {e}")
        raise


def verify_database_schema(db_connection: sqlite3.Connection) -> bool:
    """
    Verify that required tables exist in the database.
    
    Args:
        db_connection: SQLite database connection
        
    Returns:
        True if schema is valid, False otherwise
    """
    try:
        # Check if required tables exist
        cursor = db_connection.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('strategy_execution_status', 'strategy_execution_progress')
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['strategy_execution_status', 'strategy_execution_progress']
        
        missing_tables = set(required_tables) - set(existing_tables)
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("Database schema verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Database schema verification failed: {e}")
        return False


def setup_database() -> sqlite3.Connection:
    """
    Setup database connection and ensure required tables exist.
    
    Returns:
        Configured database connection
    """
    try:
        db = get_db_connection()
        
        # Verify or create schema
        if not verify_database_schema(db):
            logger.info("Initializing missing database tables...")
            initialize_execution_tables(db)
        
        return db
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise


# Module-level connection for dependency injection
_db_connection: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    """
    Get global database connection for dependency injection.
    
    Returns:
        Database connection instance
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = setup_database()
    return _db_connection


# Backward compatibility functions for existing code
def get_database_connection() -> sqlite3.Connection:
    """
    Backward compatibility function for existing imports.
    
    Returns:
        Database connection instance
    """
    return get_db_connection()


class DatabaseManager:
    """Database manager class for backward compatibility with existing code."""
    
    def __init__(self, db_path: str = None):
        """Initialize database manager with optional path."""
        self.db_path = db_path or DB_PATH
        self._connection = None
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        conn = self.get_connection()
        return conn.execute(query, params)

    def execute_one(self, query: str, params: tuple = ()):
        """Execute a query expected to return a single row.

        Returns the first row (as sqlite3.Row) or None if no rows.
        Mirrors the older helper used by legacy code.
        """
        cur = self.execute_query(query, params)
        return cur.fetchone()
    
    def commit(self):
        """Commit transaction."""
        if self._connection:
            self._connection.commit()
    
    def close(self):
        """Close connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


def get_db_manager(db_path: str = None):
    """
    Get database manager instance for backward compatibility.
    
    Args:
        db_path: Optional database path
        
    Returns:
        DatabaseManager instance
    """
    return DatabaseManager(db_path)