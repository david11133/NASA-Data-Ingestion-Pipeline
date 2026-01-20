"""
NASA NEO Backfill Pipeline DAG

This DAG is used to backfill historical NEO data.
It's designed to run manually (not on a schedule) for specific date ranges.

Usage:
1. Trigger this DAG manually from Airflow UI
2. Pass configuration: {"start_date": "2025-01-01", "end_date": "2025-12-31"}

Features:
- Processes data in weekly chunks (NASA API limit is 7 days)
- Handles rate limiting
- Skips already loaded data
- Generates backfill summary report
"""

from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
import json
import logging
from typing import List, Tuple

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.exceptions import AirflowException
from airflow.utils.dates import days_ago

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extractors.neo_extractor import NEOExtractor
from transformers.neo_transformer import NEOTransformer
from transformers.data_quality import DataQualityChecker
from loaders.neo_loader import NEOLoader
from database.schema import initialize_database

# =============================================================================
# Configuration
# =============================================================================

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

# =============================================================================
# Helper Functions
# =============================================================================

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
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    chunks = []
    current = start
    
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_size - 1), end)
        chunks.append((
            current.strftime('%Y-%m-%d'),
            chunk_end.strftime('%Y-%m-%d')
        ))
        current = chunk_end + timedelta(days=1)
    
    return chunks


def initialize_backfill(**context):
    """
    Initialize backfill process and validate parameters.
    """
    logging.info("Initializing backfill process...")
    
    # Get configuration from DAG run
    conf = context['dag_run'].conf or {}
    
    # Get date range from config or use defaults
    start_date = conf.get('start_date', '2025-01-01')
    end_date = conf.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    logging.info(f"Backfill date range: {start_date} to {end_date}")
    
    # Validate dates
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            raise ValueError("Start date must be before end date")
        
        if end > datetime.now():
            raise ValueError("End date cannot be in the future")
            
    except ValueError as e:
        raise AirflowException(f"Invalid date range: {str(e)}")
    
    # Generate date chunks
    chunks = generate_date_chunks(start_date, end_date)
    
    logging.info(f"Generated {len(chunks)} date chunks for processing")
    
    # Push to XCom for next tasks
    ti = context['task_instance']
    ti.xcom_push(key='start_date', value=start_date)
    ti.xcom_push(key='end_date', value=end_date)
    ti.xcom_push(key='date_chunks', value=chunks)
    ti.xcom_push(key='total_chunks', value=len(chunks))
    
    # Initialize database
    initialize_database(force=False)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'chunks': len(chunks)
    }


def process_date_chunk(**context):
    """
    Process a single date chunk (extract, transform, load).
    This function will be called multiple times for each chunk.
    """
    ti = context['task_instance']
    
    # Get all chunks
    chunks = ti.xcom_pull(task_ids='initialize_backfill', key='date_chunks')
    
    if not chunks:
        raise AirflowException("No date chunks found")
    
    # Track overall stats
    all_stats = {
        'chunks_processed': 0,
        'chunks_failed': 0,
        'total_neos': 0,
        'total_inserted': 0,
        'total_updated': 0,
        'errors': []
    }
    
    # Get API key
    api_key = os.getenv('NASA_API_KEY')
    if not api_key:
        api_key = Variable.get('NASA_API_KEY')
    
    # Process each chunk
    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        try:
            logging.info(f"Processing chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}")
            
            # Extract
            extractor = NEOExtractor(
                api_key=api_key,
                base_url="https://api.nasa.gov/neo/rest/v1",
                output_path="data/raw",
                timeout=30,
                max_retries=3,
                retry_delay=2
            )
            
            data = extractor.extract_by_date_range(chunk_start, chunk_end)
            neo_count = data['element_count']
            
            logging.info(f"✓ Extracted {neo_count} NEOs")
            
            # Save raw data
            dates = sorted(data['near_earth_objects'].keys())
            if dates:
                date_obj = datetime.strptime(dates[0], '%Y-%m-%d')
                year_month = date_obj.strftime('%Y-%m')
                
                raw_dir = Path('data/raw') / year_month
                raw_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = raw_dir / f"{dates[0]}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logging.info(f"✓ Saved raw data to {file_path}")
            
            # Transform
            quality_checker = DataQualityChecker()
            transformer = NEOTransformer(quality_checker=quality_checker)
            transformed_data = transformer.transform(data)
            
            quality_summary = quality_checker.get_summary()
            logging.info(f"✓ Transformed with {quality_summary['pass_rate']:.1f}% quality")
            
            # Save transformed data
            transformer.save_transformed_data(
                transformed_data,
                output_dir="data/processed"
            )
            
            # Load to database
            loader = NEOLoader()
            stats = loader.load_from_json_data(
                data,
                source_file=str(file_path) if dates else None,
                skip_if_loaded=True
            )
            
            logging.info(f"✓ Loaded: {stats['asteroids_inserted']} new, {stats['asteroids_updated']} updated")
            
            # Update overall stats
            all_stats['chunks_processed'] += 1
            all_stats['total_neos'] += neo_count
            all_stats['total_inserted'] += stats['asteroids_inserted']
            all_stats['total_updated'] += stats['asteroids_updated']
            
            # Rate limiting: wait between chunks
            if i < len(chunks):
                logging.info("Waiting 5 seconds before next chunk (rate limiting)...")
                import time
                time.sleep(5)
                
        except Exception as e:
            logging.error(f"Failed to process chunk {chunk_start} to {chunk_end}: {str(e)}")
            all_stats['chunks_failed'] += 1
            all_stats['errors'].append({
                'chunk': f"{chunk_start} to {chunk_end}",
                'error': str(e)
            })
            # Continue with next chunk instead of failing entirely
    
    # Push final stats
    ti.xcom_push(key='backfill_stats', value=all_stats)
    
    logging.info("=" * 70)
    logging.info("BACKFILL PROCESSING COMPLETE")
    logging.info(f"Chunks processed: {all_stats['chunks_processed']}/{len(chunks)}")
    logging.info(f"Total NEOs: {all_stats['total_neos']}")
    logging.info(f"Inserted: {all_stats['total_inserted']}")
    logging.info(f"Updated: {all_stats['total_updated']}")
    logging.info(f"Failed chunks: {all_stats['chunks_failed']}")
    logging.info("=" * 70)
    
    return all_stats


def generate_backfill_report(**context):
    """
    Generate comprehensive backfill report.
    """
    logging.info("Generating backfill report...")
    
    ti = context['task_instance']
    
    # Pull all data
    init_info = ti.xcom_pull(task_ids='initialize_backfill')
    backfill_stats = ti.xcom_pull(task_ids='process_chunks', key='backfill_stats')
    
    # Create report
    report = {
        'backfill_run_date': datetime.now().isoformat(),
        'dag_run_id': context['run_id'],
        'date_range': {
            'start': init_info['start_date'],
            'end': init_info['end_date'],
        },
        'processing': {
            'total_chunks': init_info['chunks'],
            'chunks_processed': backfill_stats['chunks_processed'],
            'chunks_failed': backfill_stats['chunks_failed'],
        },
        'data': {
            'total_neos_extracted': backfill_stats['total_neos'],
            'asteroids_inserted': backfill_stats['total_inserted'],
            'asteroids_updated': backfill_stats['total_updated'],
        },
        'errors': backfill_stats['errors'],
        'status': 'SUCCESS' if backfill_stats['chunks_failed'] == 0 else 'PARTIAL_SUCCESS'
    }
    
    # Save report
    report_dir = Path('data/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"backfill_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logging.info(f"✓ Backfill report saved to {report_file}")
    
    # Print summary
    logging.info("=" * 70)
    logging.info("BACKFILL SUMMARY REPORT")
    logging.info("=" * 70)
    logging.info(f"Date Range: {report['date_range']['start']} to {report['date_range']['end']}")
    logging.info(f"Chunks: {report['processing']['chunks_processed']}/{report['processing']['total_chunks']} processed")
    logging.info(f"NEOs: {report['data']['total_neos_extracted']} extracted")
    logging.info(f"Database: {report['data']['asteroids_inserted']} inserted, {report['data']['asteroids_updated']} updated")
    logging.info(f"Status: {report['status']}")
    
    if report['errors']:
        logging.warning(f"Errors: {len(report['errors'])} chunks failed")
        for error in report['errors'][:5]:
            logging.error(f"  - {error['chunk']}: {error['error']}")
    
    logging.info("=" * 70)
    
    return report


# =============================================================================
# DAG Definition
# =============================================================================

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

# =============================================================================
# Tasks
# =============================================================================

# Task 1: Initialize and validate backfill parameters
init_task = PythonOperator(
    task_id='initialize_backfill',
    python_callable=initialize_backfill,
    dag=dag,
)

# Task 2: Process all date chunks
process_task = PythonOperator(
    task_id='process_chunks',
    python_callable=process_date_chunk,
    dag=dag,
)

# Task 3: Generate backfill report
report_task = PythonOperator(
    task_id='generate_backfill_report',
    python_callable=generate_backfill_report,
    dag=dag,
)

# =============================================================================
# Dependencies
# =============================================================================

init_task >> process_task >> report_task