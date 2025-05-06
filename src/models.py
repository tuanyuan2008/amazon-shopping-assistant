from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SortOption(str, Enum):
    """Enumeration of available sorting options for product search results."""
    PRICE_ASC = "price-asc-rank"
    PRICE_DESC = "price-desc-rank"
    REVIEW = "review-rank"
    DATE_DESC = "date-desc-rank"
    RELEVANCE = "relevanceblender"

class Feature(BaseModel):
    """A product feature with its category."""
    name: str

class Filters(BaseModel):
    """Filters for product search results."""
    price_max: Optional[float] = None
    price_min: Optional[float] = None
    prime: Optional[bool] = False
    min_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    sort_by: Optional[str] = None
    deliver_by: Optional[str] = None

class Preferences(BaseModel):
    """User preferences for product ranking."""
    features: List[str] = Field(default_factory=list)

class ParsedQuery(BaseModel):
    """Structured representation of a user's shopping query."""
    search_term: str
    filters: Filters
    preferences: Preferences
