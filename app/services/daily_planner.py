import asyncio
import json
import logging
from typing import Any, Tuple

import google.generativeai as genai  # type: ignore[import-untyped]
from fastapi import HTTPException
from pydantic import ValidationError

from ..models.daily_planner_schema import (
    DailyPlannerRequest,
    DailyPlannerResponse,
    DailyPlannerEntry,
    TravelAnalysisEntry,
)
from ..settings import settings

logger = logging.getLogger(__name__)

PROMPT = """
You are an expert Low-Carbon Activity Analyzer.

The user will provide a list of daily activities written in natural language
(e.g. “เดินทางด้วยรถยนต์ 5 กม.”, “กินหมูกรอบ 1 มื้อ”, “ใช้แอร์ 3 ชม.”)
and may also provide travel origin/destination pairs.

Your tasks:
1. Interpret each activity and estimate its CO₂ emission in kg using realistic average factors.
2. Suggest a practical low-carbon alternative for each activity.
3. Estimate the CO₂ emission of the alternative.
4. Calculate how much CO₂ the user would save by switching.
5. For each travel pair, estimate distance, compare common modes (car, motorcycle, bus, rail, bicycle, walking),
   recommend the lowest-CO₂ realistic mode, and report the reduction.
6. Output strictly in JSON only, using this exact structure:

{
  "analysis": [
    {
      "original": "<original activity>",
      "current_co2": <kg>,
      "alternative": "<recommended activity>",
      "alternative_co2": <kg>,
      "reduced": <kg>
    }
  ],
  "travel_analysis": [
    {
      "origin": "<string>",
      "destination": "<string>",
      "distance_km": <float>,
      "current_mode": "car",
      "current_co2": <kg>,
      "recommended_mode": "<string>",
      "recommended_co2": <kg>,
      "reduced": <kg>
    }
  ],
  "summary_reduction": <total kg>
}

Rules:
- Be concise but accurate.
- CO₂ values must be numeric (float).
- Alternatives must be realistic and achievable.
- If the activity already has low emissions, suggest a small improvement.
- Never output additional text outside JSON.
""".strip()


class DailyPlannerService:
    @staticmethod
    def _get_model() -> genai.GenerativeModel:
        if not settings.gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        try:
            genai.configure(api_key=settings.gemini_api_key)
            return genai.GenerativeModel(
                model_name=settings.gemini_model,
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception as exc:
            logger.exception("Gemini init failed: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to initialize Gemini client") from exc

    @staticmethod
    def _clean_json(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "")
            cleaned = cleaned.replace("```", "").strip()
        return cleaned

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            return response.text
        except Exception as exc:
            logger.exception("Failed to extract Gemini text: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to parse Gemini response")

    @staticmethod
    def _parse_response(raw_text: str) -> dict:
        attempts = [raw_text, DailyPlannerService._clean_json(raw_text)]
        last_error: Exception | None = None
        for attempt in attempts:
            try:
                return json.loads(attempt)
            except Exception as exc:
                last_error = exc
        logger.exception("Gemini returned invalid JSON: %s", last_error)
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON")

    @staticmethod
    def _map_entries(parsed: dict) -> Tuple[list[DailyPlannerEntry], list[TravelAnalysisEntry]]:
        activity_raw = parsed.get("analysis") or []
        travel_raw = parsed.get("travel_analysis") or []
        activities: list[DailyPlannerEntry] = []
        travels: list[TravelAnalysisEntry] = []

        def _to_float(val: Any) -> float:
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        for item in activity_raw:
            data = {
                "original": item.get("original") or item.get("activity") or "",
                "current_co2": _to_float(item.get("current_co2")),
                "alternative": item.get("alternative") or item.get("recommended") or "",
                "alternative_co2": _to_float(item.get("alternative_co2")),
                "reduced": _to_float(item.get("reduced")),
            }
            try:
                entry = DailyPlannerEntry.model_validate(data)
            except ValidationError as exc:
                logger.exception("Activity entry validation failed: %s", exc)
                raise HTTPException(status_code=502, detail="Gemini JSON schema mismatch")
            activities.append(entry)

        for item in travel_raw:
            data = {
                "origin": item.get("origin") or "",
                "destination": item.get("destination") or "",
                "distance_km": _to_float(item.get("distance_km")),
                "current_mode": item.get("current_mode") or item.get("mode") or "car",
                "current_co2": _to_float(item.get("current_co2")),
                "recommended_mode": item.get("recommended_mode") or item.get("mode") or "",
                "recommended_co2": _to_float(item.get("recommended_co2")),
                "reduced": _to_float(item.get("reduced")),
            }
            try:
                entry = TravelAnalysisEntry.model_validate(data)
            except ValidationError as exc:
                logger.exception("Travel entry validation failed: %s", exc)
                raise HTTPException(status_code=502, detail="Gemini JSON schema mismatch")
            travels.append(entry)

        return activities, travels

    @staticmethod
    def _compute_summary(parsed: dict, activities: list[DailyPlannerEntry], travels: list[TravelAnalysisEntry]) -> float:
        if parsed.get("summary_reduction") is not None:
            try:
                return float(parsed["summary_reduction"])
            except (TypeError, ValueError):
                pass

        summary = 0.0
        for a in activities:
            summary += float(a.reduced)
        for t in travels:
            summary += float(t.reduced)
        return summary

    @classmethod
    async def analyze(cls, payload: DailyPlannerRequest) -> DailyPlannerResponse:
        model = cls._get_model()

        payload_json = json.dumps(
            {
                "activities": payload.activities,
                "travel": [item.model_dump() for item in payload.travel],
            },
            ensure_ascii=False,
            indent=2,
        )
        user_prompt = f"User input:\n{payload_json}"

        try:
            response = await asyncio.to_thread(
                model.generate_content,
                [PROMPT, user_prompt],
            )
        except Exception as exc:
            logger.exception("Gemini request failed: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to contact Gemini")

        raw_text = cls._extract_text(response)
        parsed = cls._parse_response(raw_text)

        activities, travels = cls._map_entries(parsed)
        summary = cls._compute_summary(parsed, activities, travels)

        try:
            return DailyPlannerResponse(
                analysis=activities,
                travel_analysis=travels,
                summary_reduction=summary,
            )
        except ValidationError as exc:
            logger.exception("Response validation failed: %s", exc)
            raise HTTPException(status_code=502, detail="Gemini response invalid")
