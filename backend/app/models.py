"""Database tables."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Message(Base):
    """One inbound enquiry, from the contact form or the inbox."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(16))  # form | inbox | gmail
    from_name: Mapped[str] = mapped_column(String(200))
    from_email: Mapped[str] = mapped_column(String(320))
    company: Mapped[str | None] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new | processed | error

    classification: Mapped["Classification | None"] = relationship(
        back_populates="message", uselist=False, cascade="all, delete-orphan"
    )
    lead: Mapped["LeadExtraction | None"] = relationship(
        back_populates="message", uselist=False, cascade="all, delete-orphan"
    )
    review_item: Mapped["ReviewItem | None"] = relationship(
        back_populates="message", uselist=False, cascade="all, delete-orphan"
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    category: Mapped[str] = mapped_column(String(16))  # Sales | Support | Spam | Other
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    injection_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    injection_reasons: Mapped[list] = mapped_column(JSON, default=list)
    parse_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))

    message: Mapped[Message] = relationship(back_populates="classification")


class LeadExtraction(Base):
    """Fields pulled from the enquiry plus the rule based score."""

    __tablename__ = "lead_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    # {field: {"value": ..., "confidence": float}}
    fields: Mapped[dict] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    score_breakdown: Mapped[list] = mapped_column(JSON)
    qualified: Mapped[bool] = mapped_column(Boolean)

    message: Mapped[Message] = relationship(back_populates="lead")


class ReviewItem(Base):
    """A draft (and, for qualified leads, a CRM write) waiting for a person."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(16))  # sales | support
    subject: Mapped[str] = mapped_column(String(300))
    draft_body: Mapped[str] = mapped_column(Text)
    edited_body: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    crm_payload: Mapped[dict | None] = mapped_column(JSON)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | rejected
    decided_by: Mapped[str | None] = mapped_column(String(64))  # person | auto
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message: Mapped[Message] = relationship(back_populates="review_item")

    @property
    def amber(self) -> bool:
        from app.review.gate import is_amber

        return is_amber(self.flags or [])

    @property
    def final_body(self) -> str:
        return self.edited_body if self.edited_body is not None else self.draft_body


class CrmRecord(Base):
    """Mock CRM: one record per company, with every contact we have heard from."""

    __tablename__ = "crm_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(200))
    company_key: Mapped[str] = mapped_column(String(200), index=True)
    primary_name: Mapped[str] = mapped_column(String(200))
    primary_email: Mapped[str] = mapped_column(String(320))
    contacts: Mapped[list] = mapped_column(JSON, default=list)  # [{"name", "email"}]
    need: Mapped[str | None] = mapped_column(Text)
    budget: Mapped[str | None] = mapped_column(String(200))
    timeline: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(32), default="Qualified")
    source_message_ids: Mapped[list] = mapped_column(JSON, default=list)
    merge_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutboxEmail(Base):
    """Simulated outbound email. Only written by an approved review item."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), unique=True)
    to_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)


class AuditLog(Base):
    """What happened, without personal data."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
