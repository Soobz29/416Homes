# 416Homes — Development Guide

See `CLAUDE.md` for full project context, file map, API reference, and coding rules.

## Cursor Cloud specific instructions

### Services

| Service | Command | Port |
|---------|---------|------|
| FastAPI backend | `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` | 8000 |
| Next.js frontend | `cd web-next && npm run dev` | 3000 |

### Environment files

- Backend: copy `.env.example` to `.env` at repo root. Real Supabase/Stripe/Gemini credentials are needed for full functionality; the API starts gracefully without them (Supabase client becomes `None`, listings return empty).
- Frontend: copy `web-next/.env.example` to `web-next/.env`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` to point at the local backend.

### Gotchas

- The health endpoint is at `/api/health`, not `/health`.
- `requirements-railway.txt` is the slim API dependency set (used for local dev and deployment). `requirements-full.txt` adds ML + heavy scraping libs (LightGBM, Playwright, scrapling) — only needed if working on scrapers or valuation model.
- The `valuation/model.py` and `memory/store.py` imports gracefully degrade when ML/Supabase dependencies are missing, so the API starts with just `requirements-railway.txt`.
- Frontend uses npm (lockfile is `package-lock.json`).
- `APP_URL` env var can be comma-separated for CORS origins; code uses `.split(",")[0].strip()` when constructing URLs.
- ESLint has ~21 pre-existing `@typescript-eslint/no-explicit-any` errors — these are in the existing codebase, not regressions.

### Lint / Test / Build

- **Frontend lint**: `cd web-next && npm run lint`
- **Frontend build**: `cd web-next && npm run build`
- **Backend health check**: `curl http://localhost:8000/api/health`
- **Listings API**: `curl http://localhost:8000/api/listings?limit=5`
- See `CLAUDE.md` → "Test Commands" section for scraper and pipeline test commands.
