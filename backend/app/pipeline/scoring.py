"""Rule based lead scoring against the editable ideal customer profile.

Claude extracts the signals; this module turns them into a 0 to 100 score.
Keeping the arithmetic in code makes scores repeatable and testable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import DATA_DIR
from app.llm.schemas import LeadFields

DEFAULT_ICP_PATH = DATA_DIR / "icp.yaml"


def load_icp(path: Path = DEFAULT_ICP_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def parse_icp(text: str) -> dict[str, Any]:
    """Parse ICP YAML from the settings page and check it has what scoring needs."""
    icp = yaml.safe_load(text)
    if not isinstance(icp, dict):
        raise ValueError("ICP must be a YAML mapping")
    for key in ("qualify_threshold", "weights", "industry", "company_size", "budget", "urgency"):
        if key not in icp:
            raise ValueError(f"ICP is missing '{key}'")
    total = sum(icp["weights"].values())
    if total != 100:
        raise ValueError(f"ICP weights must add up to 100 (got {total})")
    return icp


@dataclass
class ScoreResult:
    score: int
    breakdown: list[dict[str, Any]]
    qualified: bool


def _industry_factor(value: str | None, cfg: dict[str, Any]) -> tuple[float, str]:
    if not value:
        return cfg["unknown_score"], "not stated"
    text = value.lower()
    if any(term in text for term in cfg["target"]):
        return cfg["target_score"], "target industry"
    if any(term in text for term in cfg["adjacent"]):
        return cfg["adjacent_score"], "adjacent industry"
    return cfg["other_score"], "outside target industries"


def _size_factor(employees: int | None, cfg: dict[str, Any]) -> tuple[float, str]:
    if employees is None:
        return cfg["unknown_score"], "not stated"
    if employees < cfg["min"]:
        return cfg["below_min_score"], f"{employees} staff, below minimum"
    if employees < cfg["ideal_min"]:
        return cfg["small_score"], f"{employees} staff, smaller than ideal"
    if employees <= cfg["ideal_max"]:
        return cfg["ideal_score"], f"{employees} staff, ideal size"
    return cfg["above_ideal_score"], f"{employees} staff, larger than ideal"


def _budget_factor(usd: int | None, cfg: dict[str, Any]) -> tuple[float, str]:
    if usd is None:
        return cfg["unknown_score"], "no budget mentioned"
    if usd < cfg["min_usd"]:
        return cfg["below_min_score"], f"${usd:,} is below the ${cfg['min_usd']:,} minimum"
    if usd >= cfg["ideal_usd"]:
        return 1.0, f"${usd:,} meets the ideal budget"
    span = cfg["ideal_usd"] - cfg["min_usd"]
    factor = 0.5 + 0.5 * (usd - cfg["min_usd"]) / span
    return factor, f"${usd:,} is within range"


def _urgency_factor(value: str, cfg: dict[str, Any]) -> tuple[float, str]:
    return cfg.get(value, cfg["unknown"]), f"{value} urgency"


def score_lead(fields: LeadFields, icp: dict[str, Any], is_sales: bool = True) -> ScoreResult:
    weights = icp["weights"]
    parts = {
        "industry": _industry_factor(fields.industry.value, icp["industry"]),
        "company_size": _size_factor(fields.company_size.value, icp["company_size"]),
        "budget": _budget_factor(fields.budget_usd.value, icp["budget"]),
        "urgency": _urgency_factor(fields.urgency.value, icp["urgency"]),
    }
    breakdown = []
    total = 0.0
    for name, (factor, note) in parts.items():
        points = weights[name] * factor
        total += points
        breakdown.append(
            {"factor": name, "points": round(points, 1), "max": weights[name], "note": note}
        )
    score = max(0, min(100, round(total)))
    return ScoreResult(
        score=score,
        breakdown=breakdown,
        qualified=is_sales and score >= icp["qualify_threshold"],
    )
