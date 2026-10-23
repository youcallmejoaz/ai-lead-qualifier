"""BM25 keyword search over the help docs.

Ten short articles do not need embeddings: keyword search is deterministic, needs no
extra API key, and returns exact passages to cite. Implement `search` on another
class to swap in a vector store later.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import DATA_DIR

_STOPWORDS = set(
    "a an and are as at be but by can do does for from has have how i if in is it its me my "
    "of on or our so that the their them then there this to us was we what when where which "
    "who why will with you your yours".split()
)


# Everyday words clients use for things the articles name differently.
_SYNONYMS = {
    "colleague": ["team", "member", "invite"],
    "cost": ["charge", "fee"],
    "charged": ["billed"],
    "access": ["invite"],
    "broken": ["fail"],
    "error": ["fail"],
    "holiday": ["hours"],
    "christmas": ["holiday", "hours"],
    "excel": ["export"],
    "sso": ["single", "sign"],
}


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if len(word) > 3 and word[-1] == word[-2]:
        word = word[:-1]
    return word


def tokenize(text: str, expand: bool = False) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]
    if expand:
        words += [syn for w in words for syn in _SYNONYMS.get(w, [])]
    return [_stem(w) for w in words]


@dataclass(frozen=True)
class Passage:
    id: str  # e.g. HD02-3
    doc_id: str  # e.g. HD02
    doc_title: str
    section: str
    text: str


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


def load_passages(folder: Path) -> list[Passage]:
    passages: list[Passage] = []
    for path in sorted(folder.glob("*.md")):
        doc_id = path.stem.split("_", 1)[0]
        lines = path.read_text().splitlines()
        title = lines[0].lstrip("# ").strip()
        section, buf, n = None, [], 0
        for line in lines[1:] + ["## "]:
            if line.startswith("## "):
                if section and buf:
                    n += 1
                    passages.append(Passage(f"{doc_id}-{n}", doc_id, title, section, " ".join(buf).strip()))
                section, buf = line[3:].strip(), []
            elif line.strip():
                buf.append(line.strip().lstrip("- "))
    return passages


class HelpDocRetriever:
    def __init__(self, folder: Path = DATA_DIR / "help_docs"):
        self.passages = load_passages(folder)
        corpus = [tokenize(f"{p.doc_title} {p.section} {p.text}") for p in self.passages]
        self._bm25 = BM25Okapi(corpus)

    def search(self, query: str, k: int = 4) -> list[Hit]:
        scores = self._bm25.get_scores(tokenize(query, expand=True))
        ranked = sorted(zip(self.passages, scores), key=lambda x: x[1], reverse=True)
        return [Hit(p, float(s)) for p, s in ranked[:k] if s > 0]

    def get(self, passage_id: str) -> Passage | None:
        return next((p for p in self.passages if p.id == passage_id), None)
