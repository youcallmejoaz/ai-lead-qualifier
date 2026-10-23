"""Run all 80 sample enquiries through Claude and record the outputs.

Usage (needs ANTHROPIC_API_KEY):
    .venv/bin/python scripts/run_pipeline.py

Fills data/llm_cache.json (cache hits are free, so re-running only pays for
changed prompts) and writes data/run_report.md with accuracy and token cost.
"""

import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_config  # noqa: E402
from app.drafts.retriever import HelpDocRetriever  # noqa: E402
from app.intake.inbox_sim import load_enquiries  # noqa: E402
from app.llm.cache import ResponseCache  # noqa: E402
from app.llm.client import ClaudeClient  # noqa: E402
from app.pipeline.process import MessageIn, Pipeline  # noqa: E402
from app.pipeline.scoring import load_icp  # noqa: E402
from app.settings_store import DEFAULTS  # noqa: E402

# USD per million tokens (input, output). Check current pricing before quoting.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}


def main() -> None:
    config = get_config()
    cache = ResponseCache(config.cache_path)
    before = len(cache)
    llm = ClaudeClient(cache, live=True, has_key=config.has_api_key)
    pipeline = Pipeline(llm, HelpDocRetriever(), config)
    settings = {**DEFAULTS, "icp": load_icp()}
    enquiries = load_enquiries()

    def run(item):
        i, e = item
        msg = MessageIn(i, e["from_name"], e["from_email"], e["company"], e["subject"], e["body"])
        return e, pipeline.analyse(msg, settings)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(run, enumerate(enquiries, 1)))

    confusion = Counter()
    rows = []
    for e, a in results:
        got = a.triage.category
        confusion[(e["expected"], got)] += 1
        rows.append(
            f"| {e['id']} | {e['expected']} | {got} | {a.triage.confidence:.2f} | {a.score.score} | "
            f"{'yes' if a.score.qualified else ''} | {', '.join(a.flags)} | {a.triage.reason} |"
        )
    correct = sum(n for (exp, got), n in confusion.items() if exp == got)

    tokens = Counter()
    for entry in cache._data.values():
        model = next((m for m in PRICES if entry.get("model", "").startswith(m)), None)
        if model:
            tokens[(model, "in")] += entry.get("input_tokens", 0)
            tokens[(model, "out")] += entry.get("output_tokens", 0)
    cost = sum(tokens[(m, "in")] / 1e6 * p[0] + tokens[(m, "out")] / 1e6 * p[1] for m, p in PRICES.items())

    report = [
        "# Run report: 80 sample enquiries",
        "",
        f"Classification accuracy against the hand labels: **{correct}/80**",
        "",
        "| Expected | Got | Count |",
        "|---|---|---|",
        *[f"| {exp} | {got} | {n} |" for (exp, got), n in sorted(confusion.items())],
        "",
        "Token use for every recorded call (estimate at list prices, check current pricing):",
        "",
        *[f"- {m}: {tokens[(m, 'in')]:,} input, {tokens[(m, 'out')]:,} output tokens" for m in PRICES],
        f"- Estimated total: ${cost:.2f} for all 80 enquiries",
        "",
        "| ID | Expected | Got | Conf | Score | Qualified | Flags | Reason |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    (config.data_dir / "run_report.md").write_text("\n".join(report))
    print(f"accuracy {correct}/80, new cache entries {len(cache) - before}, est cost ${cost:.2f}")


if __name__ == "__main__":
    main()
