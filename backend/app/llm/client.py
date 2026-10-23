"""Claude client that returns structured JSON, with a response cache in front."""

import logging
from typing import Any, Protocol

import anthropic

from app.llm.cache import ResponseCache, cache_key

log = logging.getLogger(__name__)

# Models that accept the server side refusal fallback on the Claude API.
_FALLBACK_MODELS = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1")


class LLMUnavailable(RuntimeError):
    """No cached answer and no way to call Claude (no key, or cache only mode)."""


class LLMError(RuntimeError):
    """Claude answered, but not with something usable (refusal, cut off, empty)."""


class LLMClient(Protocol):
    def generate_json(
        self,
        *,
        purpose: str,
        model: str,
        system: str,
        user: str,
        schema: dict[str, Any],
        effort: str,
        max_tokens: int,
    ) -> str: ...


class ClaudeClient:
    def __init__(self, cache: ResponseCache, *, live: bool, has_key: bool):
        self.cache = cache
        self.live = live
        self.has_key = has_key
        self._client: anthropic.Anthropic | None = None

    def _sdk(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(max_retries=4)
        return self._client

    def generate_json(self, *, purpose, model, system, user, schema, effort, max_tokens) -> str:
        key = cache_key({"model": model, "system": system, "user": user, "schema": schema, "effort": effort})
        cached = self.cache.get(key)
        if cached is not None:
            return cached["output"]
        if not self.live or not self.has_key:
            raise LLMUnavailable(f"No cached {purpose} result and live calls are off")

        request = dict(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if model.startswith(_FALLBACK_MODELS):
                response = self._sdk().beta.messages.create(
                    **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                response = self._sdk().messages.create(**request)
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code} during {purpose}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Could not reach the Claude API during {purpose}") from exc

        if response.stop_reason == "refusal":
            raise LLMError(f"Claude declined the {purpose} request")
        if response.stop_reason == "max_tokens":
            raise LLMError(f"The {purpose} response was cut off")
        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text:
            raise LLMError(f"Empty {purpose} response")

        usage = response.usage
        self.cache.put(
            key,
            {
                "purpose": purpose,
                "model": response.model,
                "output": text,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        )
        log.info("%s call done (%s in / %s out tokens)", purpose, usage.input_tokens, usage.output_tokens)
        return text
