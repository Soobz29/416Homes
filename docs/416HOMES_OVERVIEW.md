# 416Homes

**A watcher for the Greater Toronto Area housing market: it checks listing sources automatically, prices each new home against sold comparables, and tells the right people about the ones that fit.**

| | |
|---|---|
| Live site | https://416-homes.vercel.app |
| Source | https://github.com/Soobz29/416Homes |
| Built | March 10 – November 25, 2026 (567 commits on `main`) |
| Stack | Python, FastAPI, LightGBM, Supabase (Postgres + pgvector), Gemini, Next.js, Stripe, Resend |

---

## The problem I chose

A small business owner's time is the bottleneck. In real estate, an independent agent or a buyer has to watch many listing sites by hand, and by the time they spot a good one it's often gone. The work is repetitive and easy to miss, and it takes hours that the owner would rather spend with clients.

## Why I chose it

It started as a side project. My sister was looking to buy a home, and I wanted to help her. Watching the listing sites by hand was slow, and it was easy to miss a good one. It was also the kind of work software is good at: repetitive, rule-based, and needing constant attention. So I built something to do the watching for her, and it grew into 416Homes.

## My approach to solving it

I treated it as a watching problem, not a search problem. 416Homes is built to check five listing sources on a schedule (Realtor.ca, Zoocasa, Kijiji, Condos.ca and Redfin) and remove duplicates. It prices each new home against sold comparables, so it can flag ones that look underpriced and label each match with an estimated market value. Then it alerts matching buyers and drafts outreach to listing agents, so people only hear about homes that fit them.

I automated the part that wastes the most time, which is checking sites and comparing prices, and left the human part (talking to clients, deciding to buy) to people. I also kept the system running on its own, with scheduled scraping jobs and automatic retraining of the pricing model, so it doesn't need daily attention. The supporting detail that follows is candid about where it still needs monitoring.

## What I'd do next

Relay's mission is helping owners spend less time on admin. The same idea would apply to a business's money and paperwork: watch it automatically, and surface only what needs a person.

## Links to my work

- **Live product:** https://416-homes.vercel.app
- **Source code:** https://github.com/Soobz29/416Homes

---

# Supporting detail

## How it works

```
 5 listing sources ──► orchestrator ──► Supabase ◄── sold comps (HouseSigma)
 Realtor.ca Zoocasa    (concurrent,     listings,        │
 Condos.ca Kijiji      de-duplicated)   pgvector         ▼
 Redfin                                    │       LightGBM valuation
                                           │       (retrained by CI)
                                           ▼             │
 buyer alerts ──► agent loop: match score ≥ 0.6 ◄────────┘
 (email / Telegram)      │
                         ├─► Gemini drafts email ──► Resend
                         └─► Telegram alert with valuation
                                           │
                                           ▼
                    FastAPI  ──►  Next.js site (Vercel)
                       ├─ video orders (Stripe) ─► script ─► voice ─► MP4
                       └─ tour orders  (Stripe) ─► photos ─► room manifest ─► hosted tour
```

### Key decisions

| Decision | Why |
|---|---|
| **Several sources, run concurrently, de-duplicated** on a hash of address and price | No single source is complete. One failing scraper must not crash a run, so errors are caught per listing and per source. |
| **Layered fetch strategy** (e.g. Realtor.ca: direct API, then stealth-browser and headless-browser fallbacks) | Listing sites change and block often. Fallbacks keep data flowing when one method breaks. |
| **Value against sold comps, not asking prices** | Sold prices are the signal buyers lack. The model predicts price per square foot from bedrooms, bathrooms, size, property type, neighbourhood and city, trained on the `sold_comps` table. |
| **Retrain automatically** | CI retrains the model (a weekly workflow, Sundays 08:00 UTC, plus a training step in the nightly workflow) and commits the updated artifact. |
| **Transit score for every listing** | Proximity to the subway and LRT lines, scored 0–10 from 80+ keywords. Listings the keywords cannot place fall back to a city default (Toronto 4, Mississauga/905 3, other GTA 2), so no listing shows an empty score. |
| **Never fail a paid job for lack of photos** | The tour pipeline falls back from the live page, to already-scraped photos in the database, to a curated stock set. The order always completes, and the viewer labels sample photos. |
| **Payments via Stripe webhooks** | Orders are created from the webhook, not the browser redirect, so a closed tab cannot lose a paid order. |

### Products

| Product | What it does | Price (CAD, from the live site) |
|---|---|---|
| **Buyer alerts** | Cities, budget and beds in; matches by email and Telegram with a price check | Free |
| **Listing video** | Any listing URL becomes a narrated video (cinematic tier is 30 s, 4K) | $99 / $249 / $299 |
| **Virtual tour** | Listing photos become a hosted room-by-room tour; 3D walkthroughs also supported | $49 photo, $149 3D |

## Where it stands (checked November 25, 2026)

**Working**

- The public site is live on Vercel: homepage, video order page with the three pricing tiers, tour order page, and the hosted tour viewer with a demo tour.
- The pipeline code exists end to end: scrapers, orchestrator, valuation training, agent loop, Telegram bots, video and tour pipelines, Stripe checkout.
- Scheduled jobs run: the nightly workflow (2 AM EST) succeeded on each of its last six runs, the every-3-hours refresh workflow is succeeding, and CI keeps retraining and committing the valuation model (203 of the 567 commits are automated retrain commits).

**Scraping coverage in the latest CI runs, from the GitHub Actions logs**

| Source | Latest refresh run | Latest nightly run |
|---|---|---|
| Zoocasa | 189 | 135 |
| Realtor.ca | 0 | 0 |
| Redfin | 0 | 0 |
| Kijiji | 0 | 0 |
| Condos.ca | 0 | 0 |
| HouseSigma (sold comps) | 0 | 0 |
| Zillow | 0 | 0 |
| **After de-duplication** | **27** | **27** |

The nightly job kept exactly 27 listings on each of its last six runs (November 20–25). So today, scheduled runs produce data from one of the five sources, not all five. The site's "2,500+ active GTA listings" is an estimate in its copy, not a count I could measure, and the live database cannot be checked while the API is down. A dashboard capture on May 4 did show 1,886 listings in the database, so it has held far more than 27 at times.

**Not working right now**

- **The production API is offline.** The DigitalOcean backend returns HTTP 503 on `/health` and `/api/listings`, so the dashboard shows "Failed to fetch listings". It was down on October 9 and is still down.

## Known gaps and risks

1. **Most scrapers return nothing in CI, and nothing flags it.** Redfin and Kijiji fail because Patchright's Chromium is not installed on the runner (the error itself says to run `patchright install`; the workflows only run `playwright install`). I have not diagnosed Realtor.ca, Condos.ca or HouseSigma individually; anti-bot blocking of datacenter IPs is a likely factor. The jobs still report success because zero results are not counted as failures and the minimum-listings guard is only 20. A source that silently returns nothing is exactly the kind of failure that needs an alert.
2. **Backend availability.** One hosted API serves the dashboard and the Telegram bots. It needs restoring and a basic uptime alert.
3. **Sold comps are not refreshing in CI.** HouseSigma returned 0, so retraining reuses whatever comps are already in the database.
4. **Outreach is only partly production-ready.** Real listing-agent emails depend on the scrapers capturing `agent_email`; otherwise mail falls back to a configured address. Messages go out from Resend's test sender, and there is no human approval step, opt-out handling, or review against Canada's anti-spam law (CASL).
5. **Freshness claims need aligning.** The site says listings are "scanned every 30 min". The scheduled scrapes run nightly and every 3 hours; the 30-minute interval belongs to the agent's match loop.
6. **Valuation accuracy is not published.** The training code targets a validation MAPE under 10%, but I have not measured or reported the current figure. It should be evaluated on held-out sales and shown with an error range.
7. **Scraping exposure.** Collecting data from third-party portals carries terms-of-service and licensing risk, including for sold-comp data.
8. **Thin automated tests.** A few script-style checks exist for the agent and video jobs, but there is no regression suite for the scrapers, valuation or API.

## Next steps

1. Restore the API and add an uptime check.
2. Install Patchright's browser in both scraping workflows, then re-check each source. Fail the job and alert when a source returns zero or the total drops sharply.
3. Make outreach safe: verified sender domain, real listing-agent addresses, an approval step, and an opt-out path.
4. Publish held-out valuation accuracy and show an error range beside each valuation.
5. Align the freshness claim with the real schedule.
6. Add tests around the scrapers and valuation, then gate CI on them.

## Supporting material

- Live product: https://416-homes.vercel.app
- Repository: https://github.com/Soobz29/416Homes
- Launch video (37 s, built from the live UI): `416homes_launch.mp4`
- Architecture notes in the repo: `CLAUDE.md`, `DEPLOY.md`, `VERCEL_SETUP.md`
