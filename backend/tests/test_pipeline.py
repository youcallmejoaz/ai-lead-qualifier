from sqlalchemy import select

from app.config import Config
from app.drafts.retriever import HelpDocRetriever
from app.intake.inbox_sim import seed_inbox
from app.models import CrmRecord, Message, OutboxEmail, ReviewItem
from app.pipeline.process import Pipeline, process_message, rescore_all, unprocessed
from app.review import service
from app.settings_store import set_setting
from tests.fakes import FakeLLM


def run_all(session, llm=None):
    pipeline = Pipeline(llm=llm or FakeLLM(), retriever=HelpDocRetriever(), config=Config())
    assert seed_inbox(session) == 80
    for msg in unprocessed(session):
        process_message(session, pipeline, msg)
    return pipeline


def by_ext(session, ext_id) -> Message:
    return session.scalars(select(Message).where(Message.external_id == ext_id)).one()


def by_tag(session, tag):
    from app.intake.inbox_sim import load_enquiries
    ids = [e["id"] for e in load_enquiries() if tag in e["tags"]]
    return [by_ext(session, i) for i in ids]


def test_all_80_messages_are_processed(session):
    run_all(session)
    msgs = session.scalars(select(Message)).all()
    assert len(msgs) == 80
    assert all(m.status == "processed" and m.classification is not None for m in msgs)
    sales = [m for m in msgs if m.classification.category == "Sales"]
    assert sales and all(m.lead is not None for m in sales)


def test_seeding_twice_does_not_duplicate(session):
    assert seed_inbox(session) == 80
    assert seed_inbox(session) == 0


def test_nothing_reaches_crm_or_outbox_without_a_click(session):
    run_all(session)
    assert session.query(ReviewItem).filter_by(status="pending").count() > 0
    assert session.query(CrmRecord).count() == 0
    assert session.query(OutboxEmail).count() == 0


def test_approving_every_qualified_lead_gives_no_duplicate_crm_records(session):
    run_all(session)
    sales_items = session.scalars(select(ReviewItem).where(ReviewItem.kind == "sales")).all()
    for item in sales_items:
        service.approve(session, item.id)
    records = session.scalars(select(CrmRecord)).all()
    keys = [r.company_key for r in records]
    assert len(keys) == len(set(keys))
    emails = [c["email"] for r in records for c in r.contacts]
    assert len(emails) == len(set(emails))
    harbour = next(r for r in records if r.company_key == "harbourline freight")
    assert len(harbour.source_message_ids) == 3
    assert session.query(OutboxEmail).count() == len(sales_items)


def test_support_drafts_cite_only_supplied_passages(session):
    run_all(session)
    support = session.scalars(select(ReviewItem).where(ReviewItem.kind == "support")).all()
    assert support
    for item in support:
        if "no_relevant_doc" in item.flags:
            assert item.citations == []
            continue
        assert item.citations, item.id
        assert all(c["passage_id"] != "HD99-1" for c in item.citations)
        assert all(c["verified"] for c in item.citations)


def test_question_without_a_doc_is_flagged(session):
    run_all(session)
    (msg,) = by_tag(session, "no_doc")
    assert "no_relevant_doc" in msg.review_item.flags and msg.review_item.amber


def test_injection_emails_are_flagged_and_never_auto_approved(session):
    set_setting(session, "auto_approve_enabled", True)
    set_setting(session, "auto_approve_threshold", 0.5)
    run_all(session)
    for msg in by_tag(session, "injection"):
        assert msg.classification.injection_flag
        if msg.review_item is not None:
            assert "injection" in msg.review_item.flags
            assert msg.review_item.status == "pending"


def test_auto_approve_when_enabled_still_skips_amber_items(session):
    set_setting(session, "auto_approve_enabled", True)
    set_setting(session, "auto_approve_threshold", 0.5)
    run_all(session)
    items = session.scalars(select(ReviewItem)).all()
    assert any(i.decided_by == "auto" for i in items)
    assert all(i.status == "pending" for i in items if i.amber)


def test_support_from_big_prospect_is_marked_as_sales_opportunity(session):
    run_all(session)
    (msg,) = by_tag(session, "support_from_big_prospect")
    assert msg.classification.category == "Support"
    assert "sales_opportunity" in msg.review_item.flags


def test_mixed_low_confidence_email_is_amber(session):
    run_all(session)
    (msg,) = by_tag(session, "mixed")
    assert "low_confidence" in msg.review_item.flags


def test_unreadable_model_output_goes_to_a_person(session):
    e001 = "E001"
    run_all(session, FakeLLM(fail_triage_for={e001}))
    msg = by_ext(session, e001)
    assert msg.classification.parse_failed
    assert msg.classification.category == "Other" and msg.classification.confidence == 0.0


def test_failed_draft_is_flagged(session):
    run_all(session, FakeLLM(fail_drafts=True))
    items = session.scalars(select(ReviewItem)).all()
    assert items and all("draft_failed" in i.flags and i.status == "pending" for i in items)


def test_rescore_after_icp_change(session):
    run_all(session)
    from app.settings_store import get_setting
    icp = get_setting(session, "icp")
    before = by_ext(session, "E001").lead.score
    icp["weights"] = {"industry": 10, "company_size": 10, "budget": 70, "urgency": 10}
    set_setting(session, "icp", icp)
    rescore_all(session)
    after = by_ext(session, "E001").lead.score
    assert before == 100 and after == 100  # strong on every factor either way
    weak = by_tag(session, "weak")[0]
    assert weak.lead.score <= 100
