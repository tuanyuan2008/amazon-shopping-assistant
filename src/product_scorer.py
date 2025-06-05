import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from scipy.special import expit
from scipy.stats import percentileofscore
from .constants import MISSING_SCORE
from .date_handler import DateHandler

if TYPE_CHECKING:
    from .nlp_processor import NLPProcessor # Forward declaration for type hint

class ProductScorer:
    def __init__(self, nlp_processor: 'Optional[NLPProcessor]' = None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.nlp_processor = nlp_processor
        self.date_handler = DateHandler()
        self.llm_validations_this_run = 0

    def rank_products(self, products: List[Dict], filters: Dict, preferences: Dict, search_term: str) -> List[Dict]:
        """Rank products based on filters and preferences."""
        self.llm_validations_this_run = 0
        scored = []
        all_non_positive_scores = True
        for product in products:
            score, explanation = self._calculate_product_score(product, filters, preferences, products, search_term)
            scored.append({
                **product,
                "score": score,
                "ranking_explanation": explanation,
            })
            if score > 0:
                all_non_positive_scores = False
        self.logger.info(f"All non-positive scores: {all_non_positive_scores}")
        return sorted(scored, key=lambda x: x["score"], reverse=not all_non_positive_scores)

    def _calculate_product_score(
        self, 
        product: Dict, 
        filters: Dict, 
        preferences: Dict, 
        all_products: List[Dict],
        search_term: str
    ) -> Tuple[float, str]:
        """Calculate the overall score for a product."""
        components = {
            "preference": self._calculate_preference_score(product, preferences, search_term),
            "price": self._calculate_price_score(product, filters, all_products),
            "rating": self._calculate_rating_score(product, filters),
            "reviews": self._calculate_review_score(product, filters),
            "delivery": self._calculate_delivery_score(product, filters),
        }

        score = 1.0
        explanations = []
        for name, (sub_score, explanation) in components.items():
            # Penalize heavily if the product does not meet any explicit preference features.
            if sub_score == 0 and name == "preference":
                score *= -1
                continue
            explanations.append(f"- {explanation}")
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
        except (ValueError, AttributeError):
            return None

    def _calculate_preference_score(self, product: Dict, preferences: Dict, search_term: str) -> Tuple[float, str]:
        product_title_lower = product.get('title', '').lower()
        features = preferences.get('features', [])

        preference_features_to_match = [f.strip().lower() for f in features if f]

        if not preference_features_to_match:
            return 1.0, "Preference score: 1.00 (no specific preference features provided)"

        matched_tokens = []
        missing_tokens = list(preference_features_to_match)

        for feature_term in preference_features_to_match:
            if feature_term in product_title_lower:
                matched_tokens.append(feature_term)
                if feature_term in missing_tokens:
                    missing_tokens.remove(feature_term)
        
        if not preference_features_to_match:
             match_percentage = 0.0
        else:
            match_percentage = len(matched_tokens) / len(preference_features_to_match)
        
        explanation_details = []
        if matched_tokens:
            explanation_details.append(f"Matched features: {', '.join(matched_tokens)}")
        if missing_tokens:
            explanation_details.append(f"Missing features: {', '.join(missing_tokens)}")

        explanation = f"Preference score: {match_percentage:.2f} ({'; '.join(explanation_details) if explanation_details else 'No specific preference features to match'})"

        return match_percentage, explanation

    def _get_price_pct_score(self, products: List[Dict], price: float, is_unit_price: bool) -> float:
        """Calculate price percentile score."""
        key = 'price_per_count' if is_unit_price else 'price'
        prices = [p for p in (self._get_numeric_value(p.get(key, '')) for p in products) if p is not None]
        if not prices or price is None:
            return MISSING_SCORE
        percentile = percentileofscore(prices, price)
        return (100 - percentile) / 100

    def _calculate_price_score(self, product: Dict, filters: Dict, all_products: List[Dict]) -> Tuple[float, str]:
        """Calculate price-based score."""
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

    def _calculate_rating_score(self, product: Dict, filters: Dict) -> Tuple[float, str]:
        """Calculate rating-based score."""
        try:
            rating = float(product.get('rating', '0').split(' ')[0])
        except ValueError:
            return MISSING_SCORE, f"Rating score: {MISSING_SCORE} (no rating found for product)"
        if filters.get('min_rating') and rating < filters['min_rating']:
            return 0.0, f"Rating score: 0 (rating {rating} < min {filters['min_rating']})"
        rating_score = expit(5 * (rating - 4.23))
        return rating_score, f"Rating score: {rating_score:.2f} ({rating}/5 stars)"

    def _calculate_review_score(self, product: Dict, filters: Dict) -> Tuple[float, str]:
        """Calculate review count-based score."""
        count = self._get_numeric_value(product.get('review_count', ''))
        if count is None:
            return MISSING_SCORE, f"Review count score: {MISSING_SCORE} (no reviews found for product)"
        if filters.get('min_reviews') and count < filters['min_reviews']:
            return 0.0, f"Review count score: 0 ({count} < min {filters['min_reviews']})"
        score = math.log10(min(count, 5000) + 1) / math.log10(5000)
        return score, f"Review count score: {score:.2f} ({int(count)} reviews)"

    def _calculate_delivery_score(self, product: Dict, filters: Dict) -> Tuple[float, str]:
        """Calculate delivery time-based score."""
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
            return score, f"Delivery score: {score:.2f} ({days_until} days until delivery)" 