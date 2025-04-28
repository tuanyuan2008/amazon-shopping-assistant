import logging
from src.agent import ShoppingAssistant

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize the shopping assistant
        assistant = ShoppingAssistant()
        logger.info("Shopping Assistant initialized successfully")
        
        # Example usage
        while True:
            try:
                # Get user input
                user_query = input("\nEnter your shopping request (or 'quit' to exit): ")
                if user_query.lower() == 'quit':
                    break
                
                # Process the request
                response = assistant.process_request(user_query)
                
                # Display results
                if response['status'] == 'success':
                    print("\nSearch Results:")
                    for i, product in enumerate(response['products'], 1):
                        print(f"\n{i}. {product['title']}")
                        print(f"   Price: ${product['price']:.2f}")
                        print(f"   Rating: {product['rating']}/5 ({product['review_count']} reviews)")
                        print(f"   Prime: {'Yes' if product['prime'] else 'No'}")
                        print(f"   URL: {product['url']}")
                else:
                    print(f"\nError: {response['message']}")
                
                # Handle follow-up questions
                while True:
                    follow_up = input("\nAny follow-up questions? (or 'next' for new search): ")
                    if follow_up.lower() == 'next':
                        break
                    
                    follow_up_response = assistant.handle_follow_up(response, follow_up)
                    
                    if follow_up_response['status'] == 'success':
                        print("\nUpdated Results:")
                        for i, product in enumerate(follow_up_response['products'], 1):
                            print(f"\n{i}. {product['title']}")
                            print(f"   Price: ${product['price']:.2f}")
                            print(f"   Rating: {product['rating']}/5 ({product['review_count']} reviews)")
                            print(f"   Prime: {'Yes' if product['prime'] else 'No'}")
                            print(f"   URL: {product['url']}")
                    else:
                        print(f"\nError: {follow_up_response['message']}")
                    
                    response = follow_up_response
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                print(f"\nAn error occurred: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"Fatal error: {str(e)}")
    
    finally:
        # Clean up
        if 'assistant' in locals():
            assistant.scraper.close()
        logger.info("Shopping Assistant shutdown complete")

if __name__ == "__main__":
    main() 