import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from scipy.special import expit
from scipy.stats import percentileofscore
import openai
from .utils.config import Config
from .models import ParsedQuery
from .date_handler import DateHandler
from .constants import MISSING_SCORE

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
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
        result = model_class.parse_raw(response.choices[0].message.content).dict()
        return result
    
    def summarize_results_with_llm(self, results: List[Dict]) -> str:
        """Use ChatGPT to create a natural language summary of search results."""
        try:
            limited_results = results[:5]
            
            prompt = (self.prompt_dir / 'results_summarizer.txt').read_text()
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Results: {limited_results}"}
                ],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error summarizing results with GPT: {e}")
            raise

    def parse_query(self, user_query: str) -> Dict:
        """Parse a shopping query into structured filters and preferences."""
        return self._parse_with_llm(self._get_parser_prompt(False), user_query, ParsedQuery)

    def parse_follow_up(self, query: str, previous_context: Dict) -> Dict:
        """Parse a follow-up query using the follow-up prompt."""
        try:            
            results_summary = self.summarize_results_with_llm(previous_context.get('results', []))
            prompt = self._get_parser_prompt(True)
            user_input = (
                f"Previous search: {previous_context.get('query', '')}\n"
                f"Previous filters: {previous_context.get('filters', {})}\n"
                f"Previous preferences: {previous_context.get('preferences', {})}\n"
                f"Results summary: {results_summary}\n"
                f"Follow-up: {query}"
            )
            return self._parse_with_llm(prompt, user_input, ParsedQuery)
        except Exception as e:
            self.logger.error(f"Error parsing follow-up query: {e}")
            raise

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
                explanations[-1] = f"- {name.title()} score: 0 (excluded due to missing hard requirement)"
                break
            score *= sub_score

        return score, "\n".join(explanations) + f"\nTotal score: {score:.4f}"
    
    def _get_numeric_value(self, value: str) -> Optional[float]:
        """Extract numeric value from price string, handling per-unit prices."""
        if not value:
            return None
        try:
            cleaned = value.replace('$', '').replace(',', '').strip()
            if 'per' in cleaned.lower():
                cleaned = cleaned.split('per')[0].strip()
            return float(cleaned)
        except (ValueError, IndexError):
            return None
    
    def _calculate_preference_score(self, product: Dict, preferences: Dict) -> tuple[float, str]:
        """Calculate how well the product matches user preferences."""
        product_title = product.get('title', '').lower()
        features = preferences.get('features', [])
        preference_tokens = [f.strip().lower() for f in features] if features else []

        if not preference_tokens:
            return MISSING_SCORE, f"Preference score: {MISSING_SCORE} (no preferences to match)"

        matched_tokens = []
        missing_tokens = []
        
        for token in preference_tokens:
            if token in product_title:
                matched_tokens.append(token)
            else:
                missing_tokens.append(token)
        
        match_percentage = len(matched_tokens) / len(preference_tokens)
        
        explanation = f"Preference score: {match_percentage:.2f} (matched {len(matched_tokens)}/{len(preference_tokens)} features)"
        if missing_tokens:
            explanation += f", missing: {', '.join(missing_tokens)}"

        return match_percentage, explanation

    def _get_price_pct_score(self, products: List[Dict], price: float, is_unit_price: bool) -> float:
        key = 'price_per_count' if is_unit_price else 'price'
        prices = [p for p in (self._get_numeric_value(p.get(key, '')) for p in products) if p is not None]
        if not prices or price is None:
            return MISSING_SCORE
        percentile = percentileofscore(prices, price, kind='rank')
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
            
        if unit_price is not None:
            score = self._get_price_pct_score(all_products, unit_price, True)
            return score, f"Price score: {score:.2f} (unit price: {raw_price_per_count})"
        else:
            score = self._get_price_pct_score(all_products, price, False)
            return score, f"Price score: {score:.2f} (base price: ${price})"

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
