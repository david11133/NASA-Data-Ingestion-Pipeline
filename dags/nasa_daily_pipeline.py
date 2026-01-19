"""
NASA NEO Daily Data Pipeline DAG

This DAG runs daily at 6 AM to:
1. Check NASA API health
2. Extract NEO data for the last 7 days
3. Transform and validate the data
4. Load into SQLite database
5. Run quality checks
6. Generate execution report
7. Cleanup old files (weekly)

Schedule: Daily at 6:00 AM (Africa/Cairo timezone)
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
import yaml

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

# Import task functions
from .utils import (
    check_api_health,
    extract_neo_data,
    transform_neo_data,
    load_to_database,
    run_quality_checks,
    generate_pipeline_report,
    cleanup_old_files,
)

# Import notification functions
from utils.notifications import (
    task_failure_alert,
    task_retry_alert,
    dag_success_alert
)

# ============================================================================
# Load Configuration
# ============================================================================
def load_airflow_config():
    config_path = Path(__file__).parent.parent / 'config' / 'airflow_config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_airflow_config()
dag_config = config['daily_pipeline']
default_args = config['dag_defaults']

# ============================================================================
# Default Arguments
# ============================================================================
default_args.update({
    'owner': dag_config.get('owner', 'david'),
    'depends_on_past': False,
    'email': config['notifications']['email_list'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': default_args.get('retries', 3),
    'retry_delay': timedelta(minutes=default_args.get('retry_delay_minutes', 5)),
    'execution_timeout': timedelta(minutes=default_args.get('execution_timeout_minutes', 30)),
    'on_failure_callback': task_failure_alert,
    'on_retry_callback': task_retry_alert,
})

# ============================================================================
# DAG Definition
# ============================================================================
dag = DAG(
    dag_id=dag_config['dag_id'],
    description=dag_config['description'],
    default_args=default_args,
    schedule=dag_config['schedule'],  # '0 6 * * *' = 6 AM daily
    start_date=datetime.strptime(dag_config['start_date'], '%Y-%m-%d'),
    catchup=dag_config['catchup'],
    max_active_runs=dag_config['max_active_runs'],
    tags=dag_config['tags'],
    # DAG-level success callback
    on_success_callback=dag_success_alert,
)

# ============================================================================
# Task Definitions
# ============================================================================

with dag:
    # ────────────────────────────────────────────────────────────────────
    # START
    # ────────────────────────────────────────────────────────────────────
    start = EmptyOperator(
        task_id='start',
        doc="Pipeline start marker"
    )
    
    # ────────────────────────────────────────────────────────────────────
    # HEALTH CHECK (Sensor)
    # ────────────────────────────────────────────────────────────────────
    api_health_check = PythonSensor(
        task_id='check_api_health',
        python_callable=check_api_health,
        timeout=300,  # 5 minutes
        poke_interval=30,  # Check every 30 seconds
        mode='poke',  # 'poke' or 'reschedule'
        doc="""
        Checks if NASA API is healthy and accessible.
        Will retry every 30 seconds for up to 5 minutes.
        """,
    )
    
    # ────────────────────────────────────────────────────────────────────
    # EXTRACTION TASK GROUP
    # ────────────────────────────────────────────────────────────────────
    with TaskGroup('extraction', tooltip='Extract NEO data from NASA API') as extraction_group:
        
        extract_data = PythonOperator(
            task_id='extract_data',
            python_callable=extract_neo_data,
            execution_timeout=timedelta(
                minutes=dag_config['tasks']['extract_data']['timeout_minutes']
            ),
            retries=dag_config['tasks']['extract_data']['retries'],
            doc="""
            Extracts NEO data from NASA API for the last 7 days.
            Saves raw JSON to Bronze layer (data/raw/).
            Pushes data location to XCom for downstream tasks.
            """,
        )
    
    # ────────────────────────────────────────────────────────────────────
    # TRANSFORMATION TASK GROUP
    # ────────────────────────────────────────────────────────────────────
    with TaskGroup('transformation', tooltip='Transform and validate data') as transformation_group:
        
        transform_data = PythonOperator(
            task_id='transform_data',
            python_callable=transform_neo_data,
            execution_timeout=timedelta(
                minutes=dag_config['tasks']['transform_data']['timeout_minutes']
            ),
            retries=dag_config['tasks']['transform_data']['retries'],
            doc="""
            Transforms raw JSON data into structured format.
            Runs data quality validations.
            Saves to Silver layer (data/processed/).
            """,
        )
    
    # ────────────────────────────────────────────────────────────────────
    # LOADING TASK GROUP
    # ────────────────────────────────────────────────────────────────────
    with TaskGroup('loading', tooltip='Load data to database') as loading_group:
        
        load_data = PythonOperator(
            task_id='load_data',
            python_callable=load_to_database,
            execution_timeout=timedelta(
                minutes=dag_config['tasks']['load_data']['timeout_minutes']
            ),
            retries=dag_config['tasks']['load_data']['retries'],
            doc="""
            Loads transformed data into SQLite database.
            Handles incremental loading (skips already loaded dates).
            Updates existing records if needed.
            """,
        )
    
    # ────────────────────────────────────────────────────────────────────
    # QUALITY CHECK
    # ────────────────────────────────────────────────────────────────────
    quality_check = PythonOperator(
        task_id='quality_check',
        python_callable=run_quality_checks,
        execution_timeout=timedelta(
            minutes=dag_config['tasks']['quality_check']['timeout_minutes']
        ),
        retries=dag_config['tasks']['quality_check']['retries'],
        doc="""
        Runs quality checks on loaded data:
        - Minimum/maximum record counts
        - Quality pass rate threshold
        - Error detection
        
        Raises exception if thresholds not met.
        """,
    )
    
    # ────────────────────────────────────────────────────────────────────
    # REPORTING
    # ────────────────────────────────────────────────────────────────────
    generate_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_pipeline_report,
        doc="""
        Generates execution report summarizing:
        - Extraction stats
        - Transformation quality
        - Loading results
        
        Saves report to logs/reports/
        """,
    )
    
    # ────────────────────────────────────────────────────────────────────
    # CLEANUP (Runs weekly on Sundays)
    # ────────────────────────────────────────────────────────────────────
    cleanup = PythonOperator(
        task_id='cleanup_old_files',
        python_callable=cleanup_old_files,
        # Only run on Sundays
        trigger_rule='none_failed',  # Run even if upstream tasks are skipped
        doc="""
        Cleanup old files (30+ days):
        - Raw data files
        - Processed files
        - Old reports
        
        Runs weekly to prevent disk space issues.
        """,
    )
    
    # ────────────────────────────────────────────────────────────────────
    # END
    # ────────────────────────────────────────────────────────────────────
    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed',
        doc="Pipeline end marker"
    )

# ============================================================================
# Task Dependencies
# ============================================================================
"""
DAG Flow:
    start 
      → check_api_health 
      → extraction_group (extract_data)
      → transformation_group (transform_data) 
      → loading_group (load_data)
      → quality_check 
      → generate_report 
      → cleanup_old_files
      → end
"""

start >> api_health_check >> extraction_group >> transformation_group
transformation_group >> loading_group >> quality_check >> generate_report
generate_report >> cleanup >> end

# ============================================================================
# Documentation
# ============================================================================
dag.doc_md = """
# NASA NEO Daily Pipeline

## Overview
This pipeline extracts, transforms, and loads NASA Near-Earth Object (NEO) 
data on a daily schedule.

## Schedule
- **Frequency**: Daily
- **Time**: 6:00 AM Africa/Cairo timezone
- **Cron**: `0 6 * * *`

## Pipeline Stages

### 1. Health Check (Sensor)
- Checks NASA API availability
- Retries every 30 seconds for 5 minutes
- Blocks pipeline if API is down

### 2. Extraction (Bronze Layer)
- Fetches last 7 days of NEO data
- Saves raw JSON to `data/raw/YYYY-MM/`
- Handles API retries and rate limiting

### 3. Transformation (Silver Layer)
- Normalizes nested JSON structure
- Validates data quality
- Saves to `data/processed/`

### 4. Loading (Gold Layer)
- Loads into SQLite database
- Incremental loading (skip duplicates)
- Updates existing records

### 5. Quality Checks
- Validates record counts
- Checks quality pass rate (>95%)
- Fails pipeline if thresholds not met

### 6. Reporting
- Generates execution summary
- Saves to `logs/reports/`

### 7. Cleanup
- Removes files older than 30 days
- Prevents disk space issues

## Monitoring
- Email alerts on failure
- Airflow UI: http://localhost:8080
- Logs: `airflow/logs/`

## Manual Trigger
```bash
airflow dags trigger nasa_neo_daily_pipeline
```

## Backfill
```bash
airflow dags backfill nasa_neo_daily_pipeline \
    --start-date 2026-01-01 \
    --end-date 2026-01-10
```
"""
