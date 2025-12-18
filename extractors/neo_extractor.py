from datetime import datetime, timedelta
from typing import Dict, Any
import json
import os
import re
from extractors.base_extractor import BaseExtractor

class NEOExtractor(BaseExtractor):
    """
    Extractor for NASA Near Earth Objects (NEO) data.
    """
    
    def __init__(self, api_key: str, base_url: str, output_path: str, **kwargs):
        """
        Initialize NEO extractor.
        
        Args:
            api_key: NASA API key
            base_url: Base URL for NASA NEO API
            output_path: Path to save raw JSON files
            **kwargs: Additional arguments for BaseExtractor
        """
        super().__init__(api_key, base_url, **kwargs)
        self.output_path = output_path
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
    def extract_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Extract NEO data for a specific date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing NEO data
        """
        self.logger.info(f"Extracting NEO data from {start_date} to {end_date}")
        
        # API endpoint for feed
        endpoint = "/feed"
        
        # Parameters
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Make the request using parent class method
        data = self._make_request(endpoint, params)
        
        # Save raw JSON to file
        self._save_raw_data(data, start_date, end_date)
        
        return data
    
    def extract_today(self) -> Dict[str, Any]:
        """
        Extract NEO data for today.
        
        Returns:
            Dictionary containing today's NEO data
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self.logger.info(f"Extracting NEO data for today: {today}")
        
        return self.extract_by_date_range(today, today)
    
    def extract_last_n_days(self, n_days: int = 7) -> Dict[str, Any]:
        """
        Extract NEO data for the last N days.
        
        Args:
            n_days: Number of days to fetch (NASA API allows max 7 days)
            
        Returns:
            Dictionary containing NEO data
        """
        # NASA API allows maximum 7 days
        if n_days > 7:
            self.logger.warning(f"NASA API allows max 7 days, setting n_days to 7")
            n_days = 7
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=n_days - 1)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        return self.extract_by_date_range(start_date_str, end_date_str)
    
    def _save_raw_data(self, data: Dict[str, Any], start_date: str, end_date: str):
        """
        Save raw JSON data to file with API key sanitization.
        
        Args:
            data: Data to save
            start_date: Start date for filename
            end_date: End date for filename
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"neo_raw_{start_date}_to_{end_date}_{timestamp}.json"
        filepath = os.path.join(self.output_path, filename)
        
        try:
            # Sanitize API keys before saving
            sanitized_data = self._sanitize_api_keys(data)
            
            with open(filepath, 'w') as f:
                json.dump(sanitized_data, f, indent=2)
            
            self.logger.info(f"Raw data saved to: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save raw data: {e}")
            raise
    
    def _sanitize_api_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove API keys from URLs in the data structure.
        
        Args:
            data: Dictionary containing NEO data
            
        Returns:
            Sanitized data dictionary
        """
        # Convert to JSON string, replace API keys, convert back
        data_str = json.dumps(data)
        sanitized_str = re.sub(r'api_key=[A-Za-z0-9]+', 'api_key=REDACTED', data_str)
        return json.loads(sanitized_str)
    
    def extract(self) -> Dict[str, Any]:
        """
        Default extract method - extracts last 7 days of data.
        
        Returns:
            Dictionary containing NEO data
        """
        return self.extract_last_n_days(7)