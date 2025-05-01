from datetime import datetime, timedelta
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

    def search_products(self, query: str, filters: Dict) -> List[Dict]:
        """Search Amazon for products using a keyword and filter dict."""
        try:
            url = self._construct_search_url(query, filters)
            self.logger.info(f"Navigating to Amazon: {url}")
            self.driver.get(url)
            self.rate_limiter.wait()

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
            )
            return self._extract_products()
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
                title = (
                    self._extract_text(item, "h2 a span") or
                    self._extract_text(item, ".a-size-medium.a-color-base.a-text-normal") or
                    "Title not available"
                )
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
        try:
            whole = element.select_one("span.a-price-whole")
            fraction = element.select_one("span.a-price-fraction")
            if whole and fraction:
                return float(f"{whole.text}{fraction.text}")
            return None
        except:
            return None

    def _extract_rating(self, element) -> Optional[float]:
        try:
            rating_text = element.select_one("span.a-icon-alt")
            return float(rating_text.text.split()[0]) if rating_text else None
        except:
            return None

    def _extract_review_count(self, element) -> Optional[int]:
        try:
            count_text = element.select_one("span.a-size-base")
            return int(count_text.text.replace(',', '')) if count_text else None
        except:
            return None

    def _extract_inline_delivery_estimate(self, element) -> Optional[str]:
        try:
            text = element.get_text(separator=" ", strip=True)
            match = re.search(r"(Get it [^\.]+|Arrives [^\.]+|FREE delivery [^\.]+)", text)
            return match.group(1) if match else None
        except Exception as e:
            self.logger.warning(f"Delivery estimate extraction failed: {e}")
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
        try:
            href = element.select_one("a.a-link-normal")["href"]
            return self.config.AMAZON_BASE_URL + href
        except:
            return None

    def _extract_image_url(self, element) -> Optional[str]:
        try:
            return element.select_one("img.s-image")["src"]
        except:
            return None
        
    def _normalize_delivery_keywords(self, deliver_by: str) -> List[str]:
        """
        Given a normalized delivery string like 'tomorrow', 'in 2 days', or 'May 11',
        return a list of keywords to match against Amazon's delivery estimate text.
        """
        deliver_by = deliver_by.lower().strip()
        keywords = [deliver_by]

        try:
            # Handle 'tomorrow'
            if deliver_by == "tomorrow":
                date = datetime.now() + timedelta(days=1)
                keywords.append(date.strftime("%B %-d").lower())

            # Handle 'today'
            elif deliver_by == "today":
                date = datetime.now()
                keywords.append(date.strftime("%B %-d").lower())

            # Handle relative format: 'in N days'
            elif "in" in deliver_by and "day" in deliver_by:
                num_days = int(deliver_by.split("in ")[1].split(" ")[0])
                date = datetime.now() + timedelta(days=num_days)
                keywords.append(date.strftime("%B %-d").lower())

            # If it's already something like 'May 11', leave as is
            # If it's a holiday like "mother's day", assume it's already usable
        except Exception:
            pass

        return list(set(keywords))  # Deduplicate

    def close(self):
        """Shut down the WebDriver."""
        if self.driver:
            self.driver.quit()
