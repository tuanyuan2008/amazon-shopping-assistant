from typing import Dict, List, Optional
import logging
from datetime import datetime

from .amazon_scraper import AmazonScraper
from .nlp_processor import NLPProcessor
from .utils.rate_limiter import RateLimiter
from .utils.config import Config

class ShoppingAssistant:
    def __init__(self):
        self.config = Config()
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=self.config.MAX_REQUESTS_PER_MINUTE,
            request_delay_min=self.config.REQUEST_DELAY_MIN,
            request_delay_max=self.config.REQUEST_DELAY_MAX
        )
        self.scraper = AmazonScraper(self.rate_limiter)
        self.nlp_processor = NLPProcessor()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def process_request(self, user_query: str) -> Dict:
        """
        Process a user's shopping request and return relevant product information.
        
        Args:
            user_query (str): Natural language shopping request
            
        Returns:
            Dict: Structured response with product information and recommendations
        """
        try:
            # Parse the user's request using NLP
            parsed_query = self.nlp_processor.parse_query(user_query)
            self.logger.info(f"Parsed query: {parsed_query}")
            
            # Search for products on Amazon
            products = self.scraper.search_products(
                query=parsed_query['search_term'],
                filters=parsed_query['filters']
            )
            
            # Process and rank products
            ranked_products = self.nlp_processor.rank_products(
                products=products,
                preferences=parsed_query['preferences']
            )
            
            return {
                'status': 'success',
                'query': parsed_query,
                'products': ranked_products[:5],  # Return top 5 products
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def handle_follow_up(self, previous_context: Dict, follow_up_query: str) -> Dict:
        """
        Handle follow-up questions or refinements to the previous search.
        
        Args:
            previous_context (Dict): Context from the previous interaction
            follow_up_query (str): Follow-up question or refinement
            
        Returns:
            Dict: Updated response with refined product information
        """
        try:
            # Process the follow-up query
            parsed_follow_up = self.nlp_processor.parse_follow_up(
                follow_up_query,
                previous_context
            )
            
            # Refine the search based on the follow-up
            refined_products = self.scraper.refine_search(
                previous_products=previous_context['products'],
                refinements=parsed_follow_up['refinements']
            )
            
            return {
                'status': 'success',
                'query': parsed_follow_up,
                'products': refined_products,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error handling follow-up: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            } 