import os
import logging
import asyncio
import re
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from telegram import Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
from listing_agent.activity_log import log_activity
from memory.store import memory_store
from scraper.listing_utils import is_badge_or_headline_only

# Import our agent components
# from listing_agent import agent as listing_agent (Removed to prevent circular import)
from listing_agent.memory import agent_memory

try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore[misc]
    Client = Any  # type: ignore[misc]

load_dotenv()
logger = logging.getLogger(__name__)

# White-label Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agent_config.json")
PERSONA_PATH = os.path.join(os.path.dirname(__file__), "AGENT.md")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_persona():
    if os.path.exists(PERSONA_PATH):
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""

AGENT_CONFIG = load_config()
AGENT_PERSONA = load_persona()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MAX_TELEGRAM_PHOTOS = int(os.getenv("MAX_TELEGRAM_PHOTOS", "15"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def send_notification(message: str, photo_url: str = None):
    """Global notification function callable from anywhere."""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
            return
            
        bot_client = Bot(token=TELEGRAM_BOT_TOKEN)
        if photo_url:
            await bot_client.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=photo_url,
                caption=message,
                parse_mode="HTML"
            )
        else:
            await bot_client.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="HTML"
            )
    except Exception as e:
        log_activity("ERROR", f"Telegram push failed: {e}")

class TelegramBot:
    """
    416 Agent's Telegram interface.
    Handles commands and sends proactive notifications.
    """
    
    def __init__(self):
        self.app = None
        self.is_running = False
        # photo-upload jobs keyed by chat_id
        self.pending_photo_jobs: Dict[int, Dict[str, Any]] = {}
        self.supabase: Optional[Client] = None
        if create_client and SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                logger.error(f"Failed to init Supabase client in TelegramBot: {e}")

    async def start(self):
        """Initializes and starts the Telegram bot polling loop."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in .env")
            return

        self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self.h_start))
        self.app.add_handler(CommandHandler("status", self.h_status))
        self.app.add_handler(CommandHandler("buyers", self.h_buyers))
        self.app.add_handler(CommandHandler("alerts", self.h_alerts))
        self.app.add_handler(CommandHandler("link", self.h_link))
        self.app.add_handler(CommandHandler("video", self.h_video))
        self.app.add_handler(CommandHandler("videophotos", self.h_videophotos))
        self.app.add_handler(CommandHandler("done", self.h_done_photos))
        self.app.add_handler(CommandHandler("cancel", self.h_cancel_photos))
        self.app.add_handler(CommandHandler("pause", self.h_pause))
        self.app.add_handler(CommandHandler("resume", self.h_resume))
        self.app.add_handler(CommandHandler("heartbeat", self.h_heartbeat))
        self.app.add_handler(CommandHandler("log", self.h_log))
        self.app.add_handler(CommandHandler("regions", self.h_regions))
        self.app.add_handler(CommandHandler("sources", self.h_sources))
        self.app.add_handler(CommandHandler("listings", self.h_listings))
        self.app.add_handler(CallbackQueryHandler(self.h_listings_callback, pattern=r"^listings:"))
        self.app.add_handler(CommandHandler("clear", self.h_clear))
        self.app.add_handler(CommandHandler("veobudget", self.h_veobudget))
        self.app.add_handler(CommandHandler("restart", self.h_restart))
        self.app.add_handler(CommandHandler("videostatus", self.h_videostatus))
        self.app.add_handler(MessageHandler(filters.Regex(r"(?i)add buyer\s+"), self.h_add_buyer))
        # Text messages can be either skill commands or tier selection during /videophotos
        self.app.add_handler(MessageHandler(filters.Regex(r"(?i)add skill:\s+"), self.h_add_skill))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.h_text_message))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.h_photo_upload))

        await self.app.initialize()
        await self.app.start()

        # Enable Telegram slash-command suggestions (type "/" in chat).
        try:
            await self.app.bot.set_my_commands(
                [
                    BotCommand("status", "Current health & metrics"),
                    BotCommand("sources", "Last scan breakdown by source"),
                    BotCommand("listings", "Browse last scan (Prev/Next)"),
                    BotCommand("regions", "Listing counts by GTA region"),
                    BotCommand("alerts", "Show your saved alerts"),
                    BotCommand("link", "Link this chat to your 416Homes account"),
                    BotCommand("video", "Generate video from listing URL"),
                    BotCommand("videophotos", "Upload photos and build a video"),
                    BotCommand("videostatus", "Check progress of active video jobs"),
                    BotCommand("veobudget", "Show today's Veo budget usage"),
                    BotCommand("pause", "Pause scan loop"),
                    BotCommand("resume", "Resume scan loop"),
                    BotCommand("clear", "Delete last ~50 messages (best-effort)"),
                    BotCommand("restart", "Soft-restart agent loop"),
                    BotCommand("log", "Last 20 agent actions"),
                ]
            )
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")

        await self.app.updater.start_polling()
        
        self.is_running = True
        logger.info("🤖 Telegram bot started and polling...")
        log_activity("SYSTEM", "Telegram bot started")
        
        # Send initial greeting
        welcome_msg = AGENT_CONFIG.get("telegram_welcome", "🚀 Agent is online.")
        await self.send_notification(welcome_msg)

    async def stop(self):
        """Stops the bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self.is_running = False
        logger.info("🛑 Telegram bot stopped.")
        log_activity("SYSTEM", "Telegram bot stopped")

    async def send_notification(self, text: str, photo_url: Optional[str] = None):
        """Sends a notification to the configured chat ID."""
        if not self.app or not TELEGRAM_CHAT_ID:
            return

        try:
            if photo_url:
                await self.app.bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo_url, caption=text, parse_mode='Markdown')
            else:
                await self.app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    # ── Command Handlers ──────────────────────────────────────────────────

    async def h_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        agent_name = AGENT_CONFIG.get("agent_name", "AI Agent")
        welcome = AGENT_CONFIG.get("telegram_welcome", f"Hello! I am your {agent_name}.")

        # Link this chat to a user record in Supabase (best-effort).
        try:
            if self.supabase and update.effective_user:
                chat_id = update.effective_chat.id
                username = update.effective_user.username or ""
                email_hint = update.effective_user.username or f"tg_{chat_id}@example.invalid"
                # Upsert by telegram_chat_id if present, otherwise by email fallback.
                resp = (
                    self.supabase.table("users")
                    .select("*")
                    .eq("telegram_chat_id", chat_id)
                    .limit(1)
                    .execute()
                )
                rows = getattr(resp, "data", None) or []
                if rows:
                    user_id = rows[0]["id"]
                    self.supabase.table("users").update(
                        {"telegram_username": username or None}
                    ).eq("id", user_id).execute()
                else:
                    # Either attach to existing email row, or create new.
                    existing = (
                        self.supabase.table("users")
                        .select("*")
                        .eq("email", email_hint)
                        .limit(1)
                        .execute()
                    )
                    erows = getattr(existing, "data", None) or []
                    if erows:
                        user_id = erows[0]["id"]
                        self.supabase.table("users").update(
                            {
                                "telegram_chat_id": chat_id,
                                "telegram_username": username or None,
                            }
                        ).eq("id", user_id).execute()
                    else:
                        self.supabase.table("users").insert(
                            {
                                "email": email_hint,
                                "telegram_chat_id": chat_id,
                                "telegram_username": username or None,
                            }
                        ).execute()
        except Exception as e:
            logger.warning(f"Failed to upsert Telegram user in Supabase: {e}")

        await update.message.reply_text(
            f"👋 {welcome}\n\n"
            "📋 Commands:\n"
            "/status - Current health & metrics\n"
            "/log - Last 20 agent actions\n"
            "/buyers - Active buyer profiles\n"
            "/regions - Listing counts by GTA region\n"
            "/listings - Browse last scan (Prev/Next to see all)\n"
            "/alerts - Recent listings matches\n"
            "/clear - Delete last ~50 messages (best-effort)\n"
            "/restart - Soft-restart agent loop\n"
            "/video <url> - Generate cinematic video, delivered here as MP4\n"
            "   • AI voiceover + Veo cinematic clips\n"
            "   • Delivered directly in this chat (~5-20 min)\n"
          "/videophotos - Upload photos and build a video from them\n"
            "/videostatus - Check progress of active video jobs\n"
            "/pause / /resume - Cycle scan loop\n"
            "/help - Show this message"
        )

    async def h_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Best-effort: delete last ~50 messages in this chat.
        Telegram may reject deletions (permissions/history); we ignore failures.
        """
        if not update.message or not self.app:
            return
        chat_id = update.effective_chat.id
        start_id = update.message.message_id
        deleted = 0
        for mid in range(start_id, max(start_id - 60, 1), -1):
            try:
                await self.app.bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted += 1
            except Exception:
                continue
        try:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=f"🧹 Cleared {deleted} recent messages (best-effort).",
            )
        except Exception:
            pass

    async def h_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Soft restart from chat: restart scan loop + scheduler.
        This does NOT restart the Python process.
        """
        if not update.message:
            return
        try:
            from listing_agent import agent as listing_agent
            from listing_agent.scheduler import agent_scheduler

            await update.message.reply_text("🔄 Restarting agent loop (soft restart)...")
            listing_agent.stop()
            try:
                await agent_scheduler.stop()
            except Exception:
                pass
            await agent_scheduler.start()
            listing_agent.start(interval_minutes=30)
            await update.message.reply_text("✅ Agent loop restarted.")
        except Exception as e:
            await update.message.reply_text(f"❌ Restart failed: {e}")

    async def h_veobudget(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current Veo budget usage."""
        from video_pipeline.video_producer import _load_veo_spend, VEO_DAILY_LIMIT_CAD

        if not update.message:
            return

        data = _load_veo_spend()
        spend = float(data.get("spend", 0.0))
        limit = float(VEO_DAILY_LIMIT_CAD)
        remaining = max(0.0, limit - spend)
        videos_remaining = int(remaining / 2.50) if limit > 0 else 0

        await update.message.reply_text(
            "💰 Veo Budget (Today)\n\n"
            f"Spent: CA${spend:.2f}\n"
            f"Limit: CA${limit:.2f}\n"
            f"Remaining: CA${remaining:.2f}\n"
            f"Videos left: ~{videos_remaining}\n\n"
            "Resets: Midnight UTC"
        )

    async def h_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from listing_agent import agent as listing_agent
        status = listing_agent.get_status()
        metrics = agent_memory.get_metrics()
        
        regions_list = status['criteria'].get('neighborhoods', [])
        if not regions_list:
            regions_list = ["All GTA"]
        regions_str = ", ".join(regions_list[:3])
        if len(regions_list) > 3:
            regions_str += f" (+{len(regions_list)-3} more)"

        agent_name = AGENT_CONFIG.get("agent_name", "AI Agent")
        msg = (
            f"🤖 *{agent_name} Status*\n"
            f"• *Status:* {'🟢 Running' if status['running'] else '🔴 Paused'}\n"
            f"• *Uptime Start:* `{metrics['uptime_start']}`\n"
            f"• *Restart Count:* `{metrics['restart_count']}`\n"
            f"• *Scans Today:* `{metrics.get('total_scans', 0)}`\n"
            f"• *Alerts Today:* `{metrics.get('alerts_today', 0)}`\n"
            f"• *Emails Sent:* `{metrics.get('emails_sent_today', 0)} / 50`"
            f"• *Total Known:* `{status['known_listings']}`\n"
            f"• *Regions:* `{regions_str}`\n"
            f"• *Criteria:* `${status['criteria']['max_price']:,}`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def h_buyers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        buyers = agent_memory.recall("buyers", [])
        if not buyers:
            await update.message.reply_text("No active buyer profiles found.")
            return
            
        msg = "👥 *Active Buyer Profiles*\n"
        for b in buyers:
            msg += f"• *{b['name']}*: ${b['min']}-{b['max']} | {b['beds']}bd | {b['neighbourhood']}\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def h_add_buyer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Format: add buyer <name> <budget_min>-<budget_max> <bedrooms> <neighbourhood>
        pattern = r"add buyer\s+(.+?)\s+(\d+)-(\d+)\s+(\d+)\s+(.+)"
        match = re.search(pattern, update.message.text, re.IGNORECASE)
        
        if not match:
            await update.message.reply_text("❌ Format: `add buyer <name> <min>-<max> <beds> <neighbourhood>`")
            return
            
        name, b_min, b_max, beds, hood = match.groups()
        buyer = {
            "name": name,
            "min": int(b_min),
            "max": int(b_max),
            "beds": int(beds),
            "neighbourhood": hood.strip()
        }
        
        buyers = agent_memory.recall("buyers", [])
        buyers.append(buyer)
        agent_memory.store("buyers", buyers)
        
        await update.message.reply_text(f"✅ Added buyer profile for *{name}*.", parse_mode='Markdown')

    async def h_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Show alerts configured for the current Telegram user from Supabase.
        """
        if not self.supabase:
            await update.message.reply_text("Alerts storage is not configured yet.")
            return

        chat_id = update.effective_chat.id
        try:
            user_resp = (
                self.supabase.table("users")
                .select("id,email")
                .eq("telegram_chat_id", chat_id)
                .limit(1)
                .execute()
            )
            users = getattr(user_resp, "data", None) or []
            if not users:
                await update.message.reply_text(
                    "ℹ️ No user record linked to this chat yet.\n"
                    "Create an alert in the web dashboard (using the same email) to link this chat automatically."
                )
                return
            user = users[0]
            user_id = user["id"]

            alerts_resp = (
                self.supabase.table("alerts")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
            alerts = getattr(alerts_resp, "data", None) or []
            if not alerts:
                await update.message.reply_text("ℹ️ You don't have any alerts yet.")
                return

            lines = ["🚨 *Your Alerts* (up to 10)\n"]
            for a in alerts:
                cities = a.get("cities") or ["GTA"]
                min_price = a.get("min_price")
                max_price = a.get("max_price")
                min_beds = a.get("min_beds")

                price_bits = []
                if min_price:
                    price_bits.append(f"${int(min_price):,}")
                else:
                    price_bits.append("Any")
                price_bits.append("–")
                if max_price:
                    price_bits.append(f"${int(max_price):,}")
                else:
                    price_bits.append("Any")
                beds_str = f"{int(min_beds)}+ bd" if min_beds else "Any beds"
                status = "🟢" if a.get("is_active", True) else "⚪"
                lines.append(
                    f"{status} *{', '.join(cities)}* — {' '.join(price_bits)} • {beds_str}"
                )
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"/alerts failed: {e}")
            await update.message.reply_text("❌ Failed to load alerts.")

    async def h_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Link this Telegram chat to an existing 416Homes user via a short code.
        The code is generated from the dashboard and stored in users.preferences.link_code.
        """
        if not self.supabase:
            await update.message.reply_text("Linking is not configured yet.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /link TG-XXXX\n\n"
                "First, open the 416Homes dashboard, click 'Connect Telegram', "
                "then paste the code shown there after /link."
            )
            return

        code = context.args[0].strip().upper()
        chat_id = update.effective_chat.id
        username = (update.effective_user.username or "").strip() if update.effective_user else ""

        try:
            resp = self.supabase.table("users").select("id,preferences").execute()
            rows = getattr(resp, "data", None) or []

            target = None
            for row in rows:
                prefs = row.get("preferences") or {}
                if not isinstance(prefs, dict):
                    continue
                if prefs.get("link_code", "").upper() == code:
                    expires = prefs.get("link_expires_at")
                    if expires:
                        try:
                            expiry_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                            if expiry_dt < datetime.utcnow():
                                continue
                        except Exception:
                            # If parsing fails, treat as expired.
                            continue
                    target = row
                    break

            if not target:
                await update.message.reply_text(
                    "❌ That code is invalid or has expired. Generate a new one from your dashboard."
                )
                return

            user_id = target["id"]
            prefs = target.get("preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            prefs.pop("link_code", None)
            prefs.pop("link_expires_at", None)

            self.supabase.table("users").update(
                {
                    "telegram_chat_id": chat_id,
                    "telegram_username": username or None,
                    "preferences": prefs,
                }
            ).eq("id", user_id).execute()

            await update.message.reply_text(
                "✅ This chat is now linked to your 416Homes account.\n"
                "You’ll receive alerts here when new matches are found."
            )
        except Exception as e:
            logger.error(f"/link failed: {e}")
            await update.message.reply_text("❌ Failed to link this chat. Please try again.")

    async def h_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Breakdown of last scan results by source."""
        log_path = os.path.join("listing_agent", "activity.log")
        if not os.path.exists(log_path):
            await update.message.reply_text("❌ No activity log found.")
            return

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Look for the last SCAN: Total: ... line
            last_summary = "No scan data found yet."
            for line in reversed(lines):
                if "SCAN | Total:" in line:
                    last_summary = line.split("|")[-1].strip()
                    break
            
            await update.message.reply_text(f"📊 *Scraper Aggregator Status*\n\n{last_summary}", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to parse sources: {e}")

    def _format_listings_page(
        self,
        scan_at: str,
        total: int,
        listings: List[Dict],
        page: int,
        city: str | None = None,
        region: str | None = None,
    ) -> tuple:
        """Return (message_text, reply_markup) for a listings page."""
        from listing_agent import LISTINGS_PAGE_SIZE

        page_size = LISTINGS_PAGE_SIZE
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        try:
            dt = datetime.fromisoformat(scan_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            time_str = scan_at or "Unknown"

        filter_bits = []
        if city:
            filter_bits.append(f"city={city}")
        if region:
            filter_bits.append(f"region={region}")
        filter_str = f" • {' | '.join(filter_bits)}" if filter_bits else ""

        lines = [
            f"🏠 <b>Last Scan</b> — {time_str} • Page {page}/{total_pages} • {total} listings{filter_str}",
            "",
        ]

        # Group within the page by city then region.
        def _group_key(L: Dict[str, Any]) -> tuple:
            return (str(L.get("city") or ""), str(L.get("region") or ""))

        listings_sorted = sorted(listings, key=_group_key)
        last_group = None

        for i, L in enumerate(listings_sorted, start=offset + 1):
            raw_addr = (L.get("address") or "Unknown").strip()
            addr = "Address not available" if is_badge_or_headline_only(raw_addr) else (raw_addr or "Unknown")
            addr = addr[:55]
            price = L.get("price") or 0
            price_str = f"${int(price):,}" if isinstance(price, (int, float)) else str(price)
            src = L.get("source", "?")
            url = L.get("url") or ""

            group = _group_key(L)
            if group != last_group:
                city_label, region_label = group
                lines.append(f"<b>— {self._escape_html(city_label)} / {self._escape_html(region_label)} —</b>")
                lines.append("")
                last_group = group

            lines.append(f"<b>{i}.</b> {self._escape_html(addr)}")
            lines.append(f"   💰 {price_str} • {src}")
            if url:
                lines.append(f"   🔗 <a href=\"{url}\">View listing</a>")
            lines.append("")
        text = "\n".join(lines).strip()

        # Build Prev / Next keyboard (page shown in header text)
        buttons = []
        # Encode filters into callback data.
        def _cb(p: int) -> str:
            parts = [f"page={p}"]
            if city:
                parts.append(f"city={city}")
            if region:
                parts.append(f"region={region}")
            return "listings:" + ";".join(parts)

        if page > 1:
            buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=_cb(page - 1)))
        if page < total_pages:
            buttons.append(InlineKeyboardButton("Next ▶️", callback_data=_cb(page + 1)))
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
        return (text, reply_markup)

    def _escape_html(self, s: str) -> str:
        """Escape for Telegram HTML."""
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Toronto = city + boroughs (match API behaviour)
    TORONTO_BOROUGHS = ("Toronto", "Downtown", "North York", "Scarborough", "Etobicoke")

    async def h_listings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Browse last scan listings with pagination. Prefer Supabase when scan file missing (e.g. Railway)."""
        from listing_agent import get_last_scan_listings, LISTINGS_PAGE_SIZE, LAST_SCAN_LISTINGS_FILE

        # Parse args:
        # /listings
        # /listings markham
        # /listings richmond hill
        # /listings north york
        # /listings region downtown
        # /listings markham region unionville
        args = [a.strip() for a in (context.args or []) if a.strip()]

        def _normalize_city_arg(s: str | None) -> str | None:
            if not s:
                return None
            k = " ".join(s.split()).strip().lower()
            aliases = {
                "toronto": "toronto",
                "downtown": "downtown",
                "downtown toronto": "downtown",
                "north york": "north york",
                "scarborough": "scarborough",
                "etobicoke": "etobicoke",
                "mississauga": "mississauga",
                "brampton": "brampton",
                "vaughan": "vaughan",
                "markham": "markham",
                "richmond hill": "richmond hill",
                "oakville": "oakville",
                "burlington": "burlington",
                "ajax": "ajax",
                "pickering": "pickering",
                "whitby": "whitby",
                "oshawa": "oshawa",
                "milton": "milton",
                "gta": "gta",
                "greater toronto area": "gta",
            }
            return aliases.get(k)

        city = None
        region = None

        # If user provided "region ..." split on that; everything before is city phrase.
        if args and any(a.lower() == "region" for a in args):
            idx = next(i for i, a in enumerate(args) if a.lower() == "region")
            city_phrase = " ".join(args[:idx]).strip()
            region_phrase = " ".join(args[idx + 1 :]).strip()
            city = _normalize_city_arg(city_phrase)
            region = region_phrase or None
        else:
            phrase = " ".join(args).strip()
            city = _normalize_city_arg(phrase)
            # If it wasn't a known city, fall back to treating the phrase as a region filter.
            if not city and phrase:
                region = phrase

        # Prefer Supabase when scan file is missing (e.g. on Railway worker) so /listings always has data.
        use_supabase_first = not (LAST_SCAN_LISTINGS_FILE.exists() and LAST_SCAN_LISTINGS_FILE.stat().st_size > 0)
        scan_at, total, slice_list = None, 0, []

        if not use_supabase_first:
            scan_at, total, slice_list = get_last_scan_listings(
                limit=LISTINGS_PAGE_SIZE, offset=0, city=city, region=region
            )

        if (use_supabase_first or not scan_at or not slice_list) and memory_store is not None:
            try:
                city_param = None
                cities_param = None
                if city and str(city).strip().lower() == "toronto":
                    cities_param = list(self.TORONTO_BOROUGHS)
                elif city:
                    city_param = city.strip().capitalize() if city else None
                all_rows = await memory_store.get_listings(
                    city=city_param,
                    cities=cities_param,
                    limit=1000,
                    offset=0,
                )
            except Exception as e:
                logger.warning(f"Supabase for /listings failed: {e}")
                all_rows = []

            if all_rows:
                total = len(all_rows)
                slice_list = all_rows[:LISTINGS_PAGE_SIZE]
                scan_at = datetime.utcnow().isoformat()

        if not scan_at:
            await update.message.reply_text(
                "📋 No scan data yet.\n\nRun a scan first (or wait for the next scheduled scan every 30 min)."
            )
            return
        if not slice_list:
            filt = []
            if city:
                filt.append(f"city={city}")
            if region:
                filt.append(f"region={region}")
            filt_str = (" (" + ", ".join(filt) + ")") if filt else ""
            await update.message.reply_text(
                f"📋 No listings matched your filter{filt_str}.\n\nTry `/listings` without filters.",
                parse_mode="Markdown",
            )
            return

        text, reply_markup = self._format_listings_page(
            scan_at, total, slice_list, page=1, city=city, region=region
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

    async def h_listings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Prev/Next button clicks for listings pagination. Uses Supabase when scan file missing."""
        from listing_agent import get_last_scan_listings, LISTINGS_PAGE_SIZE, LAST_SCAN_LISTINGS_FILE

        query = update.callback_query
        await query.answer()

        data = query.data
        payload = data.replace("listings:", "", 1)
        parts = {}
        for chunk in payload.split(";"):
            if "=" in chunk:
                k, v = chunk.split("=", 1)
                parts[k] = v
        try:
            page = int(parts.get("page", "1"))
        except ValueError:
            return
        city = parts.get("city") or None
        region = parts.get("region") or None

        if page < 1:
            return

        page_size = LISTINGS_PAGE_SIZE
        offset = (page - 1) * page_size
        scan_at, total, slice_list = None, 0, []
        use_supabase = not (LAST_SCAN_LISTINGS_FILE.exists() and LAST_SCAN_LISTINGS_FILE.stat().st_size > 0)

        if not use_supabase:
            scan_at, total, slice_list = get_last_scan_listings(
                limit=page_size, offset=offset, city=city, region=region
            )

        if (use_supabase or not scan_at or not slice_list) and memory_store is not None:
            try:
                city_param = None
                cities_param = None
                if city and str(city).strip().lower() == "toronto":
                    cities_param = list(self.TORONTO_BOROUGHS)
                elif city:
                    city_param = city.strip().capitalize() if city else None
                all_rows = await memory_store.get_listings(
                    city=city_param,
                    cities=cities_param,
                    limit=1000,
                    offset=0,
                )
            except Exception as e:
                logger.warning(f"Supabase for listings pagination failed: {e}")
                all_rows = []

            if all_rows:
                total = len(all_rows)
                slice_list = all_rows[offset : offset + page_size]
                scan_at = datetime.utcnow().isoformat()

        if not scan_at or not slice_list:
            await query.edit_message_text("📋 Scan data no longer available.")
            return

        text, reply_markup = self._format_listings_page(
            scan_at, total, slice_list, page=page, city=city, region=region
        )
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logger.warning(f"Listings callback edit failed: {e}")

    async def h_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate cinematic video from listing URL with tier selection."""
        if not update.message:
            return

        if not context.args:
            await update.message.reply_text(
                "🎬 *Video Generation Tiers*\n\n"
                "*Basic* - $99\n"
                "• Ken Burns photo transitions\n"
                "• AI voiceover narration\n"
                "• Background music\n"
                "• 40-60 second video\n\n"
                "*Cinematic* - $249\n"
                "• All Basic features\n"
                "• Veo 2.0 AI-generated clips\n"
                "• Smooth camera movements\n"
                "• Professional transitions\n\n"
                "*Premium* - $299\n"
                "• All Cinematic features\n"
                "• AI photo enhancement\n"
                "• Color grading\n"
                "• Priority processing\n\n"
                "Usage:\n"
                "`/video basic <url>`\n"
                "`/video cinematic <url>`\n"
                "`/video premium <url>`",
                parse_mode="Markdown",
            )
            return

        tier = context.args[0].lower()
        if tier not in ["basic", "cinematic", "premium"]:
            await update.message.reply_text(
                "❌ Invalid tier. Choose: basic, cinematic, or premium"
            )
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Missing URL. Usage: `/video <tier> <url>`",
                parse_mode="Markdown",
            )
            return

        url = context.args[1]
        chat_id = update.effective_chat.id

        tier_config = {
            "basic": {
                "force_veo": False,
                "enhance_photos": False,
                "price": 99,
                "paid_order": False,  # Test mode / Ken Burns only
            },
            "cinematic": {
                "force_veo": True,
                "enhance_photos": False,
                "price": 249,
                "paid_order": True,
            },
            "premium": {
                "force_veo": True,
                "enhance_photos": True,
                "price": 299,
                "paid_order": True,
            },
        }
        config = tier_config[tier]

        await update.message.reply_text(
            f"🎬 Starting *{tier.capitalize()}* video (${config['price']})\n"
            f"Processing {url}...",
            parse_mode="Markdown",
        )

        # Launch background task
        asyncio.create_task(
            _run_video_and_deliver(
                url=url,
                chat_id=str(chat_id),
                tier=tier,
                config=config,
            )
        )

    # ── Photo-based video flow ─────────────────────────────────────────────

    async def h_videophotos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start photo upload flow for video generation."""
        chat_id = update.effective_chat.id

        # Clean up stale jobs older than 1 hour
        now = datetime.utcnow()
        to_delete = []
        for cid, job in self.pending_photo_jobs.items():
            created = job.get("created_at")
            if isinstance(created, datetime) and now - created > timedelta(hours=1):
                to_delete.append(cid)
        for cid in to_delete:
            job = self.pending_photo_jobs.pop(cid, None)
            if job:
                job_dir = Path("video_pipeline/temp") / job["job_id"]
                shutil.rmtree(job_dir, ignore_errors=True)

        if chat_id in self.pending_photo_jobs:
            await update.message.reply_text(
                "⚠️ You already have a photo upload in progress.\n"
                "Send more photos, /done to render, or /cancel to discard."
            )
            return

        ts = int(now.timestamp())
        job_id = f"tgphotos_{chat_id}_{ts}"
        self.pending_photo_jobs[chat_id] = {
            "job_id": job_id,
            "photos": [],
            "address": None,
            "tier": "basic",
            "created_at": now,
            "last_activity": now,
        }

        await update.message.reply_text(
            "📸 Send me up to 15 property photos (JPEG/PNG).\n\n"
            "First, choose a tier by replying with: `basic`, `cinematic`, or `premium`.\n"
            "You can also just start sending photos for the default *Basic* tier.\n\n"
            "When done, send /done to start rendering.",
            parse_mode="Markdown",
        )

    async def h_photo_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming photo messages during /videophotos flow."""
        message = update.message
        if not message or not message.photo:
            return

        chat_id = update.effective_chat.id
        job = self.pending_photo_jobs.get(chat_id)
        if not job:
            # Ignore photos outside of the photo-video flow
            return

        photos: List[str] = job["photos"]
        if len(photos) >= MAX_TELEGRAM_PHOTOS:
            await message.reply_text(
                f"⚠️ Maximum {MAX_TELEGRAM_PHOTOS} photos reached. Send /done to proceed."
            )
            return

        # Prepare directories
        job_dir = Path("video_pipeline/temp") / job["job_id"]
        photos_dir = job_dir / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)

        index = len(photos) + 1
        file_path = photos_dir / f"photo_{index}.jpg"

        try:
            tg_photo = message.photo[-1]
            file = await tg_photo.get_file()
            await file.download_to_drive(custom_path=str(file_path))
        except Exception as e:
            logger.error(f"Photo download failed for chat {chat_id}: {e}")
            await message.reply_text("❌ Failed to download that photo. Please try again.")
            return

        # Basic format validation by extension
        if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            await message.reply_text("⚠️ Unsupported file format. Please send JPEG or PNG images.")
            file_path.unlink(missing_ok=True)
            return

        photos.append(str(file_path))
        job["last_activity"] = datetime.utcnow()

        await message.reply_text(
            f"✅ Photo {len(photos)}/{MAX_TELEGRAM_PHOTOS} received"
        )

    async def h_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle generic text messages:
        - Tier selection for /videophotos (basic/cinematic/premium).
        - Falls through to no-op if not in a photo job.
        """
        if not update.message:
            return

        chat_id = update.effective_chat.id
        text = (update.message.text or "").strip().lower()

        job = self.pending_photo_jobs.get(chat_id)
        if not job:
            # No active photo job; ignore here and let other handlers manage.
            return

        if text in {"basic", "cinematic", "premium"}:
            job["tier"] = text
            await update.message.reply_text(
                f"✅ Tier set to *{text.capitalize()}* for this video.\n"
                "Now send photos, then /done when finished.",
                parse_mode="Markdown",
            )

    async def h_done_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Finalize photo upload and kick off video rendering."""
        chat_id = update.effective_chat.id
        job = self.pending_photo_jobs.get(chat_id)
        if not job:
            await update.message.reply_text(
                "❌ No active photo upload. Use /videophotos to start."
            )
            return

        photos: List[str] = job["photos"]
        if not photos:
            await update.message.reply_text(
                "❌ No photos received. Use /videophotos to start over."
            )
            # Clear empty job
            self.pending_photo_jobs.pop(chat_id, None)
            return

        # Optional inactivity warning (10 minutes)
        last_activity = job.get("last_activity") or job.get("created_at")
        now = datetime.utcnow()
        if isinstance(last_activity, datetime) and now - last_activity > timedelta(minutes=10):
            await update.message.reply_text(
                "⌛ It has been more than 10 minutes since your last photo. "
                "I will still render the video now, but next time consider "
                "sending /videophotos closer to when you upload."
            )

        job_id = job["job_id"]
        job_dir = Path("video_pipeline/temp") / job_id

        # Attempt to infer address from the previous non-command message (optional)
        address = job.get("address")
        if not address:
            # Very simple heuristic: if their last message before /done was text, use it.
            # (Telegram doesn't give us easy thread context here without extra storage.)
            # We'll fall back to a generic label otherwise.
            address = f"Custom property from chat {chat_id}"

        count = len(photos)
        tier = job.get("tier", "basic")
        tier_cfg = {
            "basic": {
                "force_veo": False,
                "enhance_photos": False,
                "price": 99,
                "paid_order": False,
            },
            "cinematic": {
                "force_veo": True,
                "enhance_photos": False,
                "price": 249,
                "paid_order": True,
            },
            "premium": {
                "force_veo": True,
                "enhance_photos": True,
                "price": 299,
                "paid_order": True,
            },
        }.get(tier, {"force_veo": False, "enhance_photos": False, "price": 99, "paid_order": False})

        await update.message.reply_text(
            f"🎬 Starting *{tier.capitalize()}* video render with {count} photos...\n"
            f"Price: ${tier_cfg['price']} (simulated)\n"
            "Use /videostatus to track progress.",
            parse_mode="Markdown",
        )

        # Fire-and-forget video rendering
        asyncio.create_task(
            self._run_photos_video_and_deliver(
                chat_id=chat_id,
                job_dir=job_dir,
                listing_data={
                    "address": address,
                    "price": "",
                    "paid_order": tier_cfg.get("paid_order", False),
                    "enhance_photos": tier_cfg.get("enhance_photos", False),
                },
            )
        )

        # Clear pending job state
        self.pending_photo_jobs.pop(chat_id, None)

    async def h_cancel_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel an in-progress photo upload job."""
        chat_id = update.effective_chat.id
        job = self.pending_photo_jobs.pop(chat_id, None)
        if not job:
            await update.message.reply_text("ℹ️ No active photo upload to cancel.")
            return

        job_dir = Path("video_pipeline/temp") / job["job_id"]
        shutil.rmtree(job_dir, ignore_errors=True)
        await update.message.reply_text("❌ Photo upload cancelled.")

    async def h_videostatus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from video_pipeline.video_producer import get_active_jobs
        jobs = get_active_jobs()

        if not jobs:
            await update.message.reply_text("🎬 No active video jobs right now.")
            return

        STEP_EMOJI = {
            "initializing": "🔄", "scrape": "📸", "audio": "🎙",
            "enhance": "✨", "animate": "🎬", "assemble": "🎞",
        }
        STATUS_EMOJI = {"running": "🟢", "done": "✅", "failed": "❌"}

        lines = ["🎬 *Active Video Jobs*\n"]
        for jid, j in jobs.items():
            se = STATUS_EMOJI.get(j["status"], "⚪")
            step_e = STEP_EMOJI.get(j["step"], "▶")
            pct = j["percent"]
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)

            lines.append(f"{se} *{j['address'][:40]}*")
            lines.append(f"   {step_e} Step: `{j['step']}`")
            lines.append(f"   📊 Progress: `[{bar}] {pct}%`")

            if j["clips_total"] > 0:
                lines.append(f"   🎬 Clips: `{j['clips_done']}/{j['clips_total']}`")
            if j["photos_total"] > 0:
                lines.append(f"   📸 Photos: `{j['photos_downloaded']}`  |  ✨ Enhanced: `{j['enhanced']}`")

            extras = []
            if j["voiceover"]:
                extras.append("🎙 Voiceover")
            if j["music"]:
                extras.append("🎵 Music")
            if extras:
                lines.append(f"   {' • '.join(extras)}")

            if j["status"] != "running":
                lines.append(f"   ℹ️ `{j['detail'][:80]}`")
            lines.append("")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def h_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from listing_agent import agent as listing_agent
        listing_agent.stop()
        await update.message.reply_text("⏸ Agent scan loop paused.")

    async def h_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from listing_agent import agent as listing_agent
        listing_agent.start()
        await update.message.reply_text("▶️ Agent scan loop resumed.")

    async def h_heartbeat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Manually trigger the morning heartbeat
        # This will be called by the scheduler too
        summary = await agent_memory.summarize_day()
        await update.message.reply_text(f"💓 *Manual Heartbeat Triggered*\n\n{summary}", parse_mode='Markdown')
        log_activity("HEARTBEAT", "Manual heartbeat requested")

    async def h_add_skill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Format: add skill: alert me when listings have a pool
        text = update.message.text.split("add skill:")[1].strip()
        await update.message.reply_text(f"🛠 Generating skill: `{text}`...", parse_mode='Markdown')
        
        # Trigger Gemini skill generation
        try:
            from listing_agent.skills import generate_and_save_skill
            try:
                skill_name = await generate_and_save_skill(text)
                await update.message.reply_text(f"✅ Skill added: `{skill_name}` active.")
                log_activity("SKILL", f"New skill generated: {skill_name}")
            except Exception as gemini_err:
                log_activity("ERROR", f"gemini_call failed in h_add_skill: {gemini_err}")
                await update.message.reply_text(f"❌ Skill generation failed: {str(gemini_err)}")
        except Exception as e:
            await update.message.reply_text(f"❌ Operation failed: {str(e)}")
            log_activity("ERROR", f"h_add_skill failed: {e}")

    async def h_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Read last 20 lines of activity.log."""
        from listing_agent.activity_log import LOG_PATH
        if not os.path.exists(LOG_PATH):
            await update.message.reply_text("📋 Activity log is empty.")
            return
            
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_20 = lines[-20:]
                
            msg = "📋 *Last 20 Agent Actions:*\n`" + "".join(last_20) + "`"
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error reading log: {e}")
            log_activity("ERROR", f"h_log failed: {e}")

    async def h_regions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        events = agent_memory.data.get("event_log", [])
        # Get recent scanner alerts to aggregate region stats
        recent_alerts = [e for e in events if e['type'] == 'alert_fired'][-100:]
        
        from collections import Counter
        counts = Counter(e['data'].get('region', 'Unknown') for e in recent_alerts)
        
        msg = "📍 *GTA Regional Activity (Recent Alerts)*\n"
        if not counts:
            msg += "No recent listings processed yet."
        else:
            for region, count in sorted(counts.items()):
                msg += f"• *{region}*: {count}\n"
        
        await update.message.reply_text(msg, parse_mode='Markdown')


async def _generate_video_script(listing: dict) -> dict:
    """Use Gemini to write a voiceover script + headline from listing data."""
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return _fallback_script(listing)

        client = genai.Client(api_key=api_key)
        address = listing.get("address", "Beautiful GTA property")
        price = listing.get("price", "")
        beds = listing.get("bedrooms") or listing.get("beds", "")
        baths = listing.get("bathrooms") or listing.get("baths", "")
        sqft = listing.get("area") or listing.get("sqft", "")
        desc = listing.get("description", "")

        prompt = (
            "You are a luxury real estate video narrator. Write a 30-second voiceover "
            "script (~75 words) for this listing. Tone: warm, confident, cinematic.\n\n"
            f"Address: {address}\nPrice: {price}\nBeds: {beds}  Baths: {baths}  SqFt: {sqft}\n"
            f"Description: {desc[:300]}\n\n"
            "Return ONLY valid JSON with these keys:\n"
            '  "headline": short catchy tagline (≤8 words),\n'
            '  "voiceover_script": the full narration,\n'
            '  "music_mood": one of cinematic_luxury | warm_inspiring | modern_elegant | cozy_intimate\n'
        )

        import json as _json
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = _json.loads(text)
        if "voiceover_script" in data:
            logger.info(f"Gemini script generated: {data['headline']}")
            return data
    except Exception as e:
        logger.warning(f"Gemini script generation failed, using fallback: {e}")

    return _fallback_script(listing)


def _fallback_script(listing: dict) -> dict:
    """Deterministic fallback when Gemini is unavailable."""
    addr = listing.get("address", "this stunning property")
    price = listing.get("price", "")
    beds = listing.get("bedrooms") or listing.get("beds", "")
    baths = listing.get("bathrooms") or listing.get("baths", "")
    return {
        "headline": f"Welcome to {addr.split(',')[0]}",
        "voiceover_script": (
            f"Welcome to {addr}. "
            f"{'Offered at ' + str(price) + '. ' if price else ''}"
            f"{'This ' + str(beds) + ' bedroom, ' + str(baths) + ' bathroom home ' if beds else 'This home '}"
            f"offers an exceptional blend of style and comfort. "
            f"Every detail has been thoughtfully designed for modern living. "
            f"Premium finishes, abundant natural light, and an unbeatable location "
            f"make this one of the most compelling opportunities on the market today. "
            f"Schedule your private viewing before it's gone."
        ),
        "music_mood": "cinematic_luxury",
    }


async def _run_video_and_deliver(
    url: str,
    chat_id: str,
    tier: str = "basic",
    config: dict | None = None,
):
    try:
        bot_client = Bot(token=TELEGRAM_BOT_TOKEN)
        
        from scraper.realtor_ca import scrape_listing_details
        # realtor_ca might not exist or have scrape_listing_details in this version
        # Let's check if we can use an alternative or if it's there
        try:
            listing = await scrape_listing_details(url)
        except (ImportError, AttributeError):
            # Fallback to demo_api's helper if available via import
            from demo_api import build_fallback_listing
            listing = build_fallback_listing(url)

        # Merge tier configuration flags into listing_data
        config = config or {}
        listing_data = {
            **listing,
            "paid_order": config.get("paid_order", False),
            "enhance_photos": config.get("enhance_photos", False),
        }

        address = listing_data.get("address", url)
        price = listing_data.get("price", "")

        progress_msg = await bot_client.send_message(
            chat_id=chat_id,
            text=f"🎬 Generating video for {address}...\n"
                 f"⏱ Step 1/4: Downloading photos"
        )

        async def update_progress(step: int, label: str):
            try:
                await bot_client.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=f"🎬 Generating video for {address}...\n"
                         f"⏱ Step {step}/4: {label}"
                )
            except Exception:
                pass

        from video_pipeline.video_producer import produce_video
        import time
        from pathlib import Path

        job_id = f"tg_{int(time.time())}"
        job_dir = Path(f"video_pipeline/temp/{job_id}")

        # script_data=None → pipeline will analyze actual photos with
        # Gemini Vision and generate an accurate scene-by-scene narration
        output_path = await produce_video(
            listing_url=url,
            listing_data=listing_data,
            job_dir=job_dir,
            script_data=None,
            progress_callback=update_progress,
            force_veo=config.get("force_veo", False),
        )

        if output_path and Path(output_path).exists():
            file_size_mb = Path(output_path).stat().st_size / (1024*1024)
            if file_size_mb > 50:
                await bot_client.send_message(
                    chat_id=chat_id,
                    text=f"✅ Video ready! File is {file_size_mb:.1f}MB\n"
                         f"📁 Saved to: {output_path}\n"
                         f"(Too large for Telegram — check your PC)"
                )
            else:
                agent_name = AGENT_CONFIG.get("agent_name", "AI Agent")
                with open(output_path, 'rb') as video_file:
                    await bot_client.send_video(
                        chat_id=chat_id,
                        video=video_file,
                        caption=f"🏠 {address}\n"
                                f"💰 {price}\n"
                                f"🎬 Generated by {agent_name}",
                        supports_streaming=True,
                        width=1920,
                        height=1080
                    )
                log_activity("VIDEO", f"Sent via Telegram: {address}")
        else:
            await bot_client.send_message(
                chat_id=chat_id,
                text=f"❌ Video generation failed for {address}"
            )

    except Exception as e:
        log_activity("ERROR", f"Telegram video delivery failed: {e}")
        try:
            bot_client = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot_client.send_message(
                chat_id=chat_id,
                text=f"❌ Video failed: {str(e)}"
            )
        except Exception:
            pass


    async def _run_photos_video_and_deliver(
        self,
        chat_id: int,
        job_dir: Path,
        listing_data: Dict[str, Any],
    ):
        """Run photo-based video pipeline and deliver the result to Telegram."""
        from video_pipeline.video_producer import produce_video

        try:
            bot_client = Bot(token=TELEGRAM_BOT_TOKEN)

            progress_msg = await bot_client.send_message(
                chat_id=chat_id,
                text="⏳ Rendering video..."
            )

            async def update_progress(step: int, label: str):
                try:
                    await bot_client.edit_message_text(
                        chat_id=chat_id,
                        message_id=progress_msg.message_id,
                        text=f"🎬 Rendering video...\n⏱ Step {step}/4: {label}",
                    )
                except Exception:
                    # Edits can fail if user deletes message or we hit rate limits.
                    pass

            final_path = await produce_video(
                listing_url="custom_upload",
                listing_data=listing_data,
                job_dir=job_dir,
                script_data=None,
                progress_callback=update_progress,
            )

            if final_path and Path(final_path).exists():
                final_path = Path(final_path)
                file_size = final_path.stat().st_size
                if file_size < 50_000_000:  # ~50MB Telegram limit
                    with final_path.open("rb") as f:
                        await bot_client.send_video(
                            chat_id=chat_id,
                            video=f,
                            caption=(
                                "🏠 Your video is ready!\n"
                                f"{listing_data.get('address', 'Custom Property')}"
                            ),
                            supports_streaming=True,
                        )
                    log_activity("VIDEO", f"Sent photo-based video to chat {chat_id}")
                else:
                    await bot_client.send_message(
                        chat_id=chat_id,
                        text=(
                            "✅ Video ready but too large for Telegram.\n"
                            f"Path: {final_path}"
                        ),
                    )
            else:
                await bot_client.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Video generation failed. "
                        "Please try again with fewer photos."
                    ),
                )
        except Exception as e:
            log_activity("ERROR", f"Photo video delivery failed: {e}")
            try:
                bot_client = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot_client.send_message(
                    chat_id=chat_id,
                    text=f"❌ Video failed: {str(e)}",
                )
            except Exception:
                pass

# Singleton bot instance
bot = TelegramBot()
