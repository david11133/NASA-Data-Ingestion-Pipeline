This is a summary of everything I add to the code, so it's always up to date.

NASA DATA INGESTION PIPELINE is a personal project I'm building to learn data engineering by practice.

I am going through it step by step starting from foundation & data ingestion to the data quality and testing.

Let me clue you in.

Phase 1: Foundation & Data Ingestion (Weeks 1-2)
Simple API ingestion
1. Built my first Extractor
Project Structure:
```
nasa-de-project/
├── config/
│ └── config.yaml
├── extractors/
│ ├── __init__.py
│ ├── base_extractor.py
│ └── neo_extractor.py
├── .env
└── main.py
```

Let me give you some snipsets from each code

config.yaml:
```
api:
  base_url: "https://api.nasa.gov/neo/rest/v1"
  timeout: 30
  max_retries: 3
  retry_delay: 2
storage:
  raw_data_path: "data/raw"
logging:
  level: "INFO"
  log_file: "logs/nasa.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

base_extractor.py:
```
class BaseExtractor:
    """
    Handles common functionality like HTTP requests, retries, and error handling.
    """
    def __init__(self, api_key: str, base_url: str, timeout: int = 30, 
                 max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the base extractor.
        
        Args:
            api_key: For authentication
            base_url: API URL
            timeout: Request timeout
            max_retries: Maximum no. of retry attempts
            retry_delay: Delay between retries
        """
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP GET request with retry logic.
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters as dictionary
            
        Returns:
            JSON response
            
        Raises:
            Exception: If all retries fail
        """
    def extract(self) -> Dict[str, Any]:
        """
        Extract data from the API.
        This method should be overridden by child classes.
        """
        raise NotImplementedError("Subclasses must implement extract() method")
```

neo_extractor.py:
```
class NEOExtractor(BaseExtractor):
    """
    Extractor for NASA Near Earth Objects (NEOs) data.
    """
    def __init__(self, api_key: str, base_url: str, output_path: str, **kwargs):
        """
        Initialize NEO extractor.
        
        Args:
            api_key: NASA API key
            base_url: Base URL for NEOs API
            output_path: Path to save JSON files
            **kwargs: Additional arguments for BaseExtractor
        """
    def extract_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Extract NEO data for a specific date range (eg, 7 days ago).
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing NEO data
        """
    def extract_today(self) -> Dict[str, Any]:
        """
        Extract NEO data for today.
        
        Returns:
            Dictionary containing today's NEO data
        """
    def extract_last_n_days(self, n_days: int = 7) -> Dict[str, Any]:
        """
        Extract NEO data for the last N days.
        
        Args:
            n_days: Number of days to fetch (NASA API has limit of 7 days)
            
        Returns:
            Dictionary containing NEO data
        """
    def _save_raw_data(self, data: Dict[str, Any], start_date: str, end_date: str):
        """
        Save to JSON file
        
        Args:
            data: Data to save
            start_date: Start date for filename
            end_date: End date for filename
        """
    def _sanitize_api_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove API keys from URLs in the data structure.
        
        Args:
            data: Dictionary containing NEO data
            
        Returns:
            Sanitized data dictionary
        """
    def extract(self) -> Dict[str, Any]:
        """
        Default extract method - extracts last 7 days of data.
        
        Returns:
            Dictionary containing NEO data
        """
        return self.extract_last_n_days(7)
```

Phase 2: Data Storage & Organization (Weeks 3-4)

What I Built?
1. Organize Raw Data
```
data/
├── raw/
│ ├── neos/
│ │ ├── 2024-01/
│ │ │ ├── 2024-01-01.json
│ │ │ └── 2024-01-02.json
│ ├── apod/
│ └── mars_rover/
```

Wrote SQL DDL scripts for table creation
Created a database connection manager
Inserted data from JSON into SQLite
Wrote queries to analyze the data
Implemented incremental loading (don't reload same dates)

The data in json file is like this:

```
{
  "links": {
    "next": "http://api.nasa.gov/neo/rest/v1/feed?start_date=2026-01-03&end_date=2026-01-09&detailed=false&api_key=9VSPRf91gXNMIqnQ6Qyfd367bsbccVKp4w617pv2",
    "previous": "http://api.nasa.gov/neo/rest/v1/feed?start_date=2025-12-22&end_date=2025-12-28&detailed=false&api_key=9VSPRf91gXNMIqnQ6Qyfd367bsbccVKp4w617pv2",
    "self": "http://api.nasa.gov/neo/rest/v1/feed?start_date=2025-12-28&end_date=2026-01-03&detailed=false&api_key=9VSPRf91gXNMIqnQ6Qyfd367bsbccVKp4w617pv2"
  },
  "element_count": 103,
  "near_earth_objects": {
    "2025-12-29": [
      {
        "links": {
          "self": "http://api.nasa.gov/neo/rest/v1/neo/3313739?api_key=9VSPRf91gXNMIqnQ6Qyfd367bsbccVKp4w617pv2"
        },
        "id": "3313739",
        "neo_reference_id": "3313739",
        "name": "(2006 BA9)",
        "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=3313739",
        "absolute_magnitude_h": 22.7,
        "estimated_diameter": {
          "kilometers": {
            "estimated_diameter_min": 0.0766575574,
            "estimated_diameter_max": 0.1714115092
          },
          "meters": {
            "estimated_diameter_min": 76.6575573531,
            "estimated_diameter_max": 171.4115092306
          },
          "miles": {
            "estimated_diameter_min": 0.0476327831,
            "estimated_diameter_max": 0.1065101409
          },
          "feet": {
            "estimated_diameter_min": 251.5011804664,
            "estimated_diameter_max": 562.3737359442
          }
        },
        "is_potentially_hazardous_asteroid": false,
        "close_approach_data": [
          {
            "close_approach_date": "2025-12-29",
            "close_approach_date_full": "2025-Dec-29 08:28",
            "epoch_date_close_approach": 1766996880000,
            "relative_velocity": {
              "kilometers_per_second": "12.9830978037",
              "kilometers_per_hour": "46739.152093172",
              "miles_per_hour": "29041.8914770046"
            },
            "miss_distance": {
              "astronomical": "0.0914542175",
              "lunar": "35.5756906075",
              "kilometers": "13681356.140516725",
              "miles": "8501200.499811805"
            },
            "orbiting_body": "Earth"
          }
        ],
        "is_sentry_object": false
      },
```
(This is just a small sample of it - first item only)


Phase 3: Data Transformation & Quality (Weeks 5-6)

What I Built?
1. Created Transformation Script
```
transformers/
├── __init__.py
├── base_transformer.py
├── neo_transformer.py
└── data_quality.py
```

base_transformer.py
```
"""
Base transformer class for data transformations
"""

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
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value or default
        """
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """
        Safely convert value to integer.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Integer value or default
        """
    def _safe_bool(self, value: Any, default: bool = False) -> bool:
        """
        Safely convert value to boolean.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Boolean value or default
        """
    def _parse_date(self, date_str: str, format: str = "%Y-%m-%d") -> Optional[str]:
        """
        Parse and validate date string.
        
        Args:
            date_str: Date string to parse
            format: Expected date format
            
        Returns:
            Validated date string or None
        """
    def _convert_km_to_au(self, km: float) -> float:
        """
        Convert kilometers to astronomical units.
        
        Args:
            km: Distance in kilometers
            
        Returns:
            Distance in AU
        """
    def _convert_km_to_miles(self, km: float) -> float:
        """
        Convert kilometers to miles.
        
        Args:
            km: Distance in kilometers
            
        Returns:
            Distance in miles
        """
    def log_stats(self):
        """Log transformation statistics"""
    def reset_stats(self):
        """Reset transformation statistics"""
```

neo_transformer.py
```
"""
NEO-specific data transformer
"""
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
    def transform_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transform data from a JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Transformed data dictionary
        """
    def _transform_asteroid(self, neo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform asteroid basic information.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            Transformed asteroid dictionary
        """
    def _transform_diameters(self, neo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform estimated diameter data for all units.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            List of diameter records (one per unit)
        """
    def _transform_close_approaches(self, neo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform close approach data.
        
        Args:
            neo: Raw NEO object
            
        Returns:
            List of close approach records
        """
    def _extract_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract API metadata from raw response.
        
        Args:
            raw_data: Raw API response
            
        Returns:
            Metadata dictionary
        """
    def _run_quality_checks(self, transformed_data: Dict[str, Any]):
        """
        Run quality checks on transformed data.
        
        Args:
            transformed_data: Transformed data dictionary
        """
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
```

data_quality.py
```
"""
Data quality validation and checks
"""
@dataclass
class ValidationResult:
    """Result of a validation check"""
class DataQualityChecker:
    """
    Performs data quality checks on transformed data.
    """
    def __init__(self):
        """Initialize data quality checker"""
    def validate_asteroid_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate asteroid record against quality rules.
        
        Args:
            record: Asteroid record dictionary
            
        Returns:
            List of validation results
        """
    def validate_diameter_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate estimated diameter record.
        
        Args:
            record: Diameter record dictionary
            
        Returns:
            List of validation results
        """
    def validate_close_approach_record(self, record: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate close approach record.
        
        Args:
            record: Close approach record dictionary
            
        Returns:
            List of validation results
        """
    def check_duplicates(self, records: List[Dict[str, Any]], key_fields: List[str]) -> Dict[str, Any]:
        """
        Check for duplicate records based on key fields.
        
        Args:
            records: List of records to check
            key_fields: Fields that constitute uniqueness
            
        Returns:
            Dictionary with duplicate information
        """
    def get_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dictionary with validation statistics
        """
    def print_summary(self):
        """Print validation summary to console"""
    def reset(self):
        """Reset validation results and stats"""
    # Helper methods
    def _check_not_null(self, record: Dict[str, Any], field: str) -> ValidationResult:
        """Check if field is not null"""
    def _check_type(self, record: Dict[str, Any], field: str, expected_type) -> ValidationResult:
        """Check if field has expected type"""
    def _check_range(self, record: Dict[str, Any], field: str, 
                     min_val: float, max_val: float, message: str = None) -> ValidationResult:
        """Check if numeric field is within range"""
    def _check_positive(self, record: Dict[str, Any], field: str) -> ValidationResult:
        """Check if numeric field is positive"""
    def _validate_date_format(self, date_str: str, field: str, 
                             format: str = "%Y-%m-%d") -> ValidationResult:
        """Validate date string format"""
    def _update_stats(self, results: List[ValidationResult]):
        """Update validation statistics"""
```

Phase 4: Workflow Orchestration (Weeks 7-8)
What I built:
1. Setup Apache Airflow
- Installed Airflow locally
- Initialized database: airflow db init
- Created admin user
- Started web server and scheduler
2. Created Your First DAG
```
dags/
├── nasa_daily_pipeline.py
└── nasa_backfill_pipeline.py
```
3. DAG StructureExtract 
NEO → Store Raw → Transform → Load to DB → Quality Check → Generate Report
4. Tasks to Complete
- Created daily scheduled DAG (runs every day at 6 AM)
- Implemented task dependencies
- Added retry logic and alerts
- Created a backfill DAG for historical data
- Set up email notifications on failure
- Added sensor for API availability

nasa_daily_pipeline.py:
```
"""
NASA NEO Daily Data Pipeline DAG

This DAG runs daily to:
1. Check if NASA API is available
2. Extract NEO data from NASA API
3. Save raw data (Bronze layer)
4. Transform and validate data (Silver layer)
5. Load data into SQLite database
6. Run quality checks
7. Generate daily report

Schedule: Daily at 6:00 AM UTC
"""
default_args = {
    'owner': 'david',
    'depends_on_past': False, 
    'email': ['davidnady4yad@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}
def check_api_availability(**context):
    """
    Check if NASA API is reachable before starting the pipeline.
    """
def initialize_database_task(**context):
    """
    Initialize database schema if not exists.
    """
def extract_neo_data(**context):
    """
    Extract NEO data from NASA API for the last 7 days.
    Pushes the extracted data to XCom for next tasks.
    """
def save_raw_data(**context):
    """
    Save raw data to Bronze layer (organized by date).
    """
def transform_and_validate(**context):
    """
    Transform raw data to Silver layer and run quality checks.
    """
def load_to_database(**context):
    """
    Load transformed data into SQLite database.
    """
def generate_daily_report(**context):
    """
    Generate a summary report of the daily pipeline run.
    """
dag = DAG(
    dag_id='nasa_neo_daily_pipeline',
    default_args=default_args,
    description='Daily NASA NEO data ingestion pipeline',
    schedule_interval='0 6 * * *', 
    start_date=datetime(2026, 1, 1), 
    catchup=False,
    max_active_runs=1,
    tags=['nasa', 'neo', 'daily', 'production'],
)
api_sensor = PythonSensor(
    task_id='check_api_availability',
    python_callable=check_api_availability,
    poke_interval=60, 
    timeout=600,  
    mode='poke', 
    dag=dag,
)
init_db = PythonOperator(
    task_id='initialize_database',
    python_callable=initialize_database_task,
    dag=dag,
)
extract = PythonOperator(
    task_id='extract_neo_data',
    python_callable=extract_neo_data,
    dag=dag,
)
save_raw = PythonOperator(
    task_id='save_raw_data',
    python_callable=save_raw_data,
    dag=dag,
)
transform = PythonOperator(
    task_id='transform_and_validate',
    python_callable=transform_and_validate,
    dag=dag,
)
load_db = PythonOperator(
    task_id='load_to_database',
    python_callable=load_to_database,
    dag=dag,
)
report = PythonOperator(
    task_id='generate_daily_report',
    python_callable=generate_daily_report,
    dag=dag,
)
# The workflow:
# Check API → Init DB → Extract → Save Raw → Transform → Load → Report
#                                     ↓
#                                 (parallel)

api_sensor >> init_db >> extract >> save_raw >> transform >> load_db >> report
```

nasa_backfill_pipeline.py:
```
"""
NASA NEO Backfill Pipeline DAG

This DAG is used to backfill historical NEO data.
It's designed to run manually (not on a schedule) for specific date ranges.

Usage:
1. Trigger this DAG manually from Airflow UI
2. Pass configuration: e.g., {"start_date": "2025-01-01", "end_date": "2025-12-31"}

Features:
- Processes data in weekly chunks (NASA API limit is 7 days)
- Handles rate limiting
- Skips already loaded data
- Generates backfill summary report
"""
default_args = {
    'owner': 'david',
    'depends_on_past': False,
    'email': ['davidnady4yad@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'execution_timeout': timedelta(hours=2),
}
def generate_date_chunks(start_date: str, end_date: str, chunk_size: int = 7) -> List[Tuple[str, str]]:
    """
    Split date range into chunks (NASA API allows max 7 days per request).
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        chunk_size: Days per chunk (default 7)
    
    Returns:
        List of (start, end) date tuples
    """
def initialize_backfill(**context):
    """
    Initialize backfill process and validate parameters.
    """
def process_date_chunk(**context):
    """
    Process a single date chunk (extract, transform, load).
    This function will be called multiple times for each chunk.
    """
def generate_backfill_report(**context):
    """
    Generate comprehensive backfill report.
    """
dag = DAG(
    dag_id='nasa_neo_backfill_pipeline',
    default_args=default_args,
    description='Backfill historical NASA NEO data',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['nasa', 'neo', 'backfill', 'manual'],
)
init_task = PythonOperator(
    task_id='initialize_backfill',
    python_callable=initialize_backfill,
    dag=dag,
)
process_task = PythonOperator(
    task_id='process_chunks',
    python_callable=process_date_chunk,
    dag=dag,
)
report_task = PythonOperator(
    task_id='generate_backfill_report',
    python_callable=generate_backfill_report,
    dag=dag,
)
init_task >> process_task >> report_task
```