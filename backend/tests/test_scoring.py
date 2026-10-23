import copy

import pytest

from app.pipeline.scoring import parse_icp, score_lead
from tests.conftest import make_fields


def test_strong_lead_scores_full_marks(icp):
    result = score_lead(make_fields(), icp)
    assert result.score == 100
    assert result.qualified


def test_weak_lead_is_not_qualified(icp):
    fields = make_fields(industry="photography", company_size=1, budget_usd=500, urgency="low")
    result = score_lead(fields, icp)
    assert result.score < icp["qualify_threshold"]
    assert not result.qualified


def test_missing_budget_gets_partial_credit_not_zero(icp):
    full = score_lead(make_fields(), icp)
    no_budget = score_lead(make_fields(budget=None, budget_usd=None), icp)
    budget_part = next(p for p in no_budget.breakdown if p["factor"] == "budget")
    assert budget_part["points"] == pytest.approx(icp["weights"]["budget"] * icp["budget"]["unknown_score"])
    assert budget_part["note"] == "no budget mentioned"
    assert no_budget.score < full.score
    # Strong on everything else, so it still qualifies.
    assert no_budget.qualified


def test_budget_scales_between_min_and_ideal(icp):
    low = score_lead(make_fields(budget_usd=icp["budget"]["min_usd"]), icp)
    mid = score_lead(make_fields(budget_usd=12500), icp)
    high = score_lead(make_fields(budget_usd=icp["budget"]["ideal_usd"]), icp)
    assert low.score < mid.score < high.score


@pytest.mark.parametrize(
    "employees,expected",
    [(None, "unknown_score"), (5, "below_min_score"), (30, "small_score"), (200, "ideal_score"), (5000, "above_ideal_score")],
)
def test_company_size_bands(icp, employees, expected):
    result = score_lead(make_fields(company_size=employees), icp)
    size = next(p for p in result.breakdown if p["factor"] == "company_size")
    assert size["points"] == pytest.approx(icp["weights"]["company_size"] * icp["company_size"][expected])


def test_adjacent_industry_scores_between_target_and_other(icp):
    target = score_lead(make_fields(industry="logistics"), icp).score
    adjacent = score_lead(make_fields(industry="construction"), icp).score
    other = score_lead(make_fields(industry="crypto"), icp).score
    assert target > adjacent > other


def test_score_is_bounded_and_breakdown_adds_up(icp):
    result = score_lead(make_fields(industry=None, company_size=None, budget_usd=None, urgency="unknown"), icp)
    assert 0 <= result.score <= 100
    assert round(sum(p["points"] for p in result.breakdown)) == result.score


def test_non_sales_is_never_qualified(icp):
    assert not score_lead(make_fields(), icp, is_sales=False).qualified


def test_editing_the_icp_changes_the_score(icp):
    edited = copy.deepcopy(icp)
    edited["industry"]["target"] = ["construction"]
    edited["industry"]["adjacent"] = []
    before = score_lead(make_fields(industry="construction"), icp).score
    after = score_lead(make_fields(industry="construction"), edited).score
    assert after > before


def test_raising_the_threshold_disqualifies(icp):
    strict = copy.deepcopy(icp)
    strict["qualify_threshold"] = 101
    assert not score_lead(make_fields(), strict).qualified


def test_parse_icp_rejects_bad_weights():
    with pytest.raises(ValueError, match="add up to 100"):
        parse_icp("""
qualify_threshold: 60
weights: {industry: 50, company_size: 25, budget: 30, urgency: 15}
industry: {}
company_size: {}
budget: {}
urgency: {}
""")


def test_parse_icp_rejects_missing_section():
    with pytest.raises(ValueError, match="missing 'urgency'"):
        parse_icp("qualify_threshold: 60\nweights: {a: 100}\nindustry: {}\ncompany_size: {}\nbudget: {}\n")
