"""CRM adapter interface. Swap MockCRM for a real CRM by implementing this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.review.approval import Approval


@dataclass
class LeadPayload:
    """The clean fields we push to the CRM for a qualified lead."""

    name: str
    email: str
    company: str
    need: str | None
    budget: str | None
    timeline: str | None
    score: int
    message_id: int

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class UpsertResult:
    record_id: int
    merged: bool
    match_reason: str


class CRMAdapter(ABC):
    @abstractmethod
    def upsert_lead(self, payload: LeadPayload, approval: Approval) -> UpsertResult:
        """Create the lead, or merge it into the matching record. Requires an approval."""
