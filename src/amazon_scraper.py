from datetime import date
from typing import Dict, List, Optional
import dateparser
import logging
import re
from playwright.sync_api import sync_playwright, Playwright, Browser, Page
from bs4 import BeautifulSoup

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

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.driver: Optional[Page] = None

    def _ensure_playwright_setup(self) -> None:
        """Initialize Playwright, launch browser, and create a new page if not already done."""
        if self.driver:
            self.logger.info("Playwright setup already complete. Skipping re-initialization.")
            return

        self.logger.info("Performing Playwright setup...")
        try:
            self.playwright = sync_playwright().start()

            # More aggressive arguments for headless browser to reduce memory usage
            chromium_args = [
                "--no-sandbox", # Crucial for Docker environments
                "--disable-setuid-sandbox",
                "--disable-gpu", # Often helps with stability
                "--disable-dev-shm-usage", # Important for limited /dev/shm
                "--single-process", # Runs all tabs in one process (can be risky but saves memory)
                "--disable-blink-features=AutomationControlled",
                "--disable-features=site-per-process",
                "--disable-site-isolation-trials",
                "--incognito", # Start in incognito mode to avoid caching issues
            ]

            self.logger.info(f"Attempting to launch Chromium with headless={self.config.HEADLESS_MODE} (Type: {type(self.config.HEADLESS_MODE)})")

            # Let Playwright find its own executable path, as it's installed via Dockerfile
            self.browser = self.playwright.chromium.launch(
                headless=self.config.HEADLESS_MODE,
                args=chromium_args,
                # executable_path is no longer explicitly set here
            )

            user_agent = self.config.USER_AGENT if self.config.USER_AGENT else None
            self.driver = self.browser.new_page(user_agent=user_agent)
            self.driver.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("Playwright setup complete.")

        except Exception as e:
            self.logger.error(f"Error during Playwright setup: {e}", exc_info=True)
            if self.browser:
                try:
                    self.browser.close()
                except Exception as close_e:
                    self.logger.error(f"Error closing browser during setup failure: {close_e}")
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as stop_e:
                    self.logger.error(f"Error stopping Playwright during setup failure: {stop_e}")
            self.playwright = None
            self.browser = None
            self.driver = None
            raise


    def _get_page_results(self, page: int, first_url: Optional[str] = None) -> List[Dict]:
        """Get results from the current page."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self.driver.wait_for_selector("[data-component-type='s-search-result']", timeout=10000)
            except Exception as e:
                self.logger.warning(f"Timeout waiting for page results selector on page {page}, attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    self.driver.reload()
                    continue
                else:
                    self.logger.error(f"Failed to load page {page} after multiple retries.")
                    return []
            
            page_results = self._extract_products()
            
            if not page_results:
                self.logger.info("No results found on this page")
                return []
            
            if first_url and page_results and page_results[0]['url'] == first_url:
                if attempt < max_retries - 1:
                    self.logger.info(f"Page {page} not fully loaded, retrying... (attempt {attempt + 1}/{max_retries})")
                    self.driver.reload()
                    continue
                else:
                    self.logger.info("Page not loading properly after retries")
                    return []
            
            return page_results
        
        return []

    def search_products(self, query: str, filters: Dict, max_results: int = 96) -> List[Dict]:
        """Search Amazon for products using a keyword and filter dict."""
        self._ensure_playwright_setup()

        if not self.driver:
            self.logger.error("Playwright driver not initialized. Cannot perform search.")
            return []

        try:
            url = self._construct_search_url(query, filters)
            self.logger.info(f"Searching Amazon: {url}")
            self.driver.goto(url)
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

                self.driver.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.rate_limiter.wait()

                next_button_handle = None
                for selector in ["a.s-pagination-next", "a[href*='page=']"]:
                    button_handles = self.driver.query_selector_all(selector)
                    for handle in button_handles:
                        class_attr = handle.get_attribute("class") or ""
                        if "s-pagination-disabled" not in class_attr:
                            next_button_handle = handle
                            break
                    if next_button_handle:
                        break

                if not next_button_handle:
                    self.logger.info("No more results available (next button not found or disabled)")
                    break

                next_url = next_button_handle.get_attribute("href")
                if next_url:
                    if next_url.startswith('/'):
                        next_url = f"{self.config.AMAZON_BASE_URL}{next_url}"
                    self.driver.goto(next_url, wait_until="domcontentloaded", timeout=60000)
                    page += 1
                    self.rate_limiter.wait()
                else:
                    self.logger.info("Next button found but no href attribute.")
                    break

            self.logger.info(f"Found {len(results)} products total")
            return results
        except Exception as e:
            self.logger.error("Search failed:", exc_info=True)
            return []

    def _construct_search_url(self, query: str, filters: Dict) -> str:
        """Build an Amazon search URL based on filters."""
        base_url = self.config.AMAZON_BASE_URL
        query_param = f"k={query.replace(' ', '+')}"
        rh_parts = []

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
        soup = BeautifulSoup(self.driver.content(), 'html.parser')
        results = []

        for item in soup.select("[data-component-type='s-search-result']"):
            try:
                if item.select_one("span.puis-label-popover-default"):
                    continue

                title = None
                for selector in [
                    "h2 a span",
                    ".a-size-base-plus.a-color-base",
                    ".a-size-medium.a-color-base",
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
                self.logger.error("Product extraction failed:", exc_info=True)
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
        """
        Extract the earliest delivery date (as a date object) from a delivery estimate string in the element.
        Handles phrases like 'Get it by...', 'Arrives...', 'FREE delivery...', etc.
        """
        text = ""
        try:
            text = element.get_text(separator=" ", strip=True)
            date_matches = re.findall(r"(today|tomorrow|[A-Z][a-z]+ \d{1,2})", text, re.IGNORECASE)

            if not date_matches:
                return None

            parsed_dates = [dateparser.parse(d, settings={"PREFER_DATES_FROM": "future", "STRICT_PARSING": False}) for d in date_matches]

            valid_dates = [d.date() for d in parsed_dates if d]

            if not valid_dates:
                return None

            return min(valid_dates)

        except Exception as e:
            self.logger.error(f"Delivery date extraction failed for text snippet: '{text[:100]}...'", exc_info=True)
            return None

    def _extract_inline_unit_price(self, element) -> Optional[str]:
        try:
            text = element.get_text(separator=" ", strip=True)
            match = re.search(r"\$([\d\.]+)\s*/\s*(\w+)", text)
            return f"${match.group(1)} per {match.group(2)}" if match else None
        except Exception as e:
            self.logger.error("Unit price extraction failed:", exc_info=True)
            return None

    def _is_prime(self, element) -> bool:
        return bool(element.select_one("i.a-icon-prime"))

    def _extract_url(self, element) -> Optional[str]:
        href = element.select_one("a.a-link-normal")["href"]
        return self.config.AMAZON_BASE_URL + href

    def _extract_image_url(self, element) -> Optional[str]:
        return element.select_one("img.s-image")["src"]

    def close(self):
        """Shut down the Playwright browser and Playwright instance."""
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                self.logger.warning(f"Error closing Playwright page: {e}")
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                self.logger.warning(f"Error closing Playwright browser: {e}")
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping Playwright: {e}")
        self.logger.info("Playwright resources closed.")
        self.driver = None
        self.browser = None
        self.playwright = None
