"""
NEO Data Loader
Loads JSON data from raw files into SQLite database
Implements incremental loading to avoid duplicates
Enhanced to support both raw and transformed data
"""

##########################################################################################
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from database.connection import DatabaseManager, get_db_manager
##########################################################################################

logger = logging.getLogger(__name__)


class NEOLoader:
    """Loads NEO data from JSON files into SQLite database"""
    
##########################################################################################
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize NEO Loader
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager or get_db_manager()
        self.raw_data_path = Path("data/raw/neos")
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
    
##########################################################################################
    def check_already_loaded(self, start_date: str, end_date: str) -> bool:
        """
        Check if date range has already been loaded
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            True if already loaded, False otherwise
        """
        query = """
            SELECT COUNT(*) as count 
            FROM api_metadata 
            WHERE start_date = ? AND end_date = ? AND status = 'success'
        """
        result = self.db_manager.execute_query(
            query, 
            (start_date, end_date), 
            fetch=True
        )
        
        is_loaded = result[0]['count'] > 0 if result else False
        
        if is_loaded:
            logger.info(f"Date range {start_date} to {end_date} already loaded")
        
        return is_loaded
    
##########################################################################################
    def load_from_json_file(self, json_file_path: Path, skip_if_loaded: bool = True) -> Dict:
        """
        Load NEO data from a JSON file into database
        
        Args:
            json_file_path: Path to JSON file
            skip_if_loaded: Skip if data already loaded
            
        Returns:
            Dictionary with loading statistics
        """
        logger.info(f"Loading data from: {json_file_path}")
        
        # Read JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        return self.load_from_json_data(data, str(json_file_path), skip_if_loaded)
    
##########################################################################################
    def load_from_json_data(
        self, 
        data: Dict, 
        source_file: str = "unknown",
        skip_if_loaded: bool = True
    ) -> Dict:
        """
        Load NEO data from JSON dictionary into database
        
        Args:
            data: JSON data dictionary
            source_file: Source file path for tracking
            skip_if_loaded: Skip if data already loaded
            
        Returns:
            Dictionary with loading statistics
        """
        stats = {
            'asteroids_inserted': 0,
            'asteroids_updated': 0,
            'close_approaches_inserted': 0,
            'diameters_inserted': 0,
            'errors': []
        }
        
        # Extract metadata
        element_count = data.get('element_count', 0)
        near_earth_objects = data.get('near_earth_objects', {})
        
        # Determine date range
        dates = sorted(near_earth_objects.keys())
        if not dates:
            logger.warning("No dates found in data")
            return stats
        
        start_date = dates[0]
        end_date = dates[-1]
        
        # Check if already loaded
        if skip_if_loaded and self.check_already_loaded(start_date, end_date):
            logger.info("Data already loaded, skipping...")
            return stats
        
        logger.info(f"Processing date range: {start_date} to {end_date}")
        
        try:
            with self.db_manager.transaction():
                # Process each date's asteroids
                for date_str, asteroids in near_earth_objects.items():
                    for asteroid_data in asteroids:
                        try:
                            # Insert/update asteroid
                            asteroid_stats = self._insert_asteroid(asteroid_data)
                            stats['asteroids_inserted'] += asteroid_stats['inserted']
                            stats['asteroids_updated'] += asteroid_stats['updated']
                            
                            # Insert diameters
                            diameter_count = self._insert_diameters(asteroid_data)
                            stats['diameters_inserted'] += diameter_count
                            
                            # Insert close approaches
                            approach_count = self._insert_close_approaches(asteroid_data)
                            stats['close_approaches_inserted'] += approach_count
                            
                        except Exception as e:
                            error_msg = f"Error processing asteroid {asteroid_data.get('id')}: {e}"
                            logger.error(error_msg)
                            stats['errors'].append(error_msg)
                
                # Record API metadata
                self._insert_api_metadata(
                    start_date, 
                    end_date, 
                    element_count,
                    source_file
                )
                
                # Optionally archive raw JSON
                self._archive_raw_data(start_date, end_date, data, source_file)
        
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            stats['errors'].append(str(e))
            raise
        
        # Log summary
        logger.info(f"Loading complete: {stats}")
        return stats

##########################################################################################
    def load_transformed_data(self, transformed_data: Dict, source_file: str = "transformed") -> Dict:
        """
        Load data from transformed/validated format
        This is an alternative loading method for pre-transformed data
        
        Args:
            transformed_data: Dictionary from NEOTransformer with structure:
                {
                    'asteroids': [...],
                    'estimated_diameters': [...],
                    'close_approaches': [...],
                    'metadata': {...}
                }
            source_file: Source identifier for tracking
            
        Returns:
            Dictionary with loading statistics
        """
        logger.info("Loading from transformed data format")
        
        stats = {
            'asteroids_inserted': 0,
            'asteroids_updated': 0,
            'close_approaches_inserted': 0,
            'diameters_inserted': 0,
            'errors': []
        }
        
        try:
            with self.db_manager.transaction():
                # Load asteroids
                for asteroid in transformed_data['asteroids']:
                    try:
                        result = self._insert_transformed_asteroid(asteroid)
                        stats['asteroids_inserted'] += result['inserted']
                        stats['asteroids_updated'] += result['updated']
                    except Exception as e:
                        logger.error(f"Error loading asteroid {asteroid.get('neo_id')}: {e}")
                        stats['errors'].append(str(e))
                
                # Load diameters
                for diameter in transformed_data['estimated_diameters']:
                    try:
                        self._insert_transformed_diameter(diameter)
                        stats['diameters_inserted'] += 1
                    except Exception as e:
                        logger.error(f"Error loading diameter: {e}")
                        stats['errors'].append(str(e))
                
                # Load close approaches
                for approach in transformed_data['close_approaches']:
                    try:
                        self._insert_transformed_approach(approach)
                        stats['close_approaches_inserted'] += 1
                    except Exception as e:
                        logger.error(f"Error loading approach: {e}")
                        stats['errors'].append(str(e))
                
                # Load metadata
                metadata = transformed_data.get('metadata', {})
                if metadata:
                    self._insert_api_metadata(
                        metadata['start_date'],
                        metadata['end_date'],
                        metadata['element_count'],
                        source_file
                    )
        
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            stats['errors'].append(str(e))
            raise
        
        logger.info(f"Transformed data loading complete: {stats}")
        return stats
    
##########################################################################################
    def _insert_asteroid(self, asteroid_data: Dict) -> Dict:
        """Insert or update asteroid record from raw format"""
        neo_id = asteroid_data['id']
        
        # Check if asteroid exists
        existing = self.db_manager.execute_query(
            "SELECT neo_id FROM asteroids WHERE neo_id = ?",
            (neo_id,),
            fetch=True
        )
        
        query = """
            INSERT OR REPLACE INTO asteroids (
                neo_id, neo_reference_id, name, nasa_jpl_url,
                absolute_magnitude_h, is_potentially_hazardous,
                is_sentry_object, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = (
            neo_id,
            asteroid_data['neo_reference_id'],
            asteroid_data['name'],
            asteroid_data.get('nasa_jpl_url'),
            asteroid_data.get('absolute_magnitude_h'),
            asteroid_data.get('is_potentially_hazardous_asteroid', False),
            asteroid_data.get('is_sentry_object', False)
        )
        
        self.db_manager.execute_query(query, params)
        
        return {
            'inserted': 0 if existing else 1,
            'updated': 1 if existing else 0
        }

##########################################################################################
    def _insert_transformed_asteroid(self, asteroid: Dict) -> Dict:
        """Insert or update asteroid record from transformed format"""
        neo_id = asteroid['neo_id']
        
        # Check if asteroid exists
        existing = self.db_manager.execute_query(
            "SELECT neo_id FROM asteroids WHERE neo_id = ?",
            (neo_id,),
            fetch=True
        )
        
        query = """
            INSERT OR REPLACE INTO asteroids (
                neo_id, neo_reference_id, name, nasa_jpl_url,
                absolute_magnitude_h, is_potentially_hazardous,
                is_sentry_object, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            asteroid['neo_id'],
            asteroid['neo_reference_id'],
            asteroid['name'],
            asteroid.get('nasa_jpl_url'),
            asteroid['absolute_magnitude_h'],
            asteroid['is_potentially_hazardous'],
            asteroid['is_sentry_object'],
            asteroid['created_at'],
            asteroid['updated_at']
        )
        
        self.db_manager.execute_query(query, params)
        
        return {
            'inserted': 0 if existing else 1,
            'updated': 1 if existing else 0
        }
    
##########################################################################################
    def _insert_diameters(self, asteroid_data: Dict) -> int:
        """Insert estimated diameter records from raw format"""
        neo_id = asteroid_data['id']
        estimated_diameter = asteroid_data.get('estimated_diameter', {})
        
        if not estimated_diameter:
            return 0
        
        count = 0
        query = """
            INSERT OR REPLACE INTO estimated_diameters (
                neo_id, unit, estimated_diameter_min, estimated_diameter_max
            ) VALUES (?, ?, ?, ?)
        """
        
        for unit, values in estimated_diameter.items():
            params = (
                neo_id,
                unit,
                values.get('estimated_diameter_min'),
                values.get('estimated_diameter_max')
            )
            self.db_manager.execute_query(query, params)
            count += 1
        
        return count

##########################################################################################
    def _insert_transformed_diameter(self, diameter: Dict):
        """Insert diameter record from transformed format"""
        query = """
            INSERT OR REPLACE INTO estimated_diameters (
                neo_id, unit, estimated_diameter_min, estimated_diameter_max
            ) VALUES (?, ?, ?, ?)
        """
        
        params = (
            diameter['neo_id'],
            diameter['unit'],
            diameter['estimated_diameter_min'],
            diameter['estimated_diameter_max']
        )
        
        self.db_manager.execute_query(query, params)
    
##########################################################################################
    def _insert_close_approaches(self, asteroid_data: Dict) -> int:
        """Insert close approach records from raw format"""
        neo_id = asteroid_data['id']
        close_approaches = asteroid_data.get('close_approach_data', [])
        
        if not close_approaches:
            return 0
        
        query = """
            INSERT OR REPLACE INTO close_approaches (
                neo_id, close_approach_date, close_approach_date_full,
                epoch_date_close_approach,
                velocity_km_per_sec, velocity_km_per_hour, velocity_miles_per_hour,
                miss_distance_astronomical, miss_distance_lunar,
                miss_distance_km, miss_distance_miles,
                orbiting_body
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for approach in close_approaches:
            rel_velocity = approach.get('relative_velocity', {})
            miss_distance = approach.get('miss_distance', {})
            
            params = (
                neo_id,
                approach.get('close_approach_date'),
                approach.get('close_approach_date_full'),
                approach.get('epoch_date_close_approach'),
                float(rel_velocity.get('kilometers_per_second', 0)),
                float(rel_velocity.get('kilometers_per_hour', 0)),
                float(rel_velocity.get('miles_per_hour', 0)),
                float(miss_distance.get('astronomical', 0)),
                float(miss_distance.get('lunar', 0)),
                float(miss_distance.get('kilometers', 0)),
                float(miss_distance.get('miles', 0)),
                approach.get('orbiting_body', 'Earth')
            )
            
            self.db_manager.execute_query(query, params)
        
        return len(close_approaches)

##########################################################################################
    def _insert_transformed_approach(self, approach: Dict):
        """Insert close approach record from transformed format"""
        query = """
            INSERT OR REPLACE INTO close_approaches (
                neo_id, close_approach_date, close_approach_date_full,
                epoch_date_close_approach,
                velocity_km_per_sec, velocity_km_per_hour, velocity_miles_per_hour,
                miss_distance_astronomical, miss_distance_lunar,
                miss_distance_km, miss_distance_miles,
                orbiting_body, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            approach['neo_id'],
            approach['close_approach_date'],
            approach.get('close_approach_date_full'),
            approach.get('epoch_date_close_approach'),
            approach['velocity_km_per_sec'],
            approach['velocity_km_per_hour'],
            approach['velocity_miles_per_hour'],
            approach['miss_distance_astronomical'],
            approach['miss_distance_lunar'],
            approach['miss_distance_km'],
            approach['miss_distance_miles'],
            approach['orbiting_body'],
            approach['created_at']
        )
        
        self.db_manager.execute_query(query, params)
    
##########################################################################################
    def _insert_api_metadata(
        self, 
        start_date: str, 
        end_date: str, 
        element_count: int,
        source_file: str
    ):
        """Record API extraction metadata"""
        query = """
            INSERT OR REPLACE INTO api_metadata (
                start_date, end_date, api_endpoint,
                element_count, extraction_timestamp, status
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'success')
        """
        
        params = (
            start_date,
            end_date,
            f"neo/feed (from {source_file})",
            element_count
        )
        
        self.db_manager.execute_query(query, params)
    
##########################################################################################
    def _archive_raw_data(
        self, 
        start_date: str, 
        end_date: str, 
        data: Dict,
        file_path: str
    ):
        """Archive raw JSON data for lineage"""
        query = """
            INSERT INTO raw_data_archive (
                start_date, end_date, raw_json, file_path
            ) VALUES (?, ?, ?, ?)
        """
        
        params = (
            start_date,
            end_date,
            json.dumps(data),
            file_path
        )
        
        self.db_manager.execute_query(query, params)
    
##########################################################################################
    def load_directory(self, directory: Optional[Path] = None) -> Dict:
        """
        Load all JSON files from a directory
        
        Args:
            directory: Directory path (uses default if None)
            
        Returns:
            Combined statistics dictionary
        """
        directory = directory or self.raw_data_path
        
        json_files = sorted(directory.glob("**/*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {directory}")
            return {}
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        combined_stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'total_asteroids': 0,
            'total_approaches': 0
        }
        
        for json_file in json_files:
            try:
                stats = self.load_from_json_file(json_file)
                combined_stats['files_processed'] += 1
                combined_stats['total_asteroids'] += stats['asteroids_inserted']
                combined_stats['total_approaches'] += stats['close_approaches_inserted']
            except Exception as e:
                logger.error(f"Failed to load {json_file}: {e}")
                combined_stats['files_skipped'] += 1
        
        logger.info(f"Directory loading complete: {combined_stats}")
        return combined_stats