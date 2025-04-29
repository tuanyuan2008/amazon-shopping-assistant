from src.nlp_processor import NLPProcessor
from src.amazon_scraper import AmazonScraper

def parse_user_query(state: dict) -> dict:
    nlp = state["nlp_processor"]
    parsed = nlp.parse_query(state["user_input"])
    return {
        **state,
        "parsed_query": parsed
    }


def search_amazon(state: dict) -> dict:
    scraper = state["scraper"]
    products = scraper.search_products(
        query=state["parsed_query"]["search_term"],
        filters=state["parsed_query"].get("filters", {})
    )
    return {
        **state,
        "products": products
    }


def rank_products(state: dict) -> dict:
    nlp = state["nlp_processor"]
    ranked = nlp.rank_products(
        products=state["products"],
        preferences=state["parsed_query"].get("preferences", {})
    )
    return {
        **state,
        "ranked_products": ranked
    }
