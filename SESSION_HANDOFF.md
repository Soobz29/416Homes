# 416Homes — Session Handoff

**Last updated:** 2026-04-01  
**Branch:** `claude/add-claude-documentation-9bkXo`  
**HEAD:** `e4f0280`  
**Repo:** `github.com/Soobz29/416Homes`

---

## What Was Done This Session

Two large commits + one fix were pushed:

| Commit | What |
|---|---|
| `7ae2732` | P1–P5: CORS, embedding cache, concurrent emails, valuation confidence, scraper fixes, workflow parallelization |
| `5f57908` | P6: auth system, dashboard pagination, video revision endpoint + UI, Telegram `/newalert` flow |
| `e4f0280` | Fix: `neighborhoods` → `neighbourhoods` in `buyer_alerts` schema (init_db.py) |

---

## Current State of Every File Changed

### `api/main.py`
- CORS reads from `APP_URL` env var (comma-separated list) instead of `"*"`
- All list endpoints have bounded pagination: `limit: int = Query(default=20, ge=1, le=200)`, `offset: int = Query(default=0, ge=0)`
- New endpoints added:
  - `POST /api/auth/magic-link` — sends Supabase OTP to email
  - `POST /api/auth/session` — validates token, returns user email
  - `POST /api/video-jobs/{job_id}/revision` — max 1 revision per job, stores notes, sets status `revision_requested`
  - `GET /agent/status`, `POST /agent/start`, `POST /agent/stop` — agent control
  - `GET /agent/alerts`, `PATCH /agent/alerts/{id}/seen` — alert management
  - `POST /api/run-agent` — protected by `AGENT_SECRET` header
  - `GET /auth.js` — serves `web/auth.js`

### `api/init_db.py`
- `video_jobs` table: added `revision_count INTEGER DEFAULT 0`, `revision_notes TEXT`
- `video_jobs` status CHECK includes `'complete'`, `'revision_requested'`
- `buyer_alerts` table: `neighbourhoods TEXT[] DEFAULT '{}'` (British spelling, was `neighborhoods`)
- Index: `idx_sold_comps_neighbourhood` (was `idx_sold_comps_neighborhood`)

### `memory/store.py`
- `MemoryStore.__init__` initialises `self._embedding_cache: Dict[str, List[float]] = {}`
- `embed_text()` returns cached value if present; on cache miss calls Gemini then stores result; evicts oldest entry when cache exceeds 1024

### `valuation/model.py`
- During training, stores `self.numeric_medians['price_per_sqft'] = float(df['price_per_sqft'].median())`
- `predict()` uses `median_ppsf = self.numeric_medians.get('price_per_sqft', 700)` for confidence calculation (was incorrectly keyed on `'sqft'`)

### `agent/main.py`
- Email sending is now concurrent: `asyncio.gather(*[_process_match(l, s) for l, s in good_matches])` with `Semaphore(5)`
- Agent email reads from env: `agent_email = os.getenv("LISTING_AGENT_EMAIL", "listing@realestate.com")`

### `scraper/housesigma.py`
- `AREA_URLS["mississauga"]` uses municipality `10420` (was `10343`, same as toronto)

### `scraper/kijiji.py` + `scraper/redfin.py`
- Removed ~90 lines each of dead `extract_*_listing` / `extract_*_listing_playwright` functions
- City mapping: `"Toronto" if area.lower() in ("gta", "toronto") else area.title()`

### `scraper/orchestrator.py`
- Comment clarified: realtor.ca excluded due to Cloudflare 403s; instructions left for re-enabling

### `telegram_bot.py`
- Added `import uuid`
- Added `async def h_newalert(self, update, context)` — 3-step guided alert creation (city → budget → bedrooms), saves to Supabase `buyer_alerts`
- `h_text_message` checks `context.user_data.get("alert_step")` first before photo-job handling
- Registered `CommandHandler("newalert", self.h_newalert)`
- Bot command list includes `BotCommand("newalert", "Create a new listing alert (guided)")`

### `web/auth.js` (NEW FILE)
- Handles Supabase magic-link `#access_token=...` URL callback on page load
- Persists session (email + access_token) to `localStorage` under key `416homes_session`
- Exposes `window.Auth`:
  - `Auth.getEmail()` — returns email or null
  - `Auth.headers(extra)` — returns fetch headers with `x-user-email` + `Authorization`
  - `Auth.saveSession(email, token)` — manual session store
  - `Auth.logout()` — clears storage, redirects to `/login`
  - `Auth.isLoggedIn()` — bool
  - `Auth.init()` — call on page load to process callback

### `web/dashboard.html`
- Includes `<script src="/auth.js"></script>`; all fetches use `Auth.headers()`
- Pagination state: `PAGE_SIZE=20`, `offset`, `hasMore`, `loadingMore`
- `fetchListings(off, replace)` — `replace=true` resets list on filter change, `false` appends for "Load More"
- "Load More" button visible when `!loading && !error && hasMore && listings.length > 0`
- `getMockListings()` function removed entirely
- Error banner shown on API failure
- XSS fix: listing URLs validated with `/^https?:\/\//i` before use in `href`

### `web/video.html`
- `simulateDemo()` function removed entirely
- Revision block `<div id="revisionBlock">` shown after video completes
- `submitRevision()` POSTs to `POST /api/video-jobs/{id}/revision` with notes from textarea
- Errors shown inline; revision button disabled after submission

### `web/login.html`
- `submitMagicLink()` does real `fetch('/api/auth/magic-link', { method: 'POST', body: JSON.stringify({ email }) })`
- Removed `setTimeout` simulation

### `web/index.html`
- `submitAlert()` POSTs to `/api/alerts` with `neighborhoods, min_price, max_price, min_bedrooms, property_types`
- `simulateOutreach()` calls `POST /api/run-agent` with `AGENT_SECRET` header from input field

### `web/agent.html`
- `const API = window.location.origin;` (was hardcoded `'http://localhost:8000'`)

### `.github/workflows/nightly.yml`
- Three jobs: `scrape` (sources in parallel steps) + `train-model` (parallel with scrape) → `agent` (needs: scrape) → `notify` (needs: all three)

### `.github/workflows/retrain.yml`
- Real MAPE: trains on 80% of `sold_comps`, evaluates on 20% holdout using `mean_absolute_percentage_error`
- Exits code 1 if MAPE ≥ 15% (previously always passed with `np.random.uniform(8,15)`)

---

## Known Remaining Tasks / Next Steps

### High priority
- [ ] **Run DB migration**: The schema changes in `init_db.py` (revision columns, neighbourhoods spelling) need to be applied in Supabase SQL editor. Run `python api/init_db.py` to get the SQL, then paste into Supabase.
- [ ] **Train valuation model**: Run `python valuation/model.py` once sold_comps are in Supabase to produce `valuation_model.pkl`. Without this, API falls back to `$600/sqft` estimate.
- [ ] **Set env vars on Railway**: `APP_URL` (your Vercel domain), `AGENT_SECRET`, `LISTING_AGENT_EMAIL`
- [ ] **Set env vars on Vercel**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (for magic-link auth flow)

### Medium priority
- [ ] **Telegram bot polling vs webhook**: Currently uses long-polling. For production, set a webhook URL pointing to Railway.
- [ ] **Video revision worker**: `revision_requested` status is stored but no background job picks it up yet. Need to wire `video_pipeline/pipeline.py` to re-run when status = `revision_requested`.
- [ ] **Auth on more pages**: `web/video.html` and `web/agent.html` include `auth.js` but don't gate access. Add a redirect to `/login` if `!Auth.isLoggedIn()`.
- [ ] **Rate limiting**: No per-IP rate limiting on API endpoints yet. Consider adding `slowapi` middleware.

### Low priority
- [ ] `web/agent.html` agent control routes (`/agent/start`, `/agent/stop`) need the `AGENT_SECRET` header wired up the same way `index.html` does it.
- [ ] Zoocasa scraper returns null sqft for most listings — upstream API limitation, nothing actionable until Zoocasa exposes it.

---

## Architecture Quick Reference

```
scraper/          → concurrent multi-source runner (Kijiji, HouseSigma, Redfin, Zoocasa)
memory/store.py   → Supabase pgvector embed + search (LRU cache)
valuation/model.py→ LightGBM train + inference (price_per_sqft target)
agent/main.py     → nightly match → valuate → email loop (concurrent)
video_pipeline/   → URL → Gemini script → ElevenLabs TTS → Suno music → MP4
api/main.py       → FastAPI: listings, alerts, valuation, video, Stripe, auth
telegram_bot.py   → Telegram bot with /newalert guided flow
web/              → Static HTML/JS frontend (Vercel)
```

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | scrapling + DrissionPage / Playwright fallback |
| LLM | Gemini 2.5 Flash |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Database | Supabase Postgres + pgvector |
| ML | LightGBM |
| API | FastAPI + uvicorn (Railway) |
| Auth | Supabase magic-link OTP |
| Email | Resend |
| Payments | Stripe |
| Video | ElevenLabs TTS, Suno music |
| CI/CD | GitHub Actions |
| Frontend | Static HTML + React (CDN Babel) on Vercel |
| Bot | python-telegram-bot |

## Env Vars Required

```
# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# LLMs
GEMINI_API_KEY=

# Email
RESEND_API_KEY=
FROM_EMAIL=

# Payments
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Video
ELEVENLABS_API_KEY=
SUNO_API_KEY=

# App
APP_URL=https://your-vercel-domain.vercel.app
AGENT_SECRET=                # any secret string for /api/run-agent
LISTING_AGENT_EMAIL=         # default email when agent email unknown

# Telegram
TELEGRAM_BOT_TOKEN=
```
