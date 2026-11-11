"""The generic port: one model call made through the Watcher's SDK path for another component.

This is a transport boundary and nothing more. The Watcher owns the credentials, the SDK call, the size limits,
the mapping of a refusal and of a failure, and the provenance of the answer. It does NOT apply the oath, filter,
grade or interpret the text: the cite-or-drop rule belongs to narration (`watcher.oath`) and is not used here. No
tools, no streaming, no files. Both sides are plain JSON-shaped mappings, so the caller imports nothing of the Watcher.

The call, `complete(mapping)`, takes exactly these keys (any other key is refused, and nothing is sent):

  instructions       str, may be empty (an empty one sends no system prompt)
  inputs             non-empty list of non-empty str; sent as one user message, joined by a blank line
  model              non-empty str
  max_output_tokens  int from 1 to MAX_OUTPUT_TOKENS
  effort             optional, one of EFFORTS; DEFAULT_EFFORT when absent
  request_digest     non-empty str, opaque to the Watcher, echoed back

and returns a new mapping:

  text             str, the model's text, unfiltered
  provider_id      "watcher_mcu"
  provider_kind    "watcher_mcu"
  adapter_version  watcher.__version__
  model_requested  the `model` asked for
  model_reported   the model the API says answered, or None when it does not say
  finish_reason    the API's stop reason, or "unknown"
  usage            {"input_tokens": int, "output_tokens": int}, or None when the API reports no counts
  request_digest   the echo
  response_digest  SHA-256 (hex) of `text` as UTF-8
  is_live          True

A failure is one of four exceptions, each with a stable string `code`:

  PortFormatError  "format"       the mapping has not the shape above; nothing was sent
  PortTooLarge     "too_large"    instructions and inputs exceed MAX_INPUT_BYTES of UTF-8, or max_output_tokens
                                  exceeds MAX_OUTPUT_TOKENS; nothing was sent
  PortRefused      "refused"      the model declined (`watcher.narrate.Refused`)
  PortUnavailable  "unavailable"  no credentials, or an SDK error (connection, timeout, status), or a response that
                                  cannot be decoded or is not a message (`ModelResponseError`)

The message of a PortUnavailable raised for an SDK error names the error's type (and HTTP status when it has one) and
never repeats its text. Any other exception is a defect and is not caught.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Protocol

from . import __version__
from .cli import EFFORTS, _model_errors
from .narrate import DEFAULT_EFFORT, MAX_TOKENS, AnthropicNarrator, ModelResponseError, Refused, credentials_present

PROVIDER = "watcher_mcu"
#: The most UTF-8 bytes `instructions` and `inputs` may hold together.
MAX_INPUT_BYTES = 200_000
#: The most output tokens a caller may ask for: the limit a narration runs under.
MAX_OUTPUT_TOKENS = MAX_TOKENS
_REQUIRED = frozenset({"instructions", "inputs", "model", "max_output_tokens", "request_digest"})
_ALLOWED = _REQUIRED | {"effort"}


class PortError(RuntimeError):
    """A failure of the port. `code` is stable and is what a caller in another repository reads."""

    code = "error"


class PortFormatError(PortError):
    code = "format"


class PortTooLarge(PortError):
    code = "too_large"


class PortRefused(PortError):
    code = "refused"


class PortUnavailable(PortError):
    code = "unavailable"


class PortNarrator(Protocol):
    def complete(self, system: str | None, prompt: str, model: str, effort: str, max_tokens: int) -> dict[str, Any]: ...


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PortFormatError(f"{name} must be a non-empty string")
    return value


def _checked(request: Any) -> tuple[str, list[str], str, int, str, str]:
    if not isinstance(request, Mapping):
        raise PortFormatError("the request must be a mapping")
    keys = set(request)
    if keys - _ALLOWED:
        raise PortFormatError(f"unknown key(s): {', '.join(sorted(map(repr, keys - _ALLOWED)))}")
    if _REQUIRED - keys:
        raise PortFormatError(f"missing key(s): {', '.join(sorted(_REQUIRED - keys))}")
    instructions, inputs, tokens = request["instructions"], request["inputs"], request["max_output_tokens"]
    if not isinstance(instructions, str):
        raise PortFormatError("instructions must be a string")
    if not isinstance(inputs, list) or not inputs or not all(isinstance(item, str) and item for item in inputs):
        raise PortFormatError("inputs must be a non-empty list of non-empty strings")
    if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 1:
        raise PortFormatError("max_output_tokens must be a positive integer")
    effort = request.get("effort", DEFAULT_EFFORT)
    if effort not in EFFORTS:
        raise PortFormatError(f"effort must be one of {', '.join(EFFORTS)}")
    model, echo = _text(request["model"], "model"), _text(request["request_digest"], "request_digest")
    if tokens > MAX_OUTPUT_TOKENS:
        raise PortTooLarge(f"max_output_tokens is {tokens}; the most is {MAX_OUTPUT_TOKENS}")
    try:
        size = sum(len(part.encode("utf-8")) for part in (instructions, *inputs))
    except UnicodeEncodeError as err:
        raise PortFormatError("instructions and inputs must be text that encodes as UTF-8") from err
    if size > MAX_INPUT_BYTES:
        raise PortTooLarge(f"instructions and inputs are {size} bytes; the most is {MAX_INPUT_BYTES}")
    return instructions, list(inputs), model, tokens, effort, echo


def complete(request: Mapping[str, Any], narrator: PortNarrator | None = None) -> dict[str, Any]:
    """Send one request (the mapping in the module docstring) and return the response mapping, or raise a PortError.
    `narrator` is for tests; without one the SDK narrator is used, and only when credentials are present."""
    instructions, inputs, model, tokens, effort, echo = _checked(request)
    if narrator is None:
        if not credentials_present():
            raise PortUnavailable("no credentials are configured for the model")
        narrator = AnthropicNarrator()
    try:
        got = narrator.complete(instructions or None, "\n\n".join(inputs), model, effort, tokens)
    except Refused as err:
        raise PortRefused(str(err)) from err
    except ModelResponseError as err:
        raise PortUnavailable(str(err)) from err
    except _model_errors() as err:
        status = getattr(err, "status_code", None)
        said = f", status {status}" if isinstance(status, int) and not isinstance(status, bool) else ""
        raise PortUnavailable(f"the model could not be reached ({type(err).__name__}{said})") from err
    text = got.get("text") if isinstance(got, Mapping) else None
    try:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None
    except UnicodeEncodeError:
        digest = None
    if not isinstance(got, Mapping) or not isinstance(text, str) or digest is None:
        raise PortUnavailable("the model's answer holds no text that encodes as UTF-8")
    return {
        "text": text,
        "provider_id": PROVIDER,
        "provider_kind": PROVIDER,
        "adapter_version": __version__,
        "model_requested": model,
        "model_reported": got.get("model"),
        "finish_reason": got.get("stop_reason") or "unknown",
        "usage": got.get("usage"),
        "request_digest": echo,
        "response_digest": digest,
        "is_live": True,
    }


__all__ = [
    "MAX_INPUT_BYTES",
    "MAX_OUTPUT_TOKENS",
    "PROVIDER",
    "PortError",
    "PortFormatError",
    "PortNarrator",
    "PortRefused",
    "PortTooLarge",
    "PortUnavailable",
    "complete",
]
