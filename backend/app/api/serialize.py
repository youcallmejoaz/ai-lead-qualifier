"""Turn database rows into JSON for the front end."""

from typing import Any

from app.models import CrmRecord, Message, ReviewItem


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def message_row(m: Message) -> dict[str, Any]:
    c, lead, item = m.classification, m.lead, m.review_item
    flags = list(item.flags) if item else []
    if c and c.parse_failed and "parse_failed" not in flags:
        flags.append("parse_failed")
    if c and c.injection_flag and "injection" not in flags:
        flags.append("injection")
    return {
        "id": m.id,
        "external_id": m.external_id,
        "source": m.source,
        "from_name": m.from_name,
        "from_email": m.from_email,
        "company": m.company,
        "subject": m.subject,
        "snippet": m.body[:160],
        "received_at": _iso(m.received_at),
        "status": m.status,
        "category": c.category if c else None,
        "confidence": c.confidence if c else None,
        "reason": c.reason if c else None,
        "injection": bool(c and c.injection_flag),
        "score": lead.score if lead else None,
        "qualified": bool(lead and lead.qualified),
        "flags": flags,
        "amber": bool(item and item.amber) or bool(c and (c.parse_failed or c.injection_flag)),
        "review_id": item.id if item else None,
        "review_status": item.status if item else None,
    }


def message_detail(m: Message) -> dict[str, Any]:
    row = message_row(m)
    c, lead = m.classification, m.lead
    row.update(
        body=m.body,
        injection_reasons=c.injection_reasons if c else [],
        model=c.model if c else None,
        fields=lead.fields if lead else None,
        score_breakdown=lead.score_breakdown if lead else None,
    )
    return row


def review_row(item: ReviewItem) -> dict[str, Any]:
    m = item.message
    return {
        "id": item.id,
        "kind": item.kind,
        "status": item.status,
        "subject": item.subject,
        "draft_body": item.draft_body,
        "edited_body": item.edited_body,
        "final_body": item.final_body,
        "citations": item.citations,
        "crm_payload": item.crm_payload,
        "flags": item.flags,
        "amber": item.amber,
        "confidence": item.confidence,
        "decided_by": item.decided_by,
        "decided_at": _iso(item.decided_at),
        "created_at": _iso(item.created_at),
        "message": message_detail(m),
    }


def crm_row(r: CrmRecord) -> dict[str, Any]:
    return {
        "id": r.id,
        "company": r.company,
        "primary_name": r.primary_name,
        "primary_email": r.primary_email,
        "contacts": r.contacts,
        "need": r.need,
        "budget": r.budget,
        "timeline": r.timeline,
        "score": r.score,
        "stage": r.stage,
        "source_message_ids": r.source_message_ids,
        "merge_count": r.merge_count,
        "created_at": _iso(r.created_at),
        "updated_at": _iso(r.updated_at),
    }
