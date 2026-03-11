# Railway Deployment Guide

This guide deploys the 416Homes backend to Railway with two services:

- **`api-server`**: FastAPI app (public HTTP)
- **`telegram-worker`**: Background worker running `run_agent.py` (no HTTP)

Repo: `Soobz29/416Homes` (branch: `main`)

---

## Step 1: Create Railway Account

1. Go to `railway.app`
2. Click **Login with GitHub**
3. Authorize Railway to access GitHub

---

## Step 2: Create New Project

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Choose: `Soobz29/416Homes`
4. Select branch: `main`

---

## Step 3: Create API Server Service (`api-server`)

1. Railway will auto-detect the repo.
2. Rename the service to: **`api-server`**
3. Go to **Settings → Deploy**
4. Set **Start Command**:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

5. Set **Healthcheck path** to:

```text
/api/health
```

---

## Step 4: Add Environment Variables (api-server)

Go to **api-server → Variables → Raw Editor**, paste:

```env
# Python
PYTHONUNBUFFERED=1
PORT=8000

# Supabase (Supabase dashboard → Settings → API)
SUPABASE_URL=https://qbmxwkctscpkmxfbksmb.supabase.co
SUPABASE_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# Gemini
GEMINI_API_KEY=<your-gemini-key>

# Telegram
TELEGRAM_BOT_TOKEN=<your-admin-bot-token>
TELEGRAM_BOT_TOKEN_PUBLIC=<your-public-bot-token>
TELEGRAM_CHAT_ID=<your-admin-chat-id>

# Video APIs
ELEVENLABS_API_KEY=<your-elevenlabs-key>
RESEND_API_KEY=<your-resend-key>

# Stripe (use test keys initially, switch to live later)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Configuration
VEO_DAILY_BUDGET_CAD=10.00
MAX_TELEGRAM_PHOTOS=15
APP_URL=https://416homes.vercel.app
API_BASE_URL=${RAILWAY_PUBLIC_DOMAIN}
```

Notes:
- Railway typically sets `PORT` automatically; we set it here to match the project conventions.
- `SUPABASE_SERVICE_ROLE_KEY` is required if RLS is enabled.

---

## Step 5: Generate Domain for API

1. **api-server → Settings → Networking**
2. Click **Generate Domain**
3. Copy the URL (example: `api-server-production-xxxx.up.railway.app`)
4. Test health:

```bash
curl https://<your-domain>.up.railway.app/api/health
```

Later you can add a custom domain like `api.yourdomain.com`.

---

## Step 6: Create Worker Service (`telegram-worker`)

1. In the same Railway project click **New Service**
2. Select **GitHub Repo** → `Soobz29/416Homes`
3. Rename to: **`telegram-worker`**
4. Go to **Settings → Deploy**
5. Set **Start Command**:

```bash
python run_agent.py
```

6. Copy **ALL** environment variables from `api-server` to `telegram-worker`

No healthcheck is needed (it’s a long-running process).

---

## Step 7: Deploy & Monitor

1. Both services should auto-deploy from `main`
2. Check logs:
   - `api-server`: should show Uvicorn running
   - `telegram-worker`: should show Telegram bots started/polling
3. Verify:
   - `GET /api/health` returns 200 JSON
   - Worker keeps running (no crash loop)

---

## Troubleshooting

- **Build fails**: verify `requirements.txt` includes all packages (and pins are compatible with your Python version).
- **Port errors**: ensure the start command uses `$PORT`. If you hardcode, Railway routing may fail.
- **Import errors**: set Python 3.11/3.12 in Railway settings and redeploy.
- **Worker crashes**: check env vars match `api-server` exactly (esp. Supabase + Telegram tokens).
- **403 scraping**: some sources rate-limit (expected). This doesn’t block API health.

---

## Checklist

- [ ] Railway account created
- [ ] Project created from GitHub
- [ ] `api-server` service deployed
- [ ] `telegram-worker` service deployed
- [ ] All environment variables added
- [ ] Health endpoint returns 200
- [ ] Worker logs show “Telegram bot started”
- [ ] Public domain generated

