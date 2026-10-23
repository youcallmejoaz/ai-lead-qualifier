# Setup guide

## Requirements

- Python 3.12 or newer
- Node 20 or newer
- An Anthropic API key, only for processing enquiries that are not already in `data/llm_cache.json`

## 1. Install

```bash
git clone https://github.com/youcallmejoaz/ai-lead-qualifier.git
cd ai-lead-qualifier
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm ci && npm run build && cd ..
cp .env.example .env
```

Edit `.env` and set `ANTHROPIC_API_KEY`. Never commit `.env`.

## 2. Run

```bash
cd backend
set -a && . ../.env && set +a
../.venv/bin/uvicorn app.main:app --port 8000
```

- Dashboard: http://localhost:8000
- Contact form: http://localhost:8000/contact

For front end development with hot reload, run `npm run dev` in `frontend/` (it proxies `/api` to port 8000).

## 3. Record Claude outputs for the sample data

```bash
.venv/bin/python scripts/run_pipeline.py
```

This sends all 80 sample enquiries through Claude, saves the responses to `data/llm_cache.json`, and writes `data/run_report.md` with classification accuracy against the hand labels, flags and token cost. Re-running is free for anything already recorded.

## 4. Settings

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Needed for live calls |
| `CLASSIFY_MODEL` | `claude-haiku-5-5` | Triage and field extraction |
| `DRAFT_MODEL` | `claude-sonnet-5-5` | Sales and support drafts |
| `LLM_MODE` | `live` | `cache` never calls Claude and only uses recorded outputs |
| `DATABASE_URL` | SQLite in `data/app.db` | Any SQLAlchemy URL, for example Postgres |
| `DAILY_CALL_LIMIT` | `0` (no cap) | Live Claude calls allowed per day |
| `DEMO_MODE` | `1` | Enables `POST /api/admin/reset`, used by the clip recorder |

Auto approve, the amber threshold and the ideal customer profile are changed on the Settings page.

## 5. Deploy on Render

1. Push the repo to GitHub.
2. In Render choose New, then Blueprint, and pick the repo. `render.yaml` defines one Docker web service.
3. Set `ANTHROPIC_API_KEY` when prompted.

The free plan has no persistent disk, so the demo database is rebuilt from the sample data on each deploy. Set `DATABASE_URL` to a Postgres instance to keep data between deploys. The Docker image has not been built in the development environment, so check the first Render build log.

## 6. Plugging in real systems

- **CRM:** implement `CRMAdapter.upsert_lead` (see `backend/app/crm/hubspot_adapter.py`). Keep the `verify(approval)` call first.
- **Inbox:** implement `GmailInbox.fetch_new` to create `Message` rows with `source="gmail"`.
- **Sending:** replace the body of `review.service.send_email`, keeping the approval check.
