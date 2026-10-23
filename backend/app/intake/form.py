"""Website contact form intake."""

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.models import Message


class ContactForm(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    company: str | None = Field(default=None, max_length=200)
    subject: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=1, max_length=10000)


def create_from_form(session: Session, form: ContactForm) -> Message:
    msg = Message(
        source="form",
        from_name=form.name.strip(),
        from_email=str(form.email).strip(),
        company=(form.company or "").strip() or None,
        subject=form.subject.strip(),
        body=form.message.strip(),
        status="new",
    )
    session.add(msg)
    session.flush()
    return msg
