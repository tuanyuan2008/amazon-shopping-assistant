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
    previous_context: Dict

rate_limiter = RateLimiter(
    max_requests_per_minute=50,
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

def display_results(products: List[Dict]) -> None:
    """Display the ranked products with their explanations."""
    print("\nTop Results:")
    for i, product in enumerate(products[:5], 1):
        price_per_count = product.get("price_per_count", "N/A")
        print(f"\n{i}. {product.get('title')} - ${product.get('price')} ( Unit Price: {price_per_count} ) \n\n{product.get('url')}\n\n")
        print("Ranking Explanation:")
        print(product.get('ranking_explanation', 'No ranking explanation available'))
        print("-" * 80)

if __name__ == "__main__":
    nlp_processor = NLPProcessor()
    scraper = AmazonScraper(rate_limiter=rate_limiter)
    previous_context = {}
    
    while True:
        if not previous_context:
            user_input = input("\nWhat are you looking for? (or 'quit' to exit): ").strip()
        else:
            user_input = input("\nHow would you like to modify your search? (or 'quit' to exit): ").strip()
            
        if user_input.lower() == 'quit':
            break
            
        initial_state = {
            "user_input": user_input,
            "rate_limiter": rate_limiter,
            "nlp_processor": nlp_processor,
            "scraper": scraper,
            "previous_context": previous_context
        }
        
        app = graph.compile()
        result = app.invoke(initial_state)
        
        ranked_products = result.get("ranked_products", [])
        if ranked_products:
            display_results(ranked_products)
            
            previous_context = {
                "query": result.get("parsed_query", {}).get("search_term", ""),
                "filters": result.get("parsed_query", {}).get("filters", {}),
                "preferences": result.get("parsed_query", {}).get("preferences", {}),
                "results": ranked_products
            }
            
            print("\nYou can modify your search by:")
            print("- Adjusting the price range")
            print("- Adding or removing specific features")
            print("- Changing delivery requirements")
            print("- Looking for different brands")
            print("- Seeing more results")
            print("- Trying a different search term")
        else:
            print("\nNo results found. Let's try a different search.")
            previous_context = {}
