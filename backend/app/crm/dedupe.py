"""Duplicate matching for CRM records, by email and by company."""

import re
from collections.abc import Iterable
from typing import Protocol

FREE_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com",
    "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.com",
    "freemail.example",  # used by the sample data
}

_SUFFIXES = {
    "ltd", "limited", "inc", "incorporated", "llc", "llp", "plc", "gmbh", "co", "company",
    "corp", "corporation", "group", "holdings", "the", "and",
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_domain(email: str) -> str:
    return normalize_email(email).rsplit("@", 1)[-1]


def company_key(name: str | None) -> str:
    """'The Harbour Logistics Ltd.' and 'harbour logistics limited' -> 'harbour logistics'."""
    if not name:
        return ""
    words = re.sub(r"[^a-z0-9 ]+", " ", name.lower().replace("&", " and ")).split()
    return " ".join(w for w in words if w not in _SUFFIXES)


class Matchable(Protocol):
    company_key: str
    primary_email: str
    contacts: list


def _emails(record: Matchable) -> set[str]:
    emails = {normalize_email(record.primary_email)}
    emails.update(normalize_email(c["email"]) for c in record.contacts or [])
    return emails


def find_match(records: Iterable[Matchable], email: str, company: str | None) -> tuple[Matchable | None, str]:
    """Return (record, reason) for the record this lead duplicates, or (None, "")."""
    records = list(records)
    email_n = normalize_email(email)
    for record in records:
        if email_n in _emails(record):
            return record, "same email"
    key = company_key(company)
    if key:
        for record in records:
            if record.company_key == key:
                return record, "same company"
    domain = email_domain(email_n)
    if domain not in FREE_MAIL_DOMAINS:
        for record in records:
            if any(email_domain(e) == domain for e in _emails(record)):
                return record, "same company domain"
    return None, ""
