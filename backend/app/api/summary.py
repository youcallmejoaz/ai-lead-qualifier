"""Weekly summary numbers."""

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CrmRecord, Message, ReviewItem
from app.settings_store import get_setting


def weekly_summary(session: Session) -> dict[str, Any]:
    latest = session.scalar(select(func.max(Message.received_at)))
    if latest is None:
        return {"empty": True}
    # The demo data is a fixed week, so count back from the newest message, not from today.
    start = latest - timedelta(days=7)
    msgs = [m for m in session.scalars(select(Message)) if m.received_at.replace(tzinfo=latest.tzinfo) > start]
    processed = [m for m in msgs if m.classification]
    by_cat = Counter(m.classification.category for m in processed)
    items = [m.review_item for m in processed if m.review_item]
    by_status = Counter(i.status for i in items)
    minutes = get_setting(session, "minutes_per_enquiry")
    days = Counter(m.received_at.date().isoformat() for m in msgs)
    return {
        "empty": False,
        "week_start": start.date().isoformat(),
        "week_end": latest.date().isoformat(),
        "enquiries_in": len(msgs),
        "processed": len(processed),
        "by_category": {k: by_cat.get(k, 0) for k in ("Sales", "Support", "Spam", "Other")},
        "qualified_leads": sum(1 for m in processed if m.lead and m.lead.qualified),
        "crm_records": session.scalar(select(func.count(CrmRecord.id))),
        "duplicates_merged": session.scalar(select(func.coalesce(func.sum(CrmRecord.merge_count), 0))),
        "drafts": {
            "pending": by_status.get("pending", 0),
            "approved": by_status.get("approved", 0),
            "rejected": by_status.get("rejected", 0),
            "edited": sum(1 for i in items if i.edited_body is not None),
            "auto_approved": sum(1 for i in items if i.decided_by == "auto"),
        },
        "amber_flagged": sum(1 for i in items if i.amber),
        "injection_flagged": sum(1 for m in processed if m.classification.injection_flag),
        "per_day": [{"date": d, "count": days[d]} for d in sorted(days)],
        # Placeholder: minutes of manual triage per enquiry is a setting, not a measurement.
        "time_saved_hours": round(len(processed) * minutes / 60, 1),
        "minutes_per_enquiry": minutes,
        "time_saved_is_placeholder": True,
    }
