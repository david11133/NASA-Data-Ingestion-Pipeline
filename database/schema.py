"""
Database Schema Initialization
Handles creating tables, indexes, and views from DDL scripts
"""

##########################################################################################
import logging
from pathlib import Path
from typing import Optional
from database.connection import DatabaseManager, get_db_manager
##########################################################################################

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages database schema creation and updates"""
    
##########################################################################################
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize SchemaManager
        
        Args:
            db_manager: DatabaseManager instance (creates new if None)
        """
        self.db_manager = db_manager or get_db_manager()
        self.ddl_dir = Path(__file__).parent / "ddl"
    
##########################################################################################    
    def initialize_schema(self, force: bool = False):
        """
        Initialize database schema from DDL scripts
        
        Args:
            force: If True, drop existing tables before creating
        """
        logger.info("Initializing database schema...")
        
        if force:
            logger.warning("Force flag set - dropping existing tables")
            self._drop_all_tables()
        
        # Read and execute DDL script
        ddl_file = self.ddl_dir / "neo_tables.sql"
        
        if not ddl_file.exists():
            raise FileNotFoundError(f"DDL script not found: {ddl_file}")
        
        with open(ddl_file, 'r') as f:
            ddl_script = f.read()
        
        try:
            self.db_manager.execute_script(ddl_script)
            logger.info("✓ Database schema initialized successfully")
            self._verify_schema()
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise
    
##########################################################################################
    def _drop_all_tables(self):
        """Drop all tables in the database"""
        tables = [
            'raw_data_archive',
            'close_approaches',
            'estimated_diameters',
            'api_metadata',
            'asteroids'
        ]
        
        for table in tables:
            try:
                self.db_manager.execute_query(f"DROP TABLE IF EXISTS {table}")
                logger.debug(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Could not drop table {table}: {e}")
        
        # Drop views
        views = ['v_asteroid_close_approaches', 'v_hazardous_asteroids']
        for view in views:
            try:
                self.db_manager.execute_query(f"DROP VIEW IF EXISTS {view}")
                logger.debug(f"Dropped view: {view}")
            except Exception as e:
                logger.warning(f"Could not drop view {view}: {e}")
    
##########################################################################################
    def _verify_schema(self):
        """Verify that all expected tables exist"""
        expected_tables = [
            'asteroids',
            'estimated_diameters',
            'close_approaches',
            'api_metadata',
            'raw_data_archive'
        ]
        
        for table in expected_tables:
            if self.db_manager.table_exists(table):
                row_count = self.db_manager.count_rows(table)
                logger.info(f"  ✓ Table '{table}' exists ({row_count} rows)")
            else:
                logger.error(f"  ✗ Table '{table}' is missing!")
                raise RuntimeError(f"Required table '{table}' was not created")
    
##########################################################################################
    def get_schema_stats(self) -> dict:
        """
        Get statistics about the database schema
        
        Returns:
            Dictionary with table names and row counts
        """
        tables = [
            'asteroids',
            'estimated_diameters', 
            'close_approaches',
            'api_metadata',
            'raw_data_archive'
        ]
        
        stats = {}
        for table in tables:
            if self.db_manager.table_exists(table):
                stats[table] = self.db_manager.count_rows(table)
            else:
                stats[table] = None
        
        return stats
    
##########################################################################################
    def print_schema_info(self):
        """Print detailed schema information"""
        tables = ['asteroids', 'estimated_diameters', 'close_approaches', 'api_metadata']
        
        print("\n" + "="*70)
        print("DATABASE SCHEMA INFORMATION")
        print("="*70)
        
        for table in tables:
            if not self.db_manager.table_exists(table):
                print(f"\n❌ Table '{table}' does not exist")
                continue
            
            print(f"\n📊 Table: {table}")
            print("-" * 70)
            
            info = self.db_manager.get_table_info(table)
            
            # Print columns
            print(f"{'Column':<30} {'Type':<15} {'Not Null':<10} {'PK'}")
            print("-" * 70)
            for col in info:
                print(f"{col['name']:<30} {col['type']:<15} "
                      f"{'Yes' if col['notnull'] else 'No':<10} "
                      f"{'Yes' if col['pk'] else ''}")
            
            # Print row count
            count = self.db_manager.count_rows(table)
            print(f"\nTotal rows: {count:,}")
        
        print("\n" + "="*70)

##########################################################################################
def initialize_database(db_path: str = "data/nasa_neo.db", force: bool = False):
    """
    Convenience function to initialize database
    
    Args:
        db_path: Path to database file
        force: If True, recreate all tables
    """
    db_manager = get_db_manager(db_path)
    schema_manager = SchemaManager(db_manager)
    schema_manager.initialize_schema(force=force)
    return schema_manager

##########################################################################################
if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    schema_manager = initialize_database(force=False)
    
    # Print schema information
    schema_manager.print_schema_info()
    
    # Print statistics
    stats = schema_manager.get_schema_stats()
    print("\nDatabase Statistics:")
    for table, count in stats.items():
        if count is not None:
            print(f"  {table}: {count:,} rows")
        else:
            print(f"  {table}: Table does not exist")