import pytest

from app.llm.cache import ResponseCache, cache_key
from app.llm.client import ClaudeClient, LLMUnavailable

ARGS = dict(purpose="triage", model="claude-haiku-5-5", system="s", user="u", schema={"type": "object"},
            effort="low", max_tokens=10)


def key():
    return cache_key({k: ARGS[k] for k in ("model", "system", "user", "schema", "effort")})


def test_cache_hit_needs_no_key(tmp_path):
    cache = ResponseCache(tmp_path / "c.json")
    cache.put(key(), {"output": '{"ok": true}'})
    client = ClaudeClient(ResponseCache(tmp_path / "c.json"), live=True, has_key=False)
    assert client.generate_json(**ARGS) == '{"ok": true}'


def test_cache_miss_without_key_raises(tmp_path):
    client = ClaudeClient(ResponseCache(tmp_path / "c.json"), live=True, has_key=False)
    with pytest.raises(LLMUnavailable):
        client.generate_json(**ARGS)


def test_cache_only_mode_never_calls_claude(tmp_path):
    client = ClaudeClient(ResponseCache(tmp_path / "c.json"), live=False, has_key=True)
    with pytest.raises(LLMUnavailable):
        client.generate_json(**ARGS)


def test_changed_prompt_is_a_cache_miss():
    a = cache_key({"model": "m", "system": "v1", "user": "u"})
    b = cache_key({"model": "m", "system": "v2", "user": "u"})
    assert a != b
