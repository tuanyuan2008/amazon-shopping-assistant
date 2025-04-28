from typing import Dict, List, Optional
import openai
import logging
import json
from .utils.config import Config

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)

    def parse_query(self, user_query: str) -> Dict:
        """
        Parse a natural language shopping query into structured data.
        
        Args:
            user_query (str): Natural language shopping request
            
        Returns:
            Dict: Structured query information
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": (
                        "You are a shopping query parser. "
                        "Extract the search term, price range, and other preferences from the user's query. "
                        "Respond ONLY with a valid JSON object in this format: "
                        "{"
                        "\"search_term\": string, "
                        "\"filters\": {\"price_max\": number, \"price_min\": number, \"prime\": boolean}, "
                        "\"preferences\": {\"min_rating\": number, \"min_reviews\": integer, \"features\": [string]}"
                        "}"
                    )},
                    {"role": "user", "content": user_query}
                ],
            )
            content = response.choices[0].message.content
            self.logger.info(f"Parsed query data: {content}")
            try:
                parsed_data = json.loads(content)
            except Exception:
                parsed_data = {"raw": content}
            return parsed_data
        except Exception as e:
            self.logger.error(f"Error parsing query: {str(e)}")
            raise

    def parse_follow_up(self, follow_up_query: str, previous_context: Dict) -> Dict:
        """
        Parse a follow-up query in the context of previous search results.
        
        Args:
            follow_up_query (str): Follow-up question or refinement
            previous_context (Dict): Context from previous interaction
            
        Returns:
            Dict: Structured refinement information
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a shopping query parser. Analyze the follow-up query in the context of previous search results. Respond ONLY with a valid JSON object in this format: {"
                    "\"refinements\": {\"price_max\": number, \"price_min\": number, \"min_rating\": number, \"prime_only\": boolean, \"features\": [string]}, "
                    "\"comparison\": boolean"
                    "}"},
                    {"role": "user", "content": f"Previous search: {previous_context['query']}\nFollow-up: {follow_up_query}"}
                ],
            )
            content = response.choices[0].message.content
            self.logger.info(f"Parsed follow-up data: {content}")
            try:
                parsed_data = json.loads(content)
            except Exception:
                parsed_data = {"raw": content}
            return parsed_data
        except Exception as e:
            self.logger.error(f"Error parsing follow-up: {str(e)}")
            raise

    def rank_products(self, products: List[Dict], preferences: Dict) -> List[Dict]:
        """
        Rank products based on user preferences and product information.
        
        Args:
            products (List[Dict]): List of product information dictionaries
            preferences (Dict): User preferences for ranking
            
        Returns:
            List[Dict]: Ranked list of products
        """
        try:
            scored_products = []
            for product in products:
                score = self._calculate_product_score(product, preferences)
                scored_products.append({
                    **product,
                    'score': score
                })
            
            ranked_products = sorted(scored_products, key=lambda x: x['score'], reverse=True)
            return ranked_products
            
        except Exception as e:
            self.logger.error(f"Error ranking products: {str(e)}")
            raise

    def _calculate_product_score(self, product: Dict, preferences: Dict) -> float:
        """Calculate a score for a product based on preferences."""
        score = 0.0
        
        # Price scoring (lower is better)
        if product.get('price') and preferences.get('price_max'):
            price_ratio = min(product['price'] / preferences['price_max'], 1.0)
            score += (1 - price_ratio) * 0.3
        
        # Rating scoring
        if product.get('rating'):
            if preferences.get('min_rating'):
                if product['rating'] >= preferences['min_rating']:
                    score += (product['rating'] / 5) * 0.4
            else:
                score += (product['rating'] / 5) * 0.4
        
        # Review count scoring
        if product.get('review_count'):
            score += min(product['review_count'] / 1000, 1.0) * 0.2
        
        # Prime bonus
        if product.get('prime'):
            score += 0.1
        
        return score 