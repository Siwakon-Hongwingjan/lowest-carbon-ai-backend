from typing import List, Optional

from pydantic import BaseModel


class FoodImageUrlRequest(BaseModel):
    imageUrl: str


class IdentifiedFood(BaseModel):
    name: str
    tags: Optional[List[str]] = None
    confidence: float
    explanation: Optional[str] = None
    sourceModel: Optional[str] = None


class FoodImageResponse(BaseModel):
    item: IdentifiedFood
