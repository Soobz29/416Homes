# 416Homes — Agent Instructions

See `CLAUDE.md` for the full project overview, file map, coding rules, and current state.

## Cursor Cloud specific instructions

### Services

| Service | Command | Port |
|---------|---------|------|
| FastAPI backend | `source .venv/bin/activate && uvicorn api.main:app --reload --port 8000` | 8000 |
| Next.js frontend | `cd web-next && npm run dev` | 3000 |

### Running the backend

- Activate the venv first: `source /workspace/.venv/bin/activate`
- The backend starts without Supabase credentials — it logs a warning but all non-DB endpoints (e.g. `/health`, `/api/valuate`) still work.
- The `memory/store.py` and `valuation/model.py` imports are soft — they won't crash on missing optional libs (pandas, lightgbm, etc.).

### Running the frontend

- `cd web-next && npm run dev` — starts on port 3000.
- The frontend connects to the backend at `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000` in `.env`).

### Lint

- Frontend: `cd web-next && npx eslint .` (pre-existing warnings exist; do not introduce new ones).
- No Python linter is configured in the repo.

### Build

- Frontend: `cd web-next && npx next build` (must pass cleanly before pushing).

### Key gotchas

- Python 3.12 works fine despite `.python-version` saying 3.11.12. No 3.11-only features are used.
- `requirements.txt` just re-exports `requirements-railway.txt`. Use the latter for installs.
- `APP_URL` env var can be comma-separated for CORS origins; code splits on `,` before use.
- The deadsnakes PPA may be unreachable from Cloud Agent VMs. Python 3.12 (system default on Ubuntu 24.04) is a valid substitute.
- Node.js is provided by the nodesource repository (v20 LTS); `apt-get install -y nodejs` is sufficient.
