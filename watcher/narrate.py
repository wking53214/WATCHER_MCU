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
from collections.abc import Mapping
from typing import Any, Protocol

from .evidence import DIRTY_MARK, Evidence, clean, dirty_parts
from .oath import CITATION

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


def _cycles_that_observed(run: Mapping[str, Any]) -> list[tuple[int, int]]:
    """(cycle number, findings Ghost observed) for each cycle of the record that observed any."""
    out: list[tuple[int, int]] = []
    for cycle in run.get("cycles") or ():
        if isinstance(cycle, Mapping) and isinstance(cycle.get("number"), int):
            n = cycle.get("observed")
            if isinstance(n, int) and not isinstance(n, bool) and n > 0:
                out.append((cycle["number"], n))
    return out


#: How many finding ids the template names for one list of the record (`observed`, `reobserved`); the rest are counted,
#: said to be left out, and remain in the record. A bullet that cited hundreds of ids would bury the account.
FINDING_IDS_SHOWN = 20

#: Words of a note that say a step failed, or was not run or not enforced. Such a note is a statement of something not
#: done or gone wrong, so the template shows it under "What was not" (when it is not already shown under "measured").
_NOT_DONE_WORDS = ("failed", "not sound", "not run", "not enforced", "skipped")


def _finding_ids(evidence: Evidence, key: str) -> list[str]:
    """The ids the record lists under `key`, each once, in order, that can be cited: an id that is not a citable token
    (or that the index gave to something else) is not named."""
    ids = evidence.run.get(key)
    if not isinstance(ids, list):
        return []
    citable = [i for i in dict.fromkeys(ids) if isinstance(i, str) and CITATION.fullmatch(f"[{i}]")]
    return [i for i in citable if i in evidence.citations and evidence.citations[i].kind == "finding"]


def _finding_line(evidence: Evidence, key: str, when: str) -> str | None:
    ids = _finding_ids(evidence, key)
    if not ids:
        return None
    shown = ids[:FINDING_IDS_SHOWN]
    tags = "".join(f"[{i}]" for i in shown)
    more = len(ids) - len(shown)
    tail = f"; {more} more are not shown, the record lists them" if more else ""
    return f"- {tags} Ghost finding id(s) observed {when} ({len(ids)} distinct): {', '.join(shown)}{tail}."


def template(evidence: Evidence) -> str:
    """A cited account written from the index alone. Deterministic; no model. Each fact is one bullet,
    which the oath reads as one unit however many sentences the record's text holds."""
    c = evidence.citations
    run = evidence.run

    def fact(cid: str) -> str:
        return f"- [{cid}] {c[cid].text}"

    # Every string the record supplies is cleaned (`clean`) before it is put in a line, so that the text the oath reads
    # is the text that is rendered and no value can open a heading or a bullet of its own.
    out = ["## What happened", f"- [R] The run ended {clean(run.get('decision'))}."]
    if "V" in c:
        out.append(f"- [V] The Judge said {clean(run['verdict'].get('decision'))}.")
    out += [fact(cid) for cid, cit in c.items() if cit.kind == "cycle"]  # every cycle the record holds, in its order
    seen = _cycles_that_observed(run)
    if run.get("converged") is True and seen:  # converged is "no proposals left"; the record shows findings left
        number, count = seen[-1]
        out.append(f"- [CV] Converged is true and converged is not zero findings: Ghost still observed {count} "
                   f"finding(s) in cycle {number} [C{number}].")
    if run.get("put_back") is True and "PB" in c:
        out.append("- [PB] put_back is true: edits had been made and the whole tree was restored because the run did "
                   "not end accepted.")
    if run.get("finished") is True and "FN" in c:
        out.append("- [FN] finished is true: the finishing change was applied.")
    out.append("## What was measured")
    measured = [cid for cid, cit in c.items()
                if cit.kind == "note" and ("suite" in cit.text.lower() or "observed" in cit.text.lower())]
    out += [fact(cid) for cid in measured]
    if run.get("swizzle_sound") is True and "SS" in c:
        out.append("- [SS] swizzle_sound is true: SWIZZLE's proofs held.")
    out += [line for line in (_finding_line(evidence, "observed", "at the start"),
                              _finding_line(evidence, "reobserved", "at the end")) if line]
    if "G" in c:
        out.append(fact("G"))
    out.append("## What was not")
    if "U" in c:
        out.append(fact("U"))
    if "SS" in c and run.get("swizzle_sound") is False:
        out.append("- [SS] swizzle_sound is false: SWIZZLE's proofs did not hold.")
    elif "SS" in c and run.get("swizzle_sound") is None:
        out.append("- [SS] swizzle_sound is null: the record holds no result of SWIZZLE's proofs.")
    if run.get("allow_uncommitted_instruments") is True and "AU" in c:
        out.append(fact("AU"))  # an instrument Warden cannot name was allowed on request
    scan = run.get("ghost_scan")
    declined = scan.get("declined") if isinstance(scan, Mapping) else None
    if "G" in c and isinstance(declined, list) and declined:  # checks left out of the scan
        names = ", ".join(map(clean, declined))
        out.append(f"- [G] Ghost declined {len(declined)} check(s): {names}. A declined check "
                   "was not run, so the absence of findings from it means nothing.")
    dirty = dirty_parts(run)
    if dirty:  # the record flags uncommitted changes in a part that took part
        ids = "".join(f"[{cid}]" for cid in dict.fromkeys(cid for _, cid in dirty))
        out.append(f"- {ids} {DIRTY_MARK} (dirty: true) in {', '.join(name for name, _ in dirty)}; "
                   "the commit shown for each is not the whole of what ran.")
    out += [fact(cid) for cid, cit in c.items()
            if cit.kind == "note" and cid not in measured
            and ("gap" in cit.text.lower() or "not measured" in cit.text.lower()
                 or "uncommitted-instruments" in cit.text.lower() or "not zero findings" in cit.text.lower()
                 or any(word in cit.text.lower() for word in _NOT_DONE_WORDS))]
    info = [(cid, cit) for cid, cit in c.items() if cit.kind in ("drafter_skipped", "informational")]
    if info:  # said by Warden to change no decision: information, not a gap
        out.append("## Information, not gaps")
        out += [f"- [{cid}] {'The Drafter left a finding alone' if cit.kind == 'drafter_skipped' else 'Warden noted'}"
                f" (information, not a gap): {cit.text}" for cid, cit in info]
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
