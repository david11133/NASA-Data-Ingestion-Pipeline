"""
NASA NEO Backfill Pipeline DAG

This DAG is used for historical data backfilling.
It processes data in 7-day chunks (NASA API limit).

Schedule: Manual trigger only (no schedule)
Catchup: True (to process historical dates)

Usage:
    airflow dags backfill nasa_neo_backfill_pipeline \
        --start-date 2025-01-01 \
        --end-date 2025-12-31
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
import yaml

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

# Import task functions
from utils.task_functions import (
    extract_neo_data,
    transform_neo_data,
    load_to_database,
    run_quality_checks,
    generate_pipeline_report
)

# Import notification functions
from utils.notifications import (
    task_failure_alert,
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
dag_config = config['backfill_pipeline']
default_args = config['dag_defaults']

# ============================================================================
# Default Arguments (Modified for Backfill)
# ============================================================================
default_args.update({
    'owner': dag_config.get('owner', 'david'),
    'depends_on_past': True,  # Important for backfilling
    'email': config['notifications']['email_list'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,  # Fewer retries for backfill
    'retry_delay': timedelta(minutes=10),  # Longer delay between retries
    'execution_timeout': timedelta(minutes=45),  # Longer timeout
    'on_failure_callback': task_failure_alert,
})

# ============================================================================
# DAG Definition
# ============================================================================
dag = DAG(
    dag_id=dag_config['dag_id'],
    description=dag_config['description'],
    default_args=default_args,
    schedule=dag_config['schedule'],  # None = manual only
    start_date=datetime.strptime(dag_config['start_date'], '%Y-%m-%d'),
    end_date=None,  # No end date for backfill
    catchup=dag_config['catchup'],  # True = process historical dates
    max_active_runs=dag_config['max_active_runs'],  # Can run 3 in parallel
    tags=dag_config['tags'],
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
        doc="Backfill pipeline start marker"
    )
    
    # ────────────────────────────────────────────────────────────────────
    # EXTRACTION
    # ────────────────────────────────────────────────────────────────────
    extract_data = PythonOperator(
        task_id='extract_data',
        python_callable=extract_neo_data,
        execution_timeout=timedelta(minutes=15),
        retries=3,
        doc="""
        Extracts historical NEO data for 7-day window.
        Uses execution_date from Airflow to determine date range.
        """,
    )
    
    # ────────────────────────────────────────────────────────────────────
    # TRANSFORMATION
    # ────────────────────────────────────────────────────────────────────
    transform_data = PythonOperator(
        task_id='transform_data',
        python_callable=transform_neo_data,
        execution_timeout=timedelta(minutes=10),
        retries=2,
        doc="Transforms historical data with quality validation",
    )
    
    # ────────────────────────────────────────────────────────────────────
    # LOADING
    # ────────────────────────────────────────────────────────────────────
    load_data = PythonOperator(
        task_id='load_data',
        python_callable=load_to_database,
        execution_timeout=timedelta(minutes=20),
        retries=2,
        doc="Loads historical data to database with duplicate checking",
    )
    
    # ────────────────────────────────────────────────────────────────────
    # QUALITY CHECK (More lenient for historical data)
    # ────────────────────────────────────────────────────────────────────
    quality_check = PythonOperator(
        task_id='quality_check',
        python_callable=run_quality_checks,
        execution_timeout=timedelta(minutes=5),
        retries=1,
        trigger_rule='none_failed',  # Run even if some tasks skipped
        doc="Quality checks (lenient thresholds for historical data)",
    )
    
    # ────────────────────────────────────────────────────────────────────
    # REPORTING
    # ────────────────────────────────────────────────────────────────────
    generate_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_pipeline_report,
        trigger_rule='none_failed',
        doc="Generates backfill execution report",
    )
    
    # ────────────────────────────────────────────────────────────────────
    # END
    # ────────────────────────────────────────────────────────────────────
    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed',
        doc="Backfill pipeline end marker"
    )

# ============================================================================
# Task Dependencies (Linear)
# ============================================================================
"""
Backfill Flow:
    start 
      → extract_data 
      → transform_data 
      → load_data 
      → quality_check 
      → generate_report 
      → end
"""

start >> extract_data >> transform_data >> load_data
load_data >> quality_check >> generate_report >> end

# ============================================================================
# Documentation
# ============================================================================
dag.doc_md = """
# NASA NEO Backfill Pipeline

## Purpose
Backfill historical NASA NEO data for any date range.

## Usage

### Backfill Specific Date Range
```bash
airflow dags backfill nasa_neo_backfill_pipeline \
    --start-date 2025-01-01 \
    --end-date 2025-12-31 \
    --rerun-failed-tasks
```

### Backfill Last 30 Days
```bash
airflow dags backfill nasa_neo_backfill_pipeline \
    --start-date $(date -d "30 days ago" +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d)
```

### Check Backfill Progress
```bash
airflow dags list-runs -d nasa_neo_backfill_pipeline --state running
```

## Important Notes

1. **Parallel Processing**: Up to 3 date ranges run simultaneously
2. **Date Windows**: Processes 7 days at a time (NASA API limit)
3. **Duplicate Handling**: Skips already loaded data
4. **Depends on Past**: Tasks wait for previous execution dates to complete

## Rate Limiting
NASA API has rate limits. If you hit them:
1. Reduce `max_active_runs` to 1
2. Increase `retry_delay` 
3. Add delays between tasks

## Monitoring
- **Web UI**: http://localhost:8080
- **Logs**: `airflow/logs/nasa_neo_backfill_pipeline/`
- **Reports**: `logs/reports/`

## Cleanup After Backfill
```bash
# Clear old task instances
airflow tasks clear nasa_neo_backfill_pipeline \
    --start-date 2025-01-01 \
    --end-date 2025-12-31 \
    --yes
```
"""
