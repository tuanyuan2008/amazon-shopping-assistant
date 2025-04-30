from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from src.utils.rate_limiter import RateLimiter
from src.nlp_processor import NLPProcessor
from src.amazon_scraper import AmazonScraper
from src.langgraph_nodes import parse_user_query, search_amazon, rank_products

class AssistantState(TypedDict, total=False):
    user_input: str
    rate_limiter: RateLimiter
    nlp_processor: NLPProcessor
    scraper: AmazonScraper
    parsed_query: Dict
    products: List[Dict]
    ranked_products: List[Dict]


rate_limiter = RateLimiter(
    max_requests_per_minute=30,
    request_delay_min=2,
    request_delay_max=5
)

graph = StateGraph(state_schema=AssistantState)
graph.add_node("parse_query", parse_user_query)
graph.add_node("search_amazon", search_amazon)
graph.add_node("rank_products", rank_products)
graph.add_edge("parse_query", "search_amazon")
graph.add_edge("search_amazon", "rank_products")
graph.add_edge("rank_products", END)
graph.set_entry_point("parse_query")

if __name__ == "__main__":
    user_input = input("Enter your shopping request: ")
    nlp_processor = NLPProcessor()
    scraper = AmazonScraper(rate_limiter=rate_limiter)
    initial_state = {
        "user_input": user_input,
        "rate_limiter": rate_limiter,
        "nlp_processor": nlp_processor,
        "scraper": scraper
    }
    app = graph.compile()
    result = app.invoke(initial_state)
    print("\nTop Results:")
    for i, product in enumerate(result.get("ranked_products", [])[:5], 1):
        price_per_count = product.get("price_per_count", "N/A")
        print(f"\n{i}. {product.get('title')} - ${product.get('price')} ( Unit Price: {price_per_count} ) - {product.get('url')}")
        print("Ranking Explanation:")
        print(product.get('ranking_explanation', 'No ranking explanation available'))
        print("-" * 80)
