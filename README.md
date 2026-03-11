# 416Homes

Persistent autonomous real estate agent with Telegram control and cinematic video generation.

## Observability

The agent maintains a centralized activity log in `listing_agent/activity.log`.

### Live tailing (PowerShell)

```powershell
Get-Content -Path "listing_agent/activity.log" -Wait -Tail 10
```

## Telegram commands (admin bot)

- `/status` — Get agent health and recent metrics.
- `/buyers` — List active buyer profiles.
- `/alerts` — See the last 5 high-scoring matches.
- `/log` — Display the last 20 entries from the activity log.
- `/video <url>` — Manually trigger a cinematic video for a listing.
- `/heartbeat` — Check bot connectivity.
- `add skill: <instruction>` — Add a new matching filter (e.g., "alert me when listings have a pool").
