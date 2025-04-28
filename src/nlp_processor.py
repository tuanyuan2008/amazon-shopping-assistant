from typing import Dict, List, Optional
import openai
import logging
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
            # Use OpenAI to parse the query
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a shopping query parser. Extract the search term, price range, and other preferences from the user's query."},
                    {"role": "user", "content": user_query}
                ],
                functions=[
                    {
                        "name": "parse_shopping_query",
                        "description": "Parse a shopping query into structured data",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "search_term": {
                                    "type": "string",
                                    "description": "The main product or category being searched for"
                                },
                                "filters": {
                                    "type": "object",
                                    "properties": {
                                        "price_max": {
                                            "type": "number",
                                            "description": "Maximum price in dollars"
                                        },
                                        "price_min": {
                                            "type": "number",
                                            "description": "Minimum price in dollars"
                                        },
                                        "prime": {
                                            "type": "boolean",
                                            "description": "Whether Prime shipping is required"
                                        }
                                    }
                                },
                                "preferences": {
                                    "type": "object",
                                    "properties": {
                                        "min_rating": {
                                            "type": "number",
                                            "description": "Minimum rating out of 5"
                                        },
                                        "min_reviews": {
                                            "type": "integer",
                                            "description": "Minimum number of reviews"
                                        },
                                        "features": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "Desired product features"
                                        }
                                    }
                                }
                            },
                            "required": ["search_term"]
                        }
                    }
                ],
                function_call={"name": "parse_shopping_query"}
            )
            
            # Extract the parsed data
            parsed_data = response.choices[0].message.function_call.arguments
            self.logger.info(f"Parsed query data: {parsed_data}")
            
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
            # Use OpenAI to parse the follow-up query
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a shopping query parser. Analyze the follow-up query in the context of previous search results."},
                    {"role": "user", "content": f"Previous search: {previous_context['query']}\nFollow-up: {follow_up_query}"}
                ],
                functions=[
                    {
                        "name": "parse_follow_up",
                        "description": "Parse a follow-up shopping query",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "refinements": {
                                    "type": "object",
                                    "properties": {
                                        "price_max": {
                                            "type": "number",
                                            "description": "New maximum price in dollars"
                                        },
                                        "price_min": {
                                            "type": "number",
                                            "description": "New minimum price in dollars"
                                        },
                                        "min_rating": {
                                            "type": "number",
                                            "description": "New minimum rating out of 5"
                                        },
                                        "prime_only": {
                                            "type": "boolean",
                                            "description": "Whether to show only Prime items"
                                        },
                                        "features": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "New desired features"
                                        }
                                    }
                                },
                                "comparison": {
                                    "type": "boolean",
                                    "description": "Whether the user wants to compare products"
                                }
                            }
                        }
                    }
                ],
                function_call={"name": "parse_follow_up"}
            )
            
            # Extract the parsed data
            parsed_data = response.choices[0].message.function_call.arguments
            self.logger.info(f"Parsed follow-up data: {parsed_data}")
            
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
            # Calculate scores for each product
            scored_products = []
            for product in products:
                score = self._calculate_product_score(product, preferences)
                scored_products.append({
                    **product,
                    'score': score
                })
            
            # Sort products by score
            ranked_products = sorted(scored_products, key=lambda x: x['score'], reverse=True)
            return ranked_products
            
        except Exception as e:
            self.logger.error(f"Error ranking products: {str(e)}")
            raise

    def _calculate_product_score(self, product: Dict, preferences: Dict) -> float:
        """Calculate a score for a product based on preferences."""
        score = 0.0
        
        # Price scoring (lower is better)
        if product['price'] and preferences.get('price_max'):
            price_ratio = min(product['price'] / preferences['price_max'], 1.0)
            score += (1 - price_ratio) * 0.3
        
        # Rating scoring
        if product['rating']:
            if preferences.get('min_rating'):
                if product['rating'] >= preferences['min_rating']:
                    score += (product['rating'] / 5) * 0.4
            else:
                score += (product['rating'] / 5) * 0.4
        
        # Review count scoring
        if product['review_count']:
            score += min(product['review_count'] / 1000, 1.0) * 0.2
        
        # Prime bonus
        if product['prime']:
            score += 0.1
        
        return score 