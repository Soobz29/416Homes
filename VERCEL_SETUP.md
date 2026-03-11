# Vercel Deployment Guide

## Step 1: Create Vercel Account
1. Go to `https://vercel.com`
2. Click **Sign Up** → **Continue with GitHub**
3. Authorize Vercel to access your GitHub account

---

## Step 2: Import Project

1. In Vercel dashboard, click **Add New… → Project**
2. Under **Import Git Repository**, choose `Soobz29/416Homes`
3. When asked for project configuration:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `web-next` ⚠️ **IMPORTANT**
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

Click **Continue**.

---

## Step 3: Add Environment Variables

Before clicking **Deploy**, add these variables for the **Production** environment.

Use the **Railway public domain** for the API URL (from your `api-server` service) and your Supabase settings.

```env
NEXT_PUBLIC_API_URL=https://your-railway-domain.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://qbmxwkctscpkmxfbksmb.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
```

Notes:
- Use the **Supabase ANON key**, **not** the service role key (these values are public in the browser).
- All variables must start with `NEXT_PUBLIC_` so the Next.js frontend can read them.

---

## Step 4: Deploy

1. After environment variables are set, click **Deploy**
2. Vercel will:
   - Install dependencies with `npm install`
   - Build the Next.js app with `npm run build`
   - Host it at `https://<your-project>.vercel.app`

Once deploy is complete:
- Open the Vercel URL in your browser
- Confirm that:
  - The dashboard loads
  - API calls (listings, alerts, link code, etc.) go to your Railway backend (check Network tab for `NEXT_PUBLIC_API_URL`)

---

## Listings & Telegram with Railway backend

- **Listings**: The API serves listings from the last in-memory scan when available. On Railway (no persistent disk), it **falls back to the Supabase `listings` table**. Ensure your nightly scraper (e.g. GitHub Actions) runs and writes to Supabase so the dashboard shows data.
- **Telegram**: "Connect Telegram" needs the dashboard to call your Railway API (`/api/me`, `/api/link-code`). Set **`NEXT_PUBLIC_API_URL`** in Vercel to your Railway API URL (e.g. `https://your-app.up.railway.app`). Sign in on the dashboard with the same email you use for alerts; if the API is unreachable you’ll see a message to check `NEXT_PUBLIC_API_URL`.
- **Railway**: On the API service, set `SUPABASE_URL` and `SUPABASE_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`) so the API can read/write users and listings.

---

## Updating the deployment

Any push to `main` on `Soobz29/416Homes` will trigger a new Vercel deployment for the `web-next` app automatically.

