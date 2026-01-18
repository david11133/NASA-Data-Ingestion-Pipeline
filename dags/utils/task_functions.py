"""
Task functions for Airflow DAGs
These functions will be called by Airflow tasks
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Import the existing pipeline components
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from extractors.neo_extractor import NEOExtractor
from transformers.neo_transformer import NEOTransformer
from transformers.data_quality import DataQualityChecker
from loaders.neo_loader import NEOLoader
from database.schema import initialize_database

logger = logging.getLogger(__name__)


def load_configs():
    """Load both config files"""
    project_root = Path(__file__).parent.parent.parent
    
    with open(project_root / 'config' / 'config.yaml', 'r') as f:
        main_config = yaml.safe_load(f)
    
    with open(project_root / 'config' / 'airflow_config.yaml', 'r') as f:
        airflow_config = yaml.safe_load(f)
    
    return main_config, airflow_config


def check_api_health(**context) -> bool:
    """
    Check if NASA API is available before starting extraction.
    """
    import requests
    
    api_key = os.getenv('NASA_API_KEY')
    test_url = f"https://api.nasa.gov/neo/rest/v1/feed?api_key={api_key}"
    
    try:
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            logger.info("✓ NASA API is healthy and accessible")
            return True
        else:
            logger.warning(f"NASA API returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"API health check failed: {str(e)}")
        return False


def extract_neo_data(**context) -> Dict[str, Any]:
    """
    Extract NEO data from NASA API.
    Returns data and pushes to XCom.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    main_config, _ = load_configs()
    api_key = os.getenv('NASA_API_KEY')
    
    # Get execution date from Airflow context
    execution_date = context['execution_date']
    logger.info(f"Extracting data for execution date: {execution_date}")
    
    # Initialize extractor
    extractor = NEOExtractor(
        api_key=api_key,
        base_url=main_config['api']['base_url'],
        output_path=main_config['storage']['raw_data_path'],
        timeout=main_config['api']['timeout'],
        max_retries=main_config['api']['max_retries'],
        retry_delay=main_config['api']['retry_delay']
    )
    
    # Extract last 7 days of data
    data = extractor.extract_last_n_days(7)
    
    logger.info(f"✓ Extracted {data['element_count']} NEO objects")
    
    # Save raw data to Bronze layer
    raw_file = save_raw_data_bronze(data, main_config['storage']['raw_data_path'])
    
    # Push data location to XCom for next task
    context['task_instance'].xcom_push(key='raw_data_file', value=str(raw_file))
    context['task_instance'].xcom_push(key='element_count', value=data['element_count'])
    
    return {
        'status': 'success',
        'element_count': data['element_count'],
        'raw_file': str(raw_file)
    }


def save_raw_data_bronze(data: dict, base_path: str) -> Path:
    """
    Save raw NASA JSON data into Bronze layer
    """
    dates = sorted(data['near_earth_objects'].keys())
    start_date = dates[0]
    
    date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    year_month = date_obj.strftime('%Y-%m')
    
    raw_dir = Path(base_path) / year_month
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = raw_dir / f"{start_date}.json"
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"✓ Raw data saved to {file_path}")
    return file_path


def transform_neo_data(**context) -> Dict[str, Any]:
    """
    Transform raw data to structured format (Silver layer).
    """
    main_config, _ = load_configs()
    
    # Get raw data file from previous task via XCom
    ti = context['task_instance']
    raw_file = ti.xcom_pull(task_ids='extract_data', key='raw_data_file')
    
    logger.info(f"Transforming data from: {raw_file}")
    
    # Load raw data
    with open(raw_file, 'r') as f:
        raw_data = json.load(f)
    
    # Initialize transformer and quality checker
    quality_checker = DataQualityChecker()
    transformer = NEOTransformer(quality_checker=quality_checker)
    
    # Transform the data
    transformed_data = transformer.transform(raw_data)
    
    logger.info(f"✓ Transformed {len(transformed_data['asteroids'])} asteroids")
    logger.info(f"✓ Transformed {len(transformed_data['estimated_diameters'])} diameter records")
    logger.info(f"✓ Transformed {len(transformed_data['close_approaches'])} close approach records")
    
    # Get quality summary
    quality_summary = quality_checker.get_summary()
    logger.info(f"✓ Quality Check Pass Rate: {quality_summary['pass_rate']:.1f}%")
    
    # Save transformed data
    output_file = transformer.save_transformed_data(
        transformed_data,
        output_dir="data/processed"
    )
    
    # Push to XCom
    ti.xcom_push(key='transformed_data_file', value=output_file)
    ti.xcom_push(key='quality_summary', value=quality_summary)
    
    return {
        'status': 'success',
        'asteroids_count': len(transformed_data['asteroids']),
        'quality_pass_rate': quality_summary['pass_rate']
    }


def load_to_database(**context) -> Dict[str, Any]:
    """
    Load transformed data into SQLite database.
    """
    # Get data from previous task
    ti = context['task_instance']
    raw_file = ti.xcom_pull(task_ids='extract_data', key='raw_data_file')
    
    logger.info(f"Loading data from: {raw_file}")
    
    # Load raw data
    with open(raw_file, 'r') as f:
        data = json.load(f)
    
    # Initialize database (if needed)
    initialize_database(force=False)
    
    # Load data
    loader = NEOLoader()
    stats = loader.load_from_json_data(
        data,
        source_file=raw_file,
        skip_if_loaded=True
    )
    
    logger.info("✓ Load completed:")
    logger.info(f"  • Asteroids inserted: {stats['asteroids_inserted']}")
    logger.info(f"  • Asteroids updated: {stats['asteroids_updated']}")
    logger.info(f"  • Close approaches: {stats['close_approaches_inserted']}")
    logger.info(f"  • Diameters inserted: {stats['diameters_inserted']}")
    
    if stats['errors']:
        logger.warning(f"⚠ Errors encountered: {len(stats['errors'])}")
    
    # Push to XCom
    ti.xcom_push(key='load_stats', value=stats)
    
    return {
        'status': 'success',
        'stats': stats
    }


def run_quality_checks(**context) -> Dict[str, Any]:
    """
    Run quality checks on the loaded data.
    Raises exception if quality thresholds are not met.
    """
    _, airflow_config = load_configs()
    thresholds = airflow_config['quality_thresholds']
    
    # Get data from previous tasks
    ti = context['task_instance']
    quality_summary = ti.xcom_pull(task_ids='transform_data', key='quality_summary')
    load_stats = ti.xcom_pull(task_ids='load_data', key='load_stats')
    
    logger.info("Running quality checks...")
    
    # Check 1: Minimum records
    total_records = load_stats['asteroids_inserted'] + load_stats['asteroids_updated']
    if total_records < thresholds['min_records']:
        raise ValueError(
            f"Quality check failed: Only {total_records} records loaded, "
            f"expected at least {thresholds['min_records']}"
        )
    
    # Check 2: Maximum records (sanity check)
    if total_records > thresholds['max_records']:
        logger.warning(
            f"⚠ Unusually high record count: {total_records} "
            f"(expected max {thresholds['max_records']})"
        )
    
    # Check 3: Quality pass rate
    if quality_summary['pass_rate'] < thresholds['min_pass_rate']:
        raise ValueError(
            f"Quality check failed: Pass rate {quality_summary['pass_rate']:.1f}% "
            f"is below threshold {thresholds['min_pass_rate']}%"
        )
    
    # Check 4: No errors in loading
    if load_stats['errors']:
        logger.warning(f"⚠ {len(load_stats['errors'])} errors during loading")
    
    logger.info("✓ All quality checks passed")
    
    return {
        'status': 'success',
        'checks_passed': True,
        'total_records': total_records,
        'quality_pass_rate': quality_summary['pass_rate']
    }


def generate_pipeline_report(**context) -> str:
    """
    Generate a summary report of the pipeline run.
    """
    ti = context['task_instance']
    execution_date = context['execution_date']
    
    # Gather data from all tasks
    element_count = ti.xcom_pull(task_ids='extract_data', key='element_count')
    quality_summary = ti.xcom_pull(task_ids='transform_data', key='quality_summary')
    load_stats = ti.xcom_pull(task_ids='load_data', key='load_stats')
    
    # Create report
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║           NASA NEO PIPELINE EXECUTION REPORT                     ║
╚══════════════════════════════════════════════════════════════════╝

Execution Date: {execution_date.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline: {context['dag'].dag_id}

────────────────────────────────────────────────────────────────────
EXTRACTION
────────────────────────────────────────────────────────────────────
✓ NEO Objects Extracted: {element_count}

────────────────────────────────────────────────────────────────────
TRANSFORMATION & QUALITY
────────────────────────────────────────────────────────────────────
✓ Quality Checks Passed: {quality_summary['passed']}
✗ Quality Checks Failed: {quality_summary['failed']}
✓ Pass Rate: {quality_summary['pass_rate']:.2f}%

────────────────────────────────────────────────────────────────────
DATABASE LOADING
────────────────────────────────────────────────────────────────────
✓ Asteroids Inserted: {load_stats['asteroids_inserted']}
✓ Asteroids Updated: {load_stats['asteroids_updated']}
✓ Close Approaches: {load_stats['close_approaches_inserted']}
✓ Diameters: {load_stats['diameters_inserted']}
✗ Errors: {len(load_stats['errors'])}

────────────────────────────────────────────────────────────────────
STATUS: ✓ PIPELINE COMPLETED SUCCESSFULLY
────────────────────────────────────────────────────────────────────
"""
    
    logger.info(report)
    
    # Save report to file
    report_dir = Path('logs/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"pipeline_report_{execution_date.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"✓ Report saved to {report_file}")
    
    return str(report_file)


def cleanup_old_files(**context) -> Dict[str, Any]:
    """
    Cleanup old files (optional task).
    Remove files older than 30 days from raw and processed directories.
    """
    from datetime import datetime, timedelta
    
    cleanup_age_days = 30
    cutoff_date = datetime.now() - timedelta(days=cleanup_age_days)
    
    directories = [
        'data/raw',
        'data/processed',
        'logs/reports'
    ]
    
    files_removed = 0
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    logger.info(f"Removing old file: {file_path}")
                    file_path.unlink()
                    files_removed += 1
    
    logger.info(f"✓ Cleanup complete: {files_removed} files removed")
    
    return {
        'status': 'success',
        'files_removed': files_removed
    }
