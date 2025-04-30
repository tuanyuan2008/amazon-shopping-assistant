import re
from typing import Dict, List, Optional
import openai
import logging
import dateparser
from .utils.config import Config
from .models import ParsedQuery, ParsedFollowUp

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)

    def resolve_deliver_by(self, user_phrase: str) -> Optional[str]:
        """
        Uses ChatGPT to normalize delivery requests like 'before Mother's Day' or 'by Friday'
        into: 'today', 'tomorrow', 'in 2 days', or a concrete date like 'May 11'.
        """
        try:
            prompt = (
                "You are a delivery date normalizer. Convert the user's delivery timing request "
                "into a normalized delivery constraint. Only respond with:\n"
                "- 'today'\n- 'tomorrow'\n- 'in N days'\n- A date like 'May 11'\n- A holiday name (e.g. 'Mother's Day')\n\n"
                f"User input: {user_phrase}"
            )

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                temperature=0
            )

            return response.choices[0].message.content.strip().lower()

        except Exception as e:
            self.logger.warning(f"Failed to resolve deliver_by: {e}")
            return user_phrase  # fallback to original


    def parse_query(self, user_query: str) -> Dict:
        """
        Parse a shopping query into structured filters and preferences.
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a shopping query parser. Extract structured information from natural language shopping requests. "
                            "For features, identify specific product attributes, materials, brands, colors, sizes, and other distinguishing characteristics. "
                            "Respond ONLY with a valid JSON object in the following format:\n"
                            "{\n"
                            "  \"search_term\": string,                     // the core product name or keyword\n"
                            "  \"filters\": {\n"
                            "    \"price_max\": number,                    // optional, max price\n"
                            "    \"price_min\": number,                    // optional, min price\n"
                            "    \"prime\": boolean,                       // whether the user requested Prime shipping\n"
                            "    \"min_rating\": number,                   // optional, minimum acceptable rating (e.g. 4.0)\n"
                            "    \"sort_by\": string,                      // one of: 'price-asc-rank', 'price-desc-rank', 'review-rank', 'date-desc-rank', 'relevanceblender'\n"
                            "    \"deliver_by\": string                    // optional, one of: 'today', 'tomorrow', 'in 2 days'\n"
                            "  },\n"
                            "  \"preferences\": {\n"
                            "    \"min_reviews\": number,                  // optional, minimum number of reviews\n"
                            "    \"features\": [string]                    // list of desired features (brands, materials, colors, sizes, etc.)\n"
                            "  }\n"
                            "}"
                        )
                    },
                    {
                        "role": "user",
                        "content": user_query
                    }
                ],
                temperature=0
            )

            content = response.choices[0].message.content
            self.logger.info(f"Parsed query raw output:\n{content}")

            parsed = ParsedQuery.parse_raw(content)

            # Post-process deliver_by
            if parsed.filters.deliver_by:
                parsed.filters.deliver_by = self.resolve_deliver_by(parsed.filters.deliver_by)

            return parsed.dict()

        except Exception as e:
            self.logger.error(f"Error parsing query: {e}")
            return {
                "search_term": user_query,
                "filters": {},
                "preferences": {}
            }


    def parse_follow_up(self, follow_up_query: str, previous_context: Dict) -> Dict:
        """
        Parse a follow-up query in the context of previous search results.
        
        Note: Features are intentionally not included in follow-up parsing because:
        - The initial query (parse_query) already extracts all desired product features
        - Follow-ups are for refining search criteria (price, rating, delivery, etc.), not adding new features
        - If a user wants different features, they should start a new search rather than modifying the existing one
        - This keeps product scoring consistent throughout the conversation using the original feature set

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
                    {
                        "role": "system",
                        "content": (
                            "You are a shopping query parser. Analyze the follow-up query in the context of previous search results. "
                            "Respond ONLY with a valid JSON object in the following format:\n"
                            "{\n"
                            "  \"filters\": {\n"
                            "    \"price_max\": number,\n"
                            "    \"price_min\": number,\n"
                            "    \"min_rating\": number,\n"
                            "    \"prime\": boolean,\n"
                            "    \"sort_by\": string,\n"
                            "    \"deliver_by\": string\n"
                            "  },\n"
                            "  \"preferences\": {\n"
                            "    \"min_reviews\": number                  // optional, minimum number of reviews\n"
                            "  },\n"
                            "  \"comparison\": boolean\n"
                            "}"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Previous search: {previous_context.get('query', '')}\nFollow-up: {follow_up_query}"
                    }
                ],
                temperature=0
            )

            content = response.choices[0].message.content
            self.logger.info(f"Parsed follow-up output:\n{content}")

            parsed = ParsedFollowUp.parse_raw(content)

            # Normalize deliver_by if present
            if parsed.filters.deliver_by:
                parsed.filters.deliver_by = self.resolve_deliver_by(parsed.filters.deliver_by)

            return parsed.dict()

        except Exception as e:
            self.logger.error(f"Error parsing follow-up: {e}")
            return {
                "filters": {},
                "preferences": {},
                "comparison": False
            }


    def rank_products(self, products: List[Dict], preferences: Dict) -> List[Dict]:
        """
        Rank products based on user preferences and product information.
        
        Args:
            products (List[Dict]): List of product information dictionaries
            preferences (Dict): User preferences for ranking
            
        Returns:
            List[Dict]: Ranked list of products with ranking explanations
        """
        try:
            scored_products = []
            for product in products:
                score, explanation = self._calculate_product_score(product, preferences)
                scored_products.append({
                    **product,
                    'score': score,
                    'ranking_explanation': explanation
                })
            
            ranked_products = sorted(scored_products, key=lambda x: x['score'], reverse=True)
            return ranked_products
            
        except Exception as e:
            self.logger.error(f"Error ranking products: {str(e)}")
            raise

    def _calculate_product_score(self, product: Dict, preferences: Dict) -> tuple[float, str]:
        """Calculate a score for a product based on preferences and product information."""
        score = 0.0
        explanations = []
        
        # Fixed weights for different scoring components
        weights = {
            'preference_match': 0.3,  # Feature matching is important
            'price': 0.3,            # Price is equally important
            'rating': 0.2,           # Rating is important but not critical
            'reviews': 0.1,          # Review count is a nice to have
            'delivery': 0.1          # Delivery timing is a nice to have
        }
        
        # Preference matching using Jaccard similarity
        preference_score = self._calculate_preference_similarity(product, preferences)
        score += preference_score * weights['preference_match']
        explanations.append(f"Preference match score: {preference_score:.2f}")
        
        # Price scoring (lower is better)
        if product.get('price') and preferences.get('price_max'):
            try:
                price = float(product['price'].replace('$', '').replace(',', ''))
                price_ratio = min(price / preferences['price_max'], 1.0)
                price_score = (1 - price_ratio) * weights['price']
                score += price_score
                explanations.append(f"Price score: {price_score:.2f} (${price} vs max ${preferences['price_max']})")
            except (ValueError, TypeError):
                explanations.append("Price score: 0 (invalid price format)")
        
        # Rating scoring
        if product.get('rating'):
            try:
                rating = float(product['rating'].split(' ')[0])
                if preferences.get('min_rating'):
                    if rating >= preferences['min_rating']:
                        rating_score = (rating / 5) * weights['rating']
                        score += rating_score
                        explanations.append(f"Rating score: {rating_score:.2f} ({rating}/5 stars, meets minimum {preferences['min_rating']})")
                    else:
                        explanations.append(f"Rating score: 0 (rating {rating}/5 below minimum {preferences['min_rating']})")
                else:
                    rating_score = (rating / 5) * weights['rating']
                    score += rating_score
                    explanations.append(f"Rating score: {rating_score:.2f} ({rating}/5 stars)")
            except (ValueError, TypeError):
                explanations.append("Rating score: 0 (invalid rating format)")
        
        # Review count scoring
        if product.get('review_count'):
            try:
                review_count = int(product['review_count'].replace(',', ''))
                review_score = min(review_count / 1000, 1.0) * weights['reviews']
                score += review_score
                explanations.append(f"Review count score: {review_score:.2f} ({review_count} reviews)")
            except (ValueError, TypeError):
                explanations.append("Review count score: 0 (no reviews)")
        
        # Delivery time scoring using AmazonScraper's normalization
        if product.get('delivery_estimate'):
            delivery_score = self._calculate_delivery_score(product['delivery_estimate'], preferences)
            score += delivery_score * weights['delivery']
            explanations.append(f"Delivery score: {delivery_score:.2f}")
        
        # Combine all explanations
        explanation = "\n".join(explanations)
        explanation += f"\nTotal score: {score:.2f}"
        
        return score, explanation

    def _calculate_preference_similarity(self, product: Dict, preferences: Dict) -> float:
        """Calculate Jaccard similarity between product title tokens and preference features."""
        try:
            # Tokenize product title
            title = product.get('title', '')
            product_features = set(re.findall(r'\w+', title.lower()))

            # Tokenize preference features
            preference_features = set()
            if preferences.get('features'):
                for feature in preferences['features']:
                    preference_features.update(re.findall(r'\w+', feature.lower()))

            if not preference_features:
                self.logger.debug("No user preference features provided.")
                return 0.0

            if not product_features:
                self.logger.debug("No product features extracted.")
                return 0.0

            intersection = product_features & preference_features
            union = product_features | preference_features
            return len(intersection) / len(union) if union else 0.0

        except Exception as e:
            self.logger.warning(f"Error calculating preference similarity: {e}")
            return 0.0

    def _calculate_delivery_score(self, delivery_estimate: str, preferences: Dict) -> float:
        """Score based on whether delivery meets the user's deadline."""
        try:
            deliver_by = preferences.get('deliver_by', '')
            if not deliver_by or not delivery_estimate:
                return 0.0

            target_date = dateparser.parse(deliver_by)
            actual_date = dateparser.parse(delivery_estimate)

            if not target_date or not actual_date:
                self.logger.debug(f"Could not parse delivery dates: target='{deliver_by}', estimate='{delivery_estimate}'")
                return 0.0

            if actual_date <= target_date:
                return 1.0

            # Partial score: inversely proportional to how late it is
            days_late = (actual_date - target_date).days
            return max(0.0, 1.0 / (days_late + 1))

        except Exception as e:
            self.logger.warning(f"Error calculating delivery score: {e}")
            return 0.0