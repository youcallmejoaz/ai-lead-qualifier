"""Support reply drafts grounded in the help docs, with citations."""

import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.drafts.retriever import HelpDocRetriever
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import SUPPORT_SYSTEM
from app.llm.schemas import SupportDraft, output_schema
from app.pipeline.injection import wrap_untrusted

SCHEMA = output_schema(SupportDraft)


@dataclass
class DraftResult:
    subject: str
    body: str
    citations: list[dict] = field(default_factory=list)
    answerable: bool = True
    failed: bool = False


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def build_prompt(email: str, hits) -> str:
    passages = "\n".join(
        f'<passage id="{h.passage.id}" article="{h.passage.doc_title}" section="{h.passage.section}">\n'
        f"{h.passage.text}\n</passage>"
        for h in hits
    )
    return f"<help_articles>\n{passages}\n</help_articles>\n\n{email}"


def check_citations(draft: SupportDraft, retriever: HelpDocRetriever, allowed: set[str]) -> list[dict]:
    """Keep citations that point at a passage we actually supplied, and check the quote."""
    out = []
    for c in draft.citations:
        if c.doc_id not in allowed:
            continue
        passage = retriever.get(c.doc_id)
        out.append(
            {
                "passage_id": passage.id,
                "doc_id": passage.doc_id,
                "doc_title": passage.doc_title,
                "section": passage.section,
                "quote": c.quote,
                "verified": _norm(c.quote) in _norm(passage.text),
            }
        )
    return out


def draft_support_reply(
    *, llm: LLMClient, retriever: HelpDocRetriever, model: str, subject: str, body: str, from_name: str,
    company: str | None,
) -> DraftResult:
    hits = retriever.search(f"{subject} {body}", k=4)
    email = wrap_untrusted(subject, body, from_name, company)
    try:
        raw = llm.generate_json(
            purpose="support_draft", model=model, system=SUPPORT_SYSTEM, user=build_prompt(email, hits),
            schema=SCHEMA, effort="low", max_tokens=8000,
        )
        draft = SupportDraft.model_validate(json.loads(raw))
    except (LLMError, ValidationError, json.JSONDecodeError):
        return DraftResult(subject=f"Re: {subject}", body="", answerable=False, failed=True)
    citations = check_citations(draft, retriever, {h.passage.id for h in hits})
    return DraftResult(subject=draft.subject, body=draft.reply, citations=citations, answerable=draft.answerable)
