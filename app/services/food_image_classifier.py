import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai  # type: ignore[import-untyped]
import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from ..models.identify_food_schema import (
    FoodImageResponse,
    IdentifiedFood,
    FoodImageUrlRequest,
)
from ..settings import settings

logger = logging.getLogger(__name__)


class FoodImageClassifierService:
    model_name = settings.gemini_vision_model

    @classmethod
    def _get_model(cls) -> genai.GenerativeModel:
        if not settings.gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        try:
            genai.configure(api_key=settings.gemini_api_key)
            return genai.GenerativeModel(
                model_name=cls.model_name,
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception as exc:
            logger.exception("Gemini Vision init failed: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to initialize Gemini Vision") from exc

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            return response.text
        except Exception as exc:
            logger.exception("Failed to extract Gemini Vision text: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to parse Gemini Vision response")

    @staticmethod
    def _clean_json(text: str) -> str:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "")
            cleaned = cleaned.replace("```", "").strip()

        return cleaned

    @classmethod
    def _map_to_response(cls, parsed: dict) -> FoodImageResponse:
        name = parsed.get("name") or parsed.get("food")
        if not name:
            raise HTTPException(status_code=502, detail="Gemini Vision response missing 'name'")

        confidence_raw = parsed.get("confidence", 0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        tags = parsed.get("tags")
        if tags is not None and not isinstance(tags, list):
            tags = [str(tags)]

        item_data = {
            "name": name,
            "tags": tags,
            "confidence": confidence,
            "explanation": parsed.get("explanation") or parsed.get("reasoning"),
            "sourceModel": cls.model_name,
        }

        try:
            item = IdentifiedFood.model_validate(item_data)
            return FoodImageResponse(item=item)
        except ValidationError as exc:
            logger.exception("Gemini Vision mapping failed: %s", exc)
            raise HTTPException(status_code=502, detail="Invalid Gemini Vision response format")

    @classmethod
    async def _fetch_image(cls, image_url: str) -> tuple[bytes, str]:
        if not image_url:
            raise HTTPException(status_code=400, detail="imageUrl is required")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(image_url)
        except Exception as exc:
            logger.exception("Failed to fetch image: %s", exc)
            raise HTTPException(status_code=400, detail="Failed to download image from URL")

        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail="Image URL returned error")

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="URL is not an image")

        data = response.content
        if not data:
            raise HTTPException(status_code=400, detail="Empty image content")

        return data, content_type or "image/jpeg"

    @classmethod
    async def classify_image(cls, payload: FoodImageUrlRequest) -> FoodImageResponse:
        image_bytes, mime_type = await cls._fetch_image(payload.imageUrl)

        model = cls._get_model()

        prompt = """
You are a food image classifier. Identify the primary food in the photo.
Respond in Thai when possible (food name and explanation), but keep JSON keys in English.
Return ONLY JSON with:
{
  "name": "<main food name in Thai if known, otherwise English>",
  "tags": ["<keywords in Thai or English>"],
  "confidence": <0-1>,
  "explanation": "<short reasoning in Thai if possible>"
}
""".strip()

        try:
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, {"mime_type": mime_type, "data": image_bytes}],
            )
        except Exception as exc:
            logger.exception("Gemini Vision request failed: %s", exc)
            raise HTTPException(status_code=502, detail="Failed to contact Gemini Vision")

        raw_text = cls._extract_text(response)
        clean = cls._clean_json(raw_text)

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            logger.exception("Gemini Vision returned invalid JSON\nRAW:\n%s\nCLEAN:\n%s", raw_text, clean)
            raise HTTPException(status_code=502, detail="Gemini Vision returned invalid JSON")

        return cls._map_to_response(parsed)
