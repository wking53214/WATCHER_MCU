"""The oath, enforced: a sentence survives only if it cites the record and claims no status of its own.

This is the whole safety case. People believe fluent prose more than JSON, so the prose is allowed
through only where it points at something in the JSON. Three things drop a sentence:

1. No citation. The sentence names nothing in the record.
2. A citation that is not in the record. Worse than none: it looks like evidence and is not.
3. A status claim of its own: "production ready", "production-grade", "ready for production",
   "battle-tested", "fully tested", "100% coverage", "enterprise grade", "safe", "bulletproof",
   "hardened" and the like. The circuit's own scanner reports those labels for re-verification; the
   Watcher does not get to make them, cited or not. The sentence is read as a person reads it on a
   rendered page, so other dashes, lookalike letters, entities, markup and invisible characters do not
   hide a label.

Headings are structure, not claims; a short heading with no claim in it is kept. Nothing else is.
"""

from __future__ import annotations

import html
import logging
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

log = logging.getLogger(__name__)

#: An id in square brackets. The ids come from `watcher.evidence.index`.
CITATION = re.compile(r"\[([A-Za-z][A-Za-z0-9:_.-]*)\]")

#: Labels a reader would take as a verdict. They are matched against the sentence as a person reads it
#: (see `_as_read`: entities decoded, NFKC, casefolded, accents and invisible characters gone, every
#: dash a hyphen, Cyrillic, Greek and small-capital lookalikes folded to Latin). Words of one label
#: may be joined by spaces, hyphens, dots or slashes. Mirrors Ghost Tools' unverified_status_claim
#: and goes further: a label the Watcher may not make includes "safe", whether or not a citation follows.
_SEP = r"[\s\-./\u00b7]*"


_STATUS_CLAIMS = (
    # ready / grade / quality, in the production and enterprise senses
    r"prod(?:uction)?" + _SEP + r"(?:ready|grade|quality|worthy|proven|hardened|tested|safe|stable)",
    r"ready" + _SEP + r"(?:for|to)" + _SEP
    + r"(?:prod(?:uction)?|deploy(?:ment|ed|ing)?|releas(?:e|ed|ing)|ship(?:ping)?|merg(?:e|ing)|launch|go"
    + _SEP + r"live)",
    r"(?:deploy(?:ment)?|releas(?:e)?|ship|merge|launch|go" + _SEP + r"live)" + _SEP + r"ready",
    r"(?:ship|deploy|merg|releas)able",
    r"enterprise" + _SEP + r"(?:grade|ready|class|quality)",
    r"(?:industrial|military|commercial)" + _SEP + r"(?:grade|strength)",
    # tested
    r"battle" + _SEP + r"(?:tested|proven|hardened)",
    r"(?:fully|well|thoroughly|extensively|exhaustively|completely)" + _SEP + r"(?:tested|verified|validated|covered)",
    r"100" + _SEP + r"(?:%|per" + _SEP + r"cent)" + _SEP
    + r"(?:test" + _SEP + r")?(?:coverage|tested|covered|verified)",
    r"(?:complete|full|total)" + _SEP + r"(?:test" + _SEP + r")?coverage",
    # safe, sound, secure, free of defects
    r"(?<![a-z0-9])(?:safe|safely|secure|bulletproof|hardened|flawless|foolproof|bombproof)(?![a-z0-9])",
    r"bullet" + _SEP + r"proof",
    r"fool" + _SEP + r"proof",
    r"rock" + _SEP + r"solid",
    r"(?:bug|defect|error|regression|vulnerability|issue|flaw)" + _SEP + r"free",
    r"(?:verified|proven|guaranteed|certified)" + _SEP + r"(?:safe|correct|secure|sound)",
    r"(?:no|zero)" + _SEP + r"(?:known" + _SEP + r")?(?:bugs|defects|vulnerabilit(?:y|ies)|flaws)",
)
_STATUS = re.compile("|".join(f"(?:{p})" for p in _STATUS_CLAIMS))
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

#: Lookalikes folded to the Latin letter a reader sees. Lowercase only: the text is casefolded first.
_CONFUSABLES = {
    # Cyrillic
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u043a": "k", "\u043c": "m", "\u0442": "t", "\u043d": "h", "\u0432": "b", "\u0456": "i", "\u0458": "j",
    "\u0455": "s", "\u0501": "d", "\u051b": "q", "\u051d": "w", "\u04bb": "h", "\u04cf": "l", "\u0491": "r",
    "\u0433": "r", "\u0438": "u", "\u0457": "i", "\u0454": "e", "\u04e9": "o", "\u0461": "w",
    # Greek
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03bd": "v", "\u03c5": "u", "\u03c4": "t", "\u03b9": "i",
    "\u03ba": "k", "\u03c7": "x", "\u03b5": "e", "\u03b7": "n", "\u03b2": "b", "\u03b3": "y", "\u03c9": "w",
    "\u03c2": "s", "\u03f2": "c", "\u03f3": "j", "\u03bc": "u", "\u03b6": "z", "\u03c0": "n", "\u03c3": "o",
    # Latin letters that are not decomposed, and small capitals
    "\u0131": "i", "\u0142": "l", "\u00f8": "o", "\u0111": "d", "\u0261": "g", "\u0269": "i", "\u0251": "a",
    "\u1d00": "a", "\u0299": "b", "\u1d04": "c", "\u1d05": "d", "\u1d07": "e", "\ua730": "f", "\u0262": "g",
    "\u029c": "h", "\u026a": "i", "\u1d0a": "j", "\u1d0b": "k", "\u029f": "l", "\u1d0d": "m", "\u0274": "n",
    "\u1d0f": "o", "\u1d18": "p", "\u0280": "r", "\ua731": "s", "\u1d1b": "t", "\u1d1c": "u", "\u1d20": "v",
    "\u1d21": "w", "\u028f": "y", "\u1d22": "z",
}
#: Digits and symbols used as letters ("pr0duct10n r3ady"). Applied as a second reading, so that real
#: numbers ("100% coverage") are still read as numbers by the first.
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_DROPPED_CATEGORIES = frozenset({"Mn", "Me", "Cf", "Co", "Cs", "Cn"})
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->")
_EMPHASIS = re.compile(r"[*_`~\\]")


@dataclass(frozen=True)
class Dropped:
    sentence: str
    reason: str


@dataclass(frozen=True)
class Enforced:
    kept: tuple[str, ...]
    dropped: tuple[Dropped, ...]

    @property
    def ratio(self) -> float:
        total = len(self.kept) + len(self.dropped)
        return 1.0 if total == 0 else len(self.kept) / total


def _fold(text: str) -> str:
    """One character at a time: marks and invisible characters vanish, every dash is a hyphen, a lookalike
    is the letter it imitates, any other control or separator is a space."""
    out: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in _DROPPED_CATEGORIES:
            continue
        if cat == "Pd" or ch == "\u2212":
            out.append("-")
        elif cat in ("Cc", "Zs", "Zl", "Zp"):
            out.append(" ")
        else:
            out.append(_CONFUSABLES.get(ch, ch))
    return "".join(out)


def _as_read(text: str) -> str:
    """The sentence as a person reads it on a rendered page: entities decoded, markup, links and emphasis
    markers gone, NFKC, casefolded, accents and invisible characters gone, every dash a hyphen, lookalike
    letters folded to Latin."""
    text = _MARKDOWN_LINK.sub(r"\1", _HTML_TAG.sub("", html.unescape(text)))
    text = _EMPHASIS.sub("", unicodedata.normalize("NFKC", text)).casefold()
    return _fold(unicodedata.normalize("NFKD", text)).casefold()


def sentences(text: str) -> list[str]:
    """Lines, then sentences within a line. A bullet or a heading is one unit; a paragraph is split
    at sentence ends. Blank lines vanish."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING.match(stripped) or stripped.startswith(("-", "*", "•")):
            out.append(stripped)
            continue
        out.extend(s.strip() for s in _SENTENCE_END.split(stripped) if s.strip())
    return out


def status_claim(sentence: str) -> str:
    """The status label a sentence makes on its own, or empty. A label inside a citation's quoted
    text is still a claim here: the Watcher repeats nothing it cannot cite as a report of a label.
    The sentence is read twice, as written and with digits and symbols read as the letters they stand
    for, so "pr0duction r3ady" is caught and "100% coverage" is still a number."""
    read = _as_read(sentence)
    for reading in (read, read.translate(_LEET)):
        m = _STATUS.search(reading)
        if m:
            return m.group(0)
    return ""


def enforce(text: str, citations: Mapping[str, object], headings_allowed: bool = True) -> Enforced:
    """Keep the sentences that cite the record and make no status claim; drop the rest, with reasons."""
    kept: list[str] = []
    dropped: list[Dropped] = []
    known = set(citations)
    for sentence in sentences(text):
        claim = status_claim(sentence)
        if claim:
            dropped.append(Dropped(sentence, f"status claim of its own: {claim!r}"))
            continue
        ids = CITATION.findall(sentence)
        if not ids:
            if headings_allowed and _HEADING.match(sentence) and len(sentence) <= 80:
                kept.append(sentence)
            else:
                dropped.append(Dropped(sentence, "cites nothing in the record"))
            continue
        unknown = [i for i in ids if i not in known]
        if unknown:
            dropped.append(Dropped(sentence, f"cites what is not in the record: {', '.join(unknown)}"))
            continue
        kept.append(sentence)
    for d in dropped:
        log.debug("dropped (%s): %.80s", d.reason, d.sentence)
    log.info("oath: %d kept, %d dropped", len(kept), len(dropped))
    return Enforced(tuple(kept), tuple(dropped))


def cited_ids(kept: Iterable[str]) -> list[str]:
    """Every id the kept sentences cite, in first-seen order."""
    out: list[str] = []
    for sentence in kept:
        for cid in CITATION.findall(sentence):
            if cid not in out:
                out.append(cid)
    return out


__all__ = ["CITATION", "Dropped", "Enforced", "cited_ids", "enforce", "sentences", "status_claim"]
