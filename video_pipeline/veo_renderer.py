"""Veo-based video renderer — Vertex Veo via service account (GOOGLE_APPLICATION_CREDENTIALS_JSON)."""

from __future__ import annotations

import asyncio
import functools
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


def _trim_clip(clip_path: Path) -> Path:
    """Drop the soft Veo ramp at the start.

    ``VEO_TRIM_MODE=copy`` uses stream copy (fast) but the first output frame can sit on a
    non-ideal packet and look blurry. Default ``reencode`` places ``-ss`` after ``-i`` and
    re-encodes so frame 0 is a clean IDR that matches the photo.
    """
    trimmed_path = clip_path.with_stem(clip_path.stem + "_trimmed")
    trim_sec = float(os.getenv("VEO_TRIM_START_SEC", "0.35"))
    mode = (os.getenv("VEO_TRIM_MODE") or "reencode").strip().lower()

    if mode == "copy":
        trim_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(trim_sec),
            "-i",
            str(clip_path),
            "-c",
            "copy",
            str(trimmed_path),
        ]
    else:
        preset = (os.getenv("VEO_TRIM_PRESET") or "fast").strip()
        crf = (os.getenv("VEO_TRIM_CRF") or "18").strip()
        trim_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(clip_path),
            "-ss",
            str(trim_sec),
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(trimmed_path),
        ]

    result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 and trimmed_path.exists() and trimmed_path.stat().st_size > 1000:
        return trimmed_path
    logger.warning("Clip trim failed (rc=%s), using original", result.returncode)
    return clip_path


def _ffprobe_duration_sec(path: Path) -> float:
    """Duration in seconds (float); fallback if ffprobe fails."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return max(0.1, float(r.stdout.strip()))
    except (ValueError, subprocess.TimeoutExpired, OSError) as e:
        logger.warning("ffprobe duration failed for %s: %s", path.name, e)
    return max(0.1, float(CLIP_DURATION_SECONDS) - float(os.getenv("VEO_TRIM_START_SEC", "0.35")))


def _xfade_merge_two_sync(
    left: Path,
    right: Path,
    out_path: Path,
    offset: float,
    xfade_dur: float,
    crf: str,
    preset: str,
) -> None:
    """Merge two videos with a crossfade; video only (no audio). ~2 inputs = low RAM."""
    oc = round(offset, 3)
    xd = round(xfade_dur, 3)
    tune = (os.getenv("VIDEO_XFADE_TUNE") or "stillimage").strip()
    fc = (
        f"[0:v]format=yuv420p,setsar=1[v0];"
        f"[1:v]format=yuv420p,setsar=1[v1];"
        f"[v0][v1]xfade=transition=fade:duration={xd}:offset={oc}[vout]"
    )
    x264_args: List[str] = [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        crf,
    ]
    if tune and tune.lower() not in ("none", "off", "0"):
        x264_args.extend(["-tune", tune])
    x264_args.extend(
        [
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "2",
            str(out_path),
        ]
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(left),
        "-i",
        str(right),
        "-filter_complex",
        fc,
        "-map",
        "[vout]",
        "-an",
        *x264_args,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(
            f"FFmpeg pairwise xfade failed (rc={r.returncode}): "
            f"{(r.stderr or '')[-1200:]}"
        )


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
    fps_s = (os.getenv("VEO_FPS") or "30").strip()
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

        opening_extra = ""
        if scene_index == 0:
            opening_extra = (
                "\nOPENING SHOT: The very first frame must be tack-sharp and identical in clarity to the still photo — "
                "no fade-in from black, no soft morph, no motion blur on walls or cabinetry.\n"
            )

        prompt = f"""You are a cinematographer directing a real estate video clip from a single still photograph.
{opening_extra}
STRICT RULES — the generated video must look like the photo came to life, NOT like AI art:
- Camera moves only. The room/space must not change.
- No new objects, people, furniture, windows, or architectural elements.
- No lighting changes beyond subtle natural variation (no dramatic golden hour shifts).
- No depth-of-field bokeh that wasn't in the photo.
- Preserve exact colors, materials, textures from the photo.

Prescribe ONE smooth camera movement that reads clearly as video (not a slideshow). Choose from:
- Slow push-in (about 8–15 cm forward over the full 5 seconds)
- Slow pull-back (about 8–15 cm backward over 5 seconds)
- Slow lateral slide or arc (about 8–12 cm side-to-side over 5 seconds)
- Slow tilt down or up (about 2–4 degrees over 5 seconds)

Write a single sentence under 35 words.
Format: "[Camera movement]. [What the camera moves toward]. Preserve all room elements exactly as photographed."

Example: "Slow smooth push-in toward the kitchen island. Preserve all room elements exactly as photographed."

Analyze this photo and write the camera direction:"""

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
        ("center", "in"): "slow smooth stabilized dolly-in with visible forward motion",
        ("right", "in"): "slow push-in with gentle rightward arc and clear parallax",
        ("left", "in"): "slow push-in tracking slightly left with clear parallax",
        ("center", "out"): "graceful slow pull-back dolly with visible depth change",
        ("right", "out"): "slow pull-back panning right",
        ("left", "out"): "slow pull-back panning left",
    }.get((pan, zoom), "smooth slow stabilized camera move with readable motion")

    anchor = ""
    if features:
        clean = [str(f).strip() for f in features[:2] if str(f).strip()]
        if clean:
            anchor = f" Focal anchor: {' and '.join(clean)}."

    if scene_index == 0:
        beat = (
            "OPENING: first frame must be tack-sharp like the photograph — no soft morph or blur; "
            "establish the property and invite the viewer in."
        )
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
                    clip_path = await loop.run_in_executor(None, _trim_clip, clip_path)
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
        clip_path = await loop.run_in_executor(None, _trim_clip, clip_path)
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
        """Concatenate Veo clips into final video with 0.3s crossfade between clips."""
        loop = asyncio.get_running_loop()
        aac_bitrate = (os.getenv("VIDEO_AAC_BITRATE") or "192k").strip()

        if len(clip_paths) == 1:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(clip_paths[0]),
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map", "0:v:0", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", aac_bitrate,
                "-shortest", str(output_path),
            ]
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=120),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg single-clip failed (rc={result.returncode}): "
                    f"{(result.stderr or '')[-800:]}"
                )
            logger.info("Final video rendered: %s", output_path)
            return

        # Multiple clips — pairwise xfade (only 2 decodes at a time). One giant
        # filter_complex with N inputs spikes RAM and gets SIGKILL (rc=-9) on small hosts.
        xfade_dur = 0.3
        crf = (os.getenv("VIDEO_XFADE_CRF") or "18").strip()
        preset = (os.getenv("VIDEO_XFADE_PRESET") or "fast").strip()

        acc = clip_paths[0]
        for i in range(1, len(clip_paths)):
            prev = acc
            dur_left = _ffprobe_duration_sec(Path(prev))
            offset = max(0.05, dur_left - xfade_dur)
            step_out = self.work_dir / f"_xfade_pair_{i}.mp4"
            logger.info(
                "xfade merge step %d/%d: offset=%.3fs (left dur=%.3fs)",
                i,
                len(clip_paths) - 1,
                offset,
                dur_left,
            )
            await loop.run_in_executor(
                None,
                functools.partial(
                    _xfade_merge_two_sync,
                    Path(prev),
                    clip_paths[i],
                    step_out,
                    offset,
                    xfade_dur,
                    crf,
                    preset,
                ),
            )
            if i > 1:
                try:
                    Path(prev).unlink(missing_ok=True)
                except OSError as e:
                    logger.warning("Could not remove temp xfade file %s: %s", prev, e)
            acc = step_out

        mux_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(acc),
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
            aac_bitrate,
            "-shortest",
            str(output_path),
        ]
        result = await loop.run_in_executor(
            None,
            functools.partial(
                subprocess.run,
                mux_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            ),
        )
        try:
            Path(acc).unlink(missing_ok=True)
        except OSError:
            pass

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg final mux after xfade failed (rc={result.returncode}): "
                f"{(result.stderr or '')[-800:]}"
            )

        logger.info("Final video rendered with crossfade (pairwise): %s", output_path)
