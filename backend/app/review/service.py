"""Review queue actions. The only code path that sends email or writes to the CRM."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.crm.base import CRMAdapter, LeadPayload
from app.crm.mock_crm import MockCRM
from app.models import AuditLog, Message, OutboxEmail, ReviewItem, utcnow
from app.review import approval as approvals
from app.review.gate import should_auto_approve

log = logging.getLogger(__name__)


class ReviewError(ValueError):
    pass


def _audit(session: Session, action: str, entity: str, entity_id: int) -> None:
    session.add(AuditLog(action=action, entity=entity, entity_id=entity_id))


def create_item(
    session: Session,
    *,
    message: Message,
    kind: str,
    subject: str,
    body: str,
    confidence: float,
    flags: list[str],
    settings: dict[str, Any],
    citations: list | None = None,
    crm_payload: LeadPayload | None = None,
    crm: CRMAdapter | None = None,
) -> ReviewItem:
    item = ReviewItem(
        message_id=message.id,
        kind=kind,
        subject=subject,
        draft_body=body,
        citations=citations or [],
        crm_payload=crm_payload.to_dict() if crm_payload else None,
        flags=flags,
        confidence=confidence,
        status="pending",
    )
    session.add(item)
    session.flush()
    _audit(session, "review_created", "review_item", item.id)
    if should_auto_approve(confidence, flags, settings):
        approve(session, item.id, decided_by="auto", crm=crm)
    return item


def save_edit(session: Session, item_id: int, body: str) -> ReviewItem:
    item = _pending(session, item_id)
    item.edited_body = body
    _audit(session, "review_edited", "review_item", item.id)
    session.flush()
    return item


def approve(
    session: Session,
    item_id: int,
    *,
    edited_body: str | None = None,
    decided_by: str = "person",
    crm: CRMAdapter | None = None,
) -> ReviewItem:
    item = _pending(session, item_id)
    if edited_body is not None and edited_body != item.draft_body:
        item.edited_body = edited_body
    token = approvals.issue(item.id, decided_by)

    message = item.message
    send_email(session, item, token, to_email=message.from_email)
    if item.crm_payload:
        adapter = crm or MockCRM(session)
        result = adapter.upsert_lead(LeadPayload(**item.crm_payload), token)
        if result.merged and "merged_duplicate" not in item.flags:
            item.flags = [*item.flags, "merged_duplicate"]

    item.status = "approved"
    item.decided_by = decided_by
    item.decided_at = utcnow()
    _audit(session, f"review_approved_{decided_by}", "review_item", item.id)
    session.flush()
    log.info("review item %s approved by %s", item.id, decided_by)
    return item


def reject(session: Session, item_id: int) -> ReviewItem:
    item = _pending(session, item_id)
    item.status = "rejected"
    item.decided_by = "person"
    item.decided_at = utcnow()
    _audit(session, "review_rejected", "review_item", item.id)
    session.flush()
    return item


def send_email(session: Session, item: ReviewItem, token: approvals.Approval, *, to_email: str) -> OutboxEmail:
    """Simulated send. Real delivery (Gmail, SMTP) would go here, behind the same check."""
    approvals.verify(token, item.id)
    email = OutboxEmail(review_item_id=item.id, to_email=to_email, subject=item.subject, body=item.final_body)
    session.add(email)
    session.flush()
    return email


def _pending(session: Session, item_id: int) -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise ReviewError(f"Review item {item_id} not found")
    if item.status != "pending":
        raise ReviewError(f"Review item {item_id} is already {item.status}")
    return item
