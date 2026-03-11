# 416Homes — Test & Demo

Quick commands to test or demo the dashboard ↔ Telegram link flow and API.

---

## 1. Test link code (no Telegram, no API)

Uses your `.env` and Supabase only. Good to verify DB and code logic.

```powershell
cd c:\Users\soobo\Downloads\416homesV3
python scripts/test_link_code.py TG-DEMO
```

- **NO MATCH** (e.g. for `TG-DEMO`) = script is working; no user has that code.
- To see **MATCH**: generate a real code in the dashboard (Connect Telegram), then run:
  ```powershell
  python scripts/test_link_code.py TG-XXXXXX
  ```
  (Replace with the code shown in the dashboard.)

---

## 2. API health check

Start the API, then hit health:

```powershell
# Terminal 1
cd c:\Users\soobo\Downloads\416homesV3
uvicorn api.main:app --reload --port 8000
```

```powershell
# Terminal 2 (or browser)
curl http://localhost:8000/api/health
```

Expected: `{"status":"healthy","service":"416Homes API","version":"1.0.0"}`

---

## 3. Full link-flow demo

**Prereqs:** API and (optional) public bot running.

| Step | Action |
|------|--------|
| 1 | Start API: `uvicorn api.main:app --reload --port 8000` |
| 2 | Start Next.js dashboard: `cd web-next && npm run dev` → open http://localhost:3000/dashboard |
| 3 | Sign in with magic link (use a real email or test one). |
| 4 | Click **Connect Telegram** → copy the code (e.g. `TG-A1B2C3`). |
| 5 | Run test script: `python scripts/test_link_code.py TG-A1B2C3` → expect **MATCH** and "X minutes remaining". |
| 6 | (Optional) Start bots: `python run_agent.py` → in Telegram, send `/link TG-A1B2C3` to the public bot. |
| 7 | Back in dashboard, click **I've linked it, check status** → should show **Connected!**. |
| 8 | In Telegram, send `/alerts` → should list your dashboard alerts. |

---

## 4. Run agent (bots + scheduler + listing loop)

```powershell
cd c:\Users\soobo\Downloads\416homesV3
python run_agent.py
```

- Admin bot (your ops token) + public bot (alerts) start; scheduler and 30‑min listing scan run.
- Stop with **Ctrl+C**.

---

## 5. One-liner test summary

```powershell
cd c:\Users\soobo\Downloads\416homesV3
python scripts/test_link_code.py TG-DEMO
```

If you see "Loaded N user(s)" and "Result: NO MATCH", the script and Supabase connection are working.
