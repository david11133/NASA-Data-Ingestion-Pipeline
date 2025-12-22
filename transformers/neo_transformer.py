"""
NEO-specific data transformer
"""
import logging
from typing import Any, Dict, List, Tuple
from datetime import datetime
import json
from pathlib import Path

from .base_transformer import BaseTransformer
from .data_quality import DataQualityChecker

logger = logging.getLogger(__name__)


class NEOTransformer(BaseTransformer):
    """
    Transforms raw NASA NEO data into structured database format.
    Handles parsing nested JSON and creating normalized tables.
    """
    
    def __init__(self, quality_checker: DataQualityChecker = None):
        """
        Initialize NEO transformer.
        
        Args:
            quality_checker: Optional data quality checker instance
        """
        super().__init__()
        self.quality_checker = quality_checker or DataQualityChecker()
    
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw NEO data into structured format.
        
        Args:
            raw_data: Raw data from NASA API
            
        Returns:
            Dictionary containing transformed data:
            {
                'asteroids': [...],
                'estimated_diameters': [...],
                'close_approaches': [...],
                'metadata': {...}
            }
        """
        logger.info("Starting transformation of NEO data")
        self.reset_stats()
        
        transformed_data = {
            'asteroids': [],
            'estimated_diameters': [],
            'close_approaches': [],
            'metadata': self._extract_metadata(raw_data)
        }
        
        # Extract NEO objects grouped by date
        near_earth_objects = raw_data.get('near_earth_objects', {})
        
        for date, neos in near_earth_objects.items():
            logger.info(f"Processing {len(neos)} NEOs for date: {date}")
            
            for neo in neos:
                try:
                    self.transformation_stats['records_processed'] += 1
                    
                    # Transform asteroid basic info
                    asteroid = self._transform_asteroid(neo)
                    transformed_data['asteroids'].append(asteroid)
                    
                    # Transform diameter estimates
                    diameters = self._transform_diameters(neo)
                    transformed_data['estimated_diameters'].extend(diameters)
                    
                    # Transform close approach data
                    approaches = self._transform_close_approaches(neo)
                    transformed_data['close_approaches'].extend(approaches)
                    
                    self.transformation_stats['records_transformed'] += 1
                    
                except Exception as e:
                    self.transformation_stats['records_failed'] += 1
                    self.transformation_stats['errors'].append({
                        'neo_id': neo.get('id', 'unknown'),
                        'error': str(e)
                    })
                    logger.error(f"Error transforming NEO {neo.get('id')}: {e}")
        
        # Run quality checks
        self._run_quality_checks(transformed_data)
        
        # Log statistics
        self.log_stats()
        
        return transformed_data
    
    def transform_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transform data from a JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Transformed data dictionary
        """
        logger.info(f"Loading data from {file_path}")
        
        with open(file_path, 'r') as f:
            raw_data = json.load(f)
        
        return self.transform(raw_data)
    
    def _transform_asteroid(self, neo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform asteroid basic information.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            Transformed asteroid dictionary
        """
        asteroid = {
            'neo_id': neo.get('id'),
            'neo_reference_id': neo.get('neo_reference_id'),
            'name': neo.get('name', '').strip(),
            'nasa_jpl_url': neo.get('nasa_jpl_url'),
            'absolute_magnitude_h': self._safe_float(
                neo.get('absolute_magnitude_h')
            ),
            'is_potentially_hazardous': self._safe_bool(
                neo.get('is_potentially_hazardous_asteroid'), 
                default=False
            ),
            'is_sentry_object': self._safe_bool(
                neo.get('is_sentry_object'), 
                default=False
            ),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        return asteroid
    
    def _transform_diameters(self, neo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform estimated diameter data for all units.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            List of diameter records (one per unit)
        """
        diameters = []
        neo_id = neo.get('id')
        
        estimated_diameter = neo.get('estimated_diameter', {})
        
        # Process each unit
        for unit, values in estimated_diameter.items():
            diameter = {
                'neo_id': neo_id,
                'unit': unit,
                'estimated_diameter_min': self._safe_float(
                    values.get('estimated_diameter_min')
                ),
                'estimated_diameter_max': self._safe_float(
                    values.get('estimated_diameter_max')
                )
            }
            diameters.append(diameter)
        
        return diameters
    
    def _transform_close_approaches(self, neo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform close approach data.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            List of close approach records
        """
        approaches = []
        neo_id = neo.get('id')
        
        close_approach_data = neo.get('close_approach_data', [])
        
        for approach in close_approach_data:
            # Extract velocity data
            relative_velocity = approach.get('relative_velocity', {})
            
            # Extract miss distance data
            miss_distance = approach.get('miss_distance', {})
            
            approach_record = {
                'neo_id': neo_id,
                'close_approach_date': self._parse_date(
                    approach.get('close_approach_date')
                ),
                'close_approach_date_full': approach.get('close_approach_date_full'),
                'epoch_date_close_approach': self._safe_int(
                    approach.get('epoch_date_close_approach')
                ),
                # Velocity fields
                'velocity_km_per_sec': self._safe_float(
                    relative_velocity.get('kilometers_per_second')
                ),
                'velocity_km_per_hour': self._safe_float(
                    relative_velocity.get('kilometers_per_hour')
                ),
                'velocity_miles_per_hour': self._safe_float(
                    relative_velocity.get('miles_per_hour')
                ),
                # Distance fields
                'miss_distance_astronomical': self._safe_float(
                    miss_distance.get('astronomical')
                ),
                'miss_distance_lunar': self._safe_float(
                    miss_distance.get('lunar')
                ),
                'miss_distance_km': self._safe_float(
                    miss_distance.get('kilometers')
                ),
                'miss_distance_miles': self._safe_float(
                    miss_distance.get('miles')
                ),
                'orbiting_body': approach.get('orbiting_body', 'Earth'),
                'created_at': datetime.now().isoformat()
            }
            
            # Add derived fields
            approach_record['miss_distance_au_calculated'] = self._convert_km_to_au(
                approach_record['miss_distance_km']
            )
            
            approaches.append(approach_record)
        
        return approaches
    
    def _extract_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract API metadata from raw response.
        
        Args:
            raw_data: Raw API response
            
        Returns:
            Metadata dictionary
        """
        # Extract dates from the near_earth_objects keys
        near_earth_objects = raw_data.get('near_earth_objects', {})
        dates = list(near_earth_objects.keys())
        
        metadata = {
            'start_date': min(dates) if dates else None,
            'end_date': max(dates) if dates else None,
            'api_endpoint': 'feed',
            'element_count': raw_data.get('element_count', 0),
            'extraction_timestamp': datetime.now().isoformat(),
            'status': 'success',
            'error_message': None
        }
        
        return metadata
    
    def _run_quality_checks(self, transformed_data: Dict[str, Any]):
        """
        Run quality checks on transformed data.
        
        Args:
            transformed_data: Transformed data dictionary
        """
        logger.info("Running data quality checks")
        
        # Check asteroids
        for asteroid in transformed_data['asteroids']:
            self.quality_checker.validate_asteroid_record(asteroid)
        
        # Check diameters
        for diameter in transformed_data['estimated_diameters']:
            self.quality_checker.validate_diameter_record(diameter)
        
        # Check close approaches
        for approach in transformed_data['close_approaches']:
            self.quality_checker.validate_close_approach_record(approach)
        
        # Check for duplicates
        dup_asteroids = self.quality_checker.check_duplicates(
            transformed_data['asteroids'],
            ['neo_id']
        )
        if dup_asteroids['duplicate_count'] > 0:
            logger.warning(f"Found {dup_asteroids['duplicate_count']} duplicate asteroids")
        
        dup_approaches = self.quality_checker.check_duplicates(
            transformed_data['close_approaches'],
            ['neo_id', 'close_approach_date', 'orbiting_body']
        )
        if dup_approaches['duplicate_count'] > 0:
            logger.warning(f"Found {dup_approaches['duplicate_count']} duplicate close approaches")
        
        # Print summary
        self.quality_checker.print_summary()
    
    def save_transformed_data(
        self, 
        transformed_data: Dict[str, Any], 
        output_dir: str = "data/processed"
    ):
        """
        Save transformed data to JSON files.
        
        Args:
            transformed_data: Transformed data dictionary
            output_dir: Output directory path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with date range
        metadata = transformed_data['metadata']
        start_date = metadata['start_date']
        end_date = metadata['end_date']
        filename = f"transformed_{start_date}_{end_date}.json"
        
        file_path = output_path / filename
        
        with open(file_path, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        logger.info(f"Saved transformed data to {file_path}")
        
        # Save quality report separately
        quality_report = self.quality_checker.get_summary()
        report_filename = f"quality_report_{start_date}_{end_date}.json"
        report_path = output_path / report_filename
        
        with open(report_path, 'w') as f:
            json.dump(quality_report, f, indent=2)
        
        logger.info(f"Saved quality report to {report_path}")