"""Acceptance check on the recorded Claude outputs in data/llm_cache.json.

Skipped until the real run has been done (needs ANTHROPIC_API_KEY once).
"""

import pytest
from sqlalchemy import select

from app.config import Config
from app.drafts.retriever import HelpDocRetriever
from app.intake.inbox_sim import load_enquiries, seed_inbox
from app.llm.cache import ResponseCache
from app.llm.client import ClaudeClient
from app.models import CrmRecord, Message, ReviewItem
from app.pipeline.process import Pipeline, process_message, unprocessed
from app.review import service

config = Config()
cache = ResponseCache(config.cache_path)
pytestmark = pytest.mark.skipif(len(cache) < 80, reason="real Claude outputs not recorded yet")


def test_all_80_with_real_outputs(session):
    pipeline = Pipeline(ClaudeClient(cache, live=False, has_key=False), HelpDocRetriever(), config)
    seed_inbox(session)
    for msg in unprocessed(session):
        process_message(session, pipeline, msg)
    msgs = session.scalars(select(Message)).all()
    assert len(msgs) == 80 and all(m.status == "processed" for m in msgs)
    assert not any(m.classification.parse_failed for m in msgs)

    expected = {e["id"]: e["expected"] for e in load_enquiries()}
    correct = sum(m.classification.category == expected[m.external_id] for m in msgs)
    assert correct / 80 >= 0.9, f"classification accuracy {correct}/80"

    for item in session.scalars(select(ReviewItem).where(ReviewItem.kind == "support")):
        if "no_relevant_doc" not in item.flags:
            assert item.citations, f"support item {item.id} has no citation"

    for item in session.scalars(select(ReviewItem).where(ReviewItem.kind == "sales")):
        service.approve(session, item.id)
    keys = [r.company_key for r in session.scalars(select(CrmRecord))]
    assert len(keys) == len(set(keys))
