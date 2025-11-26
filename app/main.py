from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import CalcCo2Request, CalcCo2Response
from .services.co2 import estimate_activity_co2

app = FastAPI(
    title="Lowest Carbon AI Backend",
    version="0.1.0",
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


@app.post("/ai/calc_co2", response_model=CalcCo2Response)
async def calc_co2(payload: CalcCo2Request):
    results = [estimate_activity_co2(a) for a in payload.activities]
    total = sum(r.co2 for r in results)
    return CalcCo2Response(activities=results, totalCo2=round(total, 3))
