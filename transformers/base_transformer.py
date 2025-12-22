"""
Base transformer class for data transformations
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class BaseTransformer(ABC):
    """
    Base class for all data transformers.
    Provides common functionality for data transformation operations.
    """
    
    def __init__(self):
        """Initialize the base transformer"""
        self.transformation_stats = {
            'records_processed': 0,
            'records_transformed': 0,
            'records_failed': 0,
            'errors': []
        }
    
    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw data to structured format.
        Must be implemented by child classes.
        
        Args:
            raw_data: Raw data dictionary
            
        Returns:
            Transformed data dictionary
        """
        pass
    
    def _safe_get(self, data: Dict, *keys, default=None) -> Any:
        """
        Safely navigate nested dictionary structure.
        
        Args:
            data: Dictionary to navigate
            *keys: Sequence of keys to follow
            default: Default value if key not found
            
        Returns:
            Value at nested key or default
            
        Example:
            _safe_get(data, 'estimated_diameter', 'kilometers', 'min', default=0)
        """
        try:
            result = data
            for key in keys:
                result = result[key]
            return result if result is not None else default
        except (KeyError, TypeError, IndexError):
            return default
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value or default
        """
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to float, using default {default}")
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """
        Safely convert value to integer.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Integer value or default
        """
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to int, using default {default}")
            return default
    
    def _safe_bool(self, value: Any, default: bool = False) -> bool:
        """
        Safely convert value to boolean.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Boolean value or default
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    def _parse_date(self, date_str: str, format: str = "%Y-%m-%d") -> Optional[str]:
        """
        Parse and validate date string.
        
        Args:
            date_str: Date string to parse
            format: Expected date format
            
        Returns:
            Validated date string or None
        """
        try:
            datetime.strptime(date_str, format)
            return date_str
        except (ValueError, TypeError):
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    def _convert_km_to_au(self, km: float) -> float:
        """
        Convert kilometers to astronomical units.
        
        Args:
            km: Distance in kilometers
            
        Returns:
            Distance in AU
        """
        AU_IN_KM = 149597870.7  # 1 AU in kilometers
        return km / AU_IN_KM
    
    def _convert_km_to_miles(self, km: float) -> float:
        """
        Convert kilometers to miles.
        
        Args:
            km: Distance in kilometers
            
        Returns:
            Distance in miles
        """
        return km * 0.621371
    
    def log_stats(self):
        """Log transformation statistics"""
        logger.info(f"Transformation Statistics:")
        logger.info(f"  Records Processed: {self.transformation_stats['records_processed']}")
        logger.info(f"  Records Transformed: {self.transformation_stats['records_transformed']}")
        logger.info(f"  Records Failed: {self.transformation_stats['records_failed']}")
        if self.transformation_stats['errors']:
            logger.warning(f"  Errors: {len(self.transformation_stats['errors'])}")
    
    def reset_stats(self):
        """Reset transformation statistics"""
        self.transformation_stats = {
            'records_processed': 0,
            'records_transformed': 0,
            'records_failed': 0,
            'errors': []
        }