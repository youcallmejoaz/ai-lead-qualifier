"""The hand written demo outputs (LLM_MODE=scripted) must pass the same checks as real ones."""

from app.config import Config
from app.drafts.retriever import HelpDocRetriever
from app.intake.inbox_sim import load_enquiries
from app.llm.scripted import ScriptedLLM
from app.pipeline.process import MessageIn, Pipeline


def test_every_scripted_output_parses_and_cites_real_passages(settings):
    pipeline = Pipeline(ScriptedLLM(), HelpDocRetriever(), Config())
    for i, e in enumerate(load_enquiries(), 1):
        a = pipeline.analyse(MessageIn(i, e["from_name"], e["from_email"], e["company"], e["subject"], e["body"]), settings)
        assert not a.parse_failed, e["id"]
        assert a.triage.category == e["expected"], e["id"]
        if a.draft is not None:
            assert not a.draft.failed, e["id"]
        if a.kind == "support" and "no_doc" not in e["tags"]:
            assert a.draft.citations and all(c["verified"] for c in a.draft.citations), e["id"]
        if "injection" in e["tags"]:
            assert a.injection, e["id"]
