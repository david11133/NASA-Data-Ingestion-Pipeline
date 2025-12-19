"""
Database Connection Manager
Handles SQLite database connections with context managers and transaction support
"""

##########################################################################################
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Any, List, Tuple
##########################################################################################

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections and operations.
    Implements singleton pattern to ensure single connection pool.
    """
    
    _instance = None
    
##########################################################################################
    def __new__(cls, db_path: str = "data/nasa_neo.db"):
        """Singleton implementation"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.connection = None
        return cls._instance

##########################################################################################
    def __init__(self, db_path: str = "data/nasa_neo.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        if not hasattr(self, 'initialized'):
            self.db_path = Path(db_path)
            self.connection = None
            self.initialized = True
            
            # Create data directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"DatabaseManager initialized with path: {self.db_path}")
    
##########################################################################################
    def get_connection(self) -> sqlite3.Connection:
        """
        Get or create database connection
        
        Returns:
            sqlite3.Connection: Active database connection
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Use Row factory for dict-like access
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Database connection established: {self.db_path}")
        
        return self.connection
    
##########################################################################################
    def close_connection(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
##########################################################################################
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions
        Automatically commits on success, rolls back on error
        
        Usage:
            with db_manager.transaction():
                cursor.execute("INSERT ...")
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
    
##########################################################################################
    @contextmanager
    def cursor(self):
        """
        Context manager for database cursor
        
        Usage:
            with db_manager.cursor() as cur:
                cur.execute("SELECT ...")
        """
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()
    
##########################################################################################
    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None,
        fetch: bool = False
    ) -> Optional[List[sqlite3.Row]]:
        """
        Execute a single query
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, None otherwise
        """
        with self.cursor() as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()
            self.get_connection().commit()
            return None
    
##########################################################################################
    def execute_many(self, query: str, params_list: List[Tuple]):
        """
        Execute query with multiple parameter sets (batch insert)
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        with self.cursor() as cur:
            cur.executemany(query, params_list)
            self.get_connection().commit()
            logger.debug(f"Batch operation completed: {len(params_list)} rows")
    
##########################################################################################
    def execute_script(self, script: str):
        """
        Execute a SQL script (multiple statements)
        
        Args:
            script: SQL script string
        """
        conn = self.get_connection()
        conn.executescript(script)
        conn.commit()
        logger.info("SQL script executed successfully")
    
##########################################################################################
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,), fetch=True)
        return len(result) > 0
    
##########################################################################################
    def get_table_info(self, table_name: str) -> List[sqlite3.Row]:
        """
        Get table schema information
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query, fetch=True)
    
##########################################################################################
    def count_rows(self, table_name: str) -> int:
        """
        Count rows in a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of rows
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query, fetch=True)
        return result[0]['count'] if result else 0

##########################################################################################
# Convenience function for getting database manager instance
def get_db_manager(db_path: str = "data/nasa_neo.db") -> DatabaseManager:
    """
    Get DatabaseManager instance
    
    Args:
        db_path: Path to database file
        
    Returns:
        DatabaseManager instance
    """
    return DatabaseManager(db_path)