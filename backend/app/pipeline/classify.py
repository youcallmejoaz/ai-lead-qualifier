"""Parse and validate Claude's triage output.

Structured outputs guarantee the JSON shape, but we still validate: ranges, the
category vocabulary, and the case where the call failed or returned nothing usable.
Anything we cannot trust becomes an "Other" item flagged for a person.
"""

import json
from typing import Any

from pydantic import ValidationError

from app.llm.schemas import LeadFields, TriageResult

_CATEGORY_ALIASES = {
    "sales": "Sales",
    "sales lead": "Sales",
    "lead": "Sales",
    "support": "Support",
    "support request": "Support",
    "spam": "Spam",
    "junk": "Spam",
    "other": "Other",
}


class TriageParseError(ValueError):
    pass


def _normalise(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("category"), str):
        data = dict(data)
        data["category"] = _CATEGORY_ALIASES.get(data["category"].strip().lower(), data["category"])
    return data


def parse_triage(raw: str) -> TriageResult:
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise TriageParseError(f"Output is not valid JSON: {exc}") from exc
    try:
        return TriageResult.model_validate(_normalise(data))
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise TriageParseError(f"Output failed validation: {problems}") from exc


def empty_fields() -> LeadFields:
    blank = {"value": None, "confidence": 0.0}
    return LeadFields.model_validate(
        {
            "name": blank,
            "company": blank,
            "need": blank,
            "budget": blank,
            "budget_usd": blank,
            "timeline": blank,
            "industry": blank,
            "company_size": blank,
            "urgency": {"value": "unknown", "confidence": 0.0},
        }
    )


def fallback_triage(reason: str) -> TriageResult:
    """Used when the model output cannot be trusted. Sends the item to a person."""
    return TriageResult(
        category="Other",
        confidence=0.0,
        reason=reason[:300] or "Could not read the model output",
        injection_suspected=False,
        fields=empty_fields(),
    )
