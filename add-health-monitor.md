# Task 4: Add Selector Health Monitor

Create a GitHub Actions workflow that checks every scraper daily.
If any scraper returns 0 listings, the workflow fails and sends an alert email.
This catches broken selectors before the nightly run silently produces no data.

---

## Step 1 — Create `.github/workflows/health-check.yml`

Create this file:

```yaml
name: Scraper Health Check

on:
  schedule:
    - cron: '0 11 * * *'   # 6AM EST = 11AM UTC, runs before nightly scrape
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          playwright install-deps chromium

      - name: Check Realtor.ca
        id: check_realtor
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python -c "
          import asyncio, sys
          from scraper.realtor_ca import scrape_realtor_ca
          result = asyncio.run(scrape_realtor_ca('toronto', strategy='auto'))
          count = len(result)
          print(f'realtor_ca: {count} listings')
          if count < 5:
              print('FAIL: realtor_ca returned fewer than 5 listings')
              sys.exit(1)
          "

      - name: Check Kijiji
        id: check_kijiji
        run: |
          python -c "
          import asyncio, sys
          from scraper.kijiji import scrape_kijiji
          result = asyncio.run(scrape_kijiji('toronto'))
          count = len(result)
          print(f'kijiji: {count} listings')
          if count < 5:
              print('FAIL: kijiji returned fewer than 5 listings')
              sys.exit(1)
          "

      - name: Check Redfin
        id: check_redfin
        run: |
          python -c "
          import asyncio, sys
          from scraper.redfin import scrape_redfin
          result = asyncio.run(scrape_redfin('toronto'))
          count = len(result)
          print(f'redfin: {count} listings')
          if count < 5:
              print('FAIL: redfin returned fewer than 5 listings')
              sys.exit(1)
          "

      - name: Check Zoocasa
        id: check_zoocasa
        run: |
          python -c "
          import asyncio, sys
          from scraper.zoocasa import scrape_zoocasa
          result = asyncio.run(scrape_zoocasa('toronto'))
          count = len(result)
          print(f'zoocasa: {count} listings')
          if count < 5:
              print('FAIL: zoocasa returned fewer than 5 listings')
              sys.exit(1)
          "

      - name: Send failure alert
        if: failure()
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          AGENT_EMAIL: ${{ secrets.AGENT_EMAIL }}
        run: |
          python -c "
          import os, httpx
          failed_steps = []
          # GitHub sets STEPS context — we check env for step outcomes
          for step in ['check_realtor', 'check_kijiji', 'check_redfin', 'check_zoocasa']:
              outcome = os.environ.get(f'steps_{step}_outcome', 'unknown')
              if outcome == 'failure':
                  failed_steps.append(step.replace('check_', ''))

          body = f'416Homes scraper alert: The following scrapers returned 0 listings: {failed_steps}. Check .github/workflows/health-check.yml for details. Selectors may need updating.'

          import httpx
          httpx.post('https://api.resend.com/emails',
              headers={'Authorization': f'Bearer {os.environ[\"RESEND_API_KEY\"]}'},
              json={'from': os.environ['AGENT_EMAIL'],
                    'to': os.environ['AGENT_EMAIL'],
                    'subject': '416Homes: Scraper health check FAILED',
                    'text': body})
          print(f'Alert sent for: {failed_steps}')
          "
```

## Step 2 — Commit

```bash
git add .github/workflows/health-check.yml
git commit -m "feat: daily scraper health check with email alert on failure"
```

## Step 3 — Trigger it manually to test

After pushing to GitHub:
1. Go to repo → Actions → "Scraper Health Check"
2. Click "Run workflow"
3. Watch it run — all steps should pass if Task 1 (fix-scrapers) is done

## Step 4 — Mark done in CLAUDE.md

Change `[ ]` to `[x]` for Task 4. Then run `/project:run-demo`.
