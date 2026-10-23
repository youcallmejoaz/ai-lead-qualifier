"""App settings kept in the database, with defaults."""

from typing import Any

from sqlalchemy.orm import Session

from app.models import Setting
from app.pipeline.scoring import load_icp

DEFAULTS: dict[str, Any] = {
    # Off by default: every draft and CRM write waits for a click.
    "auto_approve_enabled": False,
    "auto_approve_threshold": 0.92,
    # Below this classification confidence an item is flagged amber.
    "amber_threshold": 0.7,
    # Below this, an extracted field counts as unsure.
    "field_confidence_threshold": 0.5,
    # Placeholder for the weekly summary, not a measured number.
    "minutes_per_enquiry": 6,
}


def get_setting(session: Session, key: str) -> Any:
    row = session.get(Setting, key)
    if row is not None:
        return row.value
    if key == "icp":
        return load_icp()
    return DEFAULTS[key]


def set_setting(session: Session, key: str, value: Any) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
    session.flush()


def all_settings(session: Session) -> dict[str, Any]:
    values = {key: get_setting(session, key) for key in DEFAULTS}
    values["icp"] = get_setting(session, "icp")
    return values
