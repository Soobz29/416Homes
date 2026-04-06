"""Video worker — polls Supabase for pending jobs and processes them.

Run as a separate Railway service:
  Start Command: python video_pipeline/worker.py
  Install Command: pip install -r requirements-railway-video.txt
"""
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [video-worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("VIDEO_WORKER_POLL_SECONDS", "30"))


async def run() -> None:
    from supabase import create_client
    from video_pipeline.pipeline import process_pending_job

    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    sb = create_client(url, key)

    logger.info("Video worker started — polling every %ds", POLL_INTERVAL)

    while True:
        try:
            rows = (
                sb.table("video_jobs")
                .select("id, listing_url, customer_email")
                .eq("status", "pending")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if rows.data:
                job = rows.data[0]
                job_id = job["id"]
                logger.info("Picked up job %s (%s)", job_id, job.get("customer_email", ""))
                # Mark as processing so no other worker instance picks it up
                sb.table("video_jobs").update({"status": "generating_script"}).eq("id", job_id).execute()
                try:
                    await process_pending_job(job_id)
                    logger.info("Completed job %s", job_id)
                except Exception as exc:
                    logger.error("Job %s failed: %s", job_id, exc)
                    sb.table("video_jobs").update({
                        "status": "failed",
                        "error_message": str(exc),
                    }).eq("id", job_id).execute()
        except Exception as exc:
            logger.error("Worker poll error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run())
