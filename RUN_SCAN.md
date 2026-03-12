# Run Nightly Scan (Refresh Listings in Supabase)

The nightly scan scrapes all sources (Realtor.ca, Zoocasa, Condos.ca, Kijiji), then **replaces** Supabase listings with the new set (old ones are removed). Dashboard and Telegram both read from Supabase, so they show the updated data.

You can run it in two ways.

---

## Option 1: Railway CLI (run in Railway’s environment)

Use this when you want the scan to run with Railway’s env (Cloudflare, Supabase, Gemini, etc.).

1. **Install Railway CLI** (if needed): https://docs.railway.app/develop/cli  
2. **Log in and link the project:**
   ```bash
   railway login
   cd path/to/416homesV3
   railway link
   ```
3. **Run the scan** (uses the linked project’s env):
   ```bash
   railway run python scripts/run_nightly_scan.py
   ```
4. Wait for it to finish (a few minutes). When you see “Supabase replaced: N listings stored”, refresh the dashboard or use `/listings` in Telegram.

---

## Option 2: Trigger via API (background scan on the API server)

Use this to start a scan from anywhere (browser, Postman, curl, another service). The scan runs in the background on the API server; no need to keep a terminal open.

1. **Call the endpoint** (replace with your API URL if different):
   ```bash
   curl -X POST https://web-production-61e684.up.railway.app/api/initiate-scan
   ```
2. You get an immediate response, e.g.:
   ```json
   {"status":"started","message":"Nightly scan started. Listings will be replaced when complete. Check logs or /api/listings in a few minutes."}
   ```
3. Wait a few minutes, then check:
   - **Dashboard:** open the app and refresh.
   - **API:** `GET https://web-production-61e684.up.railway.app/api/listings?limit=5`
   - **Telegram:** use `/listings` (it reads from the same API/Supabase).

---

## Env required (for both options)

- **Option 1 (Railway CLI):** The linked Railway project must have at least `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`. For Realtor.ca/Condos.ca when blocked, add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` (see [CRAWLING_SETUP.md](CRAWLING_SETUP.md)).
- **Option 2 (API):** The **api-server** service on Railway must have the same env vars (Supabase, Gemini; optional Cloudflare). The scan runs in that service’s process.

You can use **both**: e.g. trigger via API for ad‑hoc refreshes, and use the CLI when you want to run it from your machine with Railway’s env.
