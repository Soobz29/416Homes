# Task 5: Run Full End-to-End Demo

Execute every step below in sequence to confirm the entire stack works.
This is the demo run — everything must produce real output with no errors.
Report exact counts and file paths at the end.

---

## Step 1 — Verify environment

```bash
python3 --version          # must be 3.10+
ffmpeg -version            # must exist
python -c "import scrapling; print('scrapling ok')"
python -c "import playwright; print('playwright ok')"
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('GEMINI_API_KEY:', bool(os.environ.get('GEMINI_API_KEY')))"
```

All must pass. If any fail, fix before continuing.

## Step 2 — Seed sold comps

```bash
python -m scraper.run_all --source housesigma
```

Expected output: 33 neighbourhoods processed, 800+ comps in `sold_comps` table.
Verify in Supabase: Table Editor → sold_comps → should have rows.

## Step 3 — Scrape active listings from all sources

```bash
python -m scraper.run_all --source all --area gta
```

Expected: each source reports a count, total unique listings > 100.
Verify in Supabase: Table Editor → listings → should have rows.

## Step 4 — Train valuation model

```bash
python valuation/model.py
```

Expected: `Validation MAPE: X.XX%` — must be under 15%.
If above 15%: run housesigma with `days_back=180` and retrain.

## Step 5 — Run agent loop

```bash
python agent/main.py
```

Expected: prints matches count. Even 0 matches is fine at this point (no alerts yet).
Must complete without exceptions.

## Step 6 — Start API and run health checks

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
sleep 3

curl -s http://localhost:8000/health | python3 -m json.tool
curl -s "http://localhost:8000/listings?city=Toronto&limit=3" | python3 -m json.tool
curl -s "http://localhost:8000/listings?city=Mississauga&limit=3" | python3 -m json.tool
curl -s -X POST http://localhost:8000/valuate \
  -H "Content-Type: application/json" \
  -d '{"neighbourhood":"King West","property_type":"Condo Apt","city":"Toronto","bedrooms":1,"bathrooms":1,"sqft":550,"list_price":699000}' \
  | python3 -m json.tool
```

All four must return valid JSON with data. Kill background API: `pkill -f uvicorn`

## Step 7 — Test video pipeline (script + audio only, no Calico needed)

```bash
python -c "
import asyncio
from video_pipeline.pipeline import generate_script
script = generate_script({
    'address': '218 Broadview Ave, Toronto, ON',
    'price': '\$1,149,000',
    'beds': '3', 'baths': '2',
    'sqft': '1,850', 'property_type': 'Semi-Detached',
    'description': 'Stunning renovated Victorian in Leslieville.'
})
print('Headline:', script['headline'])
print('Script length:', len(script['voiceover_script']), 'chars')
print('Music mood:', script['music_mood'])
"
```

Must print a headline and ~400-char script without errors.

## Step 8 — Open dashboard in browser

```bash
python3 -m http.server 3000 &
sleep 1
echo "Open in browser: http://localhost:3000/dashboard.html"
```

Verify: Listings tab shows cards, Valuation tab shows the form, Videos tab shows email input.
Kill server: `pkill -f "http.server"`

## Step 9 — Final summary

Print a summary of what was verified:

```
DEMO COMPLETE
=============
✅ Scrapers: realtor_ca, kijiji, redfin, zoocasa, housesigma
✅ Database: sold_comps (N rows), listings (N rows)
✅ Valuation model: MAPE X.X%
✅ Agent loop: ran without errors
✅ API: health check + listings + valuation all returned data
✅ Video pipeline: script generation working
✅ Dashboard: loaded in browser without errors

Ready to deploy:
1. git push origin main
2. Deploy API to Render
3. Deploy dashboard.html + 416homes.html + 416homes-video.html to Netlify
4. Add GitHub Secrets (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, RESEND_API_KEY, AGENT_EMAIL)
5. Enable nightly.yml + retrain.yml workflows in GitHub Actions
6. Wire Stripe webhook to Render URL
```

## Step 10 — Mark done in CLAUDE.md

Change `[ ]` to `[x]` for Task 5.

The project is now demo-ready. All tasks complete.
