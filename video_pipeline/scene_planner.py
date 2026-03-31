"""Intelligent scene planning for video generation."""

import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ScenePlanner:
    """Plan optimal photo sequence and timing for video."""

    def plan_scenes(
        self,
        classified_photos: List[Dict[str, Any]],
        target_duration_sec: int = 30,
        min_photos: int = 6,
        max_photos: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Create an ordered scene plan from classified photos.

        Returns a list:
        {
          "photo_url": "...",
          "room_type": "...",
          "start_time": 0.0,
          "end_time": 3.5,
          "ken_burns": {"zoom": "in", "pan": "right"},
          "transition": "crossfade",
          "features": [...],
        }
        """
        logger.info("Planning scenes from %d photos", len(classified_photos))

        # Filter out very low quality frames
        good_photos = [
            p for p in classified_photos if float(p.get("quality_score", 0) or 0) >= 0.4
        ]

        if len(good_photos) < min_photos:
            logger.warning(
                "Only %d good photos (threshold 0.4), falling back to all classified photos",
                len(good_photos),
            )
            good_photos = classified_photos

        # Preserve listing crawl order (original_index), but cap exterior shots so
        # the first frames are not all facade angles (common on MLS galleries).
        sorted_photos = sorted(
            good_photos,
            key=lambda p: int(p.get("original_index", 0) or 0),
        )

        max_ext = max(1, int(os.getenv("MAX_SCENE_EXTERIOR", "1") or "1"))

        def _scene_key(photo: Dict[str, Any]) -> tuple:
            return (
                str(photo.get("url") or ""),
                int(photo.get("original_index", 0) or 0),
            )

        exterior_candidates = [
            p
            for p in sorted_photos
            if str(p.get("room_type") or "other").lower() == "exterior"
        ]
        ext_chosen = sorted(
            exterior_candidates,
            key=lambda p: (
                -float(p.get("quality_score", 0) or 0),
                int(p.get("original_index", 0) or 0),
            ),
        )[:max_ext]
        ext_allowed = {_scene_key(p) for p in ext_chosen}

        selected: List[Dict[str, Any]] = []
        for p in sorted_photos:
            if len(selected) >= max_photos:
                break
            rt = str(p.get("room_type") or "other").lower()
            if rt == "exterior":
                if _scene_key(p) not in ext_allowed:
                    continue
            selected.append(p)

        scenes = self._assign_timing(selected, target_duration_sec)

        logger.info("Created scene plan with %d scenes", len(scenes))
        return scenes

    def _assign_timing(
        self,
        photos: List[Dict[str, Any]],
        total_duration: int,
    ) -> List[Dict[str, Any]]:
        """Assign start/end times and Ken Burns effects."""

        if not photos:
            return []

        scene_duration = total_duration / len(photos)
        scenes: List[Dict[str, Any]] = []
        current_time = 0.0

        ken_burns_patterns = [
            {"zoom": "in", "pan": "right"},
            {"zoom": "out", "pan": "left"},
            {"zoom": "in", "pan": "center"},
            {"zoom": "out", "pan": "right"},
        ]

        for idx, photo in enumerate(photos):
            scenes.append(
                {
                    "photo_url": photo["url"],
                    "room_type": photo.get("room_type", "other") or "other",
                    "start_time": round(current_time, 2),
                    "end_time": round(current_time + scene_duration, 2),
                    "ken_burns": ken_burns_patterns[idx % len(ken_burns_patterns)],
                    "transition": "crossfade" if idx < len(photos) - 1 else "none",
                    "features": photo.get("features", []) or [],
                    "order_priority": float(photo.get("order_priority", 5) or 5),
                    "original_index": int(photo["original_index"])
                    if photo.get("original_index") is not None
                    else idx,
                }
            )
            current_time += scene_duration

        return scenes

