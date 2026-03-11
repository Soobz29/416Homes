# 416Homes Windsurf Rules

Read `CLAUDE.md` first. It contains everything you need to know about this project.

You are a senior Python/FastAPI engineer with full autonomy to edit, create, and
run files. Start by running the first incomplete task in the CLAUDE.md task queue.

## Rules
- Test every code change before moving to the next step
- Follow the scraper strategy-chain pattern in `scraper/realtor_ca.py`
- Commit after each completed task with a descriptive message
- All secrets come from `.env` — never hardcode
- Module imports: `from memory.store import ...` not `from store import ...`
