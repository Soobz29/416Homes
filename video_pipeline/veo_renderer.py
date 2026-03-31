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


def _patch_vertex_generate_videos_response_parser() -> None:
    """Vertex sometimes returns generatedSamples (ML-dev shape); SDK only maps `videos`.

    Without this, `generated_videos` stays empty and every clip fails.
    """
    try:
        from google.genai import models as genai_models
    except Exception as e:
        logger.warning("Veo SDK patch skipped (import): %s", e)
        return

    orig = genai_models._GenerateVideosResponse_from_vertex

    def _extended(
        from_object: Any,
        parent_object: Any = None,
        root_object: Any = None,
    ) -> Any:
        out = orig(from_object, parent_object, root_object)
        if out.get("generated_videos"):
            return out
        if not isinstance(from_object, dict):
            return out
        alt = from_object.get("generatedSamples") or from_object.get("generatedVideos")
        if not alt:
            return out
        out["generated_videos"] = [
            genai_models._GeneratedVideo_from_vertex(item, out, root_object)
            for item in alt
        ]
        return out

    genai_models._GenerateVideosResponse_from_vertex = _extended  # type: ignore[assignment]
    logger.debug("Patched google.genai.models._GenerateVideosResponse_from_vertex for Veo")


_patch_vertex_generate_videos_response_parser()


def _mime_from_image_bytes(data: bytes) -> str:
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _veo_generation_config() -> "types.GenerateVideosConfig":
    """Veo request config. Output resolution is not set — Vertex / Veo chooses the default."""
    comp_raw = (os.getenv("VEO_COMPRESSION") or "optimized").strip().lower()
    compression = (
        types.VideoCompressionQuality.LOSSLESS
        if comp_raw in ("lossless", "high", "best")
        else types.VideoCompressionQuality.OPTIMIZED
    )
    fps_kw: Dict[str, int] = {}
    fps_s = (os.getenv("VEO_FPS") or "").strip()
    if fps_s.isdigit():
        fps_kw["fps"] = max(24, min(60, int(fps_s)))
    return types.GenerateVideosConfig(
        number_of_videos=1,
        duration_seconds=CLIP_DURATION_SECONDS,
        enhance_prompt=False,
        aspect_ratio="16:9",
        compression_quality=compression,
        **fps_kw,
    )


async def _build_clip_prompt_from_vision(
    photo_path: Path,
    scene: Dict[str, Any],
    scene_index: int,
    total_scenes: int,
) -> str:
    """Send photo to Gemini Vision to get a precision Veo shot card."""
    import io

    import PIL.Image

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("No GEMINI_API_KEY -- falling back to static prompt")
        return _build_clip_prompt_static(scene, scene_index, total_scenes)

    try:
        client = genai.Client(api_key=api_key)

        photo_bytes = photo_path.read_bytes()
        img = PIL.Image.open(io.BytesIO(photo_bytes))
        if img.width > 1024:
            ratio = 1024 / img.width
            img = img.resize((1024, int(img.height * ratio)))

        if scene_index == 0:
            tour_context = (
                "CONTINUOUS TOUR -- OPENING: Start of a single walk-through visit. "
                "Establish arrival and invite the viewer into the home. "
                "This shot flows into the following spaces."
            )
        elif scene_index == total_scenes - 1:
            tour_context = (
                "CONTINUOUS TOUR -- CLOSING: Final beat of the same walk-through. "
                "Resolve the visit with a memorable last impression."
            )
        else:
            tour_context = (
                f"CONTINUOUS TOUR -- MID WALK (shot {scene_index + 1} of {total_scenes}): "
                "Same continuous property visit. Motivate forward motion through the home "
                "as if escorting a buyer room-to-room."
            )

        prompt = f"""You are a cinematic prompt engineer for luxury real estate video production.

{tour_context}

Analyze this room photo and write a single precision camera prompt for Veo 2 video generation.

Your prompt must follow this exact structure:

1. Camera movement type (e.g. "Extremely slow, measured, stabilized Micro Dolly-In" or "Smooth lateral slider pan")
2. Direction and focal anchor -- what specific object/feature the camera moves toward or tracks
3. Movement distance and easing -- e.g. "controlled 6-10 inch forward glide, slow-in and slow-out"
4. Environmental micro-motion -- subtle realistic light behavior only (shimmer, reflection, shadow shift)
5. Geometry lock constraints -- all architectural elements must stay perfectly static, vertical lines locked, no warping
6. Quality tags -- end with: 4K, HDR, photorealistic, stabilized slider shot, ultra-clean detail, premium real estate

Write ONE dense paragraph. No bullet points. No headers. Be specific to what you actually see in this image -- identify the exact focal anchor (island, fireplace, window, staircase etc). Under 120 words."""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[prompt, img],
            ),
        )
        result = response.text.strip()
        logger.info("Clip %d vision prompt: %s", scene_index, result[:100])
        return result

    except Exception as e:
        logger.warning(
            "Vision prompt failed for clip %d: %s -- using static fallback",
            scene_index,
            e,
        )
        return _build_clip_prompt_static(scene, scene_index, total_scenes)


def _build_clip_prompt_static(
    scene: Dict[str, Any],
    scene_index: int,
    total_scenes: int,
) -> str:
    """Static fallback prompt when Gemini Vision is unavailable."""
    room_type = str(scene.get("room_type") or "room").replace("_", " ")
    features = scene.get("features") or []
    ken_burns = scene.get("ken_burns") or {}
    pan = ken_burns.get("pan", "center")
    zoom = ken_burns.get("zoom", "in")

    camera = {
        ("center", "in"): "extremely slow stabilized micro dolly-in",
        ("right", "in"): "slow push-in with gentle rightward arc",
        ("left", "in"): "slow push-in tracking slightly left",
        ("center", "out"): "graceful slow pull-back dolly",
        ("right", "out"): "slow pull-back panning right",
        ("left", "out"): "slow pull-back panning left",
    }.get((pan, zoom), "smooth slow stabilized camera drift")

    anchor = ""
    if features:
        clean = [str(f).strip() for f in features[:2] if str(f).strip()]
        if clean:
            anchor = f" Focal anchor: {' and '.join(clean)}."

    if scene_index == 0:
        beat = "OPENING: establish the property and invite the viewer in."
    elif scene_index == total_scenes - 1:
        beat = "CLOSING: resolve the tour with a memorable final impression."
    else:
        beat = (
            f"MID-TOUR shot {scene_index + 1} of {total_scenes}: continue the walk-through."
        )

    return (
        f"{beat} {room_type.capitalize()} -- {camera}.{anchor} "
        "Natural lighting preserved. Vertical lines locked, no warping. "
        "4K, HDR, photorealistic, stabilized slider shot, premium real estate presentation."
    )


def _generated_videos_from_operation(op: Any) -> Optional[List[Any]]:
    """Prefer `result` (SDK examples); fall back to `response`."""
    for container in (getattr(op, "result", None), getattr(op, "response", None)):
        if container is None:
            continue
        gv = getattr(container, "generated_videos", None)
        if gv:
            return list(gv)
    return None


def _log_veo_empty_response(idx: int, op: Any) -> None:
    for container in (getattr(op, "result", None), getattr(op, "response", None)):
        if container is None:
            continue
        rai_n = getattr(container, "rai_media_filtered_count", None)
        rai_r = getattr(container, "rai_media_filtered_reasons", None)
        if rai_n is not None or rai_r:
            logger.warning(
                "Veo clip %d RAI: count=%s reasons=%s",
                idx,
                rai_n,
                rai_r,
            )
    err = getattr(op, "error", None)
    if err:
        logger.error("Veo clip %d operation error: %s", idx, err)


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

    async def _run_veo_clip(
        self,
        clip_path: Path,
        prompt: str,
        image: types.Image,
        idx: int,
        scene: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
    ) -> Path:
        """Submit Veo job, poll, write ``clip_path``."""

        def _submit() -> Any:
            return self.client.models.generate_videos(
                model=VEO_MODEL,
                source=types.GenerateVideosSource(
                    prompt=prompt,
                    image=image,
                ),
                config=_veo_generation_config(),
            )

        try:
            operation = await loop.run_in_executor(None, _submit)
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

        if getattr(op, "error", None):
            raise RuntimeError(f"Veo operation failed for clip {idx}: {op.error}")

        gv_list = _generated_videos_from_operation(op)
        if not gv_list:
            _log_veo_empty_response(idx, op)
            raise RuntimeError(f"Veo returned no generated_videos for clip {idx}")

        generated = gv_list[0]
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
            prompt = await _build_clip_prompt_from_vision(
                photo_path, scene, idx, total_scenes
            )

            logger.info(
                "Clip %d (%s): submitting to Veo (Vertex default output resolution)\n  Prompt: %s",
                idx,
                scene.get("room_type", "?"),
                prompt,
            )

            image_bytes = photo_path.read_bytes()
            mime = _mime_from_image_bytes(image_bytes)
            image = types.Image(
                image_bytes=image_bytes,
                mime_type=mime,
            )

            loop = asyncio.get_running_loop()
            return await self._run_veo_clip(
                clip_path, prompt, image, idx, scene, loop
            )

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
            (os.getenv("VIDEO_AAC_BITRATE") or "192k").strip(),
            "-shortest",
            str(output_path),
        ]

        loop = asyncio.get_running_loop()
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
