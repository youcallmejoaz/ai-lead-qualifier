"""Personalised first replies to qualified sales leads."""

import json

from pydantic import ValidationError

from app.drafts.support import DraftResult
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import SALES_SYSTEM
from app.llm.schemas import LeadFields, SalesDraft, output_schema
from app.pipeline.injection import wrap_untrusted

SCHEMA = output_schema(SalesDraft)


def _facts(fields: LeadFields) -> str:
    rows = []
    for name in ("name", "company", "need", "budget", "timeline", "industry", "company_size", "urgency"):
        value = getattr(fields, name).value
        rows.append(f"- {name}: {value if value not in (None, 'unknown') else 'not stated'}")
    return "\n".join(rows)


def draft_sales_reply(
    *, llm: LLMClient, model: str, subject: str, body: str, from_name: str, company: str | None,
    fields: LeadFields,
) -> DraftResult:
    email = wrap_untrusted(subject, body, from_name, company)
    user = f"Details already extracted from the email:\n{_facts(fields)}\n\n{email}"
    try:
        raw = llm.generate_json(
            purpose="sales_draft", model=model, system=SALES_SYSTEM, user=user,
            schema=SCHEMA, effort="low", max_tokens=8000,
        )
        draft = SalesDraft.model_validate(json.loads(raw))
    except (LLMError, ValidationError, json.JSONDecodeError):
        return DraftResult(subject=f"Re: {subject}", body="", failed=True)
    return DraftResult(subject=draft.subject, body=draft.reply)
