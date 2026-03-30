"""Veo-based video renderer — Vertex Veo via service account (GOOGLE_APPLICATION_CREDENTIALS_JSON)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-2.0-generate-001"
CLIP_DURATION_SECONDS = 5
POLL_INTERVAL = 15
MAX_CLIPS = 6  # 6 × 5s = 30s final video


_SHOT_VOCABULARY = {
    "exterior": [
        "Wide establishing shot. Camera slowly drifts forward toward the front entrance, "
        "revealing the full facade. Golden warm light. Architecture is the hero.",
        "Low angle push-in toward the front door. Slight upward tilt reveals the roofline. "
        "Confident, impressive.",
    ],
    "living_room": [
        "Camera enters the room from a low angle, gliding forward. Natural light streams "
        "from the windows. Slow arc left reveals the full breadth of the space.",
        "Steady push-in from the doorway threshold. The room opens up as we move deeper in.",
    ],
    "kitchen": [
        "Camera tracks along the countertop at a low angle, revealing the appliances and "
        "cabinetry. Clean, precise movement like a luxury commercial.",
        "Slow push-in from the kitchen entrance. Island or counters fill the foreground.",
    ],
    "dining_room": [
        "Slow orbit around the dining table. Chairs, light fixture, and room come alive "
        "with subtle motion.",
        "Push-in toward the table from the entrance. Warm ambient light.",
    ],
    "bedroom": [
        "Camera floats in from the doorway, gliding low toward the bed. Soft natural light "
        "from the window. Calm, peaceful movement.",
        "Slow arc around the foot of the bed, revealing the full room.",
    ],
    "bathroom": [
        "Slow push-in toward the vanity. Clean surfaces catch the light. "
        "Precise, deliberate movement.",
        "Pan from the shower to the vanity. Elegant, unhurried.",
    ],
    "backyard": [
        "Wide shot. Camera slowly pushes forward across the outdoor space. "
        "Sky and greenery fill the upper frame.",
        "Low angle looking across the yard. Slow drift forward.",
    ],
    "basement": [
        "Camera enters the space and slowly pans to reveal the full room. "
        "Well-lit, open.",
        "Push-in from the stairwell. The space opens up ahead.",
    ],
    "garage": [
        "Wide push-in from the garage door. Clean floor and walls revealed. "
        "Functional and spacious.",
    ],
}

_NARRATIVE_BEATS = {
    0: (
        "OPENING SHOT. This is the viewer's first impression of the property. "
        "Make it cinematic and immediately compelling. "
        "The camera movement should feel like an invitation -- come inside."
    ),
    "middle": (
        "MID-TOUR SHOT. The viewer is already inside the property. "
        "This shot continues the walk-through narrative. "
        "Camera movement should feel like a natural continuation of exploring the space."
    ),
    "closing": (
        "CLOSING SHOT. This is the final image the viewer carries away. "
        "The movement should feel conclusive -- a slow pull-back or wide reveal "
        "that makes the viewer want to book a showing."
    ),
}


def _build_clip_prompt(scene: Dict[str, Any], scene_index: int, total_scenes: int) -> str:
    """Build a videographer-directed Veo prompt grounded in the reference photo."""

    room_type = str(scene.get("room_type") or "room").lower()
    features = scene.get("features") or []
    ken_burns = scene.get("ken_burns") or {}
    pan = ken_burns.get("pan", "center")
    zoom = ken_burns.get("zoom", "in")

    shots = _SHOT_VOCABULARY.get(
        room_type,
        [
            "Slow cinematic push-in. Camera glides forward into the space.",
        ],
    )
    shot_desc = shots[scene_index % len(shots)]

    if scene_index == 0:
        beat = _NARRATIVE_BEATS[0]
    elif scene_index == total_scenes - 1:
        beat = _NARRATIVE_BEATS["closing"]
    else:
        beat = _NARRATIVE_BEATS["middle"]

    camera_override = {
        ("center", "in"): "slow dolly push-in",
        ("right", "in"): "slow push-in arcing right",
        ("left", "in"): "slow push-in arcing left",
        ("center", "out"): "slow dolly pull-back",
        ("right", "out"): "slow pull-back panning right",
        ("left", "out"): "slow pull-back panning left",
    }.get((pan, zoom), "slow cinematic drift")

    anchor = ""
    if features:
        clean = [str(f).strip() for f in features[:3] if str(f).strip()]
        if clean:
            anchor = (
                f"The reference image shows: {', '.join(clean)}. "
                "These must remain accurate in the generated clip. "
                "Do not replace or remove any element visible in the photo."
            )

    return (
        f"Real estate walk-through video. Reference image: {room_type.replace('_', ' ')}.\n\n"
        f"SHOT DIRECTION: {shot_desc}\n"
        f"CAMERA: {camera_override}. Movement is slow, smooth, and deliberate -- "
        f"never shaky, never fast.\n"
        f"NARRATIVE: {beat}\n"
        f"{anchor}\n"
        "TECHNICAL: Photorealistic. Natural lighting preserved from reference image. "
        "No added people, text, watermarks, or props not in the original photo. "
        "Preserve all colors, materials, and proportions from the reference. "
        "Shot on cinema camera, shallow depth of field, smooth stabilised motion."
    )


class VeoRenderer:
    """Render animated property videos using Vertex Veo (google-genai + service account)."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        if creds_json:
            creds_dict = json.loads(creds_json)
            self._creds_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8",
            )
            try:
                json.dump(creds_dict, self._creds_file)
                self._creds_file.flush()
            finally:
                self._creds_file.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._creds_file.name
            logger.info("Loaded service account credentials for Vertex/Veo")
        else:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON not set")

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
        self.project_id = project_id

    async def render_video(
        self,
        scene_plan: List[Dict[str, Any]],
        audio_url: Optional[str] = None,
        headline: str = "Your Dream Home Awaits",
        output_filename: str = "final.mp4",
    ) -> Path:
        """Animate listing photos with Veo following the scene plan order."""

        _ = audio_url, headline  # v1: silent AAC mux only (matches pipeline placeholder)

        if not scene_plan:
            raise ValueError("scene_plan must contain at least one scene")

        # ScenePlanner already ordered scenes; cap at MAX_CLIPS without re-sorting.
        ordered_scenes = scene_plan[:MAX_CLIPS]
        logger.info(
            "Veo scene order: %s",
            [s.get("room_type", "?") for s in ordered_scenes],
        )

        indexed_paths = await self._download_photos_in_order(ordered_scenes)
        if not indexed_paths:
            raise RuntimeError("Failed to download any photos")

        semaphore = asyncio.Semaphore(3)
        total_scenes = len(ordered_scenes)
        tasks = [
            self._generate_clip(
                photo_path, ordered_scenes[scene_idx], scene_idx, total_scenes, semaphore
            )
            for photo_path, scene_idx in indexed_paths
        ]
        clip_results = await asyncio.gather(*tasks, return_exceptions=True)

        with_scene: List[Tuple[int, Path]] = []
        for (photo_path, scene_idx), result in zip(indexed_paths, clip_results):
            if isinstance(result, Exception):
                logger.error(
                    "Clip scene %d (%s) failed: %s",
                    scene_idx,
                    ordered_scenes[scene_idx].get("room_type", "?"),
                    result,
                )
            elif result is not None:
                with_scene.append((scene_idx, result))

        with_scene.sort(key=lambda x: x[0])
        clip_paths = [p for _, p in with_scene]

        if not clip_paths:
            raise RuntimeError("All Veo clip generations failed")

        logger.info(
            "Generated %d/%d Veo clips successfully (ordered by scene index)",
            len(clip_paths),
            len(indexed_paths),
        )

        output_path = self.work_dir / output_filename
        await self._concat_clips(clip_paths, output_path)
        return output_path

    async def _download_photos_in_order(
        self, ordered_scenes: List[Dict[str, Any]]
    ) -> List[Tuple[Path, int]]:
        """Download photos; return (path, scene_index) pairs in scene order."""
        photo_paths: List[Tuple[Path, int]] = []
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            for idx, scene in enumerate(ordered_scenes):
                url = scene.get("photo_url") or scene.get("url")
                if not url:
                    logger.warning("Scene %d has no photo_url, skipping", idx)
                    continue
                filepath = self.work_dir / f"scene_{idx:03d}.jpg"
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    if len(resp.content) < 1000:
                        logger.warning("Scene %d photo too small, skipping", idx)
                        continue
                    filepath.write_bytes(resp.content)
                    logger.info(
                        "Scene %d (%s): downloaded %d bytes",
                        idx,
                        scene.get("room_type", "?"),
                        len(resp.content),
                    )
                    photo_paths.append((filepath, idx))
                except Exception as e:
                    logger.error("Failed to download scene %d: %s", idx, e)

        photo_paths.sort(key=lambda x: x[1])
        return photo_paths

    async def _generate_clip(
        self,
        photo_path: Path,
        scene: Dict[str, Any],
        idx: int,
        total_scenes: int,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Path]:
        """Generate a single Veo clip for one scene."""

        async with semaphore:
            clip_path = self.work_dir / f"veo_clip_{idx:03d}.mp4"
            prompt = _build_clip_prompt(scene, idx, total_scenes)

            logger.info(
                "Clip %d (%s): submitting to Veo\n  Prompt: %s",
                idx,
                scene.get("room_type", "?"),
                prompt,
            )

            image_bytes = photo_path.read_bytes()
            image = types.Image(
                image_bytes=image_bytes,
                mime_type="image/jpeg",
            )

            loop = asyncio.get_event_loop()

            try:
                operation = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_videos(
                        model=VEO_MODEL,
                        prompt=prompt,
                        image=image,
                        config=types.GenerateVideosConfig(
                            number_of_videos=1,
                            duration_seconds=CLIP_DURATION_SECONDS,
                            enhance_prompt=False,
                            aspect_ratio="16:9",
                        ),
                    ),
                )
            except Exception as e:
                logger.error("Veo submission failed for clip %d: %s", idx, e)
                raise

            start = time.time()
            op = operation
            while not op.done:
                await asyncio.sleep(POLL_INTERVAL)
                try:
                    op = await loop.run_in_executor(
                        None,
                        lambda current=op: self.client.operations.get(operation=current),
                    )
                except Exception as e:
                    logger.warning("Poll error clip %d: %s", idx, e)

                elapsed = time.time() - start
                logger.info("Clip %d polling... %.0fs elapsed", idx, elapsed)

                if elapsed > 360:
                    raise TimeoutError(f"Veo clip {idx} timed out after 6 minutes")

            if not (op.response and op.response.generated_videos):
                raise RuntimeError(f"Veo returned no generated_videos for clip {idx}")

            generated = op.response.generated_videos[0]
            video_obj = getattr(generated, "video", None)
            video_bytes: Optional[bytes] = None

            if video_obj is not None:
                try:
                    vb = getattr(video_obj, "video_bytes", None)
                    if vb:
                        video_bytes = vb if isinstance(vb, (bytes, bytearray)) else bytes(vb)
                except Exception:
                    video_bytes = None

            if not video_bytes:
                try:
                    downloaded = self.client.files.download(file=video_obj)
                    if hasattr(downloaded, "read"):
                        video_bytes = downloaded.read()
                    elif hasattr(downloaded, "content"):
                        video_bytes = downloaded.content
                    else:
                        video_bytes = bytes(downloaded)
                except Exception:
                    video_bytes = None

            if not video_bytes and video_obj is not None:
                try:
                    video_obj.save(str(clip_path))
                    if clip_path.exists() and clip_path.stat().st_size > 1000:
                        logger.info(
                            "Clip %d (%s) saved via .save(): %d bytes",
                            idx,
                            scene.get("room_type", "?"),
                            clip_path.stat().st_size,
                        )
                        return clip_path
                except Exception as save_err:
                    logger.warning("Veo .save() failed for clip %d: %s", idx, save_err)

            if not video_bytes:
                raise RuntimeError(f"Veo returned empty bytes for clip {idx}")

            clip_path.write_bytes(video_bytes)
            logger.info(
                "Clip %d (%s) saved: %d bytes",
                idx,
                scene.get("room_type", "?"),
                len(video_bytes),
            )
            return clip_path

    async def _concat_clips(self, clip_paths: List[Path], output_path: Path) -> None:
        """Concatenate Veo clips into final video."""
        concat_file = self.work_dir / "veo_concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.resolve().as_posix()}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-map",
            "0:v:0",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(output_path),
        ]

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=120),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg concat failed (rc={result.returncode}): "
                f"{(result.stderr or '')[-800:]}"
            )

        logger.info("Final video rendered: %s", output_path)
