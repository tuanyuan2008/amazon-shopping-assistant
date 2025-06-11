import time
import random
import logging

class RateLimiter:
    def __init__(self, max_requests_per_minute: int, request_delay_min: float, request_delay_max: float):
        self.max_requests_per_minute = max_requests_per_minute
        self.request_delay_min = request_delay_min
        self.request_delay_max = request_delay_max
        self.request_times = []
        self.logger = logging.getLogger(__name__)

    def wait(self) -> None:
        """Wait for an appropriate amount of time before making a request."""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # If we've reached the rate limit, wait until the oldest request is 1 minute old
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                self.logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        # Add random delay between requests
        random_delay = random.uniform(self.request_delay_min, self.request_delay_max)
        time.sleep(random_delay)
        
        # Record this request
        self.request_times.append(time.time())

    def reset(self) -> None:
        """Reset the request history."""
        self.request_times = [] 