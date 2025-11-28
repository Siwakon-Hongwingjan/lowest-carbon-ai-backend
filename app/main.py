from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import CalcCo2Request, CalcCo2Response
from .services.gemini_co2 import estimate_with_gemini
from .routes.identify_food import router as identify_food_router
from .routes.daily_planner import router as daily_planner_router

app = FastAPI(
    title="AI Carbon Footprint Calculator",
    version="0.2.0",
    description="Standalone AI backend that estimates CO₂ from free-text activities.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-backend"}


app.include_router(identify_food_router)
app.include_router(daily_planner_router)


@app.post("/ai/calc_co2", response_model=CalcCo2Response, tags=["ai"])
async def calc_co2(payload: CalcCo2Request) -> CalcCo2Response:
    return await estimate_with_gemini(payload)
