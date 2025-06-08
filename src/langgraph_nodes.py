from src.constants import TOP_N_FOR_LLM_VALIDATION

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
    search_term = parsed_query["search_term"]
    ranked = nlp.rank_products(
        products=state["products"],
        filters=parsed_query["filters"],
        preferences=parsed_query["preferences"],
        search_term=search_term
    )
    return {
        **state,
        "ranked_products": ranked
    }

def llm_filter_top_products(state: dict) -> dict:
    """
    Takes the ranked list of products, applies LLM validation to the top N,
    and returns the final filtered list.
    """
    nlp = state["nlp_processor"]
    ranked_products = state.get("ranked_products", [])
    search_term = state.get("parsed_query", {}).get("search_term", "")

    if not ranked_products or not search_term:
        state["ranked_products"] = []
        return state

    final_products = nlp.get_llm_validated_top_products(
        products=ranked_products,
        search_term=search_term,
        top_n_constant=TOP_N_FOR_LLM_VALIDATION
    )

    state["ranked_products"] = final_products

    nlp.logger.info(f"After LLM validation, {len(final_products)} products remain for display.")

    return state
