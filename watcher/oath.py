"""The oath, enforced: a sentence survives only if it cites the record and claims no status of its own.

This is the whole safety case. People believe fluent prose more than JSON, so the prose is allowed
through only where it points at something in the JSON. Three things drop a sentence:

1. No citation. The sentence names nothing in the record.
2. A citation that is not in the record. Worse than none: it looks like evidence and is not.
3. A status claim of its own: "production ready", "battle-tested", "fully tested", "100% coverage",
   "enterprise grade". The circuit's own scanner reports those labels for re-verification; the
   Watcher does not get to make them.

Headings are structure, not claims; a short heading with no claim in it is kept. Nothing else is.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

#: An id in square brackets. The ids come from `watcher.evidence.index`.
CITATION = re.compile(r"\[([A-Za-z][A-Za-z0-9:_.-]*)\]")

#: Labels a reader would take as a verdict. Matched the way a person reads them (NFKC, case-blind,
#: any run of spaces or hyphens between the words), mirroring Ghost Tools' unverified_status_claim.
_STATUS_CLAIMS = (
    r"production[\s-]*ready", r"battle[\s-]*tested", r"fully[\s-]*tested", r"enterprise[\s-]*grade",
    r"100\s*%\s*(?:test\s*)?coverage",
)
_STATUS = re.compile("|".join(f"({p})" for p in _STATUS_CLAIMS), re.IGNORECASE)
_INVISIBLE = re.compile("[\u00ad\u200b\u200c\u200d\u2060\ufeff]")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


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


_EMPHASIS = re.compile(r"[*_`~]")


def _as_read(text: str) -> str:
    """The sentence as a person reads it: NFKC, invisible characters and emphasis markers gone."""
    text = _INVISIBLE.sub("", unicodedata.normalize("NFKC", text))
    return _EMPHASIS.sub("", text).replace("\u00a0", " ")


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
    text is still a claim here: the Watcher repeats nothing it cannot cite as a report of a label."""
    m = _STATUS.search(_as_read(sentence))
    return m.group(0) if m else ""


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
