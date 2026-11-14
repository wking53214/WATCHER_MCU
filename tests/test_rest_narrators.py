"""The Groq, Gemini and Cloudflare narrators: request shape, reading, and failure, with no network."""

from types import SimpleNamespace

import openai
import pytest

from watcher import rest_narrators as rn
from watcher.narrate import ModelResponseError


def _client(text="ok [R]", reason="stop", error=None, seen=None):
    def create(**kw):
        if seen is not None:
            seen.update(kw)
        if error:
            raise error
        msg = SimpleNamespace(content=text)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=reason)])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.mark.parametrize("cls", [rn.GroqNarrator, rn.GeminiNarrator, rn.CloudflareNarrator])
def test_request_and_reading(cls):
    seen = {}
    assert cls(_client(seen=seen)).narrate("sys", "prompt", "m", "high") == "ok [R]"
    assert seen["model"] == "m" and seen["messages"] == [{"role": "system", "content": "sys"},
                                                         {"role": "user", "content": "prompt"}]
    assert "effort" not in seen


def test_each_provider_points_the_sdk_at_its_own_address(monkeypatch):
    made = {}
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: made.update(kw) or _client())
    monkeypatch.setenv("GROQ_API_KEY", "gsk-1")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-1")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cf-1")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct1")
    for cls, key, url in ((rn.GroqNarrator, "gsk-1", "https://api.groq.com/openai/v1"),
                          (rn.GeminiNarrator, "AIza-1", "https://generativelanguage.googleapis.com/v1beta/openai/"),
                          (rn.CloudflareNarrator, "cf-1",
                           "https://api.cloudflare.com/client/v4/accounts/acct1/ai/v1")):
        cls().narrate("s", "p", "m", "high")
        assert made["api_key"] == key and made["base_url"] == url and made["max_retries"] == 0


def test_a_cut_off_or_empty_answer_is_an_error():
    with pytest.raises(ModelResponseError, match="cut off"):
        rn.GroqNarrator(_client(reason="length")).narrate("s", "p", "m", "high")
    with pytest.raises(ModelResponseError, match="no text"):
        rn.GroqNarrator(_client(text=None)).narrate("s", "p", "m", "high")


def test_sdk_errors_are_sanitized():
    err = RuntimeError("Bearer sk-topsecret leaked in text")
    err.status_code = 401
    with pytest.raises(ModelResponseError) as info:
        rn.GroqNarrator(_client(error=err)).narrate("s", "p", "m", "high")
    assert "topsecret" not in str(info.value) and "HTTP 401" in str(info.value)


def test_malformed_response_is_refused():
    bad = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: SimpleNamespace())))
    with pytest.raises(ModelResponseError, match="not a chat completion"):
        rn.GeminiNarrator(bad).narrate("s", "p", "m", "high")


def test_missing_key_and_credentials_for(monkeypatch):
    for name in ("GROQ_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        monkeypatch.delenv(name, raising=False)
    assert not rn.credentials_for("groq") and not rn.credentials_for("cloudflare")
    with pytest.raises(ModelResponseError, match="GROQ_API_KEY"):
        rn.GroqNarrator().narrate("s", "p", "m", "high")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert rn.credentials_for("groq")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "bad/id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
    with pytest.raises(ModelResponseError, match="plain"):
        rn.CloudflareNarrator().narrate("s", "p", "m", "high")


def test_cli_provider_needs_a_model_and_credentials(monkeypatch, capsys):
    from pathlib import Path

    from watcher.cli import main
    record = str(Path(__file__).parent / "fixtures" / "warden_0_13_2_record.json")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert main(["narrate", record, "--provider", "groq"]) == 2
    assert "needs --model" in capsys.readouterr().err
    assert main(["narrate", record, "--provider", "groq", "--model", "m"]) == 3
    assert "no groq credentials" in capsys.readouterr().err


def test_cli_provider_reaches_the_oath(monkeypatch, capsys):
    from pathlib import Path

    from watcher.cli import main
    record = str(Path(__file__).parent / "fixtures" / "warden_0_13_2_record.json")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    reply = "Held, unjudged [R].\nThis is production ready."
    monkeypatch.setattr("watcher.rest_narrators.narrator_for", lambda p: rn.GroqNarrator(_client(text=reply)))
    assert main(["narrate", record, "--provider", "groq", "--model", "m"]) == 0
    out = capsys.readouterr().out
    assert "Held, unjudged [R]." in out and "production ready" not in out.split("Dropped")[0]
