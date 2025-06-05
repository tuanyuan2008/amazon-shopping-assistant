import pytest
from unittest.mock import MagicMock

from src.product_scorer import ProductScorer
from src.nlp_processor import NLPProcessor
from src.constants import ACCESSORY_PENALTY_FACTOR, MISSING_SCORE

@pytest.fixture
def mock_nlp_processor():
    processor = MagicMock(spec=NLPProcessor)
    processor._validate_product_relevance_with_llm = MagicMock(return_value="primary")
    return processor

@pytest.fixture
def product_scorer_with_nlp(mock_nlp_processor):
    scorer = ProductScorer(nlp_processor=mock_nlp_processor)
    return scorer

@pytest.fixture
def product_scorer_no_nlp():
    scorer = ProductScorer(nlp_processor=None)
    return scorer

# Test cases
@pytest.mark.parametrize("scorer_fixture, product_title, search_term, preferences, llm_validation_return, initial_terms_matched, total_relevant_terms, expected_final_score_approx, expected_in_explanation, llm_should_be_called", [
    # Case 1: LLM says "accessory" - full keyword match initially
    ("product_scorer_with_nlp", "Genuine Leather Tennis Racket Overgrip", "tennis racket", {"features": []}, "accessory", 1, 1, 1.0 * ACCESSORY_PENALTY_FACTOR, "LLM: accessory, score reduced", True),
    # Case 2: LLM says "primary" - full keyword match initially
    ("product_scorer_with_nlp", "Wilson Pro Staff Tennis Racket", "tennis racket", {"features": []}, "primary", 1, 1, 1.0, "LLM: primary", True),
    # Case 3: LLM validation is "unknown" - full keyword match initially
    ("product_scorer_with_nlp", "Some Ambiguous Tennis Product", "tennis racket", {"features": []}, "unknown", 1, 1, 1.0, "LLM: validation inconclusive", True),
    # Case 4: Partial keyword match (search term matches, feature does not) -> LLM says accessory
    ("product_scorer_with_nlp", "Tennis Racket Case", "tennis racket", {"features": ["durable"]}, "accessory", 1, 2, (1/2) * ACCESSORY_PENALTY_FACTOR, "LLM: accessory, score reduced", True),
    # Case 5: Partial keyword match (feature matches, search term does not - though search_term is now part of relevant_terms) -> LLM says primary
    # This case means search_term was e.g. "sports gear", feature "tennis racket". Product "Tennis Racket Ultimate"
    # Let's rephrase: search_term "tennis equipment", feature "lightweight", product "Lightweight Tennis Racket"
    ("product_scorer_with_nlp", "Lightweight Tennis Racket", "tennis equipment", {"features": ["lightweight"]}, "primary", 2, 2, 1.0, "LLM: primary", True),
    # Case 6: No NLP processor provided, keyword match
    ("product_scorer_no_nlp", "Another Tennis Racket", "tennis racket", {"features": []}, "primary", 1, 1, 1.0, "NLPProcessor not available", False), # Note: expected_in_explanation might need adjustment if ProductScorer logs differently
    # Case 7: No keyword match at all (search_term and features all missing from title)
    ("product_scorer_with_nlp", "Completely Unrelated Item", "tennis racket", {"features": ["durable"]}, "primary", 0, 2, 0.0, "Missing: tennis racket, durable", False),
    # Case 8: Empty search term, but feature matches (LLM should not be called as search_term is required for current LLM call logic)
    ("product_scorer_with_nlp", "Cool Feature Product", "", {"features": ["cool feature"]}, "primary", 1, 1, 1.0, "Matched: cool feature", False),
    # Case 9: Search term matches, but product title is empty (should be handled gracefully by keyword matching)
    ("product_scorer_with_nlp", "", "tennis racket", {"features": []}, "primary", 0, 1, 0.0, "Missing: tennis racket", False),
    # Case 10: No search term, no features (relevant_terms_for_matching will be empty)
    ("product_scorer_with_nlp", "Some Product", "", {"features": []}, "primary", 0, 0, MISSING_SCORE, "(no preferences or search term to match)", False),


])
def test_preference_score_llm_validation(
    request,
    scorer_fixture, product_title, search_term, preferences,
    llm_validation_return, initial_terms_matched, total_relevant_terms,
    expected_final_score_approx, expected_in_explanation, llm_should_be_called
):
    scorer = request.getfixturevalue(scorer_fixture)
    product = {"title": product_title}

    if scorer.nlp_processor and hasattr(scorer.nlp_processor, '_validate_product_relevance_with_llm'):
        scorer.nlp_processor._validate_product_relevance_with_llm.return_value = llm_validation_return

    calculated_score, explanation = scorer._calculate_preference_score(product, preferences, search_term)

    assert calculated_score == pytest.approx(expected_final_score_approx, abs=0.01)
    assert expected_in_explanation in explanation

    if scorer.nlp_processor and hasattr(scorer.nlp_processor, '_validate_product_relevance_with_llm'):
        if llm_should_be_called:
            scorer.nlp_processor._validate_product_relevance_with_llm.assert_called_with(product_title, search_term)
        else:
            scorer.nlp_processor._validate_product_relevance_with_llm.assert_not_called()
    elif llm_should_be_called:
        pytest.fail("LLM was expected to be called, but NLP processor or method is missing.")
