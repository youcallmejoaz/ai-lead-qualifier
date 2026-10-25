"""Scripted stand in for Claude (LLM_MODE=scripted).

Answers from data/demo_outputs.json, which holds hand written outputs for the sample
enquiries. Used to run and record the demo before the real run with an API key.
Real recorded outputs in data/llm_cache.json are never mixed with these.
"""

import json
import re
from pathlib import Path

from app.config import DATA_DIR
from app.llm.client import LLMUnavailable

DEMO_PATH = DATA_DIR / "demo_outputs.json"


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


class ScriptedLLM:
    def __init__(self, path: Path = DEMO_PATH):
        self.by_subject = json.loads(path.read_text())["by_subject"]

    def generate_json(self, *, purpose, model, system, user, schema, effort, max_tokens) -> str:
        match = re.search(r"<subject>(.*?)</subject>", user, re.S)
        entry = self.by_subject.get(match.group(1) if match else "")
        if entry is None or purpose not in entry:
            raise LLMUnavailable(f"No scripted {purpose} output for this email")
        out = dict(entry[purpose])
        if purpose == "support_draft":
            # Point each quote at the supplied passage that contains it, as the model would.
            passages = re.findall(r'<passage id="([^"]+)"[^>]*>\n(.*?)\n</passage>', user, re.S)
            citations = []
            for quote in out.pop("quotes"):
                pid = next((p for p, text in passages if _norm(quote) in _norm(text)), None)
                if pid:
                    citations.append({"doc_id": pid, "quote": quote})
            out["citations"] = citations
        return json.dumps(out)
