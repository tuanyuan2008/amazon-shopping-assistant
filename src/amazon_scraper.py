from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
from bs4 import BeautifulSoup
import time
import random

from .utils.rate_limiter import RateLimiter
from .utils.config import Config

class AmazonScraper:
    def __init__(self, rate_limiter: RateLimiter):
        self.config = Config()
        self.rate_limiter = rate_limiter
        self.driver = self._setup_driver()
        self.logger = logging.getLogger(__name__)

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up and configure the Chrome WebDriver."""
        chrome_options = Options()
        if self.config.HEADLESS_MODE:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument(f"user-agent={self.config.USER_AGENT}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def search_products(self, query: str, filters: Dict) -> List[Dict]:
        """
        Search for products on Amazon with given query and filters.
        
        Args:
            query (str): Search query
            filters (Dict): Dictionary of filters to apply
            
        Returns:
            List[Dict]: List of product information dictionaries
        """
        try:
            # Construct search URL with filters
            search_url = self._construct_search_url(query, filters)
            self.logger.info(f"Searching with URL: {search_url}")
            
            # Navigate to search page
            self.driver.get(search_url)
            self.rate_limiter.wait()
            
            # Wait for results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            
            # Extract product information
            products = self._extract_products()
            return products
            
        except Exception as e:
            self.logger.error(f"Error searching products: {str(e)}")
            raise

    def _construct_search_url(self, query: str, filters: Dict) -> str:
        """Construct Amazon search URL with query and filters."""
        base_url = self.config.AMAZON_BASE_URL
        search_params = []
        
        # Add search query
        search_params.append(f"k={query.replace(' ', '+')}")
        
        # Add filters
        if filters.get('price_max'):
            search_params.append(f"rh=p_36%3A{filters['price_max']}00")
        if filters.get('prime'):
            search_params.append("rh=p_85%3A2470955011")
            
        return f"{base_url}/s?{'&'.join(search_params)}"

    def _extract_products(self) -> List[Dict]:
        """Extract product information from search results page."""
        products = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        for item in soup.select("[data-component-type='s-search-result']"):
            try:
                product = {
                    'title': self._extract_text(item, "span.a-size-medium"),
                    'price': self._extract_price(item),
                    'rating': self._extract_rating(item),
                    'review_count': self._extract_review_count(item),
                    'prime': self._is_prime(item),
                    'url': self._extract_url(item),
                    'image_url': self._extract_image_url(item)
                }
                products.append(product)
            except Exception as e:
                self.logger.warning(f"Error extracting product: {str(e)}")
                continue
                
        return products

    def _extract_text(self, element, selector: str) -> Optional[str]:
        """Extract text from an element using CSS selector."""
        try:
            return element.select_one(selector).text.strip()
        except:
            return None

    def _extract_price(self, element) -> Optional[float]:
        """Extract price from product element."""
        try:
            price_text = element.select_one("span.a-price-whole").text
            price_cents = element.select_one("span.a-price-fraction").text
            return float(f"{price_text}{price_cents}")
        except:
            return None

    def _extract_rating(self, element) -> Optional[float]:
        """Extract rating from product element."""
        try:
            rating_text = element.select_one("span.a-icon-alt").text
            return float(rating_text.split()[0])
        except:
            return None

    def _extract_review_count(self, element) -> Optional[int]:
        """Extract review count from product element."""
        try:
            count_text = element.select_one("span.a-size-base").text
            return int(count_text.replace(',', ''))
        except:
            return None

    def _is_prime(self, element) -> bool:
        """Check if product is Prime eligible."""
        return bool(element.select_one("i.a-icon-prime"))

    def _extract_url(self, element) -> Optional[str]:
        """Extract product URL from element."""
        try:
            return self.config.AMAZON_BASE_URL + element.select_one("a.a-link-normal")['href']
        except:
            return None

    def _extract_image_url(self, element) -> Optional[str]:
        """Extract product image URL from element."""
        try:
            return element.select_one("img.s-image")['src']
        except:
            return None

    def refine_search(self, previous_products: List[Dict], refinements: Dict) -> List[Dict]:
        """
        Refine previous search results based on new criteria.
        
        Args:
            previous_products (List[Dict]): Previous search results
            refinements (Dict): New filters and criteria
            
        Returns:
            List[Dict]: Refined product list
        """
        # Apply refinements to existing products
        refined_products = []
        for product in previous_products:
            if self._matches_refinements(product, refinements):
                refined_products.append(product)
                
        return refined_products

    def _matches_refinements(self, product: Dict, refinements: Dict) -> bool:
        """Check if product matches refinement criteria."""
        if refinements.get('price_max') and product['price'] > refinements['price_max']:
            return False
        if refinements.get('min_rating') and product['rating'] < refinements['min_rating']:
            return False
        if refinements.get('prime_only') and not product['prime']:
            return False
        return True

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit() 