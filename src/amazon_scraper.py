from typing import Dict, List, Optional
import logging
import platform
import subprocess
import sys
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .utils.rate_limiter import RateLimiter
from .utils.config import Config


class AmazonScraper:
    def __init__(self, rate_limiter: RateLimiter):
        self.config = Config()
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        self.driver = self._initialize_driver()

    def _initialize_driver(self) -> webdriver.Remote:
        """Initialize WebDriver based on OS, fallback to Chrome if Safari fails."""
        if platform.system() == "Darwin":
            try:
                self.logger.info("Attempting to launch Safari WebDriver...")
                return self._setup_safari()
            except Exception as e:
                self.logger.warning(f"Safari WebDriver setup failed: {e}. Falling back to Chrome.")

        self.logger.info("Launching Chrome WebDriver...")
        return self._setup_chrome()

    def _setup_safari(self) -> webdriver.Safari:
        """Setup Safari driver."""
        if sys.platform == "darwin":
            try:
                subprocess.run(["pkill", "-f", "safaridriver"], check=False)
            except Exception as e:
                self.logger.warning(f"Could not kill existing safaridriver processes: {e}")

        safari_options = SafariOptions()
        if self.config.HEADLESS_MODE:
            self.logger.warning("Safari does not support headless mode. Running in normal mode.")

        service = SafariService()
        return webdriver.Safari(service=service, options=safari_options)

    def _setup_chrome(self) -> webdriver.Chrome:
        """Setup Chrome driver."""
        chrome_options = ChromeOptions()
        if self.config.HEADLESS_MODE:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument(f"user-agent={self.config.USER_AGENT}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def search_products(self, query: str, filters: Dict) -> List[Dict]:
        """Search Amazon for products based on query and filters."""
        try:
            search_url = self._construct_search_url(query, filters)
            self.logger.info(f"Searching Amazon: {search_url}")

            self.driver.get(search_url)
            self.rate_limiter.wait()

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            return self._extract_products()

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            raise

    def _construct_search_url(self, query: str, filters: Dict) -> str:
        """Build search URL from query and filters."""
        base_url = self.config.AMAZON_BASE_URL
        params = [f"k={query.replace(' ', '+')}"]

        if filters.get('price_max'):
            params.append(f"rh=p_36%3A{filters['price_max']}00")
        if filters.get('prime'):
            params.append("rh=p_85%3A2470955011")

        return f"{base_url}/s?{'&'.join(params)}"

    def _extract_products(self) -> List[Dict]:
        """Extract products from page."""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        products = []

        for item in soup.select("[data-component-type='s-search-result']"):
            try:
                product = {
                    'title': self._extract_text(item, "span.a-size-medium"),
                    'price': self._extract_price(item),
                    'rating': self._extract_rating(item),
                    'review_count': self._extract_review_count(item),
                    'prime': self._is_prime(item),
                    'url': self._extract_url(item),
                    'image_url': self._extract_image_url(item),
                    'unit_price': self._extract_inline_unit_price(item),
                    'delivery_estimate': self._extract_inline_delivery_estimate(item),
                }
                products.append(product)
            except Exception as e:
                self.logger.warning(f"Error extracting a product: {e}")
                continue

        return products

    def _extract_text(self, element, selector: str) -> Optional[str]:
        try:
            return element.select_one(selector).text.strip()
        except:
            return None

    def _extract_price(self, element) -> Optional[float]:
        try:
            whole = element.select_one("span.a-price-whole").text
            fraction = element.select_one("span.a-price-fraction").text
            return float(f"{whole}{fraction}")
        except:
            return None

    def _extract_rating(self, element) -> Optional[float]:
        try:
            rating_text = element.select_one("span.a-icon-alt").text
            return float(rating_text.split()[0])
        except:
            return None

    def _extract_review_count(self, element) -> Optional[int]:
        try:
            count_text = element.select_one("span.a-size-base").text
            return int(count_text.replace(',', ''))
        except:
            return None
        
    def _extract_inline_delivery_estimate(self, element) -> Optional[str]:
        try:
            text = element.get_text(separator=" ", strip=True)
            match = re.search(r"(Get it [^\.]+|Arrives [^\.]+|FREE delivery [^\.]+)", text)
            if match:
                return match.group(1)
        except Exception as e:
            self.logger.warning(f"Inline delivery estimate error: {e}")
        return None


    def _extract_inline_unit_price(self, element) -> Optional[str]:
        try:
            text = element.get_text(separator=" ", strip=True)
            match = re.search(r"\$([\d\.]+)\s*/\s*(\w+)", text)
            if match:
                return f"${match.group(1)} per {match.group(2)}"
        except Exception as e:
            self.logger.warning(f"Inline unit price parsing error: {e}")
        return None

    def _is_prime(self, element) -> bool:
        return bool(element.select_one("i.a-icon-prime"))

    def _extract_url(self, element) -> Optional[str]:
        try:
            href = element.select_one("a.a-link-normal")['href']
            return self.config.AMAZON_BASE_URL + href
        except:
            return None

    def _extract_image_url(self, element) -> Optional[str]:
        try:
            return element.select_one("img.s-image")['src']
        except:
            return None

    def refine_search(self, previous_products: List[Dict], refinements: Dict) -> List[Dict]:
        """Refine products based on new filters."""
        return [
            product for product in previous_products
            if self._matches_refinements(product, refinements)
        ]

    def _matches_refinements(self, product: Dict, refinements: Dict) -> bool:
        """Check if a product matches given refinement filters."""
        if refinements.get('price_max') and product.get('price', 0) > refinements['price_max']:
            return False
        if refinements.get('min_rating') and product.get('rating', 0) < refinements['min_rating']:
            return False
        if refinements.get('prime_only') and not product.get('prime', False):
            return False
        return True

    def close(self):
        """Cleanly close WebDriver."""
        if self.driver:
            self.driver.quit()
