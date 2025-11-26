from typing import List, Literal

from pydantic import BaseModel, Field

ActivityCategory = Literal["TRANSPORT", "FOOD", "OTHER"]


class ActivityInput(BaseModel):
    id: str | None = Field(
        default=None,
        description="Optional ID from core-backend, used to later update that activity",
    )
    category: ActivityCategory
    type: str = Field(..., description="e.g. BTS, Pork, Running")
    value: float = Field(..., description="distance (km), portion size, or duration (minutes)")
    date: str = Field(..., description="ISO date string, e.g. 2025-01-28")


class CalcCo2Request(BaseModel):
    activities: List[ActivityInput]


class ActivityCo2Result(BaseModel):
    id: str | None = None
    category: ActivityCategory
    type: str
    value: float
    co2: float = Field(..., description="Estimated CO2 in kg")


class CalcCo2Response(BaseModel):
    activities: List[ActivityCo2Result]
    totalCo2: float
