"""Intelligent scene planning for video generation."""

import logging
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

        # Sort by order_priority (descending)
        sorted_photos = sorted(
            good_photos,
            key=lambda p: float(p.get("order_priority", 5) or 5),
            reverse=True,
        )

        selected = self._select_diverse_photos(sorted_photos, max_photos)
        scenes = self._assign_timing(selected, target_duration_sec)

        logger.info("Created scene plan with %d scenes", len(scenes))
        return scenes

    def _select_diverse_photos(
        self,
        sorted_photos: List[Dict[str, Any]],
        max_photos: int,
    ) -> List[Dict[str, Any]]:
        """Select diverse photos ensuring good category coverage."""

        targets = {
            "exterior": 2,
            "kitchen": 2,
            "living_room": 2,
            "dining_room": 1,
            "bedroom": 2,
            "bathroom": 1,
            "amenity": 1,
            "view": 1,
        }

        selected: List[Dict[str, Any]] = []
        used_types: Dict[str, int] = {}

        for photo in sorted_photos:
            if len(selected) >= max_photos:
                break

            room_type = photo.get("room_type", "other") or "other"
            used_count = used_types.get(room_type, 0)
            target_count = targets.get(room_type, 1)

            # Prefer hitting target distribution first; then fill remaining slots
            if used_count < target_count or len(selected) < max_photos // 2:
                selected.append(photo)
                used_types[room_type] = used_count + 1

        # If still under max_photos, top up with remaining photos
        if len(selected) < max_photos:
            for photo in sorted_photos:
                if photo in selected:
                    continue
                selected.append(photo)
                if len(selected) >= max_photos:
                    break

        return selected

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
                }
            )
            current_time += scene_duration

        return scenes

