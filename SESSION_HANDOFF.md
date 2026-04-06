# 416Homes — Session Handoff
_Last updated: 2026-04-06_

---

## Current State

The project is **fully deployed** and functional on Vercel (frontend) + Railway (backend).
All critical bugs from the previous two sessions have been fixed and merged to `main`.

### Live URLs
- **Frontend (Vercel):** check Vercel dashboard — Next.js `web-next/`
- **Backend (Railway):** `api-server` service — FastAPI on port 8000
- **Health check:** `GET /health` → `{"status":"ok"}`

---

## What Was Completed (This Session)

### Design Overhaul (PR #5 — merged)
- "Neon-Noir Obsidian Luxury" redesign applied across `web-next/`
- Cormorant Garamond serif headlines, Brushed Gold `#D4AF37`, Obsidian `#0B0B0B`
- Glassmorphism utilities: `.glass-panel`, `.gold-gradient`, `.gold-glow`
- Framer Motion staggered entrance animations replacing manual `IntersectionObserver`
- Files: `layout.tsx`, `globals.css`, `page.tsx`, `listing-card.tsx`, `video/page.tsx`

### Backend Hardening + Photos (PR #7 — merged)
- `secrets.choice` replaces `random.choice` in link-code generation
- Atomic upsert for user creation (no race condition)
- Video worker wraps job in try/except, marks `failed` on crash
- Pydantic v2: `model_dump()` replaces `dict()`
- `datetime.now(timezone.utc)` replaces deprecated `datetime.utcnow()`
- `buyer_alerts` table renamed to `alerts` (aligned with API write path)
- `market_analysis_from_ppsf()` extracted to `valuation/model.py`, shared with `api/main.py`
- Photos wired end-to-end: scraper `photo` field → `listings.photo` DB column → API → dashboard cards
- Old gold tokens `#c8a96e` purged from all UI components → `#D4AF37`
- HouseSigma scraper: `headless=True`

### Bug Fixes (PR #8 — merged)
- **Embedding error fixed:** Removed unsupported `output_dimensionality=768` kwarg from `memory/store.py` `embed_content()` — was causing `TypeError` on every embedding call, so no listing ever got a vector
- **Bedroom parse error fixed:** Added `_parse_room_count()` in `memory/store.py` — converts realtor.ca's `"1 + 1"` (bedroom + den) strings to `"2"` before DB insert, fixing `22P02 invalid input syntax for type numeric`
- **Railway startup crash fixed:** `import joblib` moved inside `try/except` in `valuation/model.py` — joblib is absent from `requirements-railway.txt`, was crashing the API on startup; `save_model`/`load_model` now guard against `joblib is None`

---

## File Map

```
scraper/
  orchestrator.py       concurrent multi-source runner + dedup
  realtor_ca.py         stealth + API + Playwright fallback; photo field included
  housesigma.py         sold comps, headless=True
  kijiji.py / redfin.py / zoocasa.py
  run_all.py            CLI: python -m scraper.run_all --source X --area Y

memory/store.py
  _parse_room_count()   converts "1 + 1" → "2" before DB insert
  embed_text()          no output_dimensionality kwarg (fixed)

valuation/model.py
  market_analysis_from_ppsf()  top-level helper shared with api/main.py
  ValuationModel               joblib inside try/except (Railway-safe)
  _DS_ENABLED                  False on Railway (LightGBM not installed there)

agent/main.py           nightly match → valuate → email loop
  table: "alerts"       (not "buyer_alerts")
  alert fields: min_beds, property_types, neighbourhoods

api/main.py             FastAPI
  /health               → {"status":"ok"}
  /api/listings         paginated, filterable
  /api/valuate          LightGBM → fallback $900/sqft
  /api/alerts           CRUD (table: alerts)
  /api/video/*          job create/status/revision
  /api/stripe/webhook   payment handler

api/init_db.py          prints Supabase schema SQL

web-next/
  src/app/layout.tsx          Cormorant Garamond + Inter fonts
  src/app/globals.css         CSS tokens + glass/gold utilities
  src/app/page.tsx            landing page (Framer Motion)
  src/app/dashboard/page.tsx  dashboard + listing cards + valuation
  src/app/video/page.tsx      video order flow
  src/components/listing-card.tsx   glassmorphic card
  src/lib/api.ts              reads photos from l.photos or l.photo
  src/lib/supabase.ts         placeholder fallback for missing env vars
```

---

## Database Schema Notes

Key tables in Supabase:
- `listings` — active listings with `photo TEXT`, `embedding vector(768)`
- `sold_comps` — sold comps from HouseSigma
- `video_jobs` — video pipeline state machine
- `alerts` — buyer alerts (**NOT** `buyer_alerts`)
- `agent_matches` — listing × alert match log
- `users` — email-based user records

To re-init schema: `python api/init_db.py` → copy SQL → paste in Supabase SQL Editor.
The `photo TEXT` column is included in the schema. If your DB pre-dates it, run:
```sql
ALTER TABLE listings ADD COLUMN IF NOT EXISTS photo TEXT;
```

---

## Environment Variables Required

```
SUPABASE_URL=
SUPABASE_KEY=                    # anon key
SUPABASE_SERVICE_ROLE_KEY=       # service role key (preferred server-side)

GEMINI_API_KEY=
GEMINI_EMBEDDING_MODEL=gemini-embedding-001   # optional, this is the default

RESEND_API_KEY=
AGENT_EMAIL=                     # from address for outreach emails
LISTING_AGENT_EMAIL=             # default outreach recipient

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

ELEVENLABS_API_KEY=
VEO_PROJECT_ID=                  # Google Vertex AI project for Veo
GOOGLE_APPLICATION_CREDENTIALS= # path to service account JSON

AGENT_SECRET=                    # header secret for /agent/* endpoints
```

---

## Pending / Next Steps

### Must Do Before Photos Show Up
1. **Run Supabase photo migration** (if DB was created before `photo` column):
   ```sql
   ALTER TABLE listings ADD COLUMN IF NOT EXISTS photo TEXT;
   ```
2. **Run one full scraper pass** to populate `photo` with real URLs:
   ```bash
   python -m scraper.run_all --source all --area gta
   ```

### Must Do Before Valuation Works Accurately
3. **Train the LightGBM model** (needs sold comps in DB first):
   ```bash
   python valuation/model.py
   ```
   Or: GitHub Actions → "416Homes Model Retraining" → Run workflow.
   Target MAPE < 10%. Workflow commits `valuation_model.pkl` back to repo so Railway picks it up.

### Nice to Have
- Improve sold comps neighbourhood coverage (HouseSigma `neighbourhood` field often blank)
- Listing photo carousel in dashboard card (currently single photo)
- "Save listing" / "mark seen" per-user persistence
- Telegram alert integration (scaffolded, needs `TELEGRAM_BOT_TOKEN` env var)

---

## Test Commands

```bash
# Scraper — should show ≥10 listings, no 22P02 numeric errors, no embedding TypeErrors
python -m scraper.run_all --source realtor_ca --area toronto
python -m scraper.run_all --source all --area gta

# API
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/health
curl "http://localhost:8000/api/listings?limit=5"

# Valuation model
python valuation/model.py    # target MAPE <10%

# Agent loop
python agent/main.py

# Video pipeline
python video_pipeline/pipeline.py https://www.realtor.ca/real-estate/LISTING_URL
```

---

## PR / Branch History

| PR | Status | Summary |
|----|--------|---------|
| #5 | Merged | Luxury redesign |
| #6 | Merged | Copilot codebase analysis |
| #7 | Merged | Photos end-to-end + backend hardening |
| #8 | Merged | 3 bug fixes (embedding / bedroom parse / Railway startup) |

All work is on `main`. No open PRs. No open conflicts.

---

## Tech Stack Quick Reference

| Layer | Tool |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind 4 + Framer Motion |
| Backend | FastAPI + uvicorn (Railway) |
| Scraping | scrapling + AsyncDynamicSession / Playwright fallback |
| LLM | Gemini 2.5 Flash (`google-genai` SDK) |
| Embeddings | `gemini-embedding-001` via `client.models.embed_content()` |
| Database | Supabase Postgres + pgvector (768-dim) |
| ML | LightGBM (disabled on Railway; fallback $900/sqft used) |
| Email | Resend |
| Payments | Stripe |
| Video | ElevenLabs TTS + Veo (Vertex AI) |
| CI/CD | GitHub Actions (nightly scrape + model retrain workflows) |
