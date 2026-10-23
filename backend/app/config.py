"""Runtime configuration, read from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    database_url: str = field(
        default_factory=lambda: os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
    )
    classify_model: str = field(default_factory=lambda: os.environ.get("CLASSIFY_MODEL", "claude-haiku-5-5"))
    draft_model: str = field(default_factory=lambda: os.environ.get("DRAFT_MODEL", "claude-sonnet-5-5"))
    # "live": call Claude on a cache miss. "cache": never call Claude, cached results only.
    llm_mode: str = field(default_factory=lambda: os.environ.get("LLM_MODE", "live"))
    # 0 means no cap. Set on public deployments.
    daily_call_limit: int = field(default_factory=lambda: int(os.environ.get("DAILY_CALL_LIMIT", "0")))
    demo_mode: bool = field(default_factory=lambda: _env_bool("DEMO_MODE", True))
    data_dir: Path = DATA_DIR
    cache_path: Path = field(
        default_factory=lambda: Path(os.environ.get("LLM_CACHE_PATH", DATA_DIR / "llm_cache.json"))
    )

    @property
    def has_api_key(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_config() -> Config:
    return Config()
