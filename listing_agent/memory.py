import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import asyncio
from dotenv import load_dotenv
from listing_agent.activity_log import log_activity

load_dotenv()
logger = logging.getLogger(__name__)

MEMORY_FILE = Path("listing_agent/memory.json")

class AgentMemory:
    """
    Persistent memory layer for the 416Homes Agent.
    Stores context, metrics, and event logs to a local JSON file.
    """
    
    def __init__(self, file_path: Path = MEMORY_FILE):
        self.file_path = file_path
        self.data: Dict[str, Any] = {
            "storage": {},
            "event_log": [],
            "metrics": {
                "uptime_start": datetime.utcnow().isoformat(),
                "restart_count": 0,
                "total_scans": 0,
                "total_alerts": 0,
                "total_videos": 0
            }
        }
        self._load()
        self.data["metrics"]["restart_count"] += 1
        self._save()

    def _load(self):
        """Load memory from disk."""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    disk_data = json.load(f)
                    # Merge disk data into default structure
                    for key in self.data:
                        if key in disk_data:
                            if isinstance(self.data[key], dict):
                                self.data[key].update(disk_data[key])
                            else:
                                self.data[key] = disk_data[key]
                logger.info(f"💾 Memory loaded from {self.file_path}")
            except Exception as e:
                logger.error(f"Error loading memory: {e}")

    def _save(self):
        """Save memory to disk."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def store(self, key: str, value: Any):
        """Saves a key-value pair to persistent storage."""
        self.data["storage"][key] = value
        self._save()

    def recall(self, key: str, default: Any = None) -> Any:
        """Retrieves a value from persistent storage."""
        return self.data["storage"].get(key, default)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Appends an event to the persistent event log."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data
        }
        self.data["event_log"].append(event)
        
        # Update metrics based on event type
        metrics = self.data.get("metrics", {})
        if event_type == "listing_scanned":
            metrics["total_scans"] = metrics.get("total_scans", 0) + 1
        elif event_type == "alert_fired":
            metrics["total_alerts"] = metrics.get("total_alerts", 0) + 1
            metrics["alerts_today"] = metrics.get("alerts_today", 0) + 1
        elif event_type == "video_generated":
            metrics["total_videos"] = metrics.get("total_videos", 0) + 1
        elif event_type == "email_sent":
            metrics["emails_sent_today"] = metrics.get("emails_sent_today", 0) + 1
            
        self.data["metrics"] = metrics
            
        # Keep log size manageable (last 1000 events)
        if len(self.data["event_log"]) > 1000:
            self.data["event_log"] = self.data["event_log"][-1000:]
            
        self._save()

    def get_metrics(self) -> Dict[str, Any]:
        """Returns current agent metrics."""
        return self.data["metrics"]

    async def summarize_day(self) -> str:
        """Uses Gemini to summarize today's activity from the event log."""
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return "Gemini API key not found. Cannot summarize today's activity."

            client = genai.Client(api_key=api_key)
            model_id = "gemini-2.5-flash"

            # Get events from the last 24 hours
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            recent_events = [
                e for e in self.data["event_log"]
                if datetime.fromisoformat(e["timestamp"]) > yesterday
            ]

            if not recent_events:
                return "No significant activity in the last 24 hours."

            prompt = f"Summarize the following agent activity from the last 24 hours into a concise, professional report:\n{json.dumps(recent_events, indent=2)}"
            
            try:
                response = await asyncio.to_thread(client.models.generate_content, model=model_id, contents=prompt)
                return response.text.strip()
            except Exception as gemini_err:
                log_activity("ERROR", f"gemini_call failed in summarize_day: {gemini_err}")
                return f"Failed to generate summary: {str(gemini_err)}"
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            log_activity("ERROR", f"summarize_day failed: {e}")
            return f"Failed to generate summary: {str(e)}"

# Singleton instance
from datetime import timedelta
agent_memory = AgentMemory()
