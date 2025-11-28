from typing import List

from pydantic import BaseModel, Field


class ActivityInput(BaseModel):
    id: str = Field(..., description="Unique activity identifier")
    category: str = Field(..., description="Original category provided by the client")
    type: str = Field(..., description="Free-text description from the user")
    value: float = Field(..., description="Quantity, distance, duration, or portion size")
    date: str = Field(..., description="ISO date string, e.g. 2025-01-28")


class CalcCo2Request(BaseModel):
    activities: List[ActivityInput]


class ActivityCo2Result(BaseModel):
    id: str
    co2: float = Field(..., description="Estimated CO₂ in kilograms (kgCO2e)")
    description: str | None = Field(
        default=None,
        description="Short human-friendly summary of the activity and its CO₂ impact",
    )


class CalcCo2Response(BaseModel):
    activities: List[ActivityCo2Result]
    totalCo2: float = Field(..., description="Total CO₂ across all activities (kgCO2e)")
