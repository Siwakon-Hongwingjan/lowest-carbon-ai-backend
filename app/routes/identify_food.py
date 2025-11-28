from fastapi import APIRouter

from ..models.identify_food_schema import FoodImageResponse, FoodImageUrlRequest
from ..services.food_image_classifier import FoodImageClassifierService

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/identify_food_image", response_model=FoodImageResponse)
async def identify_food_image(payload: FoodImageUrlRequest) -> FoodImageResponse:
    return await FoodImageClassifierService.classify_image(payload)
