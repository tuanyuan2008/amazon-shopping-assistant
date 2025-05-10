import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import holidays
import openai
import dateparser
from .utils.config import Config

class DateHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.date_parser_settings = {
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now(),
            'RETURN_AS_TIMEZONE_AWARE': False,
            'SKIP_TOKENS': [],
        }

        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        self.prompt_dir = Path(__file__).parent / 'prompts'

    def _get_date_parser_prompt(self, year: int) -> str:
        prompt_path = self.prompt_dir / 'date_parser.txt'
        with open(prompt_path) as f:
            return f.read().format(year=year)

    def _parse_date_with_llm(self, date_str: str, year: int) -> Optional[date]:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_date_parser_prompt(year)},
                    {"role": "user", "content": date_str}
                ],
                temperature=0
            )
            result = response.choices[0].message.content.strip()
            if result.lower() == 'none':
                return None
            return datetime.strptime(result, '%Y-%m-%d').date()
        except Exception as e:
            self.logger.warning(f"Error parsing date with GPT: {e}")
            return None

    def parse_date(self, date_input, use_gpt: bool = False) -> Optional[date]:
        if not date_input:
            return None

        if isinstance(date_input, date):
            return date_input
        if isinstance(date_input, datetime):
            return date_input.date()
        if not isinstance(date_input, str):
            self.logger.warning(f"Expected str/date input, got: {type(date_input)}")
            return None

        date_str = date_input.strip().lower()
        current_year = datetime.now().year

        # 1. Check built-in U.S. holidays
        us_holidays = holidays.country_holidays("US", years=current_year)
        for holiday_date, name in us_holidays.items():
            if date_str in name.lower():
                return holiday_date

        # 2. Try parsing directly
        parsed = dateparser.parse(date_str, settings=self.date_parser_settings)
        if parsed:
            return parsed.date()

        # 3. Fallback to GPT if enabled
        if use_gpt:
            return self._parse_date_with_llm(date_str, current_year)
        return None 