"""Shapes of the structured outputs we ask Claude for, plus JSON schema helpers.

The Pydantic models carry the validation rules (ranges, allowed values). The JSON
schema sent to the API is derived from them with constraints stripped, because
structured outputs only enforce the shape; our own validation enforces the rest.
"""

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["Sales", "Support", "Spam", "Other"]
Urgency = Literal["high", "medium", "low", "unknown"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TextField(_Strict):
    value: str | None
    confidence: float = Field(ge=0.0, le=1.0)


class IntField(_Strict):
    value: int | None
    confidence: float = Field(ge=0.0, le=1.0)


class UrgencyField(_Strict):
    value: Urgency
    confidence: float = Field(ge=0.0, le=1.0)


class LeadFields(_Strict):
    name: TextField
    company: TextField
    need: TextField
    budget: TextField  # as written, e.g. "around $25k"
    budget_usd: IntField  # best estimate in USD, null if not stated
    timeline: TextField
    industry: TextField
    company_size: IntField  # employees, null if not stated
    urgency: UrgencyField


class TriageResult(_Strict):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=300)
    injection_suspected: bool
    fields: LeadFields


class Citation(_Strict):
    doc_id: str
    quote: str


class SupportDraft(_Strict):
    answerable: bool
    subject: str
    reply: str = Field(min_length=1)
    citations: list[Citation]


class SalesDraft(_Strict):
    subject: str
    reply: str = Field(min_length=1)


_UNSUPPORTED_KEYS = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "title",
    "default",
}


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            return _inline_refs(copy.deepcopy(defs[name]), defs)
        return {k: _inline_refs(v, defs) for k, v in node.items() if k not in _UNSUPPORTED_KEYS}
    if isinstance(node, list):
        return [_inline_refs(v, defs) for v in node]
    return node


def _close_objects(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())
        for v in node.values():
            _close_objects(v)
    elif isinstance(node, list):
        for v in node:
            _close_objects(v)


def output_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON schema for output_config.format: refs inlined, every object closed."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})
    schema = _inline_refs(raw, defs)
    _close_objects(schema)
    return schema
