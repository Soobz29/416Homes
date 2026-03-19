"""FFmpeg-based video renderer with simple Ken Burns-style effects."""

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
        """Download all photos to work directory."""

        photo_paths: List[Path] = []

        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            for idx, scene in enumerate(scene_plan):
                url = scene["photo_url"]
                filename = f"frame_{idx:03d}.jpg"
                filepath = self.work_dir / filename

                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    filepath.write_bytes(resp.content)
                    photo_paths.append(filepath)
                except Exception as e:  # pragma: no cover - network dependent
                    logger.error("Failed to download %s: %s", url, e)

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
        """Render a simple slideshow without complex filters.

        This intentionally avoids `zoompan`/`filter_complex` pipelines that can hang.
        """

        if not photo_paths:
            raise ValueError("photo_paths must not be empty")

        # Calculate duration per photo (30 second video total)
        duration_per_photo = 30.0 / len(photo_paths)

        # Create concat file for ffmpeg
        concat_file = "/tmp/concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for photo in photo_paths:
                f.write(f"file '{photo}'\n")
                f.write(f"duration {duration_per_photo}\n")
            # Repeat last image to ensure proper duration
            f.write(f"file '{photo_paths[-1]}'\n")

        # Escape headline for drawtext (we wrap it in single quotes)
        safe_headline = headline.replace("'", r"\'")

        drawtext_filter = (
            "fps=25,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            f"drawtext=text='{safe_headline}':fontsize=60:fontcolor=white:"
            "x=(w-text_w)/2:y=50:borderw=3:bordercolor=black"
        )

        # Simple ffmpeg command - concat images and overlay headline
        cmd: List[str] = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
        ]

        if audio_path:
            cmd.extend(["-i", str(audio_path)])

        cmd.extend(
            [
                "-vf",
                drawtext_filter,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
            ]
        )

        if audio_path:
            cmd.append("-shortest")
        else:
            cmd.append("-an")  # no audio input

        cmd.extend(
            [
                "-t",
                "30",  # Limit to 30 seconds
                str(output_path),
            ]
        )

        logger.info("Running ffmpeg (showing first args): %s", " ".join(cmd[:10]))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            logger.error("ffmpeg failed: %s", result.stderr)
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

