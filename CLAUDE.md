# 416Homes — Agent Instructions

You are a senior full-stack Python engineer working on 416Homes.
You have full autonomy. Never ask for permission. Never explain what you are
about to do — just do it, then summarize what changed and what was verified.

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
  kijiji.py / redfin.py / zoocasa.py
  run_all.py        CLI: python -m scraper.run_all --source X --area Y

memory/store.py     Supabase pgvector embed + search
valuation/model.py  LightGBM train + inference
agent/main.py       nightly match → valuate → email loop
video_pipeline/pipeline.py  URL → script → voice → animate → MP4
api/main.py         FastAPI: listings, alerts, valuation, video, Stripe
api/init_db.py      prints Supabase schema SQL to paste and run
.github/workflows/nightly.yml / retrain.yml
416homes.html / 416homes-video.html
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | scrapling + AsyncDynamicSession / Playwright fallback |
| LLM | Gemini 2.0 Flash |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Database | Supabase Postgres + pgvector |
| ML | LightGBM |
| API | FastAPI + uvicorn |
| Email/Payments | Resend / Stripe |
| Video | ElevenLabs TTS, Suno music, Calico AI animation |
| CI/CD | GitHub Actions |

---

## Coding Rules

- All async code uses `async/await`. Never call `asyncio.run()` inside a function.
- All scrapers return: `id, address, price, bedrooms, bathrooms, area, lat, lng, source, url, scraped_at, strategy`
- Per-listing errors are caught and skipped — never crash the whole run.
- Secrets always come from `.env` via `python-dotenv`. Never hardcode.
- Supabase writes for listings go through `memory/store.py → embed_and_store_listing()`.
- HouseSigma comps go directly to the `sold_comps` table.
- After every code change run the relevant test command. Fix failures before continuing.

---

## Current State (as of 2026-04-01)
- sqft: fixed in realtor_ca (parses Building.SizeInterior) + housesigma (parses card text). Zoocasa API returns null sqft for most listings — nothing to fix there.
- Valuation tab: fully wired to /api/valuate with pre-fill from VALUATE button
- Valuation model: API uses real LightGBM with $600/sqft fallback. Model not yet trained — needs `python valuation/model.py` run once with sold_comps in Supabase.
- retrain.yml: fixed to commit valuation_model.pkl back to main after training so Railway gets it. Trigger manually from GitHub Actions → "416Homes Model Retraining" → Run workflow.
- All code on main, deployed to Vercel + Railway.

## Test Commands

```bash
python -m scraper.run_all --source kijiji --area toronto  # ≥10 listings
python -m scraper.run_all --source all --area gta
python valuation/model.py                                 # target MAPE <10%
python agent/main.py
uvicorn api.main:app --reload --port 8000 && curl http://localhost:8000/health
python video_pipeline/pipeline.py https://www.realtor.ca/real-estate/LISTING_URL
```
