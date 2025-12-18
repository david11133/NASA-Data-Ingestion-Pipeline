import requests
import time
import logging
from typing import Dict, Any, Optional

class BaseExtractor:
    """
    Base class for all API extractors.
    Handles common functionality like HTTP requests, retries, and error handling.
    """
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30, 
                 max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the base extractor.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP GET request with retry logic.
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters as dictionary
            
        Returns:
            JSON response as dictionary
            
        Raises:
            Exception: If all retry attempts fail
        """
        # Add API key to parameters
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        # Build full URL
        url = f"{self.base_url}{endpoint}"
        
        # Retry loop
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Attempt {attempt}/{self.max_retries}: Requesting {url}")
                
                # Make the request
                response = requests.get(url, params=params, timeout=self.timeout)
                
                # Check if request was successful
                response.raise_for_status()
                
                self.logger.info(f"Successfully fetched data from {url}")
                return response.json()
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Request timed out after {self.max_retries} attempts")
                    
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"HTTP Error: {e}")
                if response.status_code == 429:  # Rate limit
                    self.logger.warning("Rate limit hit, waiting longer...")
                    time.sleep(self.retry_delay * 2)
                elif attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"HTTP Error after {self.max_retries} attempts: {e}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Request failed after {self.max_retries} attempts: {e}")
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract data from the API.
        This method should be overridden by child classes.
        """
        raise NotImplementedError("Subclasses must implement extract() method")