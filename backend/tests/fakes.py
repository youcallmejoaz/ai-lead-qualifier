"""A stand in for Claude used by the pipeline tests.

It answers from the `expected` labels in the sample data, so the tests check our
wiring (scoring, flags, review queue, CRM dedupe), not the model's judgement.
"""

import json
import re

from app.intake.inbox_sim import load_enquiries
from app.llm.client import LLMError


def _fields(e, strong):
    company = e["company"] or e["from_email"].split("@")[1].split(".")[0].replace("-", " ").title()
    if "Harbourline" in e["body"] or "harbourline" in e["from_email"].lower():
        company = "Harbourline Freight Ltd" if "Ltd" in e["body"] else "Harbourline Freight"
    budget = re.search(r"\$(\d+)k|\$([\d,]+)", e["body"])
    usd = None
    if budget:
        usd = int(budget.group(1)) * 1000 if budget.group(1) else int(budget.group(2).replace(",", ""))
    size = re.search(r"(\d[\d,]*) (?:person|people|staff|employees)", e["body"])
    conf = 0.9 if strong else 0.6
    return {
        "name": {"value": e["from_name"], "confidence": conf},
        "company": {"value": company, "confidence": conf},
        "need": {"value": e["subject"], "confidence": conf},
        "budget": {"value": budget.group(0) if budget else None, "confidence": conf if budget else 0.0},
        "budget_usd": {"value": usd, "confidence": conf if usd else 0.0},
        "timeline": {"value": "next month" if strong else None, "confidence": conf if strong else 0.0},
        "industry": {"value": "logistics" if strong else "other", "confidence": conf},
        "company_size": {"value": int(size.group(1).replace(",", "")) if size else None,
                         "confidence": conf if size else 0.0},
        "urgency": {"value": "high" if strong else "low", "confidence": conf},
    }


class FakeLLM:
    def __init__(self, fail_triage_for=(), fail_drafts=False):
        self.by_subject = {e["subject"]: e for e in load_enquiries()}
        self.fail_triage_for = set(fail_triage_for)
        self.fail_drafts = fail_drafts
        self.calls = []

    def generate_json(self, *, purpose, model, system, user, schema, effort, max_tokens):
        self.calls.append(purpose)
        subject = re.search(r"<subject>(.*?)</subject>", user, re.S).group(1)
        e = self.by_subject.get(subject)
        if purpose == "triage":
            if e is None or e["id"] in self.fail_triage_for:
                return "not json"
            strong = "weak" not in e["tags"]
            return json.dumps({
                "category": e["expected"],
                "confidence": 0.55 if "mixed" in e["tags"] else 0.95,
                "reason": f"Looks like {e['expected']}",
                "injection_suspected": "injection" in e["tags"],
                "fields": _fields(e, strong),
            })
        if self.fail_drafts:
            raise LLMError("boom")
        if purpose == "support_draft":
            ids = re.findall(r'<passage id="([^"]+)"', user)
            if "no_doc" in (e or {}).get("tags", []) or not ids:
                return json.dumps({"answerable": False, "subject": f"Re: {subject}",
                                   "reply": "A member of the team will follow up.", "citations": []})
            passage = re.search(r'<passage id="%s"[^>]*>\n(.*?)\n</passage>' % re.escape(ids[0]), user, re.S).group(1)
            first_sentence = passage.split(". ")[0]
            return json.dumps({"answerable": True, "subject": f"Re: {subject}", "reply": "Here is how.",
                               "citations": [{"doc_id": ids[0], "quote": first_sentence},
                                             {"doc_id": "HD99-1", "quote": "made up"}]})
        return json.dumps({"subject": f"Re: {subject}", "reply": "Thanks for getting in touch."})
