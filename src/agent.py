from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from src.utils.rate_limiter import RateLimiter
from src.nlp_processor import NLPProcessor
from src.amazon_scraper import AmazonScraper
from src.langgraph_nodes import parse_user_query, search_amazon, rank_products, llm_filter_top_products

class AssistantState(TypedDict, total=False):
    user_input: str
    rate_limiter: RateLimiter
    nlp_processor: NLPProcessor
    scraper: AmazonScraper
    parsed_query: Dict
    products: List[Dict]
    ranked_products: List[Dict]
    previous_context: Dict

def initialize_agent():
    """
    Initializes the NLPProcessor, AmazonScraper, RateLimiter, and the LangGraph app.
    Returns:
        Tuple: nlp_processor, scraper, rate_limiter, compiled_graph_app
    """
    rate_limiter = RateLimiter(
        max_requests_per_minute=30,
        request_delay_min=3,
        request_delay_max=6
    )
    nlp_processor = NLPProcessor()
    scraper = AmazonScraper(rate_limiter=rate_limiter)

    graph = StateGraph(state_schema=AssistantState)
    graph.add_node("parse_query", parse_user_query)
    graph.add_node("search_amazon", search_amazon)
    graph.add_node("rank_products", rank_products)
    graph.add_node("llm_filter_top_products", llm_filter_top_products)

    graph.add_edge("parse_query", "search_amazon")
    graph.add_edge("search_amazon", "rank_products")
    graph.add_edge("rank_products", "llm_filter_top_products")
    graph.add_edge("llm_filter_top_products", END)

    graph.set_entry_point("parse_query")
    app = graph.compile()

    return nlp_processor, scraper, rate_limiter, app

def process_query(app, nlp_processor, scraper, rate_limiter, user_input, previous_context):
    """
    Processes a single user query using the LangGraph app.
    Args:
        app: The compiled LangGraph app.
        nlp_processor: The NLPProcessor instance.
        scraper: The AmazonScraper instance.
        rate_limiter: The RateLimiter instance.
        user_input (str): The user's input query.
        previous_context (Dict): The context from the previous interaction.
    Returns:
        Tuple: ranked_products, summary, new_context
    """
    initial_state = {
        "user_input": user_input,
        "rate_limiter": rate_limiter,
        "nlp_processor": nlp_processor,
        "scraper": scraper,
        "previous_context": previous_context
    }
    
    ranked_products = []
    summary = None
    new_context = {}
    
    try:
        result = app.invoke(initial_state)

        ranked_products = result.get("ranked_products", [])

        if ranked_products:
            summary = nlp_processor.summarize_results_with_llm(ranked_products)
            new_context = {
                "query": result.get("parsed_query", {}).get("search_term", ""),
                "filters": result.get("parsed_query", {}).get("filters", {}),
                "preferences": result.get("parsed_query", {}).get("preferences", {}),
                "results": ranked_products
            }

    except Exception as e:
        print(f"Error during app.invoke or result processing: {e}")
        raise
    finally:
        if scraper:
            scraper.close()
            scraper.logger.info("AmazonScraper resources closed after process_query execution.")

    return ranked_products, summary, new_context

def format_display_results(products: List[Dict]) -> str:
    """Formats the ranked products for display."""
    if not products:
        return "No products to display."

    output_lines = ["\nTop Results:"]
    for i, product in enumerate(products[:5], 1):
        price_per_count = product.get("price_per_count", "N/A")
        output_lines.append(f"\n{i}. {product.get('title')} - ${product.get('price')} ( Unit Price: {price_per_count} ) \n\n{product.get('url')}\n")
        output_lines.append("Ranking Explanation:")
        output_lines.append(product.get('ranking_explanation', 'No ranking explanation available'))
        output_lines.append("-" * 80)
    return "\n".join(output_lines)

def format_summary(summary_text: str) -> str:
    """Formats the summary text for display."""
    if not summary_text:
        return "No summary to display."
    return f"\nSummary of Results:\n{summary_text}"
