from datetime import date
from typing import Dict, List, Optional
import dateparser
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
from selenium.common.exceptions import ElementClickInterceptedException

from .utils.rate_limiter import RateLimiter
from .utils.config import Config

class AmazonScraper:
    def __init__(self, rate_limiter: RateLimiter):
        self.config = Config()
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.driver = self._initialize_driver()

    def _initialize_driver(self) -> webdriver.Remote:
        """Initialize WebDriver based on OS."""
        if platform.system() == "Darwin":
            try:
                self.logger.info("Attempting to launch Safari WebDriver...")
                return self._setup_safari()
            except Exception as e:
                self.logger.warning(f"Safari WebDriver setup failed: {e}. Falling back to Chrome.")

        self.logger.info("Launching Chrome WebDriver...")
        return self._setup_chrome()

    def _setup_safari(self) -> webdriver.Safari:
        """Setup Safari WebDriver."""
        if sys.platform == "darwin":
            try:
                subprocess.run(["pkill", "-f", "safaridriver"], check=False)
            except Exception as e:
                self.logger.warning(f"Could not kill safaridriver: {e}")
        options = SafariOptions()
        if self.config.HEADLESS_MODE:
            self.logger.warning("Safari does not support headless mode.")
        return webdriver.Safari(service=SafariService(), options=options)

    def _setup_chrome(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with stealth options."""
        options = ChromeOptions()
        if self.config.HEADLESS_MODE:
            options.add_argument("--headless")
        options.add_argument(f"user-agent={self.config.USER_AGENT}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def _get_page_results(self, page: int, first_url: Optional[str] = None) -> List[Dict]:
        """Get results from the current page with retry logic."""
        max_retries = 2
        for attempt in range(max_retries):
            # Wait for search results to load and stabilize
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            
            # Additional wait to ensure dynamic content is loaded
            self.rate_limiter.wait()
            
            # Wait for any loading indicators to disappear
            WebDriverWait(self.driver, 5).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".s-loading-spinner"))
            )
            
            page_results = self._extract_products()
            
            if not page_results:
                self.logger.info("No results found on this page")
                return []
            
            # Check for duplicates only if we have a first_url to compare against
            if first_url and page_results[0]['url'] == first_url:
                if attempt < max_retries - 1:
                    self.logger.info(f"Page {page} not fully loaded, retrying... (attempt {attempt + 1}/{max_retries})")
                    self.driver.refresh()
                    self.rate_limiter.wait()
                    continue
                else:
                    self.logger.info("Page not loading properly after retries, stopping pagination")
                    return []
            
            return page_results
        
        return []

    def search_products(self, query: str, filters: Dict, max_results: int = 100) -> List[Dict]:
        """Search Amazon for products using a keyword and filter dict."""
        try:
            url = self._construct_search_url(query, filters)
            self.logger.info(f"Searching Amazon: {url}")
            self.driver.get(url)
            self.rate_limiter.wait()

            results = []
            first_url = None
            page = 1

            while len(results) < max_results:
                page_results = self._get_page_results(page, first_url)
                if not page_results:
                    break
                    
                results.extend(page_results)
                first_url = page_results[0]['url']
                self.logger.info(f"Page {page}: {len(page_results)} products, {len(results)} total")
                
                if len(results) >= max_results:
                    results = results[:max_results]
                    break
                
                # Scroll to bottom and wait for any dynamic content
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self.rate_limiter.wait()

                # Find next button
                next_button = None
                for selector in ["a.s-pagination-next", "a[href*='page=']"]:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if next_button and "s-pagination-disabled" not in next_button.get_attribute("class"):
                        break

                if not next_button or "s-pagination-disabled" in next_button.get_attribute("class"):
                    break

                # Scroll the next button into view and click it
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                self.driver.execute_script("arguments[0].click();", next_button)
                page += 1
                self.rate_limiter.wait()

            self.logger.info(f"Found {len(results)} products total")
            return results
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    def _construct_search_url(self, query: str, filters: Dict) -> str:
        """Build an Amazon search URL based on filters."""
        base_url = self.config.AMAZON_BASE_URL
        query_param = f"k={query.replace(' ', '+')}"
        rh_parts = []

        # Price range
        price_min = filters.get('price_min')
        price_max = filters.get('price_max')
        if price_min is not None and price_max is not None:
            rh_parts.append(f"p_36:{int(price_min) * 100}-{int(price_max) * 100}")
        elif price_max is not None:
            rh_parts.append(f"p_36:{int(price_max) * 100}")

        min_rating = filters.get('min_rating')
        if min_rating:
            rh_parts.append(f"p_72:{int(min_rating * 10)}")

        min_reviews = filters.get('min_reviews')
        if min_reviews:
            rh_parts.append(f"p_n_reviews:{min_reviews}")

        if filters.get('prime'):
            rh_parts.append("p_85:2470955011")

        delivery_code_map = {
            "today": "8308911011",
            "tomorrow": "8308921011",
            "in 2 days": "8308931011"
        }

        deliver_by = filters.get("deliver_by")
        if deliver_by:
            code = delivery_code_map.get(deliver_by.lower())
            if code:
                rh_parts.append(f"p_90:{code}")

        rh_param = f"rh={','.join(rh_parts)}" if rh_parts else None
        sort_by = filters.get('sort_by')
        sort_param = f"s={sort_by}" if sort_by else None

        params = [p for p in [query_param, rh_param, sort_param] if p]
        return f"{base_url}/s?{'&'.join(params)}"

    def _extract_products(self) -> List[Dict]:
        """Parse search results and return structured product info."""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = []

        for item in soup.select("[data-component-type='s-search-result']"):
            try:
                # Skip sponsored products to dedup
                if item.select_one("span.puis-label-popover-default"):
                    continue

                title = None
                for selector in [
                    "h2 a span",  # Standard product title
                    ".a-size-base-plus.a-color-base",  # Alternative title format
                    ".a-size-medium.a-color-base",  # Another common title format
                ]:
                    title = self._extract_text(item, selector)
                    if title:
                        break
                
                if not title:
                    self.logger.warning(f"Could not extract title. Available text: {item.get_text()[:100]}")
                    title = "Title not available"

                price = self._extract_price(item)
                rating = self._extract_rating(item)
                review_count = self._extract_review_count(item)

                product = {
                    "title": title,
                    "price": f"{price:.2f}" if price else "Price not available",
                    "rating": f"{rating:.1f} out of 5 stars" if rating else "No rating",
                    "review_count": f"{review_count:,}" if review_count else "No reviews",
                    "prime": self._is_prime(item),
                    "url": self._extract_url(item) or "URL not available",
                    "image_url": self._extract_image_url(item),
                    "price_per_count": self._extract_inline_unit_price(item),
                    "delivery_estimate": self._extract_inline_delivery_estimate(item),
                }
                results.append(product)
            except Exception as e:
                self.logger.warning(f"Product extraction failed: {e}")
                continue

        return results

    def _extract_text(self, element, selector: str) -> Optional[str]:
        try:
            return element.select_one(selector).text.strip()
        except:
            return None

    def _extract_price(self, element) -> Optional[float]:
        whole = element.select_one("span.a-price-whole")
        fraction = element.select_one("span.a-price-fraction")
        if whole and fraction:
            return float(f"{whole.text}{fraction.text}")
        return None

    def _extract_rating(self, element) -> Optional[float]:
        rating_text = element.select_one("span.a-icon-alt")
        return float(rating_text.text.split()[0]) if rating_text else None

    def _extract_review_count(self, element) -> Optional[int]:
        try:
            count_text = element.select_one("span.a-size-base.s-underline-text")
            if not count_text:
                count_text = element.select_one("span.a-size-base")
            return int(count_text.text.replace(',', '')) if count_text else None
        except:
            return None

    def _extract_inline_delivery_estimate(self, element) -> Optional[date]:
        """
        Extract the earliest delivery date (as a date object) from a delivery estimate string in the element.
        Handles phrases like 'Get it by...', 'Arrives...', 'FREE delivery...', etc.
        """
        try:
            text = element.get_text(separator=" ", strip=True)
            # Extract all date-like phrases
            date_matches = re.findall(r"(today|tomorrow|[A-Z][a-z]+ \d{1,2})", text, re.IGNORECASE)
            parsed_dates = [dateparser.parse(d, settings={"PREFER_DATES_FROM": "future"}) for d in date_matches]
            return min([d.date() for d in parsed_dates if d]) if parsed_dates else None
        except Exception as e:
            self.logger.warning(f"Delivery date extraction failed: {e}")
            return None

    def _extract_inline_unit_price(self, element) -> Optional[str]:
        try:
            text = element.get_text(separator=" ", strip=True)
            match = re.search(r"\$([\d\.]+)\s*/\s*(\w+)", text)
            return f"${match.group(1)} per {match.group(2)}" if match else None
        except Exception as e:
            self.logger.warning(f"Unit price extraction failed: {e}")
            return None

    def _is_prime(self, element) -> bool:
        return bool(element.select_one("i.a-icon-prime"))

    def _extract_url(self, element) -> Optional[str]:
        href = element.select_one("a.a-link-normal")["href"]
        return self.config.AMAZON_BASE_URL + href

    def _extract_image_url(self, element) -> Optional[str]:
        return element.select_one("img.s-image")["src"]

    def close(self):
        """Shut down the WebDriver."""
        if self.driver:
            self.driver.quit()
