from types import SimpleNamespace

import pytest

from app.crm.base import LeadPayload
from app.crm.dedupe import company_key, find_match
from app.crm.mock_crm import MockCRM
from app.models import CrmRecord
from app.review import approval


def record(company, email, extra=()):
    return SimpleNamespace(
        company_key=company_key(company),
        primary_email=email,
        contacts=[{"name": "x", "email": e} for e in (email, *extra)],
    )


@pytest.mark.parametrize(
    "a,b",
    [
        ("Harbourline Freight", "Harbourline Freight Ltd"),
        ("Harbourline Freight", "harbourline freight limited"),
        ("The Calder & Finch Group", "Calder and Finch"),
        ("Kestrel Manufacturing, Inc.", "KESTREL MANUFACTURING"),
    ],
)
def test_company_key_ignores_suffixes_case_and_punctuation(a, b):
    assert company_key(a) == company_key(b)


def test_different_companies_have_different_keys():
    assert company_key("Harbourline Freight") != company_key("Bluewater Logistics")


def test_match_on_email_ignores_case_and_whitespace():
    rec = record("Harbourline Freight", "dana.whitlock@harbourline-freight.example")
    match, reason = find_match([rec], "  DANA.Whitlock@harbourline-freight.example ", None)
    assert match is rec and reason == "same email"


def test_match_on_company_name_variant():
    rec = record("Harbourline Freight", "dana@harbourline-freight.example")
    match, reason = find_match([rec], "ravi@other-domain.example", "Harbourline Freight Ltd")
    assert match is rec and reason == "same company"


def test_match_on_corporate_domain_for_a_different_person():
    rec = record("Harbourline Freight", "dana@harbourline-freight.example")
    match, reason = find_match([rec], "ravi.shah@harbourline-freight.example", None)
    assert match is rec and reason == "same company domain"


def test_free_mail_domain_never_merges_different_people():
    rec = record("Lucy F Weddings", "lucy.fernandes@freemail.example")
    match, _ = find_match([rec], "jess.thornton@freemail.example", "Wrenfield Clinics")
    assert match is None


def test_no_match_for_new_company():
    rec = record("Harbourline Freight", "dana@harbourline-freight.example")
    match, reason = find_match([rec], "sofia@brightpath-shop.example", "Brightpath Ecommerce")
    assert match is None and reason == ""


def payload(**kw):
    base = dict(name="Dana Whitlock", email="dana.whitlock@harbourline-freight.example",
                company="Harbourline Freight", need="Bookings", budget="$30k", timeline="next month",
                score=90, message_id=1)
    base.update(kw)
    return LeadPayload(**base)


def test_mock_crm_merges_duplicates_into_one_record(session):
    crm = MockCRM(session)
    first = crm.upsert_lead(payload(), approval.issue(1, "person"))
    again = crm.upsert_lead(payload(email="DANA.WHITLOCK@harbourline-freight.example", budget="$40k",
                                    score=95, message_id=2), approval.issue(2, "person"))
    colleague = crm.upsert_lead(payload(name="Ravi Shah", email="ravi.shah@harbourline-freight.example",
                                        company="Harbourline Freight Ltd", need="Invoice matching",
                                        budget="$25k", score=80, message_id=3),
                                approval.issue(3, "person"))
    other = crm.upsert_lead(payload(name="Sofia", email="sofia@brightpath-shop.example",
                                    company="Brightpath Ecommerce", message_id=4), approval.issue(4, "person"))

    assert not first.merged and other.record_id != first.record_id
    assert again.merged and again.record_id == first.record_id and again.match_reason == "same email"
    assert colleague.merged and colleague.record_id == first.record_id

    records = session.query(CrmRecord).all()
    assert len(records) == 2
    harbour = session.get(CrmRecord, first.record_id)
    assert harbour.source_message_ids == [1, 2, 3]
    assert {c["email"] for c in harbour.contacts} == {
        "dana.whitlock@harbourline-freight.example", "ravi.shah@harbourline-freight.example"}
    # Dana's follow up updated the budget; Ravi's separate project did not overwrite it.
    assert harbour.score == 95 and harbour.budget == "$40k" and harbour.merge_count == 2
    assert "Ravi Shah: Invoice matching" in harbour.need
