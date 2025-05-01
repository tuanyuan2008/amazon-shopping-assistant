import re
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional
import holidays
import openai
import dateparser
from .utils.config import Config
from .models import ParsedQuery

class DateHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.date_parser_settings = {
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now(),
            'RETURN_AS_TIMEZONE_AWARE': False,
            'SKIP_TOKENS': [],
        }

        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.prompt_dir = Path(__file__).parent / 'prompts'

    def _get_date_parser_prompt(self, year: int) -> str:
        prompt_path = self.prompt_dir / 'date_parser.txt'
        with open(prompt_path) as f:
            return f.read().format(year=year)

    def _parse_date_with_llm(self, date_str: str, year: int) -> Optional[date]:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_date_parser_prompt(year)},
                    {"role": "user", "content": date_str}
                ],
                temperature=0
            )
            result = response.choices[0].message.content.strip()
            if result.lower() == 'none':
                return None
            return datetime.strptime(result, '%Y-%m-%d').date()
        except Exception as e:
            self.logger.warning(f"Error parsing date with GPT: {e}")
            return None

    def parse_date(self, date_input, use_gpt: bool = False) -> Optional[date]:
        if not date_input:
            return None

        if isinstance(date_input, date):
            return date_input
        if isinstance(date_input, datetime):
            return date_input.date()
        if not isinstance(date_input, str):
            self.logger.warning(f"Expected str/date input, got: {type(date_input)}")
            return None

        date_str = date_input.strip().lower()
        current_year = datetime.now().year

        # 1. Check built-in U.S. holidays
        us_holidays = holidays.country_holidays("US", years=current_year)
        for holiday_date, name in us_holidays.items():
            if date_str in name.lower():
                return holiday_date

        # 2. Try parsing directly
        parsed = dateparser.parse(date_str, settings=self.date_parser_settings)
        if parsed:
            return parsed.date()

        # 3. Fallback to GPT if enabled
        if use_gpt:
            return self._parse_date_with_llm(date_str, current_year)
        return None

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)
        self.date_handler = DateHandler()
        self.prompt_dir = Path(__file__).parent / 'prompts'

    def _get_parser_prompt(self, is_follow_up: bool = False) -> str:
        """Get the appropriate system prompt for parsing queries."""
        base_prompt_path = self.prompt_dir / 'query_parser.txt'
        with open(base_prompt_path) as f:
            base_prompt = f.read()

        if is_follow_up:
            follow_up_path = self.prompt_dir / 'query_parser_follow_up.txt'
            with open(follow_up_path) as f:
                return base_prompt + f.read()
        else:
            search_term_path = self.prompt_dir / 'query_parser_search_term.txt'
            with open(search_term_path) as f:
                return base_prompt + f.read()

    def _parse_with_llm(self, prompt: str, user_input: str, model_class) -> Dict:
        """Common method to parse queries using the LLM."""
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
        """Parse a shopping query into structured filters and preferences."""
        prompt = self._get_parser_prompt(is_follow_up=False)
        return self._parse_with_llm(prompt, user_query, ParsedQuery)

    def parse_follow_up(self, follow_up_query: str, previous_context: Dict) -> Dict:
        """Parse a follow-up query in the context of previous search results."""
        prompt = self._get_parser_prompt(is_follow_up=True)
        user_input = f"Previous search: {previous_context.get('query', '')}\nFollow-up: {follow_up_query}"
        result = self._parse_with_llm(prompt, user_input, ParsedQuery)
        if result:
            result["comparison"] = True  # Mark as comparison since it's a follow-up
        return result

    def rank_products(self, products: List[Dict], filters: Dict, preferences: Dict) -> List[Dict]:
        """
        Rank products based on user filters and preferences.
        """
        try:
            scored_products = []
            for product in products:
                score, explanation = self._calculate_product_score(product, filters, preferences)
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

    def _calculate_product_score(self, product: Dict, filters: Dict, preferences: Dict) -> tuple[float, str]:
        """Calculate a score for a product based on filters and preferences and product information."""
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
        if product.get('price') and filters.get('price_max'):
            try:
                price = float(product['price'].replace('$', '').replace(',', ''))
                if price > filters['price_max']:
                    explanations.append(f"Price score: 0 (product price ${price} exceeds maximum price ${filters['price_max']})")
                else:
                    price_ratio = min(price / filters['price_max'], 1.0)
                    price_score = (1 - price_ratio) * weights['price']
                    score += price_score
                    explanations.append(f"Price score: {price_score:.2f} (product price ${price} vs maximum price ${filters['price_max']})")
            except (ValueError, TypeError):
                explanations.append("Price score: 0 (invalid price format)")
        
        # Rating scoring
        if product.get('rating'):
            try:
                rating = float(product['rating'].split(' ')[0])
                if filters.get('min_rating'):
                    if rating < filters['min_rating']:
                        explanations.append(f"Rating score: 0 (rating {rating}/5 below minimum {filters['min_rating']})")
                    else:
                        rating_score = (rating / 5) * weights['rating']
                        score += rating_score
                        explanations.append(f"Rating score: {rating_score:.2f} ({rating}/5 stars, meets minimum {filters['min_rating']})")
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
                if filters.get('min_reviews'):
                    if review_count < filters['min_reviews']:
                        explanations.append(f"Review count score: 0 ({review_count} reviews below minimum {filters['min_reviews']})")
                    else:
                        review_score = min(review_count / 1000, 1.0) * weights['reviews']
                        score += review_score
                        explanations.append(f"Review count score: {review_score:.2f} ({review_count} reviews, meets minimum {filters['min_reviews']})")
                else:
                    review_score = min(review_count / 1000, 1.0) * weights['reviews']
                    score += review_score
                    explanations.append(f"Review count score: {review_score:.2f} ({review_count} reviews)")
            except (ValueError, TypeError):
                explanations.append("Review count score: 0 (no reviews)")
        
        # Delivery time scoring
        if product.get('delivery_estimate') and filters.get('deliver_by'):
            delivery_score = self._calculate_delivery_score(product['delivery_estimate'], filters['deliver_by'])
            if delivery_score == 0:
                actual_date = self.date_handler.parse_date(product['delivery_estimate'])
                target_date = self.date_handler.parse_date(filters['deliver_by'])
                explanations.append(f"Delivery score: 0 ({actual_date} does not meet delivery deadline {target_date})")
            else:
                score += delivery_score * weights['delivery']
                explanations.append(f"Delivery score: {delivery_score:.2f}")
        else:
            explanations.append("Delivery score: 0 (no delivery estimate or delivery deadline)")
        
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

    def _calculate_delivery_score(self, delivery_estimate: str, deliver_by: str) -> float:
        """Score based on whether delivery meets the user's deadline."""
        try:
            if not deliver_by or not delivery_estimate:
                return 0.0

            target_date = self.date_handler.parse_date(deliver_by)
            actual_date = self.date_handler.parse_date(delivery_estimate)

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