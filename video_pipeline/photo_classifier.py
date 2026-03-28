"""Gemini Vision-based photo classification and ranking."""

import os
import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


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

    def __init__(self):
        """Initialize Gemini Vision client (Vertex Studio key preferred, else GEMINI_API_KEY)."""
        import google.genai as genai

        self._genai_client = None
        self.model = None
        api_key = (
            (os.getenv("VERTEX_AI_API_KEY") or "").strip()
            or (os.getenv("GEMINI_API_KEY") or "").strip()
        )
        if not api_key:
            logger.warning(
                "VERTEX_AI_API_KEY and GEMINI_API_KEY missing; photo classification will fail per-photo until one is set"
            )
            return

        if hasattr(genai, "configure"):
            genai.configure(api_key=api_key)  # type: ignore[attr-defined]
            self.model = genai.GenerativeModel("gemini-2.5-flash-lite")  # type: ignore[attr-defined]
        else:
            self._genai_client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
            self.model = "gemini-2.5-flash-lite"

        logger.info("Photo classifier Gemini client configured")

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
        """Classify a single photo using Vertex AI."""
        import json
        import google.genai as genai

        # Download image
        async with httpx.AsyncClient() as client:
            response = await client.get(photo_url)
            response.raise_for_status()
            image_data = response.content

        # Prepare prompt
        prompt = f"""Analyze this property listing photo and return JSON with:

- "room_type": one of {self.ROOM_TYPES}
- "quality_score": 0.0-1.0
- "features": list of 2-4 key features
- "order_priority": 1-10

Return ONLY valid JSON, no markdown.
"""

        if self.model is None and self._genai_client is None:
            raise RuntimeError("Gemini API key not configured for photo classification")

        # Call model with image + prompt
        if self._genai_client is None:
            response = self.model.generate_content([prompt, image_data])  # type: ignore[union-attr]
            result_text = getattr(response, "text", None) or str(response)
        else:
            # google-genai SDK path
            from google.genai import types  # type: ignore

            image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
            response = self._genai_client.models.generate_content(  # type: ignore[union-attr]
                model=self.model,
                contents=[prompt, image_part],
            )
            result_text = getattr(response, "text", None) or str(response)

        # Parse JSON response
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1].rsplit("\n```", 1)[0]

        result = json.loads(result_text)
        result["url"] = photo_url

        return result

