"""Inbox simulator: loads the sample enquiries as unprocessed messages."""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.models import Message

ENQUIRIES_PATH = DATA_DIR / "enquiries.json"


def load_enquiries(path: Path = ENQUIRIES_PATH) -> list[dict]:
    return json.loads(path.read_text())


def seed_inbox(session: Session, path: Path = ENQUIRIES_PATH) -> int:
    """Add any sample enquiries not already in the database. Returns how many were added."""
    existing = set(session.scalars(select(Message.external_id)))
    added = 0
    for e in load_enquiries(path):
        if e["id"] in existing:
            continue
        session.add(
            Message(
                external_id=e["id"],
                source=e["source"],
                from_name=e["from_name"],
                from_email=e["from_email"],
                company=e["company"],
                subject=e["subject"],
                body=e["body"],
                received_at=datetime.fromisoformat(e["received_at"].replace("Z", "+00:00")),
                status="new",
            )
        )
        added += 1
    session.flush()
    return added
