##########################################################################################
import os
import json
import logging
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from extractors.neo_extractor import NEOExtractor
from database.schema import initialize_database
from loaders.neo_loader import NEOLoader
##########################################################################################

def setup_logging(config: dict):
    log_config = config['logging']

    log_dir = os.path.dirname(log_config['log_file'])
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.FileHandler(log_config['log_file']),
            logging.StreamHandler()
        ]
    )

##########################################################################################
def load_config(config_path: str = 'config/config.yaml') -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

##########################################################################################
# Raw Data
def save_raw_data(data: dict, base_path: str) -> Path:
    """
    Save raw NASA JSON data into Bronze layer
    data/raw/neos/YYYY-MM/YYYY-MM-DD.json
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

    return file_path


##########################################################################################
# Main Pipeline
def main():
    load_dotenv()

    api_key = os.getenv('NASA_API_KEY')
    if not api_key:
        raise ValueError("NASA_API_KEY not found in .env file")

    config = load_config()
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("NASA NEO DATA PIPELINE STARTED")
    logger.info("=" * 70)

    # 1: Initialize Database Schema
    logger.info("[1/4] Initializing database schema...")
    initialize_database(force=False)

    # 2: Extract Data from NASA API
    logger.info("[2/4] Extracting NEO data from NASA API...")
    extractor = NEOExtractor(
        api_key=api_key,
        base_url=config['api']['base_url'],
        output_path=config['storage']['raw_data_path'],
        timeout=config['api']['timeout'],
        max_retries=config['api']['max_retries'],
        retry_delay=config['api']['retry_delay']
    )

    data = extractor.extract_last_n_days(7)

    logger.info(f"Extracted {data['element_count']} NEOs")

    # 3: Save Raw Data
    logger.info("[3/4] Saving raw JSON data...")
    raw_file = save_raw_data(
        data,
        base_path=config['storage']['raw_data_path']
    )

    logger.info(f"Raw data saved to {raw_file}")

    # 4: Load into SQLite
    logger.info("[4/4] Loading data into SQLite database...")
    loader = NEOLoader()

    stats = loader.load_from_json_data(
        data,
        source_file=str(raw_file),
        skip_if_loaded=True
    )

    logger.info("Load completed:")
    logger.info(f"  Asteroids inserted: {stats['asteroids_inserted']}")
    logger.info(f"  Asteroids updated: {stats['asteroids_updated']}")
    logger.info(f"  Close approaches: {stats['close_approaches_inserted']}")
    logger.info(f"  Diameters inserted: {stats['diameters_inserted']}")

    if stats['errors']:
        logger.warning(f"Errors encountered: {len(stats['errors'])}")

    logger.info("=" * 70)
    logger.info("PIPELINE FINISHED SUCCESSFULLY")
    logger.info("=" * 70)

##########################################################################################
if __name__ == "__main__":
    main()