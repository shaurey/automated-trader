"""Database connection and session management for the FastAPI application.

This module provides database connection utilities that integrate with
the existing SQLite database and db.py module.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional

from .models import DatabaseConfig


class DatabaseManager:
    """Database connection manager for SQLite operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default from environment.
        """
        if db_path is None:
            # Default to existing database location
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "at_data.sqlite"
            )
            db_path = os.getenv("DATABASE_PATH", default_path)
        
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the database file exists and is accessible."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        # Test connection
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to database: {e}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection context manager.
        
        Yields:
            sqlite3.Connection: Database connection with row factory set
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
        
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()
    
    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Get a database cursor context manager.
        
        Yields:
            sqlite3.Cursor: Database cursor for executing queries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return all results.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            List of sqlite3.Row objects
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a SELECT query and return first result.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            sqlite3.Row object or None if no results
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.
    
    Returns:
        DatabaseManager: The global database manager
    """
    return db_manager


# Dependency for FastAPI routes
def get_database_connection():
    """FastAPI dependency to get database connection.
    
    Yields:
        sqlite3.Connection: Database connection for use in routes
    """
    # Create a fresh connection for each request to avoid threading issues
    conn = None
    try:
        # Allow SQLite connection to be used across threads
        conn = sqlite3.connect(db_manager.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()