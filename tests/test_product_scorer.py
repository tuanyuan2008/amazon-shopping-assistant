import pytest

from src.product_scorer import ProductScorer
from src.constants import MISSING_SCORE

@pytest.fixture
def product_scorer():
    return ProductScorer()

# Test cases for preference scoring
@pytest.mark.parametrize("product_title, preferences, expected_score, expected_in_explanation", [
    # Case 1: No preference features provided
    ("Tennis Racket", {"features": []}, 1.0, "no specific preference features provided"),
    
    # Case 2: All preference features match
    ("Wilson Pro Staff Tennis Racket", {"features": ["wilson", "tennis"]}, 1.0, "Matched features: wilson, tennis"),
    
    # Case 3: Some preference features match
    ("Wilson Pro Staff Tennis Racket", {"features": ["wilson", "durable"]}, 0.5, "Matched features: wilson"),
    
    # Case 4: No preference features match
    ("Wilson Pro Staff Tennis Racket", {"features": ["durable", "lightweight"]}, 0.0, "Missing features: durable, lightweight"),
    
    # Case 5: Empty product title
    ("", {"features": ["tennis"]}, 0.0, "Missing features: tennis"),
    
    # Case 6: Case insensitive matching
    ("WILSON TENNIS RACKET", {"features": ["wilson", "tennis"]}, 1.0, "Matched features: wilson, tennis"),
    
    # Case 7: Feature with spaces
    ("Wilson Pro Staff Tennis Racket", {"features": ["pro staff"]}, 1.0, "Matched features: pro staff"),
])
def test_preference_score_calculation(product_title, preferences, expected_score, expected_in_explanation):
    scorer = ProductScorer()
    product = {"title": product_title}

    calculated_score, explanation = scorer._calculate_preference_score(product, preferences)

    assert calculated_score == pytest.approx(expected_score, abs=0.01)
    assert expected_in_explanation in explanation

def test_price_score_missing_price():
    """Test that price score returns MISSING_SCORE when no price is available."""
    scorer = ProductScorer()
    product = {"title": "Test Product", "price": "Price not available"}
    filters = {}
    all_products = [product]
    
    score, explanation = scorer._calculate_price_score(product, filters, all_products)
    
    assert score == MISSING_SCORE
    assert "no price found for product" in explanation
