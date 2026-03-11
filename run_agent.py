"""
416Homes — Combined launcher: Telegram bot + Listing Agent + Scheduler.
Run:  python run_agent.py
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root so it works regardless of cwd
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("416homes")


async def main():
    from telegram_bot import bot
    from public_telegram_bot import public_bot
    from listing_agent import agent
    from listing_agent.scheduler import agent_scheduler

    logger.info("Starting admin Telegram bot...")
    await bot.start()

    logger.info("Starting public Telegram bot...")
    await public_bot.start()

    logger.info("Starting scheduler (8 AM heartbeat, midnight reset)...")
    await agent_scheduler.start()

    logger.info("Starting listing agent scan loop (every 30 min)...")
    agent.start(interval_minutes=30)

    logger.info("All systems online. Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
        agent.stop()
        await agent_scheduler.stop()
        await public_bot.stop()
        await bot.stop()
        logger.info("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
