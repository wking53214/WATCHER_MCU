"""Narrators for Groq, Gemini and Cloudflare Workers AI, beside the Claude one in `narrate.py`.

All three providers publish an OpenAI-compatible endpoint, so each narrator is the official `openai` SDK
pointed at that provider's address. Each takes the same `narrate(system, prompt, model, effort)` call and
returns text; the text then goes through the same oath as any other narrator's, so the model is trusted to write,
never to be right. The SDK is imported only when a narrator runs, so `--no-model` and the Claude path need
neither it nor this module's dependency. `effort` is a Claude setting and is not sent. Keys come from the
environment and never appear in an error. Any failure is a `ModelResponseError`, which the CLI reports as
"no model could be reached".
"""

from __future__ import annotations

import os
from typing import Any

from .narrate import ModelResponseError

#: Smaller than the Claude limit: hosted open models commonly cap output lower.
MAX_TOKENS = 8000
TIMEOUT_S = 120.0
PROVIDERS = ("anthropic", "groq", "gemini", "cloudflare")
_KEYS = {"groq": ("GROQ_API_KEY",), "gemini": ("GEMINI_API_KEY",),
         "cloudflare": ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")}


def credentials_for(provider: str) -> bool:
    """Whether the environment holds what `provider` needs, without making a request."""
    return all(os.environ.get(name, "").strip() for name in _KEYS[provider])


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or any(c in value for c in " \r\n\t"):
        raise ModelResponseError(f"{name} is not set")
    return value


class _CompatNarrator:
    _name = ""
    _base_url = ""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def _address(self) -> str:
        return self._base_url

    def _key(self) -> str:
        return _env(_KEYS[self._name][0])

    def _get(self) -> Any:
        if self._client is None:
            import openai  # imported here so the other paths need no SDK
            self._client = openai.OpenAI(api_key=self._key(), base_url=self._address(), timeout=TIMEOUT_S,
                                         max_retries=0)
        return self._client

    def narrate(self, system: str, prompt: str, model: str, effort: str) -> str:
        client = self._get()
        try:
            reply = client.chat.completions.create(
                model=model, max_tokens=MAX_TOKENS,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
        except ModelResponseError:
            raise
        except Exception as err:  # the SDK's own errors (status, connection, timeout) have no common base but this
            # The class name and HTTP status only: an SDK error's text can echo a request.
            status = getattr(err, "status_code", None)
            raise ModelResponseError(f"{self._name} request failed ({type(err).__name__}"
                                     f"{'' if status is None else f', HTTP {status}'})") from None
        try:
            (choice,) = reply.choices
            text, reason = choice.message.content, choice.finish_reason
        except (AttributeError, TypeError, ValueError):
            raise ModelResponseError("the response is not a chat completion") from None
        if not isinstance(text, str):
            raise ModelResponseError("the response holds no text")
        if reason == "length":
            raise ModelResponseError("the answer was cut off at the output limit")
        return text


class GroqNarrator(_CompatNarrator):
    _name = "groq"
    _base_url = "https://api.groq.com/openai/v1"


class GeminiNarrator(_CompatNarrator):
    _name = "gemini"
    _base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"


class CloudflareNarrator(_CompatNarrator):
    _name = "cloudflare"

    def _address(self) -> str:
        account = _env("CLOUDFLARE_ACCOUNT_ID")
        if not account.isalnum():
            raise ModelResponseError("CLOUDFLARE_ACCOUNT_ID is not plain letters and digits")
        return f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1"

    def _key(self) -> str:
        return _env("CLOUDFLARE_API_TOKEN")


def narrator_for(provider: str) -> Any:
    return {"groq": GroqNarrator, "gemini": GeminiNarrator, "cloudflare": CloudflareNarrator}[provider]()
