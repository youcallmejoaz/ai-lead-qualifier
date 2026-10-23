"""The pipeline: triage, score, draft, then queue for review.

`analyse` does the slow work (Claude calls, retrieval, scoring) and touches no
database, so many messages can be analysed in parallel. `persist` writes the
result and creates the review item.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Config
from app.crm.base import LeadPayload
from app.crm.dedupe import email_domain
from app.drafts.retriever import HelpDocRetriever
from app.drafts.sales import draft_sales_reply
from app.drafts.support import DraftResult, draft_support_reply
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import PROMPT_VERSION, TRIAGE_SYSTEM
from app.llm.schemas import TriageResult, output_schema
from app.models import Classification, LeadExtraction, Message
from app.pipeline.classify import TriageParseError, fallback_triage, parse_triage
from app.pipeline.injection import scan, wrap_untrusted
from app.pipeline.scoring import ScoreResult, score_lead
from app.review import service as review
from app.review.gate import compute_flags, item_confidence
from app.settings_store import all_settings

log = logging.getLogger(__name__)

TRIAGE_SCHEMA = output_schema(TriageResult)


@dataclass(frozen=True)
class MessageIn:
    id: int
    from_name: str
    from_email: str
    company: str | None
    subject: str
    body: str

    @classmethod
    def of(cls, m: Message) -> "MessageIn":
        return cls(m.id, m.from_name, m.from_email, m.company, m.subject, m.body)


@dataclass
class Analysis:
    triage: TriageResult
    parse_failed: bool
    injection_reasons: list[str]
    score: ScoreResult
    draft: DraftResult | None = None
    kind: str | None = None  # sales | support | None (no review item)
    flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    crm_payload: LeadPayload | None = None

    @property
    def injection(self) -> bool:
        return bool(self.injection_reasons)


@dataclass
class Pipeline:
    llm: LLMClient
    retriever: HelpDocRetriever
    config: Config

    def triage(self, msg: MessageIn) -> tuple[TriageResult, bool]:
        email = wrap_untrusted(msg.subject, msg.body, msg.from_name, msg.company)
        try:
            raw = self.llm.generate_json(
                purpose="triage", model=self.config.classify_model, system=TRIAGE_SYSTEM, user=email,
                schema=TRIAGE_SCHEMA, effort="low", max_tokens=4000,
            )
            return parse_triage(raw), False
        except (LLMError, TriageParseError) as exc:
            log.warning("triage failed for message %s: %s", msg.id, exc)
            return fallback_triage(f"Needs a person: {exc}"), True

    def analyse(self, msg: MessageIn, settings: dict[str, Any]) -> Analysis:
        triage, parse_failed = self.triage(msg)
        reasons = scan(f"{msg.subject}\n{msg.body}")
        if triage.injection_suspected and "model flagged instructions in the email" not in reasons:
            reasons.append("model flagged instructions in the email")

        icp = settings["icp"]
        score = score_lead(triage.fields, icp, is_sales=triage.category == "Sales")
        a = Analysis(triage=triage, parse_failed=parse_failed, injection_reasons=reasons, score=score)

        if triage.category == "Sales" and score.qualified:
            a.kind = "sales"
            a.draft = draft_sales_reply(
                llm=self.llm, model=self.config.draft_model, subject=msg.subject, body=msg.body,
                from_name=msg.from_name, company=msg.company, fields=triage.fields,
            )
            a.crm_payload = self._payload(msg, triage, score)
        elif triage.category == "Support":
            a.kind = "support"
            a.draft = draft_support_reply(
                llm=self.llm, retriever=self.retriever, model=self.config.draft_model, subject=msg.subject,
                body=msg.body, from_name=msg.from_name, company=msg.company,
            )

        if a.kind:
            a.confidence = item_confidence(triage.confidence, triage.fields, a.kind)
            a.flags = compute_flags(
                classification_confidence=triage.confidence,
                injection=a.injection,
                parse_failed=parse_failed,
                fields=triage.fields,
                kind=a.kind,
                settings=settings,
                citations=a.draft.citations if a.kind == "support" else None,
                answerable=a.draft.answerable if a.kind == "support" else True,
                # A support email that also carries a buying signal: a stated budget and a strong score.
                sales_opportunity=(
                    a.kind == "support"
                    and triage.fields.budget_usd.value is not None
                    and score.score >= icp["qualify_threshold"]
                ),
            )
            if a.draft.failed:
                a.flags.append("draft_failed")
        return a

    @staticmethod
    def _payload(msg: MessageIn, triage: TriageResult, score: ScoreResult) -> LeadPayload:
        f = triage.fields
        company = f.company.value or msg.company or email_domain(msg.from_email).split(".")[0].title()
        return LeadPayload(
            name=f.name.value or msg.from_name,
            email=msg.from_email,
            company=company,
            need=f.need.value,
            budget=f.budget.value,
            timeline=f.timeline.value,
            score=score.score,
            message_id=msg.id,
        )


def persist(session: Session, message: Message, a: Analysis, settings: dict[str, Any], model: str) -> None:
    t = a.triage
    message.classification = Classification(
        category=t.category,
        confidence=t.confidence,
        reason=t.reason,
        injection_flag=a.injection,
        injection_reasons=a.injection_reasons,
        parse_failed=a.parse_failed,
        model=model,
        prompt_version=PROMPT_VERSION,
    )
    if t.category in ("Sales", "Support"):
        message.lead = LeadExtraction(
            fields=t.fields.model_dump(),
            score=a.score.score,
            score_breakdown=a.score.breakdown,
            qualified=a.score.qualified,
        )
    session.flush()
    if a.kind and a.draft is not None:
        review.create_item(
            session,
            message=message,
            kind=a.kind,
            subject=a.draft.subject,
            body=a.draft.body,
            confidence=a.confidence,
            flags=a.flags,
            settings=settings,
            citations=a.draft.citations,
            crm_payload=a.crm_payload,
        )
    message.status = "processed"
    session.flush()


def process_message(session: Session, pipeline: Pipeline, message: Message) -> None:
    settings = all_settings(session)
    analysis = pipeline.analyse(MessageIn.of(message), settings)
    persist(session, message, analysis, settings, pipeline.config.classify_model)


def unprocessed(session: Session) -> list[Message]:
    return list(session.scalars(select(Message).where(Message.status == "new").order_by(Message.received_at)))


def rescore_all(session: Session) -> int:
    """Re-run scoring after the ICP changes. Pending items follow; decided ones stay as they were."""
    from app.llm.schemas import LeadFields

    icp = all_settings(session)["icp"]
    count = 0
    for lead in session.scalars(select(LeadExtraction)):
        category = lead.message.classification.category
        result = score_lead(LeadFields.model_validate(lead.fields), icp, is_sales=category == "Sales")
        lead.score, lead.score_breakdown, lead.qualified = result.score, result.breakdown, result.qualified
        item = lead.message.review_item
        if item is not None and item.status == "pending" and item.crm_payload:
            item.crm_payload = {**item.crm_payload, "score": result.score}
        count += 1
    session.flush()
    return count
