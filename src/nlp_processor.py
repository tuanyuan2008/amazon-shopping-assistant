import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
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
        self.product_scorer = ProductScorer(nlp_processor=self) # Pass self
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
        """Use ChatGPT to create a natural language summary of search results."""
        try:
            limited_results = results[:5]
            
            prompt = (self.prompt_dir / 'results_summarizer.txt').read_text()
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Results: {limited_results}"}
                ],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error summarizing results with GPT: {e}")
            raise

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
