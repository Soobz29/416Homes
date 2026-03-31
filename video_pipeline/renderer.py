"""FFmpeg-based video renderer with Ken Burns-style effects and optional audio."""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


def _libx264_quality_args() -> List[str]:
    """H.264 quality for slideshow output (tune via VIDEO_H264_PRESET / VIDEO_H264_CRF)."""
    preset = (os.getenv("VIDEO_H264_PRESET") or "medium").strip()
    crf_s = (os.getenv("VIDEO_H264_CRF") or "20").strip()
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
        """Render slideshow in a single FFmpeg pass using the image concat demuxer."""

        _ = scene_plan, headline  # reserved for overlays / future use

        if not photo_paths:
            raise ValueError("photo_paths must not be empty")

        duration_per_photo = 30.0 / len(photo_paths)

        # Absolute paths avoid concat demuxer path bugs under /tmp and Windows.
        abs_photos = [p.resolve() for p in photo_paths]

        images_txt = self.work_dir / "images.txt"
        with open(images_txt, "w", encoding="utf-8") as f:
            for photo in abs_photos:
                f.write(f"file '{photo.as_posix()}'\n")
                f.write(f"duration {duration_per_photo:.3f}\n")
            # FFmpeg concat demuxer requires the last file repeated without duration.
            f.write(f"file '{abs_photos[-1].as_posix()}'\n")

        if audio_path:
            audio_inputs: List[str] = ["-i", str(audio_path)]
            audio_map = ["-map", "1:a"]
        else:
            audio_inputs = [
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
            ]
            audio_map = ["-map", "1:a"]

        enc = self._choose_video_encoder()
        if enc == "libx264":
            enc_opts: List[str] = _libx264_quality_args()
        else:
            enc_opts = ["-preset", "veryfast", "-crf", "23"]

        aac_br = (os.getenv("VIDEO_AAC_BITRATE") or "192k").strip()

        cmd: List[str] = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(images_txt),
            *audio_inputs,
            "-map",
            "0:v:0",
            *audio_map,
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p",
            "-c:v",
            enc,
            *enc_opts,
            "-c:a",
            "aac",
            "-b:a",
            aac_br,
            "-r",
            "25",
            "-shortest",
            "-t",
            "30",
            str(output_path),
        ]

        logger.info("Rendering single-pass slideshow (%d photos, encoder=%s)", len(photo_paths), enc)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            logger.error(
                "FFmpeg failed (rc=%s): cmd=%s stderr_tail=%s",
                result.returncode,
                " ".join(cmd),
                (result.stderr or "")[-2000:],
            )
            raise RuntimeError(f"FFmpeg failed (rc={result.returncode})")

        logger.info("✅ Video rendered: %s", output_path)
