# Changelog: Telegram Bots & Link Flow

Summary of changes made during the Telegram public-bot split, link-code fixes, and related updates.

---

## 1. Public Telegram bot (new)

**File:** `public_telegram_bot.py`

- New bot that uses **`TELEGRAM_BOT_TOKEN_PUBLIC`** from `.env`.
- Commands: **`/start`**, **`/link`**, **`/alerts`**, **`/help`** (no admin commands).
- Supabase client:
  - Prefers **`SUPABASE_SERVICE_ROLE_KEY`** when set (bypasses RLS for `/link` and `/alerts`).
  - Falls back to **`SUPABASE_KEY`** (anon); logs a warning that `/link` may fail if RLS blocks reads on `users`.
- Token loading:
  - **`TELEGRAM_BOT_TOKEN_PUBLIC`** read via `os.getenv()` first.
  - Fallback **`_read_token_from_env_file()`** reads `.env` from project root and parses the `TELEGRAM_BOT_TOKEN_PUBLIC=` line so the bot works even when `getenv` fails (e.g. wrong cwd).
- `.env` path:
  - **`load_dotenv(Path(__file__).resolve().parent / ".env")`** so the same `.env` is used regardless of current working directory.
- **`/link` logic:**
  - Code comparison: `prefs.get("link_code", "").upper() == code` (case-insensitive).
  - **Expiry parsing:** Timezone-aware comparison using `datetime.now(timezone.utc)`.
  - **Defensive expiry strings:** Handles truncated DB values (e.g. `"2026-03-11T00:07"` without seconds/timezone):
    - Normalize string (add `:00` and `+00:00` when missing).
    - If parsed datetime is naive, treat as UTC with `expiry_dt.replace(tzinfo=timezone.utc)`.
    - If parsing raises, do **not** reject the code (only skip when we’re sure expiry is in the past).
  - **Logging:** On failure, **`logger.exception("/link failed")`** so the full traceback appears in the bot logs.

---

## 2. Launcher: run both bots

**File:** `run_agent.py`

- Load **`.env` from project root:**  
  `_env_path = Path(__file__).resolve().parent / ".env"` and `load_dotenv(_env_path)` so env vars are correct no matter where the process is started.
- Start **admin bot** (`telegram_bot.bot`) then **public bot** (`public_telegram_bot.public_bot`).
- On shutdown: stop **public bot** first, then admin bot.

---

## 3. API: link-code expiry

**File:** `api/main.py`

- **`datetime`:** Added `timezone` to imports: `from datetime import datetime, timedelta, timezone`.
- **Link-code endpoint** (`POST /api/link-code`):
  - Expiry set to **30 minutes** (was 1 hour, then 24 hours):  
    `(datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")`.
  - Stored expiry is always full ISO with Z: `%Y-%m-%dT%H:%M:%S.000Z` to avoid truncation in the DB.

---

## 4. Dashboard: rate-limit message

**File:** `web-next/src/app/dashboard/page.tsx`

- In **`handleAuthSubmit`** (magic-link sign-in): if the error message matches `/rate limit/i`, show a friendlier message:  
  **"Too many login attempts. Please wait a few minutes and try again."**  
  (Supabase Auth returns “email rate limit exceeded”.)

---

## 5. Test script for link flow

**File:** `scripts/test_link_code.py` (new)

- Local script that runs the **same** Supabase lookup and expiry logic as the public bot (no Telegram).
- **Usage:** From project root,  
  `python scripts/test_link_code.py TG-XXXX`  
  (use a fresh code from the dashboard “Connect Telegram”.)
- **Behavior:**
  - Loads `.env` from project root and connects to Supabase (same key logic as bot).
  - Fetches all `users`, prints each row’s `link_code` and `link_expires_at`.
  - For the given code: reports match/no match and whether expiry is valid.
  - Prints **MATCH** (bot would link) or **NO MATCH** (not found or expired).
- Use this to verify link logic and DB data without sending `/link` in Telegram.

---

## 6. Unchanged

- **`telegram_bot.py`** (admin bot): Still uses **`TELEGRAM_BOT_TOKEN`** and **`TELEGRAM_CHAT_ID`**; all existing admin commands and **`send_notification()`** unchanged.
- **Dashboard, API routes, Supabase schema:** No other changes besides the items above.
- **Stage 2 (nightly per-user alerts via public bot):** Not implemented yet.

---

## Environment variables (reference)

| Variable | Where used | Purpose |
|----------|------------|---------|
| `TELEGRAM_BOT_TOKEN` | Admin bot, `send_notification()` | Admin bot and ops notifications to `TELEGRAM_CHAT_ID`. |
| `TELEGRAM_BOT_TOKEN_PUBLIC` | Public bot | Public bot (e.g. 416Homes Alerts). |
| `TELEGRAM_CHAT_ID` | Admin bot | Target chat for admin/ops messages. |
| `SUPABASE_URL` | API, bots, script | Supabase project URL. |
| `SUPABASE_KEY` | API, bots, script | Anon key. |
| `SUPABASE_SERVICE_ROLE_KEY` | Public bot (optional), script | Service role key so bot can read/update `users` if RLS is enabled. |

---

## User-flow alignment (from spec)

- **API**
  - **GET /api/me**: Returns `id`, `email`, `telegram_chat_id`, `telegram_username` for the user identified by `x-user-email`. Used by the dashboard to show "Connected!" and for the "Check status" button.
  - **Link code**: Now **6 characters** (e.g. `TG-A1B2C3`) for slightly better entropy; still 30-minute expiry.
- **Dashboard**
  - **Linked state**: On load and after "I've linked it, check status", calls **/api/me** and shows a "Connected!" block when `telegram_chat_id` is set.
  - **Connect Telegram**: When a code is shown, instructions reference @Homes_Alertsbot and the exact `/link CODE` command; **"I've linked it, check status"** button refetches /api/me and clears the code when linked.
- **Public bot**
  - **/start**: Welcome text updated to match spec (416homes.com, Connect Telegram, example /link TG-A1B2C3).
  - **/link success**: Reply includes the user’s email: "Success! This chat is now linked to {email}."
  - **send_user_alert(chat_id, listing)**: New helper for Stage 2; call from the listing agent to send a "New Listing Match!" message via the public bot. Listing dict can have address, price, bedrooms, bathrooms, area/sqft, url.
- **Test script**
  - On **MATCH**, prints: "✅ MATCH — Code is valid", User email, Expires (UTC), "Valid (X minutes remaining)".

---

## Quick test checklist

1. **Public bot starts:**  
   `python run_agent.py` → log line “Public Telegram bot started and polling.”
2. **Link code test:**  
   Dashboard → Connect Telegram → copy code →  
   `python scripts/test_link_code.py TG-XXXX` → expect **MATCH** for a valid, non-expired code.
3. **Telegram link:**  
   In the public bot chat, send `/link TG-XXXX` (same code) → expect “This chat is now linked…”.
4. **Alerts in bot:**  
   Send `/alerts` → expect your dashboard alerts (or “You don’t have any alerts yet”).
