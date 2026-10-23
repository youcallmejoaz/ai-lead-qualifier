"""Approval tokens: proof that a review item was approved.

The CRM adapters and the outbox refuse to write without a token, and tokens are
only issued by the review service when a person clicks Approve (or when the
optional auto approve rule allows it). This keeps the "nothing final without a
click" rule in one place instead of trusting every caller.
"""

from dataclasses import dataclass, field

_SECRET = object()


class ApprovalRequired(PermissionError):
    pass


@dataclass(frozen=True)
class Approval:
    review_item_id: int
    decided_by: str  # "person" | "auto"
    _seal: object = field(repr=False, compare=False, default=None)


def issue(review_item_id: int, decided_by: str) -> Approval:
    return Approval(review_item_id=review_item_id, decided_by=decided_by, _seal=_SECRET)


def verify(approval: object, review_item_id: int | None = None) -> Approval:
    if not isinstance(approval, Approval) or approval._seal is not _SECRET:
        raise ApprovalRequired("This write needs an approval from the review queue")
    if review_item_id is not None and approval.review_item_id != review_item_id:
        raise ApprovalRequired("Approval was issued for a different review item")
    return approval
