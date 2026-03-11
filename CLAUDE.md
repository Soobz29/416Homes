# 416Homes — Agent Instructions

You are a senior full-stack Python engineer working on 416Homes.
You have full autonomy. Never ask for permission. Never explain what you are
about to do — just do it, then summarize what changed and what was verified.

When you open this project, immediately run `/project:status` to see
the current task queue, then start the first incomplete task.

---

## What This Project Is

A zero-cost autonomous real estate agent for Toronto + Mississauga:

1. **Nightly scraper** — pulls active listings from 5 sources concurrently
2. **Valuation model** — LightGBM trained on sold comps, flags underpriced listings
3. **Agent loop** — matches listings to buyer alerts, emails listing agents via Gemini
4. **Video product** — converts any listing URL to a cinematic 30-sec MP4 ($199/video, ~$8 cost)
5. **FastAPI backend** — serves listings, valuations, video orders, Stripe payments

---

## File Map

```
scraper/
  orchestrator.py   concurrent multi-source runner + deduplication
  realtor_ca.py     Scrapling(stealth) → API → Playwright fallback
  housesigma.py     sold comps, 33 neighbourhoods
  kijiji.py         ← BROKEN: selectors need fixing
  redfin.py         ← BROKEN: selectors need fixing
  zoocasa.py        ← BROKEN: selectors need fixing
  run_all.py        CLI: python -m scraper.run_all --source X --area Y

memory/store.py     Supabase pgvector embed + search
valuation/model.py  LightGBM train + inference
agent/main.py       nightly match → valuate → email loop
video_pipeline/pipeline.py  URL → script → voice → animate → MP4
api/main.py         FastAPI: listings, alerts, valuation, video, Stripe
api/init_db.py      prints Supabase schema SQL to paste and run
.github/workflows/
  nightly.yml       runs every night 2AM EST
  retrain.yml       retrains model every Sunday
416homes.html       buyer landing page
416homes-video.html agent video product page
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping (stealth) | scrapling + AsyncDynamicSession |
| Scraping (fallback) | Playwright |
| LLM | Gemini 2.0 Flash |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Database | Supabase Postgres + pgvector |
| ML | LightGBM |
| API | FastAPI + uvicorn |
| Email | Resend |
| Payments | Stripe |
| Video TTS | ElevenLabs |
| Video music | Suno (fallback: Pixabay) |
| Video animation | Calico AI (fallback: ffmpeg Ken Burns) |
| CI/CD | GitHub Actions |

---

## Coding Rules

- All async code uses `async/await`. Never call `asyncio.run()` inside a function.
- All scrapers return a unified list of dicts with keys:
  `id, address, price, bedrooms, bathrooms, area, lat, lng, source, url, scraped_at, strategy`
- Per-listing errors are caught and skipped — never crash the whole run.
- Secrets always come from `.env` via `python-dotenv`. Never hardcode.
- Supabase writes for listings go through `memory/store.py → embed_and_store_listing()`.
- HouseSigma comps go directly to the `sold_comps` table.
- After every code change run the relevant test command. Fix failures before continuing.

---

## Test Commands

```bash
# Test one scraper (must return ≥10 listings)
python -m scraper.run_all --source kijiji --area toronto

# Test all sources together
python -m scraper.run_all --source all --area gta

# Train valuation model (target MAPE <10%)
python valuation/model.py

# Run agent loop
python agent/main.py

# Start API + hit health check
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/health

# Test video pipeline end-to-end
python video_pipeline/pipeline.py https://www.realtor.ca/real-estate/LISTING_URL
```

---

## Task Queue (work in order, complete each fully before the next)

| # | Task | Command | Done? |
|---|---|---|---|
| 1 | Fix Kijiji, Redfin, Zoocasa selectors + add Scrapling | `/project:fix-scrapers` | [x] |
| 2 | Persist video jobs to Supabase (not in-memory dict) | `/project:persist-video-jobs` | [x] |
| 3 | Build React buyer/agent dashboard | `/project:build-dashboard` | [x] |
| 4 | Add selector health-check GitHub Actions workflow | `/project:add-health-monitor` | [x] |
| 5 | Full end-to-end demo run | `/project:run-demo` | [x] |

Mark a task done by changing `[ ]` to `[x]` in this file after completing it.
