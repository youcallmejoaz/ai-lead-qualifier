"""Review gate rules: which flags an item gets and whether it may skip a person."""

from typing import Any

from app.llm.schemas import LeadFields

# Flags that turn an item amber and block auto approval.
AMBER_FLAGS = {
    "low_confidence",
    "unsure_fields",
    "injection",
    "parse_failed",
    "no_citation",
    "no_relevant_doc",
}
# Informational flags: shown on the card, do not block anything.
INFO_FLAGS = {"sales_opportunity", "merged_duplicate"}

KEY_FIELDS = ("name", "company", "need")


def unsure_fields(fields: LeadFields, threshold: float) -> list[str]:
    return [name for name in KEY_FIELDS if getattr(fields, name).confidence < threshold]


def item_confidence(classification_confidence: float, fields: LeadFields | None, kind: str) -> float:
    """Overall confidence for the item: the weakest of the parts that matter."""
    if kind != "sales" or fields is None:
        return classification_confidence
    return min(classification_confidence, *(getattr(fields, n).confidence for n in KEY_FIELDS))


def compute_flags(
    *,
    classification_confidence: float,
    injection: bool,
    parse_failed: bool,
    fields: LeadFields | None,
    kind: str,
    settings: dict[str, Any],
    citations: list | None = None,
    answerable: bool = True,
    sales_opportunity: bool = False,
) -> list[str]:
    flags: list[str] = []
    if parse_failed:
        flags.append("parse_failed")
    if classification_confidence < settings["amber_threshold"]:
        flags.append("low_confidence")
    if injection:
        flags.append("injection")
    if kind == "sales" and fields is not None and unsure_fields(fields, settings["field_confidence_threshold"]):
        flags.append("unsure_fields")
    if kind == "support":
        if not answerable:
            flags.append("no_relevant_doc")
        elif not citations:
            flags.append("no_citation")
    if sales_opportunity:
        flags.append("sales_opportunity")
    return flags


def is_amber(flags: list[str]) -> bool:
    return any(f in AMBER_FLAGS for f in flags)


def should_auto_approve(confidence: float, flags: list[str], settings: dict[str, Any]) -> bool:
    if not settings["auto_approve_enabled"]:
        return False
    if is_amber(flags):
        return False
    return confidence >= settings["auto_approve_threshold"]
