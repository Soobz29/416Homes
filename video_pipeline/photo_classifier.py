"""Gemini Vision-based photo classification and ranking."""

import os
import logging
from typing import List, Dict, Any
import base64
import json

import httpx
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part

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
        """Initialize Vertex AI photo classifier."""
        import os
        import json
        import base64
        from google.cloud import aiplatform
        from vertexai.generative_models import GenerativeModel

        # Decode and write service account key to file
        vertex_key_b64 = os.getenv("VERTEX_KEY_BASE64")
        if not vertex_key_b64:
            raise ValueError("VERTEX_KEY_BASE64 environment variable required")

        try:
            key_json = base64.b64decode(vertex_key_b64).decode('utf-8')
            key_path = "/tmp/vertex-key.json"
            with open(key_path, 'w') as f:
                f.write(key_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
            print(f"✅ Service account key loaded from {key_path}")
        except Exception as e:
            raise ValueError(f"Failed to decode VERTEX_KEY_BASE64: {e}")

        # Initialize Vertex AI
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "homes-490422")
        location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

        print(f"Initializing Vertex AI: project={project}, location={location}")
        aiplatform.init(project=project, location=location)

        self.model = GenerativeModel("gemini-2.0-flash-001")
        print("✅ Vertex AI model initialized")

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
        import httpx
        from vertexai.generative_models import Part

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

        # Create image part using Vertex AI format
        image_part = Part.from_data(data=image_data, mime_type="image/jpeg")

        # Call Vertex AI
        response = self.model.generate_content([prompt, image_part])

        # Parse JSON response
        import json
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1].rsplit("\n```", 1)[0]

        result = json.loads(result_text)
        result["url"] = photo_url

        return result

