from fastapi import APIRouter

from ..schemas import CalcCo2Request, CalcCo2Response
from ..services.gemini_co2 import estimate_with_gemini

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/calc_co2", response_model=CalcCo2Response)
async def calc_co2(payload: CalcCo2Request) -> CalcCo2Response:
    return await estimate_with_gemini(payload)
