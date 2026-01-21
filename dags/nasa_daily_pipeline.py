###############################################################################s
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
import json
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.exceptions import AirflowException

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extractors.neo_extractor import NEOExtractor
from transformers.neo_transformer import NEOTransformer
from transformers.data_quality import DataQualityChecker
from loaders.neo_loader import NEOLoader
from database.schema import initialize_database
###############################################################################

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

###############################################################################
# DAG Configuration 
###############################################################################
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

###############################################################################
# Helper Functions (Tasks)
###############################################################################

def check_api_availability(**context):
    """
    Check if NASA API is reachable before starting the pipeline.
    """
    import requests
    
    api_key = os.getenv('NASA_API_KEY')
    if not api_key:
        api_key = Variable.get('NASA_API_KEY', default_var=None)
    
    if not api_key:
        raise AirflowException("NASA_API_KEY not found in environment or Airflow Variables")
    
    try:
        url = "https://api.nasa.gov/neo/rest/v1/feed"
        params = {
            'api_key': api_key,
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            logging.info("✓ NASA API is available")
            return True
        else:
            logging.warning(f"NASA API returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"Failed to reach NASA API: {str(e)}")
        return False


def initialize_database_task(**context):
    """
    Initialize database schema if not exists.
    """
    logging.info("Initializing database schema...")
    initialize_database(force=False)
    logging.info("✓ Database schema ready")


def extract_neo_data(**context):
    """
    Extract NEO data from NASA API for the last 7 days.
    Pushes the extracted data to XCom for next tasks.
    """
    logging.info("Starting NEO data extraction...")

    api_key = os.getenv('NASA_API_KEY')
    if not api_key:
        api_key = Variable.get('NASA_API_KEY')

    extractor = NEOExtractor(
        api_key=api_key,
        base_url="https://api.nasa.gov/neo/rest/v1",
        output_path="data/raw",
        timeout=30,
        max_retries=3,
        retry_delay=2
    )

    data = extractor.extract_last_n_days(7)
    
    logging.info(f"✓ Extracted {data['element_count']} NEO objects")
    
    # Push data to XCom (Airflow's way of passing data between tasks)
    # We will save the file path instead of the entire data (more efficient)
    raw_file_path = context['task_instance'].xcom_push(
        key='neo_data_count',
        value=data['element_count']
    )
    
    # Store metadata for the report
    context['task_instance'].xcom_push(
        key='extraction_date',
        value=datetime.now().isoformat()
    )
    
    return data


def save_raw_data(**context):
    """
    Save raw data to Bronze layer (organized by date).
    """
    logging.info("Saving raw data to Bronze layer...")
    
    # Pull data from previous task
    ti = context['task_instance']
    data = ti.xcom_pull(task_ids='extract_neo_data')
    
    if not data:
        raise AirflowException("No data received from extraction task")
    
    # Organize by date
    dates = sorted(data['near_earth_objects'].keys())
    start_date = dates[0]
    
    date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    year_month = date_obj.strftime('%Y-%m')
    
    raw_dir = Path('data/raw') / year_month
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = raw_dir / f"{start_date}.json"
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logging.info(f"✓ Raw data saved to {file_path}")
    
    # Push file path to XCom for next tasks
    ti.xcom_push(key='raw_file_path', value=str(file_path))
    
    return str(file_path)


def transform_and_validate(**context):
    """
    Transform raw data to Silver layer and run quality checks.
    """
    logging.info("Starting data transformation and validation...")

    ti = context['task_instance']
    data = ti.xcom_pull(task_ids='extract_neo_data')
    
    if not data:
        raise AirflowException("No data received from extraction task")
    
    # Initialize quality checker and transformer
    quality_checker = DataQualityChecker()
    transformer = NEOTransformer(quality_checker=quality_checker)

    transformed_data = transformer.transform(data)
    
    logging.info(f"✓ Transformed {len(transformed_data['asteroids'])} asteroids")
    logging.info(f"✓ Transformed {len(transformed_data['estimated_diameters'])} diameter records")
    logging.info(f"✓ Transformed {len(transformed_data['close_approaches'])} close approach records")
    
    # Get quality summary
    quality_summary = quality_checker.get_summary()
    logging.info(f"✓ Quality Check Pass Rate: {quality_summary['pass_rate']:.1f}%")
    
    # Save transformed data
    transformer.save_transformed_data(
        transformed_data,
        output_dir="data/processed"
    )
    
    # Push quality metrics to XCom for reporting
    ti.xcom_push(key='quality_summary', value=quality_summary)
    ti.xcom_push(key='transformed_count', value=len(transformed_data['asteroids']))
    
    # Fail the task if quality is too low
    if quality_summary['pass_rate'] < 95.0:
        raise AirflowException(
            f"Quality check failed! Pass rate: {quality_summary['pass_rate']:.1f}% (minimum: 95%)"
        )
    
    return transformed_data


def load_to_database(**context):
    """
    Load transformed data into SQLite database.
    """
    logging.info("Loading data into database...")
    
    # Pull data from previous tasks
    ti = context['task_instance']
    data = ti.xcom_pull(task_ids='extract_neo_data')
    raw_file_path = ti.xcom_pull(task_ids='save_raw_data')
    
    if not data:
        raise AirflowException("No data to load")
    
    # Initialize loader
    loader = NEOLoader()
    
    # Load data
    stats = loader.load_from_json_data(
        data,
        source_file=raw_file_path,
        skip_if_loaded=True
    )
    
    logging.info("✓ Load completed:")
    logging.info(f"  • Asteroids inserted: {stats['asteroids_inserted']}")
    logging.info(f"  • Asteroids updated: {stats['asteroids_updated']}")
    logging.info(f"  • Close approaches: {stats['close_approaches_inserted']}")
    logging.info(f"  • Diameters inserted: {stats['diameters_inserted']}")
    
    # Push stats to XCom for reporting
    ti.xcom_push(key='load_stats', value=stats)
    
    if stats['errors']:
        logging.warning(f"⚠ Errors encountered: {len(stats['errors'])}")
        # Don't fail the task, but log errors
        for error in stats['errors'][:5]:
            logging.error(f"  - {error}")
    
    return stats


def generate_daily_report(**context):
    """
    Generate a summary report of the daily pipeline run.
    """
    logging.info("Generating daily report...")
    
    ti = context['task_instance']
    
    # Pull all metrics from XCom
    neo_count = ti.xcom_pull(task_ids='extract_neo_data', key='neo_data_count')
    extraction_date = ti.xcom_pull(task_ids='extract_neo_data', key='extraction_date')
    quality_summary = ti.xcom_pull(task_ids='transform_and_validate', key='quality_summary')
    load_stats = ti.xcom_pull(task_ids='load_to_database', key='load_stats')
    
    # Create report
    report = {
        'pipeline_run_date': datetime.now().isoformat(),
        'execution_date': context['execution_date'].isoformat(),
        'dag_run_id': context['run_id'],
        'metrics': {
            'neos_extracted': neo_count,
            'neos_transformed': ti.xcom_pull(task_ids='transform_and_validate', key='transformed_count'),
            'asteroids_inserted': load_stats.get('asteroids_inserted', 0) if load_stats else 0,
            'asteroids_updated': load_stats.get('asteroids_updated', 0) if load_stats else 0,
            'quality_pass_rate': quality_summary.get('pass_rate', 0) if quality_summary else 0,
        },
        'status': 'SUCCESS'
    }
    
    # Save report
    report_dir = Path('data/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logging.info(f"✓ Daily report saved to {report_file}")
    logging.info("=" * 70)
    logging.info("PIPELINE SUMMARY")
    logging.info("=" * 70)
    logging.info(f"✓ Extracted: {report['metrics']['neos_extracted']} NEO objects")
    logging.info(f"✓ Transformed: {report['metrics']['neos_transformed']} records")
    logging.info(f"✓ Quality: {report['metrics']['quality_pass_rate']:.1f}% passed")
    logging.info(f"✓ Loaded: {report['metrics']['asteroids_inserted']} new, {report['metrics']['asteroids_updated']} updated")
    logging.info("=" * 70)
    
    return report


###############################################################################
# DAG Definition
###############################################################################

# Create the DAG
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

###############################################################################
# Task Definitions
###############################################################################

# Task 1: Check API Availability
api_sensor = PythonSensor(
    task_id='check_api_availability',
    python_callable=check_api_availability,
    poke_interval=60, 
    timeout=600,  
    mode='poke', 
    dag=dag,
)

# Task 2: Initialize Database
init_db = PythonOperator(
    task_id='initialize_database',
    python_callable=initialize_database_task,
    dag=dag,
)

# Task 3: Extract NEO Data
extract = PythonOperator(
    task_id='extract_neo_data',
    python_callable=extract_neo_data,
    dag=dag,
)

# Task 4: Save Raw Data (Bronze Layer)
save_raw = PythonOperator(
    task_id='save_raw_data',
    python_callable=save_raw_data,
    dag=dag,
)

# Task 5: Transform and Validate (Silver Layer)
transform = PythonOperator(
    task_id='transform_and_validate',
    python_callable=transform_and_validate,
    dag=dag,
)

# Task 6: Load to Database
load_db = PythonOperator(
    task_id='load_to_database',
    python_callable=load_to_database,
    dag=dag,
)

# Task 7: Generate Daily Report
report = PythonOperator(
    task_id='generate_daily_report',
    python_callable=generate_daily_report,
    dag=dag,
)

###############################################################################
# Task Dependencies (Pipeline Flow)
###############################################################################

# The workflow:
# Check API → Init DB → Extract → Save Raw → Transform → Load → Report
#                                     ↓
#                                 (parallel)

api_sensor >> init_db >> extract >> save_raw >> transform >> load_db >> report