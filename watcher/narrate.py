"""The narrator: Claude, asked to describe a run and told the oath.

The model sees the citation index and nothing else: no files, no diff, no instrument, no seat. It
is asked for plain prose where every sentence carries an id in square brackets. What it says is
then put through `watcher.oath.enforce`; the model is trusted to write well, never to be right.

Without a model (no credentials, or `--no-model`) `template()` writes the same kind of account from
the index alone, one cited bullet per fact. That path is deterministic and is what the tests use.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from .evidence import Evidence

log = logging.getLogger(__name__)

#: The default model. Any current Claude model id works; pass --model to choose.
DEFAULT_MODEL = "claude-fable-5-1"
DEFAULT_EFFORT = "high"

SYSTEM = """You are the Watcher for a code-governance circuit. You see the record of one run and you \
are sworn not to interfere: you describe, you never grade. Nothing you write reaches the governor, \
the judge or the scanner. A person reads it to understand what happened.

Rules you must follow, because a filter enforces them after you write:
1. Every sentence must cite at least one id from the record, in square brackets, like [N3] or \
[ghost-1b3766cb418b]. A sentence without a citation is deleted. A citation that is not in the record \
deletes the sentence.
2. Never make a status claim of your own. Do not write "production ready", "production-grade", "ready for \
production", "battle-tested", "fully tested", "enterprise grade", "100% coverage", "safe", "secure", \
"bulletproof", "hardened", "reliable", "robust", "trustworthy", "approved", "LGTM", "looks good", \
"ship it", "good to go", "all clear" or "no issues" in your own voice, in any form, in any alphabet. A plain \
denial that cites the record ("nothing was approved [R]", "not production ready [R]") is kept; "no issues" is kept \
only as a report of an instrument ("Ghost reported no issues [G]").
3. Do not say that the run passed, failed, is safe or is approved in your own voice (a sentence that calls \
anything safe is deleted). Say what the \
record says and cite it: the decision [R], the Judge's verdict [V], the suite lines, the unmeasured \
list [U].
4. Prefer short sentences. Lead with what happened, then why, then what a person could do next, each \
cited. Use a heading per section if you like (headings need no citation).
5. Say what was NOT measured as plainly as what was."""


class Refused(RuntimeError):
    """The model declined the request (a safety classifier), so there is no account."""


class ModelResponseError(RuntimeError):
    """The API answered, but the answer cannot be used: the body did not decode (a 200 with text that is not
    JSON, a proxy's error page) or it has not the shape of a message. Treated like any other API failure."""


class Narrator(Protocol):
    def narrate(self, system: str, prompt: str, model: str, effort: str) -> str: ...


def prompt_for(evidence: Evidence) -> str:
    """The record as a list of citable lines. This is everything the model is shown."""
    lines = ["The record of the run, one citable thing per line as [id] kind: text.", ""]
    for cid, c in evidence.citations.items():
        lines.append(f"[{cid}] {c.kind}: {c.text}")
    lines += ["", "Write the Watcher's account of this run for a person. Cite an id in every sentence."]
    return "\n".join(lines)


class AnthropicNarrator:
    """Claude through the official SDK. Thinking is the model's default; depth is `effort`."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def _get(self) -> Any:
        if self._client is None:
            import anthropic  # imported here so `--no-model` needs no SDK
            self._client = anthropic.Anthropic()
        return self._client

    def narrate(self, system: str, prompt: str, model: str, effort: str) -> str:
        try:
            response = self._get().beta.messages.create(
                model=model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except ValueError as err:  # the SDK lets a body that does not decode (json.JSONDecodeError) escape
            raise ModelResponseError(f"the response could not be decoded ({type(err).__name__}: {err})") from err
        if getattr(response, "stop_reason", None) == "refusal":
            details = getattr(response, "stop_details", None)
            raise Refused(f"the model declined ({getattr(details, 'category', None)})")
        blocks = getattr(response, "content", None)
        if not isinstance(blocks, (list, tuple)):  # a plain string comes back for a body that was not JSON
            raise ModelResponseError(f"the response is not a message ({type(response).__name__})")
        texts: list[str] = []
        for block in blocks:
            if getattr(block, "type", "") == "text":
                text = getattr(block, "text", None)
                if not isinstance(text, str):
                    raise ModelResponseError("a text block of the response has no text")
                texts.append(text)
        return "\n".join(texts)


def credentials_present() -> bool:
    """Whether the SDK has something to authenticate with, without making a request."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    profile = os.path.expanduser("~/.config/anthropic")
    return os.path.isdir(profile) and any(os.scandir(profile))


def template(evidence: Evidence) -> str:
    """A cited account written from the index alone. Deterministic; no model. Each fact is one bullet,
    which the oath reads as one unit however many sentences the record's text holds."""
    c = evidence.citations
    run = evidence.run

    def fact(cid: str) -> str:
        return f"- [{cid}] {c[cid].text}"

    out = ["## What happened", f"- [R] The run ended {run.get('decision')}."]
    if "V" in c:
        out.append(f"- [V] The Judge said {run['verdict'].get('decision')}.")
    out += [fact(cid) for cid in ("C1", "C2", "C3") if cid in c]
    out.append("## What was measured")
    out += [fact(cid) for cid, cit in c.items()
            if cit.kind == "note" and ("suite" in cit.text.lower() or "observed" in cit.text.lower())]
    if "G" in c:
        out.append(fact("G"))
    out.append("## What was not")
    if "U" in c:
        out.append(fact("U"))
    if run.get("allow_uncommitted_instruments") is True and "AU" in c:
        out.append(fact("AU"))  # an instrument Warden cannot name was allowed on request
    out += [fact(cid) for cid, cit in c.items()
            if cit.kind == "note" and ("gap" in cit.text.lower() or "not measured" in cit.text.lower()
                                       or "uncommitted-instruments" in cit.text.lower())]
    joins = [cid for cid, cit in c.items() if cit.kind == "join"]
    if joins:
        out.append("## What was joined")
        out += [fact(cid) for cid in joins]
    out.append("## Who took part")
    if "W" in c:
        out.append(fact("W"))
    return "\n".join(out)


def narrate(evidence: Evidence, narrator: Narrator | None, model: str = DEFAULT_MODEL,
            effort: str = DEFAULT_EFFORT) -> str:
    """The raw account: from the narrator when one is given, else from the template."""
    if narrator is None:
        log.debug("writing the template account from %d citable things", len(evidence.citations))
        return template(evidence)
    prompt = prompt_for(evidence)
    log.debug("asking %s (effort %s) with a prompt of %d characters", model, effort, len(prompt))
    return narrator.narrate(SYSTEM, prompt, model, effort)


__all__ = [
    "DEFAULT_EFFORT",
    "DEFAULT_MODEL",
    "SYSTEM",
    "AnthropicNarrator",
    "ModelResponseError",
    "Narrator",
    "Refused",
    "credentials_present",
    "narrate",
    "prompt_for",
    "template",
]
