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
from typing import Any, Dict, List, Optional

import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-2.0-generate-001"
CLIP_DURATION_SECONDS = 5
POLL_INTERVAL = 15
MAX_CLIPS = 6  # 6 × 5s = 30s final video


def _build_clip_prompt(scene: Dict[str, Any]) -> str:
    """Build a Veo prompt from a scene plan entry."""

    room_type = scene.get("room_type", "room")
    features = scene.get("features", [])
    ken_burns = scene.get("ken_burns", {})
    pan = ken_burns.get("pan", "center")
    zoom = ken_burns.get("zoom", "in")

    room_descriptions = {
        "exterior": "exterior of the property, architectural details, curb appeal",
        "living_room": "bright spacious living room, comfortable seating area",
        "kitchen": "modern kitchen, countertops and cabinetry",
        "bedroom": "serene bedroom, natural light through windows",
        "bathroom": "clean elegant bathroom, fixtures and finishes",
        "dining_room": "dining room, ideal for entertaining",
        "basement": "finished lower level, additional living space",
        "backyard": "outdoor living space, landscaped backyard",
        "garage": "garage and parking area",
    }
    room_desc = room_descriptions.get(room_type, f"{str(room_type).replace('_', ' ')}")

    feature_text = ""
    if features:
        feature_text = f" featuring {', '.join(str(f) for f in features[:3])}"

    camera_map = {
        ("left", "in"): "slow push-in with gentle pan left",
        ("right", "in"): "slow push-in with gentle pan right",
        ("center", "in"): "slow cinematic push-in",
        ("left", "out"): "slow pull-back with pan left",
        ("right", "out"): "slow pull-back with pan right",
        ("center", "out"): "slow cinematic pull-back",
    }
    camera = camera_map.get((pan, zoom), "smooth slow camera movement")

    prompt = (
        f"Professional real estate photography, {room_desc}{feature_text}. "
        f"{camera.capitalize()}. Cinematic quality, steady motion, warm lighting. "
        f"No people, no text overlays."
    )

    return prompt


class VeoRenderer:
    """Render animated property videos using Vertex Veo (google-genai + service account)."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "416homes")
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

        photo_paths = await self._download_photos_in_order(ordered_scenes)
        if not photo_paths:
            raise RuntimeError("Failed to download any photos")

        semaphore = asyncio.Semaphore(3)
        tasks = [
            self._generate_clip(photo_path, ordered_scenes[i], i, semaphore)
            for i, photo_path in enumerate(photo_paths)
        ]
        clip_results = await asyncio.gather(*tasks, return_exceptions=True)

        clip_paths: List[Path] = []
        for i, result in enumerate(clip_results):
            if isinstance(result, Exception):
                logger.error(
                    "Clip %d (%s) failed: %s",
                    i,
                    ordered_scenes[i].get("room_type", "?"),
                    result,
                )
            elif result is not None:
                clip_paths.append(result)

        if not clip_paths:
            raise RuntimeError("All Veo clip generations failed")

        logger.info(
            "Generated %d/%d Veo clips successfully",
            len(clip_paths),
            len(photo_paths),
        )

        output_path = self.work_dir / output_filename
        await self._concat_clips(clip_paths, output_path)
        return output_path

    async def _download_photos_in_order(
        self, ordered_scenes: List[Dict[str, Any]]
    ) -> List[Path]:
        """Download photos following scene plan order."""
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

        return [p for p, _ in sorted(photo_paths, key=lambda x: x[1])]

    async def _generate_clip(
        self,
        photo_path: Path,
        scene: Dict[str, Any],
        idx: int,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Path]:
        """Generate a single Veo clip for one scene."""

        async with semaphore:
            clip_path = self.work_dir / f"veo_clip_{idx:03d}.mp4"
            prompt = _build_clip_prompt(scene)

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
