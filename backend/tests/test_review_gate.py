import pytest

from app.crm.base import LeadPayload
from app.crm.mock_crm import MockCRM
from app.models import CrmRecord, Message, OutboxEmail
from app.review import approval, service
from app.review.approval import ApprovalRequired
from app.review.gate import compute_flags, should_auto_approve
from tests.conftest import make_fields


def make_message(session, email="dana@harbourline-freight.example"):
    msg = Message(source="form", from_name="Dana", from_email=email, company="Harbourline Freight",
                  subject="Hi", body="Hello")
    session.add(msg)
    session.flush()
    return msg


def lead_payload(message_id):
    return LeadPayload(name="Dana", email="dana@harbourline-freight.example", company="Harbourline Freight",
                       need="Bookings", budget="$30k", timeline="soon", score=90, message_id=message_id)


def new_item(session, settings, *, confidence=0.95, flags=None, crm_payload=True):
    msg = make_message(session)
    return service.create_item(
        session, message=msg, kind="sales", subject="Re: Hi", body="Draft reply",
        confidence=confidence, flags=flags or [], settings=settings,
        crm_payload=lead_payload(msg.id) if crm_payload else None,
    )


def test_auto_approve_is_off_by_default(settings):
    assert settings["auto_approve_enabled"] is False
    assert not should_auto_approve(0.99, [], settings)


def test_nothing_is_sent_or_written_before_approval(session, settings):
    item = new_item(session, settings, confidence=0.99)
    assert item.status == "pending"
    assert session.query(OutboxEmail).count() == 0
    assert session.query(CrmRecord).count() == 0


def test_approve_sends_and_writes_crm(session, settings):
    item = new_item(session, settings)
    service.approve(session, item.id)
    assert item.status == "approved" and item.decided_by == "person"
    assert session.query(OutboxEmail).count() == 1
    assert session.query(CrmRecord).count() == 1


def test_edit_then_approve_sends_the_edited_text(session, settings):
    item = new_item(session, settings)
    service.approve(session, item.id, edited_body="Edited reply")
    sent = session.query(OutboxEmail).one()
    assert sent.body == "Edited reply"
    assert item.draft_body == "Draft reply"


def test_reject_leaves_crm_and_outbox_untouched(session, settings):
    item = new_item(session, settings)
    service.reject(session, item.id)
    assert item.status == "rejected"
    assert session.query(OutboxEmail).count() == 0
    assert session.query(CrmRecord).count() == 0


def test_cannot_approve_twice(session, settings):
    item = new_item(session, settings)
    service.approve(session, item.id)
    with pytest.raises(service.ReviewError):
        service.approve(session, item.id)


def test_crm_refuses_writes_without_an_approval(session):
    crm = MockCRM(session)
    with pytest.raises(ApprovalRequired):
        crm.upsert_lead(lead_payload(1), approval=None)
    forged = approval.Approval(review_item_id=1, decided_by="person")
    with pytest.raises(ApprovalRequired):
        crm.upsert_lead(lead_payload(1), approval=forged)
    assert session.query(CrmRecord).count() == 0


def test_outbox_refuses_approval_for_another_item(session, settings):
    item = new_item(session, settings)
    with pytest.raises(ApprovalRequired):
        service.send_email(session, item, approval.issue(item.id + 1, "person"), to_email="x@y.example")


def test_auto_approve_applies_only_above_threshold(session, settings):
    on = {**settings, "auto_approve_enabled": True, "auto_approve_threshold": 0.9}
    low = new_item(session, on, confidence=0.85)
    high = new_item(session, on, confidence=0.95)
    assert low.status == "pending"
    assert high.status == "approved" and high.decided_by == "auto"


@pytest.mark.parametrize("flag", ["injection", "low_confidence", "unsure_fields", "parse_failed", "no_citation"])
def test_amber_flags_block_auto_approve(session, settings, flag):
    on = {**settings, "auto_approve_enabled": True, "auto_approve_threshold": 0.5}
    item = new_item(session, on, confidence=0.99, flags=[flag])
    assert item.status == "pending"


def test_info_flag_does_not_block_auto_approve(settings):
    on = {**settings, "auto_approve_enabled": True, "auto_approve_threshold": 0.5}
    assert should_auto_approve(0.99, ["sales_opportunity"], on)


def test_compute_flags(settings):
    unsure = make_fields(overrides={"company": {"value": None, "confidence": 0.2}})
    flags = compute_flags(classification_confidence=0.55, injection=True, parse_failed=False,
                          fields=unsure, kind="sales", settings=settings)
    assert set(flags) == {"low_confidence", "injection", "unsure_fields"}

    assert compute_flags(classification_confidence=0.95, injection=False, parse_failed=False, fields=None,
                         kind="support", settings=settings, citations=[], answerable=True) == ["no_citation"]
    assert compute_flags(classification_confidence=0.95, injection=False, parse_failed=False, fields=None,
                         kind="support", settings=settings, citations=[], answerable=False) == ["no_relevant_doc"]
    assert compute_flags(classification_confidence=0.95, injection=False, parse_failed=False, fields=make_fields(),
                         kind="sales", settings=settings) == []
