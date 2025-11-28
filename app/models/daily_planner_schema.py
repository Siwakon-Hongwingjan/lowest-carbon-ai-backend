from typing import List

from pydantic import BaseModel, Field


class TravelInput(BaseModel):
    origin: str = Field(..., description="Travel starting point")
    destination: str = Field(..., description="Travel destination")


class DailyPlannerRequest(BaseModel):
    activities: List[str] = Field(
        default_factory=list, description="List of user activities in natural language"
    )
    travel: List[TravelInput] = Field(
        default_factory=list, description="List of travel origin/destination pairs"
    )


class DailyPlannerEntry(BaseModel):
    original: str
    current_co2: float
    alternative: str
    alternative_co2: float
    reduced: float


class TravelAnalysisEntry(BaseModel):
    origin: str
    destination: str
    distance_km: float
    current_mode: str
    current_co2: float
    recommended_mode: str
    recommended_co2: float
    reduced: float


class DailyPlannerResponse(BaseModel):
    analysis: List[DailyPlannerEntry]
    travel_analysis: List[TravelAnalysisEntry]
    summary_reduction: float
