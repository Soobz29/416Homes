# Task 3: Build React Dashboard

Create `dashboard.html` — a single-file React app that connects to the 416Homes API.
Buyers see matched listings and run instant valuations.
Agents see their video order history and can download completed videos.
Style must match the existing 416homes.html (black bg, gold accent, DM Mono font).

---

## Step 1 — Create dashboard.html

Create a new file `dashboard.html` in the project root. Build it as a complete,
self-contained React SPA using CDN imports (no build step needed).

The file must have this structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>416Homes Dashboard</title>

  <!-- API base URL — change this to your Render URL before deploying -->
  <script>window.API_URL = "http://localhost:8000";</script>

  <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">

  <style>
    :root {
      --black: #0a0a08; --white: #f5f4ef; --gold: #c8a96e;
      --gold-light: #e4c98a; --grey: #6b6b60; --green: #2ed573;
      --border: rgba(200,169,110,0.2); --card: rgba(255,255,255,0.025);
    }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:var(--black); color:var(--white); font-family:'Syne',sans-serif; min-height:100vh; }
    /* ... rest of styles ... */
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    const { useState, useEffect, useCallback } = React;
    /* ... React components ... */
    ReactDOM.createRoot(document.getElementById('root')).render(<App />);
  </script>
</body>
</html>
```

---

## Step 2 — Nav + Tab Switcher

The `App` component renders a sticky nav with the 416Homes logo and three tab buttons:
**Listings** | **Valuation** | **My Videos**

Active tab has gold underline. Clicking switches the active component below.

---

## Step 3 — Listings Tab

Component: `ListingsTab`

**Filter bar** (horizontally laid out, gold borders):
- City: `<select>` with options All / Toronto / Mississauga
- Min Price: number input (placeholder "$400,000")
- Max Price: number input (placeholder "$2,000,000")
- Min Beds: `<select>` 1/2/3/4+
- "Search" button (gold background, black text)

**On mount and on every filter change**, call:
```javascript
const res = await fetch(`${window.API_URL}/listings?${new URLSearchParams(filters)}&limit=30`);
const data = await res.json();
```

**Listing grid** (3 columns desktop, 1 mobile):
Each card shows:
- Address (bold, white)
- Price (large, gold, formatted as $1,149,000)
- Beds / Baths / Neighbourhood in DM Mono grey
- Source badge (small pill: realtor.ca / kijiji / redfin / zoocasa — each a different subtle colour)
- "View Listing →" link (opens `listing.url` in new tab)
- If `listing.signal` exists: show "UNDERPRICED" in green or "OVERPRICED" in red

**Loading state**: show 6 skeleton cards (grey pulsing rectangles)
**Empty state**: "No listings match your filters."

---

## Step 4 — Valuation Tab

Component: `ValuationTab`

**Form** (two columns):
- Neighbourhood (text input)
- Property Type (select: Detached / Semi-Detached / Condo Apt / Townhouse / Other)
- City (select: Toronto / Mississauga)
- Bedrooms (number)
- Bathrooms (number)
- Square Feet (number, optional)
- List Price (number, required)
- "Get Valuation" button (full width, gold)

**On submit**, POST to `/valuate`:
```javascript
const res = await fetch(`${window.API_URL}/valuate`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(formData)
});
const result = await res.json();
```

**Result card** (shown below form):
- Large gold number: `Fair Value: $1,210,000`
- Delta: `+5.3% above list price` (green if underpriced, red if overpriced)
- Signal badge: `UNDERPRICED` / `OVERPRICED` / `FAIRLY PRICED`

**Recent comps** (shown after valuation):
Call `GET /neighbourhood/{neighbourhood}/comps` and display a table:
| Address | Sold Price | Beds | Baths | Days on Market | Sold Date |

---

## Step 5 — My Videos Tab

Component: `VideosTab`

**Email lookup**:
- Text input: "Enter your agent email"
- "Find My Videos" button
- On submit: `GET /video/history/{email}`

**Job list**:
Each job row shows:
- Listing address (or URL if no address yet)
- Status badge: `processing` (gold pulsing dot) / `complete` (green) / `failed` (red)
- If processing: show `progress_step` + `progress_message` in DM Mono grey
- If complete: show green "⬇ Download Video" button linking to `/video/download/{job_id}`
- If failed: show error message in red

**Auto-refresh**: if any job has `status === "processing"`, re-fetch every 10 seconds.

**Order button**: "Order New Video →" button at the top, links to `416homes-video.html`.

---

## Step 6 — Test locally

1. Start API: `uvicorn api.main:app --reload --port 8000`
2. Open `dashboard.html` in browser via `python3 -m http.server 3000` then visit `localhost:3000/dashboard.html`
3. Verify each tab loads without console errors
4. Verify Listings tab shows data from the API
5. Verify Valuation form submits and shows a result
6. Verify Videos tab accepts an email and shows job history

---

## Step 7 — Link from main site

In `416homes.html`, find the `<nav>` element. Add a "Dashboard" link:
```html
<a href="dashboard.html" class="nav-back">My Dashboard →</a>
```

In `416homes-video.html`, add the same link.

---

## Step 8 — Commit

```bash
git add dashboard.html 416homes.html 416homes-video.html
git commit -m "feat: React buyer + agent dashboard with listings, valuation, video history"
```

## Step 9 — Mark done in CLAUDE.md

Change `[ ]` to `[x]` for Task 3. Then run `/project:add-health-monitor`.
