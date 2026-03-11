# How to Use This Project With Cursor or Windsurf

This project is configured to be built autonomously by an AI coding agent.
Everything the agent needs to know is already written in config files it reads
automatically. You should not need to type instructions manually.

---

## Setup (one time, ~5 minutes)

1. **Unzip** this project and open the folder in Cursor or Windsurf

2. **Fill in your secrets:**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and paste in your API keys (Supabase, Gemini, Resend, etc.)

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   playwright install-deps chromium
   patchright install chromium
   brew install ffmpeg   # Mac. Linux: sudo apt install ffmpeg -y
   ```

4. **Create your Supabase database:**
   ```bash
   python api/init_db.py
   ```
   Copy the printed SQL → paste into Supabase SQL Editor → click Run

---

## Starting the Agent (Cursor)

Open the Cursor chat panel (⌘L or Ctrl+L) and type:

```
/project:status
```

The agent reads `CLAUDE.md`, sees the task queue, and starts working on Task 1
automatically. It will work through all 5 tasks in order, testing each one before
moving to the next, and committing after each completion.

---

## Starting the Agent (Windsurf)

Open the Cascade panel and type:

```
Read CLAUDE.md and start the first pending task in the task queue.
```

Windsurf reads the project rules from `.windsurf/rules.md` and `CLAUDE.md`,
then begins executing the tasks.

---

## What the Agent Will Do (in order)

| Task | What happens | How long |
|---|---|---|
| 1. Fix scrapers | Navigates Kijiji/Redfin/Zoocasa live, finds real CSS selectors, fixes code, tests it | ~20 min |
| 2. Persist video jobs | Moves in-memory job dict to Supabase table, tests restart survival | ~10 min |
| 3. Build dashboard | Creates `dashboard.html` React app with listings, valuation, video history | ~25 min |
| 4. Health monitor | Creates GitHub Actions daily scraper check with email alert | ~5 min |
| 5. Full demo run | Seeds data, trains model, runs agent, starts API, opens dashboard | ~30 min |

Total estimated autonomous execution time: **~90 minutes**

---

## Monitoring Progress

The agent updates `CLAUDE.md` as it completes each task, changing `[ ]` to `[x]`
in the task table. You can watch the file to see progress.

You can also interrupt at any time and ask:
- "What did you just do?" — get a summary
- "Show me the test output for the Kijiji scraper"
- "Skip to Task 3"

---

## After All Tasks Complete

The agent will print a final deploy checklist. At that point:

1. `git push origin main`
2. Deploy API to Render (connect GitHub repo)
3. Deploy `dashboard.html`, `416homes.html`, `416homes-video.html` to Netlify
4. Add 5 secrets to GitHub Actions (names listed in CLAUDE.md)
5. Enable the nightly + retrain workflows
6. Wire Stripe webhook to your Render URL

---

## Files the Agent Uses

| File | Purpose |
|---|---|
| `CLAUDE.md` | Master instructions + task queue (read on every action) |
| `.cursor/rules/416homes.mdc` | Cursor-specific behaviour rules |
| `.windsurf/rules.md` | Windsurf-specific behaviour rules |
| `.claude/commands/status.md` | `/project:status` command |
| `.claude/commands/fix-scrapers.md` | `/project:fix-scrapers` command |
| `.claude/commands/persist-video-jobs.md` | `/project:persist-video-jobs` command |
| `.claude/commands/build-dashboard.md` | `/project:build-dashboard` command |
| `.claude/commands/add-health-monitor.md` | `/project:add-health-monitor` command |
| `.claude/commands/run-demo.md` | `/project:run-demo` command |
