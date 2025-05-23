from src.agent import (
    initialize_agent,
    process_query,
    format_display_results,
    format_summary
)

if __name__ == "__main__":
    nlp_processor, scraper, rate_limiter, app = initialize_agent()
    previous_context = {}

    while True:
        if not previous_context:
            user_input = input("\nWhat are you looking for? (or 'quit' to exit): ").strip()
        else:
            user_input = input("\nHow would you like to modify your search? (or 'quit' to exit): ").strip()

        if user_input.lower() == 'quit':
            break

        ranked_products, summary_text, new_context = process_query(
            app, nlp_processor, scraper, rate_limiter, user_input, previous_context
        )

        if ranked_products:
            if summary_text:
                print(format_summary(summary_text))
            
            print(format_display_results(ranked_products))
            
            previous_context = new_context
            
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
