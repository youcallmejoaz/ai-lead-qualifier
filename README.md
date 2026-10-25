# AI Lead Qualifier and Inbox Triage

Your contact form and inbox bring in 50 to 100 enquiries a week. This app reads every one, sorts sales leads from support, spam and other mail, scores each lead against your ideal customer, pulls out clean fields for the CRM, and drafts a reply. **Nothing is sent or written to the CRM until a person clicks Approve.**

All sample data is fictional. Fernhollow Digital is a made up B2B services company, and every email address uses the reserved `.example` domain.

## How it works

1. **Intake.** A website contact form (`/contact`) and an inbox simulator loaded with 80 sample enquiries. A Gmail adapter stub shows where a real inbox plugs in.
2. **Triage (Claude Haiku 5.5).** One structured output call per email returns the category (Sales, Support, Spam, Other), a confidence, a one line reason, and the lead fields (name, company, need, budget, timeline, industry, size, urgency), each with its own confidence.
3. **Scoring (rules in code).** The fields are scored 0 to 100 against `data/icp.yaml` (industry, company size, budget, urgency). The profile can be edited on the Settings page, and saving it rescores every lead. Claude extracts the facts and code does the maths, so scores repeat exactly and are covered by tests.
4. **Drafts (Claude Sonnet 5.5).** Qualified leads get a personalised reply. Support emails get an answer drafted only from the 10 help articles, found with BM25 keyword search, with a citation for every fact. Each quote is checked against the source passage.
5. **Review queue.** Every draft waits with Approve, Edit and Reject buttons. Approving sends the reply (simulated outbox) and, for a lead, writes it to the CRM. Duplicates are merged by email, company name or company domain; free mail domains are never merged.
6. **Dashboard.** Inbox with colour tags, a lead list sorted by score, the CRM view, the review queue, and a weekly summary.

## Safeguards

| Risk | How it is handled |
|---|---|
| AI sends something wrong | Every send and CRM write needs an approval token that only the review service issues. Auto approve exists but is **off by default** |
| AI is unsure | Low category confidence, unsure key fields, a missing citation or no matching help article turns the item **amber**. Amber items can never be auto approved |
| Prompt injection in an email | Email text is wrapped as untrusted data, the prompts tell Claude never to follow instructions inside it, and a pattern scan plus Claude's own `injection_suspected` flag mark the item. Flagged items always wait for a person |
| Unreadable model output | Validated against a strict schema. Anything that fails becomes "Other, needs a person" instead of a guess |
| Personal data in logs | Code logs message ids only, and a logging filter redacts emails and phone numbers as a safety net |
| Keys | Read from environment variables only. `.env` is git ignored |
| Public demo cost | `DAILY_CALL_LIMIT` caps live Claude calls per day |

## Run it locally

See [docs/SETUP.md](docs/SETUP.md) for the full guide. In short:

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm ci && npm run build && cd ..
cp .env.example .env   # add ANTHROPIC_API_KEY to process new enquiries live
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000
```

Open http://localhost:8000. On first start the 80 sample enquiries are loaded and processed. Results already recorded in `data/llm_cache.json` are reused for free; anything else calls Claude.

No API key yet? Start with `LLM_MODE=scripted` to run the whole app on hand written stand in outputs (`data/demo_outputs.json`, built by `scripts/build_demo_outputs.py`). The demo clips in `clips/` were recorded this way; see `clips/MANIFEST.md`.

## Tests

```bash
cd backend && ../.venv/bin/pytest
```

They cover classification parsing (valid output, aliases, out of range confidence, missing or extra fields, malformed JSON), scoring rules and ICP edits, dedupe (email case, company suffixes, shared domains, free mail), the review gate (no write without approval, forged or mismatched approvals, auto approve threshold, amber blocking), the injection guard, PII redaction, retrieval and citations, the full pipeline on all 80 messages, and the API. `test_acceptance_real_outputs.py` re-runs the acceptance criteria against the recorded Claude outputs.

## Project layout

```
backend/app/
  intake/      contact form, inbox simulator, Gmail stub
  llm/         Claude client, response cache, prompts, output schemas
  pipeline/    triage parsing, injection guard, ICP scoring, orchestration
  drafts/      BM25 help doc retriever, support and sales drafts
  review/      approval tokens, gate rules, approve/edit/reject service
  crm/         adapter interface, mock CRM, dedupe, HubSpot style stub
  api/         serializers, weekly summary
  main.py      FastAPI app and routes
frontend/      React + Vite dashboard and contact form
data/          80 enquiries, 10 help articles, icp.yaml, recorded Claude outputs
scripts/       build_enquiries.py (sample data), run_pipeline.py (record outputs + report)
clips/         demo video clips and MANIFEST.md
```

## Limits

- The CRM is a mock and email sending is simulated. The HubSpot and Gmail adapters are stubs that show the integration points.
- Leads that become qualified only after an ICP edit are rescored, but they do not get a new draft until they are reprocessed.
- BM25 suits a small help centre. For hundreds of articles, swap in embeddings behind the same `search` interface.
- Time saved on the weekly summary is a placeholder based on a minutes per enquiry setting, not a measurement.
