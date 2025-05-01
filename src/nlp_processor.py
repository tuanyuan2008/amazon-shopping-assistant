import re
from typing import Dict, List, Optional
import openai
import logging
import dateparser
from .utils.config import Config
from .models import ParsedQuery

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)

    def _get_parser_prompt(self, is_follow_up: bool = False) -> str:
        """
        Get the appropriate system prompt for parsing queries.
        """
        base_prompt = (
            "You are a shopping query parser. Extract structured information from natural language shopping requests. "
            "For features, identify specific product attributes, materials, brands, colors, sizes, and other distinguishing characteristics. "
            "Respond ONLY with a valid JSON object in the following format:\n"
            "{\n"
            "  \"search_term\": string,                     // the core product name or keyword, optimized with relevant preferences\n"
            "  \"filters\": {\n"
            "    \"price_max\": number,                    // optional, max price\n"
            "    \"price_min\": number,                    // optional, min price\n"
            "    \"prime\": boolean,                       // whether the user requested Prime shipping\n"
            "    \"min_rating\": number,                   // optional, minimum acceptable rating (e.g. 4.0)\n"
            "    \"min_reviews\": number,                  // optional, minimum number of reviews\n"
            "    \"sort_by\": string,                      // one of: 'price-asc-rank', 'price-desc-rank', 'review-rank', 'date-desc-rank', 'relevanceblender'\n"
            "    \"deliver_by\": string                    // optional, normalized to: 'today', 'tomorrow', 'in N days', a specific date like '2024-05-11', or a holiday name like 'Mother's Day'\n"
            "  },\n"
            "  \"preferences\": {\n"
            "    \"features\": [string]                    // list of desired features (brands, materials, colors, sizes, etc.)\n"
            "  }\n"
            "}\n\n"
            "For delivery dates, normalize them to one of these formats:\n"
            "- 'today' for same-day delivery\n"
            "- 'tomorrow' for next-day delivery\n"
            "- 'in N days' for future delivery (e.g., 'in 2 days')\n"
            "- A specific date in YYYY-MM-DD format (e.g., '2024-05-11')\n"
            "- A holiday name (e.g., 'Mother's Day', 'Christmas', 'Valentine's Day')\n"
            "For example:\n"
            "- 'by Friday' → 'in 2 days' (if today is Wednesday)\n"
            "- 'before Mother's Day' → 'Mother's Day'\n"
            "- 'next week' → 'in 7 days'\n"
            "- 'ASAP' → 'today'\n"
            "- 'by Christmas' → 'Christmas'\n"
        )

        if is_follow_up:
            return (
                base_prompt +
                "Analyze the follow-up query in the context of previous search results. "
                "You can modify any aspect of the search, including:\n"
                "- Adding or changing features (e.g., 'I want a black Nike backpack' after 'I want a bookbag')\n"
                "- Adjusting filters (e.g., 'Show me cheaper options')\n"
                "- Changing the search term (e.g., 'Actually, I want a messenger bag instead')\n"
                "For example:\n"
                "- If user asks 'Show me cheaper options', update price_max to the cheapest price found in the previous search\n"
                "- If user asks 'Only show items with 4+ stars', update min_rating to 4\n"
                "- If user asks 'I need it by tomorrow', update deliver_by to 'tomorrow'\n"
                "- If user asks 'Sort by price', update sort_by to 'price-asc-rank'\n"
                "- If user asks 'I want a black Nike backpack', update search_term and features\n"
                "Remember: The follow-up can modify any aspect of the search, not just filters."
            )
        else:
            return (
                base_prompt +
                "When generating the search_term, incorporate relevant preferences and features to improve search results. "
                "The search_term should be optimized for Amazon's search algorithm while maintaining the user's intent. "
                "For example:\n"
                "- If user asks 'Show me laptops under $1000 with 4+ stars', search_term should be 'laptop' (price and rating go to filters)\n"
                "- If user asks 'Find me the cheapest wireless earbuds with Prime delivery', search_term should be 'wireless earbuds' (Prime and sorting go to filters)\n"
                "- If user asks 'I need a gaming laptop with 16GB RAM and RTX 3080', search_term should be 'gaming laptop RTX 3080 16GB RAM'\n"
                "- If user asks 'Show me organic coffee beans with at least 1000 reviews', search_term should be 'organic coffee beans' (review count goes to filters)\n"
                "- If user asks 'I need a waterproof phone case for iPhone 13 that can arrive tomorrow', search_term should be 'iPhone 13 waterproof case' (delivery goes to filters)\n"
                "The features list should contain all relevant attributes that can be used for filtering and scoring."
            )

    def _parse_with_llm(self, prompt: str, user_input: str, model_class) -> Dict:
        """
        Common method to parse queries using the LLM.
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0
            )

            content = response.choices[0].message.content
            self.logger.info(f"Parsed output:\n{content}")

            parsed = model_class.parse_raw(content)
            return parsed.dict()

        except Exception as e:
            self.logger.error(f"Error parsing query: {e}")
            return {}

    def parse_query(self, user_query: str) -> Dict:
        """
        Parse a shopping query into structured filters and preferences.
        """
        prompt = self._get_parser_prompt(is_follow_up=False)
        return self._parse_with_llm(prompt, user_query, ParsedQuery)

    def parse_follow_up(self, follow_up_query: str, previous_context: Dict) -> Dict:
        """
        Parse a follow-up query in the context of previous search results.
        """
        prompt = self._get_parser_prompt(is_follow_up=True)
        user_input = f"Previous search: {previous_context.get('query', '')}\nFollow-up: {follow_up_query}"
        result = self._parse_with_llm(prompt, user_input, ParsedQuery)
        if result:
            result["comparison"] = True  # Mark as comparison since it's a follow-up
        return result

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
                if price > preferences['price_max']:
                    explanations.append(f"Price score: 0 (product price ${price} exceeds maximum price ${preferences['price_max']})")
                else:
                    price_ratio = min(price / preferences['price_max'], 1.0)
                    price_score = (1 - price_ratio) * weights['price']
                    score += price_score
                    explanations.append(f"Price score: {price_score:.2f} (product price ${price} vs maximum price ${preferences['price_max']})")
            except (ValueError, TypeError):
                explanations.append("Price score: 0 (invalid price format)")
        
        # Rating scoring
        if product.get('rating'):
            try:
                rating = float(product['rating'].split(' ')[0])
                if preferences.get('min_rating'):
                    if rating < preferences['min_rating']:
                        explanations.append(f"Rating score: 0 (rating {rating}/5 below minimum {preferences['min_rating']})")
                    else:
                        rating_score = (rating / 5) * weights['rating']
                        score += rating_score
                        explanations.append(f"Rating score: {rating_score:.2f} ({rating}/5 stars, meets minimum {preferences['min_rating']})")
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
                if preferences.get('min_reviews'):
                    if review_count < preferences['min_reviews']:
                        explanations.append(f"Review count score: 0 ({review_count} reviews below minimum {preferences['min_reviews']})")
                    else:
                        review_score = min(review_count / 1000, 1.0) * weights['reviews']
                        score += review_score
                        explanations.append(f"Review count score: {review_score:.2f} ({review_count} reviews, meets minimum {preferences['min_reviews']})")
                else:
                    review_score = min(review_count / 1000, 1.0) * weights['reviews']
                    score += review_score
                    explanations.append(f"Review count score: {review_score:.2f} ({review_count} reviews)")
            except (ValueError, TypeError):
                explanations.append("Review count score: 0 (no reviews)")
        
        # Delivery time scoring using AmazonScraper's normalization
        if product.get('delivery_estimate'):
            delivery_score = self._calculate_delivery_score(product['delivery_estimate'], preferences)
            if delivery_score == 0:
                explanations.append("Delivery score: 0 (does not meet delivery deadline)")
            else:
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