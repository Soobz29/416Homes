# Task 2: Persist Video Jobs to Supabase

The `video_jobs: dict = {}` in `api/main.py` is in-memory. Every Render restart
wipes all job state. Fix this by routing reads and writes through the `video_jobs`
Supabase table (already exists in schema). Execute every step. Commit at the end.

---

## Step 1 — Add four DB helper functions to `api/main.py`

Find the line `supabase = create_client(...)`. Immediately after it, insert:

```python
# ── Video job DB helpers ─────────────────────────────────────────────────────
def _job_create(job_id: str, data: dict):
    supabase.table("video_jobs").insert({"id": job_id, **data}).execute()

def _job_update(job_id: str, data: dict):
    supabase.table("video_jobs").update(data).eq("id", job_id).execute()

def _job_get(job_id: str) -> dict | None:
    r = supabase.table("video_jobs").select("*").eq("id", job_id).execute()
    return r.data[0] if r.data else None

def _jobs_by_email(email: str) -> list:
    r = supabase.table("video_jobs").select("*") \
        .eq("agent_email", email) \
        .order("created_at", desc=True).limit(20).execute()
    return r.data or []
```

## Step 2 — Delete the in-memory dict

Find and delete this line:
```python
video_jobs: dict = {}
```

## Step 3 — Replace all dict operations with DB calls

Do a global find-and-replace across `api/main.py`:

| Find | Replace with |
|---|---|
| `video_jobs[job_id] = {` | `_job_create(job_id, {` (close the dict and call) |
| `video_jobs[job_id].update({...})` | `_job_update(job_id, {...})` |
| `video_jobs[job_id]["key"] = val` | `_job_update(job_id, {"key": val})` |
| `job = video_jobs[job_id]` | `job = _job_get(job_id)` |
| `if job_id not in video_jobs:` | `if _job_get(job_id) is None:` |

In the `/video/history/{agent_email}` endpoint, replace the list comprehension
with: `return _jobs_by_email(agent_email)`

## Step 4 — Update the on_progress callback in `_run_video_pipeline`

Find:
```python
async def on_progress(step: str, msg: str):
    video_jobs[job_id]["progress_step"] = step
    video_jobs[job_id]["progress_message"] = msg
```

Replace with:
```python
async def on_progress(step: str, msg: str):
    _job_update(job_id, {"progress_step": step, "progress_message": msg})
```

## Step 5 — Test

Start the API:
```bash
uvicorn api.main:app --reload --port 8000
```

Submit a test job:
```bash
curl -s -X POST http://localhost:8000/video/create-checkout \
  -H "Content-Type: application/json" \
  -d '{"listing_url":"https://www.realtor.ca/test","agent_email":"test@test.com"}' \
  | python3 -m json.tool
```

Copy the `job_id` from the response. Check it exists in Supabase:
```bash
curl -s http://localhost:8000/video/status/JOB_ID_HERE | python3 -m json.tool
```

Stop the API with Ctrl+C. Restart it. Poll the same job_id again — it must still exist.

## Step 6 — Commit

```bash
git add api/main.py
git commit -m "fix: persist video_jobs to Supabase instead of in-memory dict"
```

## Step 7 — Mark done in CLAUDE.md

Change `[ ]` to `[x]` for Task 2 in the CLAUDE.md task table.
Then run `/project:build-dashboard`.
