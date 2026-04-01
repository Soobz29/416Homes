import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Import our agent components
from telegram_bot import bot as telegram_bot
from listing_agent.memory import agent_memory
from listing_agent.activity_log import log_activity

logger = logging.getLogger(__name__)

class AgentScheduler:
    """
    APScheduler for 416 Agent.
    Handles recurring tasks like morning heartbeats.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def start(self):
        """Starts the scheduler and adds scheduled jobs."""
        if self.is_running:
            return

        # Morning Heartbeat at 8:00 AM
        self.scheduler.add_job(
            self.morning_heartbeat,
            CronTrigger(hour=8, minute=0),
            id="morning_heartbeat",
            replace_existing=True
        )

        # Midnight Reset at 12:00 AM
        self.scheduler.add_job(
            self.midnight_reset,
            CronTrigger(hour=0, minute=0),
            id="midnight_reset",
            replace_existing=True
        )

        # Optional: 9:00 PM Daily Digest
        # self.scheduler.add_job(...)

        self.scheduler.start()
        self.is_running = True
        logger.info("📅 Agent scheduler started.")

    async def stop(self):
        """Stops the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("🛑 Agent scheduler stopped.")

    async def morning_heartbeat(self):
        """Sends the 8am heartbeat message via Telegram."""
        logger.info("💓 Triggering morning heartbeat...")
        summary = await agent_memory.summarize_day()
        
        from telegram_bot import send_notification

        heartbeat_msg = (
            "🌅 <b>Good Morning, 416 Agent!</b>\n\n"
            f"Here's what happened in the last 24 hours:\n\n"
            f"{summary}\n\n"
            "Ready for today's scans! 🔍"
        )
        
        await send_notification(heartbeat_msg)
        log_activity("HEARTBEAT", "Morning digest sent")

    async def midnight_reset(self):
        """Resets daily counters in memory."""
        logger.info("🕛 Resetting daily metrics (midnight)...")
        if "metrics" not in agent_memory.data:
            agent_memory.data["metrics"] = {}
        agent_memory.data["metrics"]["emails_sent_today"] = 0
        agent_memory.data["metrics"]["alerts_today"] = 0
        agent_memory._save()
        log_activity("SYSTEM", "Daily metrics reset (midnight)")

# Singleton instance
agent_scheduler = AgentScheduler()
