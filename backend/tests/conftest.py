import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db, make_engine, make_session_factory  # noqa: E402
from app.llm.schemas import LeadFields  # noqa: E402
from app.pipeline.scoring import load_icp  # noqa: E402
from app.settings_store import DEFAULTS  # noqa: E402


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    init_db(engine)
    factory = make_session_factory(engine)
    s = factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def icp():
    return load_icp()


@pytest.fixture
def settings(icp):
    return {**DEFAULTS, "icp": icp}


def make_fields(
    *,
    name="Dana Whitlock",
    company="Harbourline Freight",
    need="Automate booking emails",
    budget="$30k to $40k",
    budget_usd=35000,
    timeline="next month",
    industry="freight forwarding",
    company_size=180,
    urgency="high",
    confidence=0.9,
    overrides=None,
) -> LeadFields:
    data = {
        "name": {"value": name, "confidence": confidence},
        "company": {"value": company, "confidence": confidence},
        "need": {"value": need, "confidence": confidence},
        "budget": {"value": budget, "confidence": confidence},
        "budget_usd": {"value": budget_usd, "confidence": confidence},
        "timeline": {"value": timeline, "confidence": confidence},
        "industry": {"value": industry, "confidence": confidence},
        "company_size": {"value": company_size, "confidence": confidence},
        "urgency": {"value": urgency, "confidence": confidence},
    }
    for key, value in (overrides or {}).items():
        data[key] = value
    return LeadFields.model_validate(data)
