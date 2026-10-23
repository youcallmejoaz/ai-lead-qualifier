"""Mock CRM stored in the app database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.base import CRMAdapter, LeadPayload, UpsertResult
from app.crm.dedupe import company_key, find_match, normalize_email
from app.models import CrmRecord, utcnow
from app.review.approval import Approval, verify


class MockCRM(CRMAdapter):
    def __init__(self, session: Session):
        self.session = session

    def upsert_lead(self, payload: LeadPayload, approval: Approval) -> UpsertResult:
        verify(approval)
        records = self.session.scalars(select(CrmRecord)).all()
        match, reason = find_match(records, payload.email, payload.company)
        email = normalize_email(payload.email)

        if match is None:
            record = CrmRecord(
                company=payload.company,
                company_key=company_key(payload.company),
                primary_name=payload.name,
                primary_email=email,
                contacts=[{"name": payload.name, "email": email}],
                need=payload.need,
                budget=payload.budget,
                timeline=payload.timeline,
                score=payload.score,
                source_message_ids=[payload.message_id],
            )
            self.session.add(record)
            self.session.flush()
            return UpsertResult(record_id=record.id, merged=False, match_reason="")

        record = match
        contacts = list(record.contacts or [])
        same_person = any(normalize_email(c["email"]) == email for c in contacts)
        if not same_person:
            contacts.append({"name": payload.name, "email": email})
        record.contacts = contacts
        record.source_message_ids = [*record.source_message_ids, payload.message_id]
        record.score = max(record.score, payload.score)
        if same_person:
            # A follow up from the same person: newer details win.
            record.need = payload.need or record.need
            record.budget = payload.budget or record.budget
            record.timeline = payload.timeline or record.timeline
        else:
            # A colleague: keep the original details, fill gaps, note their need too.
            if payload.need and payload.need != record.need:
                record.need = f"{record.need}\n{payload.name}: {payload.need}" if record.need else payload.need
            record.budget = record.budget or payload.budget
            record.timeline = record.timeline or payload.timeline
        record.merge_count += 1
        record.updated_at = utcnow()
        self.session.flush()
        return UpsertResult(record_id=record.id, merged=True, match_reason=reason)
