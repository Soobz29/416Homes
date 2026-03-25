"""FFmpeg-based video renderer with Ken Burns-style effects and optional audio."""

import subprocess
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


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
                p = self._run_ffmpeg_probe(["ffmpeg", "-hide_banner", "-h", f"encoder={enc}"], timeout_sec=5)
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

                    # Verify it's a valid image using ffprobe
                    probe_cmd = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=codec_name,width,height",
                        "-of",
                        "default=noprint_wrappers=1",
                        str(filepath),
                    ]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)

                    if probe_result.returncode != 0:
                        logger.warning(
                            "Skipping scene %d: ffprobe failed - %s",
                            idx,
                            (probe_result.stderr or "")[:200],
                        )
                        filepath.unlink(missing_ok=True)
                        continue

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

    def _render_slideshow(
        self,
        photo_paths: List[Path],
        scene_plan: List[Dict[str, Any]],
        audio_path: Optional[Path],
        headline: str,
        output_path: Path,
    ) -> None:
        """Render 30-second slideshow with Ken Burns effects using two-pass approach."""

        if not photo_paths:
            raise ValueError("photo_paths must not be empty")

        duration_per_photo = 30.0 / len(photo_paths)

        # --- FFmpeg preflight (version + encoder availability) ---
        try:
            v = self._run_ffmpeg_probe(["ffmpeg", "-hide_banner", "-version"], timeout_sec=5)
            logger.info("FFmpeg preflight: rc=%s", v.returncode)
            if (v.stdout or "").strip():
                logger.info("FFmpeg preflight stdout (tail): %s", (v.stdout or "")[-800:])
            if (v.stderr or "").strip():
                logger.info("FFmpeg preflight stderr (tail): %s", (v.stderr or "")[-800:])
        except Exception as e:
            logger.exception("FFmpeg preflight failed to execute: %s", e)

        chosen_encoder = self._choose_video_encoder()
        logger.info("FFmpeg encoder chosen for Pass1/Pass2: %s", chosen_encoder)
        logger.info(
            "Timing: photo_count=%d duration_per_photo=%.3fs fps=25 (~%.1f frames)",
            len(photo_paths),
            duration_per_photo,
            duration_per_photo * 25,
        )

        # PASS 1: Convert each photo to a video clip with Ken Burns effect
        clip_paths: List[Path] = []
        debug_failures_logged = 0

        for i, photo in enumerate(photo_paths):
            clip_path = self.work_dir / f"clip_{i:03d}.mp4"

            # Create individual clip (minimal scale/crop)
            photo_exists = photo.exists()
            photo_size = photo.stat().st_size if photo_exists else None
            jpeg_magic_ok: Optional[bool] = None
            if photo_exists:
                try:
                    with photo.open("rb") as f:
                        jpeg_magic_ok = f.read(2) == b"\xff\xd8"
                except Exception:
                    jpeg_magic_ok = None

            if not photo_exists or not photo_size:
                logger.error(
                    "Skipping frame %d: missing/empty file (exists=%s size=%s) path=%s",
                    i,
                    photo_exists,
                    photo_size,
                    photo,
                )
                continue

            if jpeg_magic_ok is False:
                logger.error("Skipping frame %d: not a JPEG (magic mismatch) path=%s", i, photo)
                continue

            cmd: List[str] = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-framerate",
                "25",
                "-i",
                str(photo),
                "-vf",
                "scale=1920:1080,format=yuv420p",
                "-c:v",
                chosen_encoder,
                "-preset",
                "fast",
                "-crf",
                "28",
                "-t",
                str(duration_per_photo),
                "-r",
                "25",
                "-pix_fmt",
                "yuv420p",
                str(clip_path),
            ]

            started = time.time()
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired as e:
                elapsed = time.time() - started
                logger.error("FFmpeg timed out creating clip %d after %.2fs from %s", i, elapsed, photo)
                logger.error("FFmpeg cmd: %s", " ".join(cmd))
                logger.error("FFmpeg stderr (tail): %s", (getattr(e, "stderr", "") or "")[-8000:])
                logger.error("FFmpeg stdout (tail): %s", (getattr(e, "stdout", "") or "")[-2000:])
                continue
            except OSError as e:
                elapsed = time.time() - started
                logger.exception("FFmpeg failed to start for clip %d after %.2fs: %s", i, elapsed, e)
                logger.error("FFmpeg cmd: %s", " ".join(cmd))
                continue

            if result.returncode != 0:
                elapsed = time.time() - started
                logger.error("❌ Failed to create clip %d from %s", i, photo)
                logger.error("FFmpeg cmd: %s", " ".join(cmd))
                # With -hide_banner -loglevel error, stderr should contain the real failure.
                logger.error("FFmpeg stderr (tail): %s", (result.stderr or "")[-8000:])
                logger.error("FFmpeg stdout (tail): %s", (result.stdout or "")[-2000:])
                logger.error("FFmpeg rc=%s elapsed=%.2fs photo_size=%s jpeg_magic_ok=%s", result.returncode, elapsed, photo_size, jpeg_magic_ok)
                debug_failures_logged += 1
                continue

            logger.info("✅ Created clip %d: %s", i, clip_path.name)
            clip_paths.append(clip_path)

        if not clip_paths:
            logger.error(
                "Pass1 produced 0 clips (photo_count=%d duration_per_photo=%.3fs work_dir=%s)",
                len(photo_paths),
                duration_per_photo,
                self.work_dir,
            )
            raise RuntimeError("Failed to create any video clips")

        # Create concat file
        concat_file = self.work_dir / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")

        # PASS 2: Concat clips, normalize pixel format, re-encode video (CRF) + AAC audio.
        # Smaller final file (~8–15MB for 30s 1080p) for Supabase upload limits.
        # Audio input
        if audio_path:
            audio_inputs: List[str] = ["-i", str(audio_path)]
            audio_map: List[str] = ["-map", "1:a"]
        else:
            audio_inputs = [
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
            ]
            audio_map = ["-map", "1:a"]

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            *audio_inputs,
            "-map",
            "0:v:0",
            *audio_map,
            "-vf",
            "format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-t",
            "30",
            str(output_path),
        ]

        logger.info("Concatenating clips (re-encode video CRF28 + AAC)")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            logger.error("ffmpeg concat failed: %s", (result.stderr or "")[:1000])
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        logger.info("✅ Video concat complete: %s", output_path)
