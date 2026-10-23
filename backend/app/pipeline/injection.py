"""Prompt injection guard for inbound email.

Two layers:
1. Email text is always wrapped as untrusted data before it reaches Claude, and the
   system prompt tells Claude never to follow instructions found inside it.
2. A heuristic scan flags emails that look like they are trying to steer the AI.
   Claude also reports `injection_suspected`. Either one flags the item, and a
   flagged item can never be auto approved.
"""

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("asks the AI to ignore its instructions",
     re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,30}\b(instructions?|rules|prompts?|guidelines)\b", re.I | re.S)),
    ("addresses the AI or assistant directly",
     re.compile(r"\b(dear|attention|note to|hey)\s+(ai|assistant|bot|language model|llm|classifier)\b", re.I)),
    ("mentions a system prompt",
     re.compile(r"\bsystem\s*prompt\b", re.I)),
    ("tries to set its own classification or score",
     re.compile(r"\b(classify|mark|label|tag|score|rate)\b.{0,30}\b(this|me|email|message|lead)\b.{0,40}\b(as|with|at)\b.{0,20}\b(sales|qualified|high priority|urgent|100|top)\b", re.I | re.S)),
    ("asks for automatic approval or sending",
     re.compile(r"\b(auto[- ]?approve|approve (this|it) automatically|send (this|the reply) without|skip (the )?review|bypass)\b", re.I)),
    ("asks the AI to reveal data",
     re.compile(r"\b(reveal|print|output|list|send me)\b.{0,30}\b(all|every|other)\b.{0,30}\b(emails?|contacts?|customers?|leads?|api keys?|passwords?)\b", re.I | re.S)),
    ("contains hidden role markers",
     re.compile(r"(<\s*/?\s*(system|assistant|instructions?)\s*>|\[\s*(system|inst)\s*\]|###\s*(system|instruction))", re.I)),
]


def scan(text: str) -> list[str]:
    """Return the reasons this text looks like a prompt injection (empty if none)."""
    return [label for label, pattern in _PATTERNS if pattern.search(text)]


def wrap_untrusted(subject: str, body: str, from_name: str, company: str | None) -> str:
    """Wrap an email as data. Closing tags inside the email are neutralised."""

    def clean(value: str) -> str:
        return re.sub(r"</?\s*untrusted_email\s*>", "[removed tag]", value, flags=re.I)

    return (
        "<untrusted_email>\n"
        f"<from_name>{clean(from_name)}</from_name>\n"
        f"<company_field>{clean(company or '')}</company_field>\n"
        f"<subject>{clean(subject)}</subject>\n"
        f"<body>\n{clean(body)}\n</body>\n"
        "</untrusted_email>"
    )
