"""FFmpeg-based video renderer with Ken Burns-style effects and optional audio."""

import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class VideoRenderer:
    """Render video from photos using FFmpeg with Ken Burns effects."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

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

        # PASS 1: Convert each photo to a video clip with Ken Burns effect
        clip_paths: List[Path] = []

        for i, photo in enumerate(photo_paths):
            clip_path = self.work_dir / f"clip_{i:03d}.mp4"

            # Create individual clip with Ken Burns effect
            cmd: List[str] = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(photo),
                "-vf",
                ",".join(
                    [
                        "scale=1920:1080:force_original_aspect_ratio=increase",
                        "crop=1920:1080",
                        "zoompan=z='min(zoom+0.0015,1.2)':d={}:s=1920x1080:fps=25".format(
                            int(duration_per_photo * 25)
                        ),
                        "fade=t=in:st=0:d=0.5",
                        "fade=t=out:st={}:d=0.5".format(duration_per_photo - 0.5),
                        "format=yuv420p",
                    ]
                ),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-t",
                str(duration_per_photo),
                "-pix_fmt",
                "yuv420p",
                str(clip_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error("❌ Failed to create clip %d from %s", i, photo)
                logger.error("FFmpeg stderr: %s", (result.stderr or "")[:500])
                continue

            logger.info("✅ Created clip %d: %s", i, clip_path.name)
            clip_paths.append(clip_path)

        if not clip_paths:
            raise RuntimeError("Failed to create any video clips")

        # Create concat file
        concat_file = self.work_dir / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")

        # PASS 2: Concat clips, add text overlay and audio
        safe_headline = (
            headline.replace("\\", "\\\\")
            .replace("'", "")
            .replace(":", "\\:")
            .replace("=", "\\=")
        )[:200]

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

        drawtext_filter = (
            f"drawtext=text='{safe_headline}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=40"
            f":box=1:boxcolor=black@0.5:boxborderw=10"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            *audio_inputs,
            "-vf",
            drawtext_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            *audio_map,
            "-shortest",
            "-t",
            "30",
            str(output_path),
        ]

        logger.info("Concatenating clips and adding overlay")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            logger.error("ffmpeg concat failed: %s", result.stderr)
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
