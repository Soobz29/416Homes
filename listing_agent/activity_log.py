from datetime import datetime
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "activity.log")

def log_activity(action: str, detail: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action} | {detail}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
