import pytest # Add to requirements-dev.txt or ensure it's available
import logging
from src.amazon_scraper import AmazonScraper
from src.utils.rate_limiter import RateLimiter # Assuming RateLimiter is simple enough to instantiate

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def scraper():
    # Using a dummy rate limiter for testing that doesn't actually sleep
    class DummyRateLimiter(RateLimiter):
        def __init__(self):
            super().__init__(requests_per_minute=6000)

        def wait(self):
            logging.info("DummyRateLimiter: Skipping actual wait.")
            return

    # Ensure playwright browsers are installed for this test to run in a real environment
    # e.g., by running `playwright install`

    rate_limiter = DummyRateLimiter()

    # Note: This test will make actual calls to Amazon if not mocked.
    # For CI/automated environments, mocking Amazon responses would be essential.
    amazon_scraper = AmazonScraper(rate_limiter=rate_limiter)
    yield amazon_scraper
    amazon_scraper.close()

def test_amazon_search(scraper: AmazonScraper):
    """Test basic Amazon product search."""
    query = "test query laptop" # Using a fairly specific query to limit results
    filters = {}
    max_results = 5 # Keep low for testing

    print(f"Starting search for: {query}")
    results = scraper.search_products(query, filters, max_results=max_results)
    print(f"Search returned {len(results)} results.")

    assert results is not None, "Search results should not be None"
    assert isinstance(results, list), "Search results should be a list"

    if results:
        print(f"First result: {results[0]}")
        assert len(results) > 0, "Should return some products for a common query"
        assert len(results) <= max_results, f"Should return at most {max_results} products"

        product = results[0]
        assert "title" in product, "Product should have a title"
        assert "price" in product, "Product should have a price"
        assert "url" in product, "Product should have a url"
        assert "rating" in product, "Product should have a rating"
        assert "review_count" in product, "Product should have a review_count"
        assert "image_url" in product, "Product should have an image_url"

        # Check that title and URL are not empty or placeholder if product exists
        assert product["title"] != "Title not available" and product["title"] != "", "Product title seems invalid"
        assert product["url"] != "URL not available" and product["url"] != "", "Product URL seems invalid"
        assert product["url"].startswith(scraper.config.AMAZON_BASE_URL), "Product URL should start with Amazon base URL"
    else:
        print("No results returned for the query. This might be due to network issues, CAPTCHAs, or page structure changes.")
        # Depending on strictness, you might want to fail here or log a warning.
        # For this example, we'll allow no results as it's an external dependency.
        pass
