def parse_user_query(state: dict) -> dict:
    nlp = state["nlp_processor"]
    if state.get("previous_context"):
        parsed = nlp.parse_follow_up(state["user_input"], state["previous_context"])
    else:
        parsed = nlp.parse_query(state["user_input"])
    return {
        **state,
        "parsed_query": parsed
    }


def search_amazon(state: dict) -> dict:
    scraper = state["scraper"]
    products = scraper.search_products(
        query=state["parsed_query"]["search_term"],
        filters=state["parsed_query"]["filters"],
    )
    return {
        **state,
        "products": products
    }


def rank_products(state: dict) -> dict:
    nlp = state["nlp_processor"]
    parsed_query = state["parsed_query"]
    ranked = nlp.rank_products(
        products=state["products"],
        filters=parsed_query["filters"],
        preferences=parsed_query["preferences"]
    )
    return {
        **state,
        "ranked_products": ranked
    }
