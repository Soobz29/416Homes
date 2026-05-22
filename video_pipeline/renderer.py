"""FFmpeg-based video renderer with Ken Burns-style effects and optional audio."""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    """Return the path to an ffmpeg executable.

    Search order:
    1. FFMPEG_PATH env var (explicit override)
    2. System PATH (shutil.which)
    3. imageio-ffmpeg bundled binary (pip-installed, no apt needed)
    """
    override = os.getenv("FFMPEG_PATH", "").strip()
    if override:
        return override

    system = shutil.which("ffmpeg")
    if system:
        return system

    try:
        import imageio_ffmpeg  # type: ignore
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info("Using imageio-ffmpeg bundled binary: %s", exe)
        return exe
    except Exception as e:
        logger.warning("imageio-ffmpeg not available: %s", e)

    # Last resort — let the subprocess raise a clear error
    return "ffmpeg"


_FFMPEG_EXE: Optional[str] = None


def _ffmpeg() -> str:
    """Cached ffmpeg executable path."""
    global _FFMPEG_EXE
    if _FFMPEG_EXE is None:
        _FFMPEG_EXE = _find_ffmpeg()
    return _FFMPEG_EXE


def _libx264_quality_args() -> List[str]:
    """H.264 quality for slideshow output (tune via VIDEO_H264_PRESET / VIDEO_H264_CRF).

    Default preset is 'veryfast' to keep peak RAM under ~300 MB on constrained workers
    (0.5 GB DO instances).  Override with VIDEO_H264_PRESET=medium for local/higher-RAM builds.
    """
    preset = (os.getenv("VIDEO_H264_PRESET") or "veryfast").strip()
    crf_s = (os.getenv("VIDEO_H264_CRF") or "23").strip()
    try:
        crf = max(0, min(51, int(crf_s)))
    except ValueError:
        crf = 20
    return ["-preset", preset, "-crf", str(crf)]


class VideoRenderer:
    """Render video from photos using FFmpeg with Ken Burns effects."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._encoder_cache: Optional[str] = None

    def _run_ffmpeg_probe(self, args: List[str], timeout_sec: int = 5) -> subprocess.CompletedProcess[str]:
        """Run a small ffmpeg/ffprobe command and capture output."""
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout_sec)

    def _choose_video_encoder(self) -> str:
        """Pick a H.264-ish encoder that exists in the current ffmpeg build."""
        if self._encoder_cache:
            return self._encoder_cache

        candidates = ["libx264", "libopenh264", "h264_nvenc", "h264_qsv", "h264_vaapi", "mpeg4"]
        for enc in candidates:
            try:
                # `-h encoder=NAME` returns 0 if encoder exists, non-0 otherwise.
                p = self._run_ffmpeg_probe([_ffmpeg(), "-hide_banner", "-h", f"encoder={enc}"], timeout_sec=5)
                if p.returncode == 0:
                    self._encoder_cache = enc
                    return enc
            except Exception:
                continue

        # Last resort — keep current behavior; failure logs will explain why.
        self._encoder_cache = "libx264"
        return self._encoder_cache

    async def render_video(
        self,
        scene_plan: List[Dict[str, Any]],
        audio_url: Optional[str] = None,
        headline: str = "Luxury Property",
        output_filename: str = "final.mp4",
    ) -> Path:
        """
        Render final MP4 from scene plan.

        Args:
            scene_plan: List of scenes with photo_url, timing, ken_burns
            audio_url: Optional audio track URL
            headline: Text overlay at start
            output_filename: Output file name
        """
        if not scene_plan:
            raise ValueError("scene_plan must contain at least one scene")

        logger.info("Rendering video with %d scenes", len(scene_plan))

        photo_paths = await self._download_photos(scene_plan)
        if not photo_paths:
            raise RuntimeError("Failed to download any photos for rendering")

        audio_path: Optional[Path] = None
        if audio_url:
            audio_path = await self._download_audio(audio_url)

        output_path = self.work_dir / output_filename

        logger.info("🖼️ photo_paths count: %d", len(photo_paths))
        logger.info("🖼️ photo_paths: %s", photo_paths[:3])

        self._render_slideshow(photo_paths, scene_plan, audio_path, headline, output_path)

        logger.info("Video rendered at %s", output_path)
        return output_path

    async def _download_photos(self, scene_plan: List[Dict[str, Any]]) -> List[Path]:
        """Download all photos to work directory and validate them."""

        photo_paths: List[Path] = []

        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            for idx, scene in enumerate(scene_plan):
                url = scene["photo_url"]
                filename = f"frame_{idx:03d}.jpg"
                filepath = self.work_dir / filename

                try:
                    logger.info("Downloading scene %d: %s", idx, url[:80])
                    resp = await client.get(url)
                    resp.raise_for_status()

                    # Validate we got actual image data
                    content_type = resp.headers.get("content-type", "")
                    content_length = len(resp.content)

                    if content_length < 1000:  # Less than 1KB is suspicious
                        logger.warning("Skipping scene %d: file too small (%d bytes)", idx, content_length)
                        continue

                    if "image" not in content_type and content_length < 50000:
                        logger.warning("Skipping scene %d: unexpected content-type '%s'", idx, content_type)
                        continue

                    # Write file
                    filepath.write_bytes(resp.content)

                    # Validate with magic bytes (JPEG: FF D8 FF, PNG: 89 50 4E 47, WEBP: RIFF...WEBP)
                    # This replaces ffprobe which is not guaranteed to be installed on all workers.
                    data = resp.content
                    is_jpeg = data[:3] == b"\xff\xd8\xff"
                    is_png = data[:4] == b"\x89PNG"
                    is_webp = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
                    if not (is_jpeg or is_png or is_webp):
                        logger.warning(
                            "Skipping scene %d: unrecognised image magic bytes %s",
                            idx,
                            data[:4].hex(),
                        )
                        filepath.unlink(missing_ok=True)
                        continue

                    # Try ffprobe for extra validation only if available — never fail on its absence
                    try:
                        probe_cmd = [
                            "ffprobe", "-v", "error",
                            "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name,width,height",
                            "-of", "default=noprint_wrappers=1",
                            str(filepath),
                        ]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
                        if probe_result.returncode != 0:
                            logger.warning(
                                "ffprobe rejected scene %d (%s) — keeping anyway (magic bytes OK)",
                                idx, (probe_result.stderr or "")[:120],
                            )
                    except FileNotFoundError:
                        pass  # ffprobe not installed — magic bytes check is sufficient

                    logger.info(
                        "✅ Downloaded valid image: %s (%d bytes, %s)",
                        filename,
                        content_length,
                        content_type,
                    )
                    photo_paths.append(filepath)

                except Exception as e:
                    logger.error("Failed to download scene %d from %s: %s", idx, url[:80], e)

        logger.info("Successfully downloaded %d/%d valid photos", len(photo_paths), len(scene_plan))
        return photo_paths

    async def _download_audio(self, audio_url: str) -> Path:
        """Download audio file to work directory."""

        audio_path = self.work_dir / "audio.mp3"

        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            audio_path.write_bytes(resp.content)

        return audio_path

    # ------------------------------------------------------------------
    # Ken Burns helpers
    # ------------------------------------------------------------------

    def _make_ken_burns_clip(
        self,
        photo_path: Path,
        duration: float,
        zoom_dir: str,
        pan_dir: str,
        output_path: Path,
        w: int,
        h: int,
        fps: int,
        enc: str,
        enc_opts: List[str],
    ) -> None:
        """Render a single Ken Burns clip with smooth zoom + pan from a still photo.

        Strategy
        --------
        1. Pre-scale the photo to 2× the output size (2560×1440 for 1280×720 output)
           so the zoompan filter has headroom to zoom in up to 1.5× without
           exceeding the source boundaries.
        2. Apply ``zoompan`` with per-frame zoom/pan expressions.
        3. Encode at the requested resolution / codec.
        """
        frames = max(int(duration * fps), 1)
        z_step = round(0.35 / frames, 8)   # 1.0 → 1.35 (or reverse) over clip

        # Zoom expressions ---------------------------------------------------
        if zoom_dir == "in":
            z_expr = f"min(zoom+{z_step},1.35)"
        else:  # "out"
            # seed to 1.35 on frame 1, then shrink back to 1.0
            z_expr = f"if(eq(on,1),1.35,max(zoom-{z_step},1.0))"

        # Pan expressions (2 px/frame drift on 2× source = very subtle) ------
        px = 2
        if pan_dir == "right":
            x_expr = f"min(iw-iw/zoom,max(0,iw/2-iw/zoom/2+{px}*on))"
        elif pan_dir == "left":
            x_expr = f"min(iw-iw/zoom,max(0,iw/2-iw/zoom/2-{px}*on))"
        else:  # center — gentle vertical drift only
            x_expr = "iw/2-iw/zoom/2"

        y_expr = "ih/2-ih/zoom/2"   # always vertically centred

        src_w, src_h = w * 2, h * 2   # 2× source for zoom headroom
        vf = (
            f"scale={src_w}:{src_h}:force_original_aspect_ratio=increase,"
            f"crop={src_w}:{src_h},"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={frames}:s={w}x{h}:fps={fps},"
            f"format=yuv420p"
        )

        cmd: List[str] = [
            _ffmpeg(), "-y",
            "-loop", "1",
            "-framerate", str(fps),
            "-t", f"{duration + 0.5:.3f}",   # slight overrun so zoompan has input
            "-i", str(photo_path),
            "-vf", vf,
            "-c:v", enc, *enc_opts,
            "-r", str(fps),
            "-t", f"{duration:.3f}",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(
                f"Ken Burns clip {output_path.name} failed "
                f"(rc={result.returncode}): {(result.stderr or '')[-600:]}"
            )

    def _xfade_concat(
        self,
        clip_paths: List[Path],
        clip_dur: float,
        fade_dur: float,
        output_path: Path,
        fps: int,
        enc: str,
        enc_opts: List[str],
    ) -> None:
        """Concatenate pre-rendered clips with xfade crossfade transitions.

        Each clip overlaps the next by ``fade_dur`` seconds, so the total
        output duration = N * clip_dur - (N-1) * fade_dur ≈ 30 s.
        """
        n = len(clip_paths)
        if n < 2:
            raise ValueError("Need ≥ 2 clips for xfade concat")

        # Build filter_complex -----------------------------------------------
        parts: List[str] = []

        # Normalise PTS for each input stream
        for i in range(n):
            parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

        # Chain xfades: [v0][v1]→[x0], [x0][v2]→[x1], …, [x_{n-3}][v_{n-1}]→[vout]
        prev = "v0"
        for k in range(n - 1):
            offset = round((k + 1) * (clip_dur - fade_dur), 4)
            out_label = "vout" if k == n - 2 else f"x{k}"
            parts.append(
                f"[{prev}][v{k+1}]"
                f"xfade=transition=fade:duration={fade_dur:.3f}:offset={offset:.4f}"
                f"[{out_label}]"
            )
            prev = out_label

        filter_complex = ";".join(parts)

        cmd: List[str] = [_ffmpeg(), "-y"]
        for cp in clip_paths:
            cmd += ["-i", str(cp)]
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", enc, *enc_opts,
            "-r", str(fps),
            "-t", "30",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(
                f"xfade concat failed (rc={result.returncode}): "
                f"{(result.stderr or '')[-800:]}"
            )

    def _render_slideshow(
        self,
        photo_paths: List[Path],
        scene_plan: List[Dict[str, Any]],
        audio_path: Optional[Path],
        headline: str,
        output_path: Path,
    ) -> None:
        """Render a professional Ken Burns video with smooth zoom/pan + xfade transitions.

        Each photo gets a unique zoom direction (in/out alternating) and pan direction
        (right/left/center cycling) driven by the scene_plan ``ken_burns`` field.
        Clips are then crossfaded together with a 0.5-second dissolve.
        """
        if not photo_paths:
            raise ValueError("photo_paths must not be empty")

        fps    = 25
        fade   = 0.5    # crossfade duration between clips (seconds)
        total  = 30.0   # target output duration

        # ── Pad to ≥ 6 photos ────────────────────────────────────────────────
        padded = list(photo_paths)
        while len(padded) < 6:
            padded.extend(photo_paths)
        padded = padded[: max(6, len(photo_paths))]
        n = len(padded)

        # Duration of each source clip (includes fade overlap with neighbour)
        clip_dur = (total + (n - 1) * fade) / n

        # Pad scene_plan to match
        plan: List[Dict[str, Any]] = list(scene_plan or [])
        while len(plan) < n:
            plan.append({})
        plan = plan[:n]

        w   = int(os.getenv("VIDEO_OUTPUT_WIDTH",  "1280"))
        h   = int(os.getenv("VIDEO_OUTPUT_HEIGHT", "720"))
        enc = self._choose_video_encoder()
        enc_opts: List[str] = (
            _libx264_quality_args() if enc == "libx264"
            else ["-preset", "veryfast", "-crf", "23"]
        )

        # ── Step 1: Ken Burns per-clip ────────────────────────────────────────
        clip_paths: List[Path] = []
        abs_photos = [p.resolve() for p in padded]

        for i, (photo, scene) in enumerate(zip(abs_photos, plan)):
            cp  = self.work_dir / f"clip_{i:03d}.mp4"
            kb  = (scene or {}).get("ken_burns", {})
            # Fall back to alternating zoom + cycling pan when not specified
            zoom_dir = (kb.get("zoom") or ("in" if i % 2 == 0 else "out")).lower()
            pan_dir  = (kb.get("pan")  or ["right", "left", "center"][i % 3]).lower()
            self._make_ken_burns_clip(
                photo, clip_dur, zoom_dir, pan_dir,
                cp, w, h, fps, enc, enc_opts,
            )
            clip_paths.append(cp)
            logger.info("Ken Burns clip %d/%d done (%s/%s): %s", i + 1, n, zoom_dir, pan_dir, cp.name)

        # ── Step 2: Concatenate with xfade ───────────────────────────────────
        if n == 1:
            combined = clip_paths[0]
        else:
            combined = self.work_dir / "combined.mp4"
            try:
                self._xfade_concat(clip_paths, clip_dur, fade, combined, fps, enc, enc_opts)
            except Exception as exc:
                # xfade unavailable (older ffmpeg build) → fall back to hard cuts
                logger.warning("xfade failed (%s) — using hard-cut fallback", exc)
                combined = self.work_dir / "combined_hc.mp4"
                clips_txt = self.work_dir / "clips.txt"
                with open(clips_txt, "w", encoding="utf-8") as f:
                    for cp in clip_paths:
                        f.write(f"file '{cp.resolve().as_posix()}'\n")
                res = subprocess.run(
                    [_ffmpeg(), "-y", "-f", "concat", "-safe", "0",
                     "-i", str(clips_txt), "-c:v", enc, *enc_opts,
                     "-r", str(fps), "-t", "30", str(combined)],
                    capture_output=True, text=True, timeout=300,
                )
                if res.returncode != 0:
                    raise RuntimeError(f"Hard-cut fallback failed: {res.stderr[-500:]}")

        # ── Step 3: Add audio track (real or silent) ─────────────────────────
        if audio_path and audio_path.exists() and audio_path.stat().st_size > 1000:
            audio_inputs: List[str] = ["-i", str(audio_path)]
            audio_filter: List[str] = ["-af", "apad=whole_dur=30"]
        else:
            audio_inputs = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            audio_filter = []

        aac_br = (os.getenv("VIDEO_AAC_BITRATE") or "192k").strip()
        cmd: List[str] = [
            _ffmpeg(), "-y",
            "-i", str(combined),
            *audio_inputs,
            "-map", "0:v:0",
            "-map", "1:a",
            *audio_filter,
            "-c:v", "copy",          # video is already encoded — just remux
            "-c:a", "aac", "-b:a", aac_br,
            "-t", "30",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning(
                "Audio-add step failed (rc=%s) — using combined directly: %s",
                result.returncode, (result.stderr or "")[-600:],
            )
            import shutil
            shutil.copy(str(combined), str(output_path))
        else:
            logger.info("✅ Ken Burns video rendered: %s", output_path)

        logger.info("✅ Video rendered: %s", output_path)
