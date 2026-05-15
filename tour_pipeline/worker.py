"""Tour worker — polls Supabase for pending tour jobs and processes them.

Run as a separate DigitalOcean worker component (or locally alongside the API):
  Start Command: python tour_pipeline/worker.py

This is more reliable than FastAPI BackgroundTasks because jobs survive
API restarts and deploys — they stay in Supabase as 'pending' until picked up.
"""
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [tour-worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("TOUR_WORKER_POLL_SECONDS", "30"))


async def run() -> None:
    from supabase import create_client
    from tour_pipeline.pipeline import process_tour_job

    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    sb = create_client(url, key)

    logger.info("Tour worker started — polling every %ds", POLL_INTERVAL)

    while True:
        try:
            rows = (
                sb.table("tour_jobs")
                .select("id, listing_url, customer_email")
                .eq("status", "pending")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if rows.data:
                job = rows.data[0]
                jid = job["id"]
                logger.info("Picked up tour job %s (%s)", jid, job.get("customer_email", ""))
                # Mark as classifying so no other worker instance picks it up
                sb.table("tour_jobs").update({"status": "classifying"}).eq("id", jid).execute()
                try:
                    await process_tour_job(jid)
                    logger.info("Completed tour job %s", jid)
                except Exception as exc:
                    logger.error("Tour job %s failed: %s", jid, exc)
                    sb.table("tour_jobs").update({
                        "status": "failed",
                        "error_message": str(exc),
                    }).eq("id", jid).execute()
        except Exception as exc:
            logger.error("Tour worker poll error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run())
