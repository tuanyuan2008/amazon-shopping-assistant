import re
import logging
import math
from datetime import datetime, date
from pathlib import Path
from scipy.special import expit
from scipy.stats import percentileofscore
from typing import Dict, List, Optional
import holidays
import openai
import dateparser
from .utils.config import Config
from .models import ParsedQuery

MISSING_SCORE = 0.15

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
        """Get the system prompt for parsing queries, formatted with current year."""
        current_year = datetime.now().year
        base_prompt = (self.prompt_dir / 'query_parser.txt').read_text().replace('CURRENT_YEAR', str(current_year))
        suffix = 'query_parser_follow_up.txt' if is_follow_up else 'query_parser_search_term.txt'
        suffix_prompt = (self.prompt_dir / suffix).read_text().replace('CURRENT_YEAR', str(current_year))
        return base_prompt + suffix_prompt

    def _parse_with_llm(self, prompt: str, user_input: str, model_class) -> Dict:
        """Parse input using the LLM."""
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )
        return model_class.parse_raw(response.choices[0].message.content).dict()

    def parse_query(self, user_query: str) -> Dict:
        """Parse a shopping query into structured filters and preferences."""
        return self._parse_with_llm(self._get_parser_prompt(False), user_query, ParsedQuery)

    def parse_follow_up(self, follow_up_query: str, previous_context: Dict) -> Dict:
        """Parse a follow-up query in the context of previous search results."""
        prompt = self._get_parser_prompt(True)

        # Exclude URL and image_url to conserve tokens
        shorthand_result = [
            {k: v for k, v in p.items() if k not in ['url', 'image_url']}
            for p in previous_context.get('results', [])
        ]
        
        user_input = (
            f"Previous search: {previous_context.get('query', '')}\n"
            f"Previous filters: {previous_context.get('filters', {})}\n"
            f"Previous preferences: {previous_context.get('preferences', {})}\n"
            f"Previous results: {shorthand_result}\n"
            f"Follow-up: {follow_up_query}"
        )

        result = self._parse_with_llm(prompt, user_input, ParsedQuery)
        if result:
            result["comparison"] = True
        return result

    def rank_products(self, products: List[Dict], filters: Dict, preferences: Dict) -> List[Dict]:
        scored = []
        for product in products:
            score, explanation = self._calculate_product_score(product, filters, preferences, products)
            scored.append({
                **product,
                "score": score,
                "ranking_explanation": explanation,
            })
        return sorted(scored, key=lambda x: x["score"], reverse=True)

    def _get_numeric_value(self, value: str) -> Optional[float]:
        if not value:
            return None
        try:
            if 'per' in value.lower():
                return float(value.split('per')[0].replace('$', '').replace(',', '').strip())
            return float(value.replace('$', '').replace(',', ''))
        except ValueError:
            return None

    def _calculate_product_score(
        self, 
        product: Dict, 
        filters: Dict, 
        preferences: Dict, 
        all_products: List[Dict]
    ) -> tuple[float, str]:
        components = {
            "preference": self._calculate_preference_score(product, preferences),
            "price": self._calculate_price_score(product, filters, all_products),
            "rating": self._calculate_rating_score(product, filters),
            "reviews": self._calculate_review_score(product, filters),
            "delivery": self._calculate_delivery_score(product, filters),
        }

        score = 1.0
        explanations = []
        for name, (sub_score, explanation) in components.items():
            explanations.append(f"- {explanation}")
            if sub_score == 0.0:
                score = 0.0
                explanations[-1] = f"- {name.title()} score: 0 (excluded due to hard requirement)"
                break
            score *= sub_score

        return score, "\n".join(explanations) + f"\nTotal score: {score:.4f}"

    def _calculate_preference_score(self, product: Dict, preferences: Dict) -> tuple[float, str]:
        product_tokens = set(re.findall(r'\w+', product.get('title', '').lower()))
        preference_tokens = set(re.findall(r'\w+', ' '.join(preferences.get('features', [])).lower()))
        if not preference_tokens or not product_tokens:
            return MISSING_SCORE, "Preference score: 0 (no tokens to compare)"
        similarity = len(product_tokens & preference_tokens) / len(product_tokens | preference_tokens)
        return similarity if similarity else MISSING_SCORE, f"Preference match score: {similarity:.2f}" # TODO: fix this
    

    def _get_unit_price_score(self, products: List[Dict], unit_price: float) -> float:
        prices = [p for p in (self._get_numeric_value(p.get('price_per_count', '')) for p in products) if p is not None]
        if not prices or unit_price is None:
            return MISSING_SCORE
        percentile = percentileofscore(prices, unit_price, kind='rank')
        return (100 - percentile) / 100

    def _calculate_price_score(self, product: Dict, filters: Dict, all_products: List[Dict]) -> tuple[float, str]:
        price = self._get_numeric_value(product.get('price', ''))
        raw_price_per_count = product.get('price_per_count', '')
        unit_price = self._get_numeric_value(raw_price_per_count)
        price_max = filters.get('price_max')
        
        if price is None:
            return MISSING_SCORE, f"Price score: {MISSING_SCORE} (no price found for product)"
        if price_max and price > price_max:
            return 0.0, f"Price score: 0 (price ${price} > max ${price_max})"
            
        score = self._get_unit_price_score(all_products, unit_price)
        return score, f"Price score: {score:.2f} (unit price: {raw_price_per_count if raw_price_per_count else 'N/A'})"

    def _calculate_rating_score(self, product: Dict, filters: Dict) -> tuple[float, str]:
        try:
            rating = float(product.get('rating', '0').split(' ')[0])
        except ValueError:
            return MISSING_SCORE, f"Rating score: {MISSING_SCORE} (no rating found for product)"
        if filters.get('min_rating') and rating < filters['min_rating']:
            return 0.0, f"Rating score: 0 (rating {rating} < min {filters['min_rating']})"
        rating_score = expit(5 * (rating - 4.23))
        return rating_score, f"Rating score: {rating_score:.2f} ({rating}/5 stars)"

    def _calculate_review_score(self, product: Dict, filters: Dict) -> tuple[float, str]:
        count = self._get_numeric_value(product.get('review_count', ''))
        if count is None:
            return MISSING_SCORE, f"Review count score: {MISSING_SCORE} (no reviews found for product)"
        if filters.get('min_reviews') and count < filters['min_reviews']:
            return 0.0, f"Review count score: 0 ({count} < min {filters['min_reviews']})"
        score = math.log10(min(count, 5000) + 1) / math.log10(5000) # TODO: consider large user inputs here
        return score, f"Review count score: {score:.2f} ({int(count)} reviews)"

    def _calculate_delivery_score(self, product: Dict, filters: Dict) -> tuple[float, str]:
        target = self.date_handler.parse_date(filters.get('deliver_by'))
        actual = self.date_handler.parse_date(product.get('delivery_estimate'))
        if not actual:
            return MISSING_SCORE, f"Delivery score: {MISSING_SCORE} (no delivery date found for product)"
        if target and target < actual:
            days_late = (actual - target).days
            score = max(0.0, 1.0 / (days_late + 1))
            return score, f"Delivery score: {score:.2f} Actual delivery: {actual}, Target delivery: {target} ({days_late} days late)"
        else:
            days_until = (actual - datetime.now().date()).days
            score = 1 - expit(1.5 * (days_until - 2))
            return score, f"Delivery score: {score:.2f} (delivery date: {actual})"
