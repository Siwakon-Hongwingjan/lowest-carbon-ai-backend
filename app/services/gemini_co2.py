import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai  # type: ignore[import-untyped]
from fastapi import HTTPException
from pydantic import ValidationError

from ..schemas import CalcCo2Request, CalcCo2Response
from ..settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Carbon Footprint Estimator.
Users may input any free-text activity (especially FOOD and OTHER).
Input may be in English or Thai; handle both naturally.
Infer the meaning, calculate realistic carbon emissions using international
sources (IPCC, FAO, DEFRA, OurWorldInData), and return ONLY valid JSON.

Only the field `type` is free-text. All other fields (id, category, value, date)
must remain unchanged. Convert grams to kilograms when appropriate. If unknown,
infer the closest real-world activity and provide a reasonable estimate.

Value interpretation by category (do not change the numbers, just interpret):
- TRANSPORT: `value` = distance in kilometers.
- FOOD: `value` = number of servings/plates.
- OTHER: `value` = duration in hours.

Input:
{{activities_json}}

Return:
{
  "activities": [
    {
      "id": "...",
      "co2": <kg_CO2e>,
      "description": "Short human-friendly summary (e.g., 'กินข้าวขาหมู 1 จาน ปล่อย CO2 1.2 kg')"
    }
  ],
  "totalCo2": <sum>
}

No explanations. JSON only.
""".strip()


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


def _extract_text(response: Any) -> str:
    try:
        return response.text
    except Exception as exc:
        logger.exception("Failed to extract .text: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to parse Gemini response")


def _clean_json(text: str) -> str:
    cleaned = text.strip()

    # remove ```json and ```
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "")
        cleaned = cleaned.replace("```", "").strip()

    return cleaned


async def estimate_with_gemini(payload: CalcCo2Request) -> CalcCo2Response:
    model = _get_model()

    activities_json = json.dumps(payload.model_dump(), ensure_ascii=False)

    user_prompt = f"""
Input:
{activities_json}

Value meaning reminder (do NOT modify numbers):
- TRANSPORT value = distance in kilometers
- FOOD value = number of servings/plates
- OTHER value = duration in hours

Return JSON only:
{{
  "activities": [ {{ "id": "...", "co2": <kg>, "description": "..." }} ],
  "totalCo2": <number>
}}
""".strip()

    try:
        response = await asyncio.to_thread(
            model.generate_content,
            [SYSTEM_PROMPT, user_prompt],
        )
    except Exception as exc:
        logger.exception("Gemini request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to contact Gemini")

    raw_text = _extract_text(response)
    clean = _clean_json(raw_text)

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        logger.exception(
            "Gemini returned invalid JSON\nRAW:\n%s\nCLEAN:\n%s", raw_text, clean
        )
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON")

    try:
        return CalcCo2Response.model_validate(parsed)
    except ValidationError:
        logger.exception("Schema mismatch: %s", parsed)
        raise HTTPException(status_code=502, detail="Gemini JSON schema mismatch")
