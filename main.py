import os
import logging
import yaml
from dotenv import load_dotenv
from extractors.neo_extractor import NEOExtractor

def setup_logging(config: dict):
    """
    Setup logging configuration.
    
    Args:
        config: Configuration dictionary
    """
    log_config = config['logging']
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_config['log_file'])
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.FileHandler(log_config['log_file']),
            logging.StreamHandler()  # Also print to console
        ]
    )

def load_config(config_path: str = 'config/config.yaml') -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    """
    Main function to run the data extraction.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('NASA_API_KEY')
    
    if not api_key:
        raise ValueError("NASA_API_KEY not found in .env file!")
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Starting NASA NEO Data Extraction")
    logger.info("=" * 60)
    
    try:
        # Initialize NEO extractor
        extractor = NEOExtractor(
            api_key=api_key,
            base_url=config['api']['base_url'],
            output_path=config['storage']['raw_data_path'],
            timeout=config['api']['timeout'],
            max_retries=config['api']['max_retries'],
            retry_delay=config['api']['retry_delay']
        )
        
        # Extract data for last 7 days
        logger.info("Extracting NEO data for the last 7 days...")
        data = extractor.extract_last_n_days(7)
        
        # Print summary
        logger.info("-" * 60)
        logger.info("Extraction Summary:")
        logger.info(f"Total NEOs found: {data['element_count']}")
        
        # Count NEOs per day
        for date, neos in data['near_earth_objects'].items():
            logger.info(f"  {date}: {len(neos)} NEOs")
        
        logger.info("-" * 60)
        logger.info("[SUCCESS] Data extraction completed successfully!")
        
    except Exception as e:
        logger.error(f"[ERROR] Data extraction failed: {e}")
        raise

if __name__ == "__main__":
    main()