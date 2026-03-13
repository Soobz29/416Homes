"""Gemini Vision-based photo classification and ranking."""

import os
import logging
from typing import List, Dict, Any
import base64
import json

import httpx

logger = logging.getLogger(__name__)

try:
    # Prefer new google-genai SDK when available
    from google import genai as _genai  # type: ignore
    _GENAI_SDK = "google-genai"
except Exception:  # pragma: no cover
    try:
        # Fallback to legacy google-generativeai
        import google.generativeai as _genai  # type: ignore
        _GENAI_SDK = "google-generativeai"
    except Exception:  # pragma: no cover
        _genai = None  # type: ignore[assignment]
        _GENAI_SDK = "none"


class PhotoClassifier:
    """Classify and rank property photos using Gemini Vision."""

    ROOM_TYPES = [
        "exterior",
        "kitchen",
        "living_room",
        "dining_room",
        "bedroom",
        "bathroom",
        "amenity",
        "view",
        "floorplan",
        "other",
    ]

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or _genai is None or _GENAI_SDK == "none":
            raise ValueError("GEMINI_API_KEY and Gemini SDK are required for photo classification")

        if _GENAI_SDK == "google-genai":
            self.client = _genai.Client(api_key=api_key)  # type: ignore[attr-defined]
            self.model_id = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash-exp")
        else:
            _genai.configure(api_key=api_key)  # type: ignore[call-arg]
            self.client = _genai.GenerativeModel(  # type: ignore[call-arg]
                os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash")
            )
            self.model_id = ""

    async def classify_photos(self, photo_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Classify multiple photos in batch.

        Returns a list of dicts:
        {
          "url": "...",
          "room_type": "kitchen",
          "quality_score": 0.85,
          "features": [...],
          "order_priority": 8,
          "original_index": 0,
        }
        """
        logger.info("Classifying %d photos with Gemini Vision", len(photo_urls))

        classified: List[Dict[str, Any]] = []

        for idx, url in enumerate(photo_urls):
            try:
                result = await self._classify_single_photo(url)
                result["original_index"] = idx
                classified.append(result)
            except Exception as e:  # pragma: no cover - best-effort
                logger.error("Failed to classify %s: %s", url, e)
                classified.append(
                    {
                        "url": url,
                        "room_type": "other",
                        "quality_score": 0.5,
                        "features": [],
                        "order_priority": 5,
                        "original_index": idx,
                        "error": str(e),
                    }
                )

        logger.info("Successfully classified %d photos", len(classified))
        return classified

    async def _classify_single_photo(self, photo_url: str) -> Dict[str, Any]:
        """Classify a single photo using Gemini Vision."""

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(photo_url)
            resp.raise_for_status()
            image_data = resp.content

        prompt = (
            "Analyze this property listing photo and return JSON with:\n\n"
            f'- "room_type": one of {self.ROOM_TYPES}\n'
            '- "quality_score": 0.0-1.0 (technical quality: lighting, focus, composition)\n'
            '- "features": list of 2-4 key visual features\n'
            '- "order_priority": 1-10 (1=show last, 10=hero shot/show first)\n\n'
            "Rules:\n"
            "- Exterior/entry photos get priority 9-10\n"
            "- Kitchen/living get priority 7-9\n"
            "- Bedrooms get priority 5-7\n"
            "- Bathrooms get priority 4-6\n"
            "- Floorplans/views get priority 3-5\n"
            "- Blurry/dark photos get quality_score < 0.5\n\n"
            "Return ONLY valid JSON, no markdown."
        )

        if _GENAI_SDK == "google-genai":
            # New google-genai SDK
            response = self.client.models.generate_content(  # type: ignore[attr-defined]
                model=self.model_id,
                contents=[
                    prompt,
                    {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_data).decode("utf-8"),
                    },
                ],
            )
            text = getattr(response, "text", None) or "".join(
                [c.text for c in getattr(response, "candidates", []) if getattr(c, "text", None)]
            )
        else:
            # Legacy google-generativeai
            response = self.client.generate_content(  # type: ignore[call-arg]
                [
                    prompt,
                    {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_data).decode("utf-8"),
                    },
                ]
            )
            # Response schema differs; try common attributes
            text = getattr(response, "text", None)
            if not text and getattr(response, "candidates", None):
                parts = []
                for c in response.candidates:
                    for p in getattr(c, "content", []).parts:
                        if getattr(p, "text", None):
                            parts.append(p.text)
                text = "".join(parts)

        if not text:
            raise RuntimeError("Gemini vision response was empty")

        result_text = text.strip()
        if result_text.startswith("```"):
            # Strip markdown fences if model added them
            result_text = result_text.split("\n", 1)[1].rsplit("\n```", 1)[0]

        data = json.loads(result_text)
        data["url"] = photo_url
        return data

