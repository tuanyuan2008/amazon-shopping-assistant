from typing import Dict, List
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai
from .utils.config import Config
from .models import ParsedQuery
from .date_handler import DateHandler
from .product_scorer import ProductScorer

class NLPProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.date_handler = DateHandler()
        self.product_scorer = ProductScorer(nlp_processor=self)
        self.prompt_dir = Path(__file__).parent / 'prompts'

    def _get_parser_prompt(self, is_follow_up: bool = False) -> str:
        """Get the system prompt for parsing queries, formatted with current year."""
        current_year = datetime.now().year
        base_prompt = (self.prompt_dir / 'query_parser.txt').read_text().replace('CURRENT_YEAR', str(current_year))
        suffix = 'query_parser_follow_up.txt' if is_follow_up else 'query_parser_search_term.txt'
        suffix_prompt = (self.prompt_dir / suffix).read_text().replace('CURRENT_YEAR', str(current_year))
        return base_prompt + suffix_prompt

    def _parse_with_llm(self, prompt: str, user_input: str, model_class) -> Dict:
        """Parse input using the LLM."""
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )
        result = model_class.parse_raw(response.choices[0].message.content).dict()
        return result
    
    def summarize_results_with_llm(self, results: List[Dict]) -> str:
        """Use an LLM to create a natural language summary of the provided search results."""
        try:
            if not results:
                return "No products to summarize." # Or a more user-friendly "No relevant products found."

            self.logger.info(f"Summarizing {len(results)} final products.")

            product_summaries_for_prompt = []
            for i, product in enumerate(results, 1):
                title = product.get('title', 'N/A')
                price = product.get('price', 'N/A')
                rating = product.get('rating', 'N/A')
                product_info = f"{i}. Title: {title}, Price: ${price}, Rating: {rating}"
                product_summaries_for_prompt.append(product_info)
            
            concise_results_str = "\n".join(product_summaries_for_prompt)
            prompt_template = (self.prompt_dir / 'results_summarizer.txt').read_text()

            user_message_content = (
                "Please provide a concise summary for the following list of products. "
                "Highlight any notable trends in terms of price, ratings, or common features if apparent. "
                "Do not list each product individually in your summary; give an overall synthesis.\n\n"
                "Products:\n"
                f"{concise_results_str}"
            )

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": user_message_content}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error summarizing results with LLM: {e}", exc_info=True)
            return "Error generating summary."

    def parse_query(self, user_query: str) -> Dict:
        """Parse a shopping query into structured filters and preferences."""
        result = self._parse_with_llm(self._get_parser_prompt(False), user_query, ParsedQuery)
        self.logger.info(f"Processing main query with preferences: {result.get('preferences', {})}")
        return result

    def parse_follow_up(self, query: str, previous_context: Dict) -> Dict:
        """Parse a follow-up query using the follow-up prompt."""
        try:            
            results_summary = self.summarize_results_with_llm(previous_context.get('results', []))
            prompt = self._get_parser_prompt(True)
            user_input = (
                f"Previous search: {previous_context.get('query', '')}\n"
                f"Previous filters: {previous_context.get('filters', {})}\n"
                f"Previous preferences: {previous_context.get('preferences', {})}\n"
                f"Results summary: {results_summary}\n"
                f"Follow-up: {query}"
            )
            self.logger.info(f"Processing follow-up query with preferences: {previous_context.get('preferences', {})}")
            return self._parse_with_llm(prompt, user_input, ParsedQuery)
        except Exception as e:
            self.logger.error(f"Error parsing follow-up query: {e}")
            raise

    def rank_products(self, products: List[Dict], filters: Dict, preferences: Dict, search_term: str) -> List[Dict]:
        """Rank products using the ProductScorer, passing the search term for context."""
        return self.product_scorer.rank_products(products, filters, preferences, search_term)

    def _validate_product_relevance_with_llm(self, product_title: str, search_term: str) -> str:
        """
        Uses an LLM to validate if a product title is a DIRECT and PRIMARY match for a search term,
        considering likely user intent.
        Returns "yes" (for primary match), "no" (not a primary match), or "unknown".
        """
        try:
            prompt_template = (self.prompt_dir / 'relevance_validator.txt').read_text()
            prompt = prompt_template.replace("[search_term]", search_term).replace("[product_title]", product_title)

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": f"Product title: {product_title}\nSearch term: {search_term}"}
                ],
                temperature=0,
                max_tokens=3
            )

            llm_response = response.choices[0].message.content.strip().lower()

            if llm_response == "yes" or llm_response == "no":
                return llm_response
            else:
                self.logger.warning(f"Unexpected LLM response for (yes/no) relevance validation: '{llm_response}'. Defaulting to 'unknown'.")
                return "unknown"

        except Exception as e:
            self.logger.error(f"Error during LLM (yes/no) relevance validation: {e}", exc_info=True)
            return "unknown"

    def get_llm_validated_top_products(self,
                                       products: List[Dict],
                                       search_term: str,
                                       top_n_constant: int) -> List[Dict]:
        """
        Takes a list of products, selects the top N, validates their relevance
        concurrently using LLM, and returns only those validated as "yes".
        """
        if not products:
            return []

        products_to_validate = products[:top_n_constant]

        if not products_to_validate:
            return []

        validated_products_with_llm_response = []
        max_workers = min(len(products_to_validate), 5)

        if max_workers == 0: # Should be caught by earlier products_to_validate check, but as safety.
            return []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_product = {
                executor.submit(self._validate_product_relevance_with_llm, product.get('title', ''), search_term): product
                for product in products_to_validate
            }

            for future in as_completed(future_to_product):
                product_data = future_to_product[future]
                try:
                    llm_decision = future.result()
                    validated_products_with_llm_response.append({
                        "product": product_data,
                        "llm_decision": llm_decision
                    })
                except Exception as exc:
                    self.logger.error(f"LLM validation for product '{product_data.get('title', '')}' generated an exception: {exc}", exc_info=True)
                    validated_products_with_llm_response.append({
                        "product": product_data,
                        "llm_decision": "unknown"
                    })

        final_filtered_products = []
        llm_decisions_map = {item["product"]["url"]: item["llm_decision"] for item in validated_products_with_llm_response if item["product"].get("url")}

        for product in products_to_validate:
            product_url = product.get("url")
            llm_decision = llm_decisions_map.get(product_url)
            
            if product_url and llm_decision == "yes":
                final_filtered_products.append(product)
            elif product_url:
                # Log products that were explicitly classified as "no" or defaulted to "unknown"
                self.logger.info(f"Product excluded by LLM validation (decision: {llm_decision}): '{product.get('title')}'")
            else: 
                # This case handles products missing a URL
                self.logger.warning(f"Product '{product.get('title')}' missing URL, cannot map LLM decision. Excluding.")

        self.logger.info(f"LLM validation complete. Kept {len(final_filtered_products)} out of {len(products_to_validate)} top products.")
        return final_filtered_products
