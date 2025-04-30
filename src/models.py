from pydantic import BaseModel, Field
from typing import List, Optional

class Filters(BaseModel):
    price_max: Optional[float] = None
    price_min: Optional[float] = None
    prime: Optional[bool] = False
    min_rating: Optional[float] = None
    sort_by: Optional[str] = None
    deliver_by: Optional[str] = None

class Preferences(BaseModel):
    min_reviews: Optional[int] = None
    features: List[str] = Field(default_factory=list)

class ParsedQuery(BaseModel):
    search_term: str
    filters: Filters
    preferences: Preferences

class ParsedFollowUp(BaseModel):
    filters: Filters
    comparison: bool = False