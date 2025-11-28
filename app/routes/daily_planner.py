from fastapi import APIRouter

from ..models.daily_planner_schema import DailyPlannerRequest, DailyPlannerResponse
from ..services.daily_planner import DailyPlannerService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/daily_planner", response_model=DailyPlannerResponse)
async def daily_planner(payload: DailyPlannerRequest) -> DailyPlannerResponse:
    return await DailyPlannerService.analyze(payload)
