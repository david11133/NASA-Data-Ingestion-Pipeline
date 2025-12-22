"""
Data quality validation and checks
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    field_name: str
    error_message: Optional[str] = None
    value: Any = None


class DataQualityChecker:
    """
    Performs data quality checks on transformed data.
    """
    
    def __init__(self):
        """Initialize data quality checker"""
        self.validation_results = []
        self.stats = {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0
        }
    
    def validate_asteroid_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate asteroid record against quality rules.
        
        Args:
            record: Asteroid record dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        # Required field checks
        results.append(self._check_not_null(record, 'neo_id'))
        results.append(self._check_not_null(record, 'name'))
        results.append(self._check_not_null(record, 'neo_reference_id'))
        
        # Type checks
        results.append(self._check_type(record, 'neo_id', str))
        results.append(self._check_type(record, 'absolute_magnitude_h', (int, float)))
        results.append(self._check_type(record, 'is_potentially_hazardous', bool))
        
        # Range checks
        if record.get('absolute_magnitude_h') is not None:
            results.append(self._check_range(
                record, 'absolute_magnitude_h', 0, 35, 
                "Absolute magnitude typically between 0-35"
            ))
        
        # Update stats
        self._update_stats(results)
        self.validation_results.extend(results)
        
        return results
    
    def validate_diameter_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate estimated diameter record.
        
        Args:
            record: Diameter record dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        # Required fields
        results.append(self._check_not_null(record, 'neo_id'))
        results.append(self._check_not_null(record, 'unit'))
        results.append(self._check_not_null(record, 'estimated_diameter_min'))
        results.append(self._check_not_null(record, 'estimated_diameter_max'))
        
        # Logical checks
        min_val = record.get('estimated_diameter_min', 0)
        max_val = record.get('estimated_diameter_max', 0)
        
        if min_val and max_val:
            is_valid = min_val <= max_val
            results.append(ValidationResult(
                is_valid=is_valid,
                field_name='diameter_range',
                error_message=None if is_valid else "Min diameter should be <= max diameter",
                value=f"min:{min_val}, max:{max_val}"
            ))
        
        # Unit validation
        valid_units = ['kilometers', 'meters', 'miles', 'feet']
        unit = record.get('unit')
        is_valid = unit in valid_units
        results.append(ValidationResult(
            is_valid=is_valid,
            field_name='unit',
            error_message=None if is_valid else f"Invalid unit: {unit}",
            value=unit
        ))
        
        self._update_stats(results)
        self.validation_results.extend(results)
        
        return results
    
    def validate_close_approach_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate close approach record.
        
        Args:
            record: Close approach record dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        # Required fields
        results.append(self._check_not_null(record, 'neo_id'))
        results.append(self._check_not_null(record, 'close_approach_date'))
        results.append(self._check_not_null(record, 'orbiting_body'))
        
        # Date format validation
        date_val = record.get('close_approach_date')
        if date_val:
            results.append(self._validate_date_format(date_val, 'close_approach_date'))
        
        # Velocity checks (should be positive)
        velocity_fields = [
            'velocity_km_per_sec',
            'velocity_km_per_hour',
            'velocity_miles_per_hour'
        ]
        for field in velocity_fields:
            if record.get(field) is not None:
                results.append(self._check_positive(record, field))
        
        # Distance checks (should be positive)
        distance_fields = [
            'miss_distance_astronomical',
            'miss_distance_lunar',
            'miss_distance_km',
            'miss_distance_miles'
        ]
        for field in distance_fields:
            if record.get(field) is not None:
                results.append(self._check_positive(record, field))
        
        # Orbiting body validation
        valid_bodies = ['Earth', 'Moon', 'Mars', 'Venus', 'Mercury']
        body = record.get('orbiting_body')
        is_valid = body in valid_bodies
        results.append(ValidationResult(
            is_valid=is_valid,
            field_name='orbiting_body',
            error_message=None if is_valid else f"Unexpected orbiting body: {body}",
            value=body
        ))
        
        self._update_stats(results)
        self.validation_results.extend(results)
        
        return results
    
    def check_duplicates(self, records: List[Dict[str, Any]], key_fields: List[str]) -> Dict[str, Any]:
        """
        Check for duplicate records based on key fields.
        
        Args:
            records: List of records to check
            key_fields: Fields that constitute uniqueness
            
        Returns:
            Dictionary with duplicate information
        """
        seen = set()
        duplicates = []
        
        for record in records:
            key = tuple(record.get(field) for field in key_fields)
            if key in seen:
                duplicates.append(record)
            else:
                seen.add(key)
        
        result = {
            'total_records': len(records),
            'unique_records': len(seen),
            'duplicate_count': len(duplicates),
            'duplicates': duplicates
        }
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate records")
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dictionary with validation statistics
        """
        failed_validations = [v for v in self.validation_results if not v.is_valid]
        
        summary = {
            'total_checks': self.stats['total_checks'],
            'passed': self.stats['passed_checks'],
            'failed': self.stats['failed_checks'],
            'pass_rate': (self.stats['passed_checks'] / self.stats['total_checks'] * 100) 
                        if self.stats['total_checks'] > 0 else 0,
            'failed_validations': [
                {
                    'field': v.field_name,
                    'error': v.error_message,
                    'value': v.value
                }
                for v in failed_validations
            ]
        }
        
        return summary
    
    def print_summary(self):
        """Print validation summary to console"""
        summary = self.get_summary()
        
        logger.info("=" * 60)
        logger.info("DATA QUALITY VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Checks: {summary['total_checks']}")
        logger.info(f"Passed: {summary['passed']} ({summary['pass_rate']:.2f}%)")
        logger.info(f"Failed: {summary['failed']}")
        
        if summary['failed_validations']:
            logger.warning("\nFailed Validations:")
            for fail in summary['failed_validations'][:10]:  # Show first 10
                logger.warning(f"  - {fail['field']}: {fail['error']} (value: {fail['value']})")
            
            if len(summary['failed_validations']) > 10:
                logger.warning(f"  ... and {len(summary['failed_validations']) - 10} more")
        
        logger.info("=" * 60)
    
    def reset(self):
        """Reset validation results and stats"""
        self.validation_results = []
        self.stats = {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0
        }
    
    # Helper methods
    def _check_not_null(self, record: Dict[str, Any], field: str) -> ValidationResult:
        """Check if field is not null"""
        value = record.get(field)
        is_valid = value is not None and value != ''
        return ValidationResult(
            is_valid=is_valid,
            field_name=field,
            error_message=None if is_valid else f"{field} is null or empty",
            value=value
        )
    
    def _check_type(self, record: Dict[str, Any], field: str, expected_type) -> ValidationResult:
        """Check if field has expected type"""
        value = record.get(field)
        if value is None:
            return ValidationResult(is_valid=True, field_name=field)
        
        is_valid = isinstance(value, expected_type)
        return ValidationResult(
            is_valid=is_valid,
            field_name=field,
            error_message=None if is_valid else f"{field} has wrong type: {type(value).__name__}",
            value=value
        )
    
    def _check_range(self, record: Dict[str, Any], field: str, 
                     min_val: float, max_val: float, message: str = None) -> ValidationResult:
        """Check if numeric field is within range"""
        value = record.get(field)
        if value is None:
            return ValidationResult(is_valid=True, field_name=field)
        
        is_valid = min_val <= value <= max_val
        error_msg = message or f"{field} out of range [{min_val}, {max_val}]"
        return ValidationResult(
            is_valid=is_valid,
            field_name=field,
            error_message=None if is_valid else error_msg,
            value=value
        )
    
    def _check_positive(self, record: Dict[str, Any], field: str) -> ValidationResult:
        """Check if numeric field is positive"""
        value = record.get(field)
        if value is None:
            return ValidationResult(is_valid=True, field_name=field)
        
        is_valid = value > 0
        return ValidationResult(
            is_valid=is_valid,
            field_name=field,
            error_message=None if is_valid else f"{field} should be positive",
            value=value
        )
    
    def _validate_date_format(self, date_str: str, field: str, 
                             format: str = "%Y-%m-%d") -> ValidationResult:
        """Validate date string format"""
        try:
            datetime.strptime(date_str, format)
            return ValidationResult(is_valid=True, field_name=field, value=date_str)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name=field,
                error_message=f"Invalid date format: expected {format}",
                value=date_str
            )
    
    def _update_stats(self, results: List[ValidationResult]):
        """Update validation statistics"""
        self.stats['total_checks'] += len(results)
        self.stats['passed_checks'] += sum(1 for r in results if r.is_valid)
        self.stats['failed_checks'] += sum(1 for r in results if not r.is_valid)