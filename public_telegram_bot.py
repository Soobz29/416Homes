"""
416Homes — Public Telegram bot (end users).
Uses TELEGRAM_BOT_TOKEN_PUBLIC. Commands: /start, /link, /alerts, /help.
"""

import os
import logging
from datetime import datetime, timezone
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pathlib import Path
from dotenv import load_dotenv

try:
    from supabase import create_client, Client  # type: ignore
except Exception:
    create_client = None  # type: ignore[misc]
    Client = None  # type: ignore[misc]

# Load .env from project root (same folder as run_agent.py)
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)
logger = logging.getLogger(__name__)


def _read_token_from_env_file() -> str | None:
    """Fallback: read TELEGRAM_BOT_TOKEN_PUBLIC directly from .env if getenv failed."""
    try:
        if not _env_path.exists():
            return None
        with open(_env_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN_PUBLIC="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val if val else None
    except Exception as e:
        logger.debug("Could not read .env for TELEGRAM_BOT_TOKEN_PUBLIC: %s", e)
    return None


TELEGRAM_BOT_TOKEN_PUBLIC = os.getenv("TELEGRAM_BOT_TOKEN_PUBLIC") or _read_token_from_env_file()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Service role key bypasses RLS so the bot can read users by link_code and update telegram_chat_id.
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class PublicTelegramBot:
    """Public-facing bot: link account and view alerts only."""

    def __init__(self):
        self.app = None
        self.is_running = False
        self.supabase: Client | None = None
        key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
        if create_client and SUPABASE_URL and key:
            try:
                self.supabase = create_client(SUPABASE_URL, key)
                if not SUPABASE_SERVICE_ROLE_KEY:
                    logger.warning(
                        "SUPABASE_SERVICE_ROLE_KEY not set; /link may fail if RLS blocks anon on users table. "
                        "Add service_role key from Supabase Dashboard → Settings → API."
                    )
            except Exception as e:
                logger.error("Failed to init Supabase in PublicTelegramBot: %s", e)

    async def start(self):
        if not TELEGRAM_BOT_TOKEN_PUBLIC:
            logger.warning("TELEGRAM_BOT_TOKEN_PUBLIC not set; public bot will not start")
            return

        self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN_PUBLIC).build()
        self.app.add_handler(CommandHandler("start", self.h_start))
        self.app.add_handler(CommandHandler("link", self.h_link))
        self.app.add_handler(CommandHandler("alerts", self.h_alerts))
        self.app.add_handler(CommandHandler("help", self.h_help))

        await self.app.initialize()
        await self.app.start()

        try:
            await self.app.bot.set_my_commands(
                [
                    BotCommand("start", "Welcome & get started"),
                    BotCommand("link", "Link this chat to your 416Homes account"),
                    BotCommand("alerts", "Show your saved alerts"),
                    BotCommand("help", "How to use this bot"),
                ]
            )
        except Exception as e:
            logger.warning("Failed to set public bot commands: %s", e)

        await self.app.updater.start_polling()
        self.is_running = True
        logger.info("Public Telegram bot started and polling.")

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self.is_running = False
        logger.info("Public Telegram bot stopped.")

    async def h_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Welcome to 416Homes Alerts!\n\n"
            "I'll send you instant notifications when properties matching "
            "your criteria hit the market.\n\n"
            "To get started:\n"
            "1. Create an account at 416homes.com\n"
            "2. Click \"Connect Telegram\" in your dashboard\n"
            "3. Copy the code and send it here with /link\n\n"
            "Example: /link TG-A1B2C3",
            parse_mode="HTML",
        )

    async def h_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🔗 *Link your account*\n"
            "1. Sign in at the 416Homes dashboard and open *Connect Telegram*.\n"
            "2. Send /link followed by the code shown (e.g. /link TG-ABCD).\n\n"
            "📋 *Alerts*\n"
            "Create and edit alerts on the dashboard. Use /alerts here to see them.",
            parse_mode="Markdown",
        )

    async def h_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.supabase:
            await update.message.reply_text("Alerts are not configured yet.")
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
                    "Create an alert in the web dashboard and use /link with the code from 'Connect Telegram'."
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
            logger.error("/alerts failed: %s", e)
            await update.message.reply_text("❌ Failed to load alerts.")

    async def h_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.supabase:
            await update.message.reply_text("Linking is not configured yet.")
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /link TG-XXXX\n\n"
                "Open the 416Homes dashboard, click 'Connect Telegram', "
                "then paste the code shown there after /link."
            )
            return

        code = context.args[0].strip().upper()
        chat_id = update.effective_chat.id
        username = (update.effective_user.username or "").strip() if update.effective_user else ""

        try:
            resp = self.supabase.table("users").select("id,email,preferences").execute()
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
                            s = str(expires).strip().replace("Z", "+00:00").rstrip(".")
                            if s and "+00:00" not in s and "+" not in s and "Z" not in s:
                                s = s.rstrip("Z") + (":00" if s.count(":") == 1 else "") + "+00:00"
                            if s:
                                expiry_dt = datetime.fromisoformat(s)
                                if expiry_dt.tzinfo is None:
                                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                                if expiry_dt < datetime.now(timezone.utc):
                                    continue
                        except Exception:
                            pass
                    target = row
                    break

            if not target:
                await update.message.reply_text(
                    "❌ That code is invalid or has expired. Generate a new one from your dashboard."
                )
                return

            user_id = target.get("id")
            if user_id is None:
                await update.message.reply_text("❌ User record has no id. Contact support.")
                return
            pk_col = "id"

            prefs = dict(target.get("preferences") or {})
            prefs.pop("link_code", None)
            prefs.pop("link_expires_at", None)

            # One Telegram chat can only be linked to one user. Clear it from any other user first.
            try:
                self.supabase.table("users").update({
                    "telegram_chat_id": None,
                    "telegram_username": None,
                }).eq("telegram_chat_id", int(chat_id)).neq(pk_col, user_id).execute()
            except Exception:
                pass

            payload = {
                "telegram_chat_id": int(chat_id),
                "preferences": prefs,
            }
            if username:
                payload["telegram_username"] = username

            self.supabase.table("users").update(payload).eq(pk_col, user_id).execute()

            email = target.get("email") or "your account"
            await update.message.reply_text(
                f"✅ Success! This chat is now linked to {email}.\n\n"
                "You'll receive alerts here when new properties match your criteria."
            )
        except Exception as e:
            err_msg = str(e).strip() or type(e).__name__
            logger.exception("/link failed: %s", err_msg)
            await update.message.reply_text(
                "❌ Failed to link this chat. Please try again. "
                "Check the terminal where the bot runs for the error; add SUPABASE_SERVICE_ROLE_KEY to .env if needed."
            )


# Singleton for run_agent.py
public_bot = PublicTelegramBot()


async def send_user_alert(chat_id: int, listing: dict) -> None:
    """
    Send a new-listing alert to a user via the public bot (Stage 2: nightly alerts).
    Call from listing_agent when a listing matches a user's alert.
    """
    if not TELEGRAM_BOT_TOKEN_PUBLIC:
        logger.warning("TELEGRAM_BOT_TOKEN_PUBLIC not set; skipping user alert")
        return
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN_PUBLIC)
        address = listing.get("address", "Property")
        price = listing.get("price") or listing.get("list_price") or ""
        price_str = f"${int(price):,}" if price else "Price N/A"
        beds = listing.get("bedrooms") or listing.get("beds") or ""
        baths = listing.get("bathrooms") or listing.get("baths") or ""
        url = listing.get("url", "")
        message = (
            f"🏠 New Listing Match!\n\n"
            f"📍 {address}\n"
            f"💰 {price_str}\n"
            f"🛏 {beds} beds · 🛁 {baths} baths\n"
        )
        if listing.get("area") or listing.get("sqft"):
            message += f"📏 {listing.get('area') or listing.get('sqft')} sqft\n"
        if url:
            message += f"\n🔗 {url}"
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.exception("send_user_alert failed: %s", e)
