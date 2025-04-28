import os
from dotenv import load_dotenv
from typing import Optional

class Config:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Amazon Configuration
        self.AMAZON_BASE_URL = os.getenv('AMAZON_BASE_URL', 'https://www.amazon.com')
        
        # Rate Limiting Configuration
        self.MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '30'))
        self.REQUEST_DELAY_MIN = float(os.getenv('REQUEST_DELAY_MIN', '2'))
        self.REQUEST_DELAY_MAX = float(os.getenv('REQUEST_DELAY_MAX', '5'))
        
        # Selenium Configuration
        self.HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'True').lower() == 'true'
        self.USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Validate configuration
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate the configuration values."""
        if self.MAX_REQUESTS_PER_MINUTE <= 0:
            raise ValueError("MAX_REQUESTS_PER_MINUTE must be greater than 0")
        
        if self.REQUEST_DELAY_MIN < 0 or self.REQUEST_DELAY_MAX < 0:
            raise ValueError("Request delay values must be non-negative")
        
        if self.REQUEST_DELAY_MIN > self.REQUEST_DELAY_MAX:
            raise ValueError("REQUEST_DELAY_MIN must be less than or equal to REQUEST_DELAY_MAX")
        
        if not self.AMAZON_BASE_URL.startswith(('http://', 'https://')):
            raise ValueError("AMAZON_BASE_URL must be a valid URL starting with http:// or https://") 