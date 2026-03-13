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
        """Render slideshow with basic Ken Burns and crossfades using ffmpeg."""

        total_duration = scene_plan[-1]["end_time"] if scene_plan else 30.0
        duration_per_photo = max(total_duration / len(photo_paths), 1.5)

        filters: List[str] = []

        # Per-photo zoompan
        for idx, (photo_path, scene) in enumerate(zip(photo_paths, scene_plan)):
            kb = scene.get("ken_burns", {}) or {}
            zoom_direction = kb.get("zoom", "in")

            frame_count = int(duration_per_photo * 25)
            if zoom_direction == "in":
                zoom_expr = "min(zoom+0.0015,1.5)"
            else:
                zoom_expr = "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))"

            zoom_filter = (
                f"[{idx}:v]zoompan=z='{zoom_expr}':d={frame_count}:s=1920x1080,setsar=1[v{idx}]"
            )
            filters.append(zoom_filter)

        concat_inputs = "".join(f"[v{i}]" for i in range(len(photo_paths)))
        filters.append(f"{concat_inputs}concat=n={len(photo_paths)}:v=1:a=0[outv]")

        # Title overlay for first few seconds
        safe_headline = headline.replace("'", r"\'")
        title_filter = (
            f"[outv]drawtext=text='{safe_headline}':fontsize=60:fontcolor=white:"
            "x=(w-text_w)/2:y=100:enable='between(t,0,3)'[titled]"
        )
        filters.append(title_filter)

        filter_complex = ";".join(filters)

        cmd: List[str] = ["ffmpeg", "-y"]

        for photo_path in photo_paths:
            cmd.extend(["-loop", "1", "-t", f"{duration_per_photo:.2f}", "-i", str(photo_path)])

        if audio_path:
            cmd.extend(["-i", str(audio_path)])

        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[titled]",
            ]
        )

        if audio_path:
            cmd.extend(["-map", f"{len(photo_paths)}:a"])

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                str(output_path),
            ]
        )

        logger.info("Running ffmpeg (showing first args): %s", " ".join(cmd[:10]))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.error("ffmpeg failed: %s", result.stderr)
            raise RuntimeError(f"ffmpeg render failed: {result.stderr}")

