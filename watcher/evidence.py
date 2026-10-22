"""The record of a run, turned into things a sentence can cite.

Warden prints one JSON object at the end of `warden tagteam`. This module reads it and gives every
measurable thing in it an id: the decision, the Judge's verdict, each note, each cycle, each
finding Ghost observed, each checkout joined, the unmeasured list, the scan summary. The ids are
what the narrator may cite and what the oath checks against. Nothing here interprets; it only
names.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cns.run import RunRecord

from .oath import CITATION, status_claim

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Citation:
    """One thing in the record that a sentence may point at."""

    id: str
    kind: str
    text: str


@dataclass(frozen=True)
class Evidence:
    """A run record with its citation index and the paths the Watcher must never write into."""

    run: Mapping[str, Any]
    citations: Mapping[str, Citation]
    forbidden_paths: tuple[Path, ...] = field(default_factory=tuple)

    def cited(self, id: str) -> Citation | None:
        return self.citations.get(id)


class UnreadableRecord(ValueError):
    """The file is not a Warden run record."""


#: Bidirectional controls: text between them can be shown in another order, including the words around it.
_BIDI_CONTROLS = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def clean(value: Any, limit: int = 400) -> str:
    """A string of the record as one plain line: every run of whitespace (a newline included) is one space, any other
    control character is a space, bidirectional controls are gone, and a long one is cut. Every string that the record
    supplies and the account shows goes through this, so that a value cannot start a heading, a bullet or a second
    record line of its own."""
    text = "".join(" " if unicodedata.category(ch) == "Cc" else ch for ch in str(value) if ch not in _BIDI_CONTROLS)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _declined(scan: Mapping[str, Any]) -> list[str]:
    """The checks the record says Ghost left out (`ghost_scan.declined`), as text. A declined check was not run."""
    declined = scan.get("declined")
    return [str(name) for name in declined] if isinstance(declined, (list, tuple)) else []


#: How many of the names already shown a declined name is read with.
_NEIGHBOURS = 24


def declined_checks(scan: Mapping[str, Any]) -> tuple[list[str], int]:
    """(the declined checks the account may name, how many it may not). Each name is cleaned. A name is withheld, and
    only that name, when the oath would drop a line that repeats it: it holds a status label (or reads as one with its
    neighbours, as letters set apart do) or it holds text that reads as a citation. Without this, one such name in a
    list of seven made the oath drop the whole line, and the account said nothing of the other six."""
    shown: list[str] = []
    for name in map(clean, _declined(scan)):
        # A label can be spelled across neighbouring names (single letters set apart), so a name is read with the
        # last names shown, not alone; the window keeps a very long list from costing a quadratic reading.
        if CITATION.search(name) or status_claim(", ".join([*shown[-_NEIGHBOURS:], name])):
            continue
        shown.append(name)
    return shown, len(_declined(scan)) - len(shown)


def declined_phrase(scan: Mapping[str, Any]) -> str:
    """The declined checks as one phrase for a line of the account: the names that may be repeated, and, when any were
    withheld, how many (the record has them)."""
    shown, withheld = declined_checks(scan)
    phrase = ", ".join(shown)
    if withheld:
        note = f"{withheld} name(s) not shown here because they hold a label or a citation tag, the record has them"
        phrase = f"{phrase}; {note}" if phrase else note
    return phrase


def _dirty(entry: Mapping[str, Any]) -> bool:
    """Whether the record flags this checkout as having uncommitted changes: `dirty` is the boolean true."""
    return entry.get("dirty") is True


def _unreadable(entry: Mapping[str, Any]) -> bool:
    """Whether the record's `dirty` flag is something other than true, false or null (the text "true", the number 1,
    a list...). Warden writes a boolean or null; anything else is not a flag the Watcher can read, so the part is
    treated as possibly dirty, and said to be."""
    flag = entry.get("dirty")
    return flag is not None and flag is not True and flag is not False


#: What the account says beside a part whose `dirty` flag is true.
DIRTY_MARK = "DIRTY: uncommitted changes"


def _mark(entry: Mapping[str, Any]) -> str:
    """What the account says beside a part of `versions` about its `dirty` flag: nothing when it is false or null."""
    if _dirty(entry):
        return f" ({DIRTY_MARK})"
    if _unreadable(entry):
        return f" ({UNREADABLE_MARK}: the dirty flag is {type(entry.get('dirty')).__name__}, not true or false)"
    return ""


#: What the account says beside a part whose `dirty` flag is neither true, false nor null.
UNREADABLE_MARK = "DIRTY OR UNREADABLE"


def _parts(run: Mapping[str, Any]) -> list[tuple[str, str, Mapping[str, Any]]]:
    """(name, citation id, entry) of every part of `versions` that carries a dirty flag: the four named entries and
    the seats under [W], each join under its [J<n>]."""
    out: list[tuple[str, str, Mapping[str, Any]]] = []
    versions = run.get("versions")
    if not isinstance(versions, Mapping):
        return out
    for name in ("warden", "ghost_tools", "swizzle", "assay"):
        v = versions.get(name)
        if isinstance(v, Mapping):
            out.append((name, "W", v))
    seats = versions.get("seats")
    if isinstance(seats, Mapping):
        out += [(f"{clean(role)} seat", "W", seat) for role, seat in seats.items() if isinstance(seat, Mapping)]
    for n, join in enumerate(versions.get("joins") or (), start=1):
        if isinstance(join, Mapping):
            out.append((f"join {clean(join.get('path'))}", f"J{n}", join))
    return out


def dirty_parts(run: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(name, citation id) of every part of `versions` the record flags `dirty: true`. Nothing is added that the
    record does not hold."""
    return [(name, cid) for name, cid, entry in _parts(run) if _dirty(entry)]


def unreadable_dirty_parts(run: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(name, citation id) of every part of `versions` whose `dirty` flag is neither true, false nor null."""
    return [(name, cid) for name, cid, entry in _parts(run) if _unreadable(entry)]


def _at(entry: Mapping[str, Any]) -> str:
    """" at <12 characters of the commit>", or ", commit not recorded" when the record holds none (a Warden that is
    not a git checkout records null)."""
    commit = entry.get("commit")
    return f" at {str(commit)[:12]}" if commit not in (None, "") else ", commit not recorded"


def _version(entry: Mapping[str, Any]) -> str:
    version = entry.get("version")
    return str(version) if version not in (None, "") else "version not recorded"


def index(run: Mapping[str, Any]) -> dict[str, Citation]:
    """Every citable thing in a run record, keyed by id. Ids are stable for a given record."""
    out: dict[str, Citation] = {}

    def put(cid: str, kind: str, text: str, limit: int = 400) -> None:
        out[cid] = Citation(cid, kind, clean(text, limit))

    put("R", "decision", f"decision {run.get('decision')!s}; reason: {run.get('reason')!s}")
    verdict = run.get("verdict")
    if isinstance(verdict, Mapping):
        put("V", "verdict", f"Judge {verdict.get('judge', '')}: {verdict.get('decision')}; "
                            f"reasons: {'; '.join(map(str, verdict.get('reasons') or ())) or 'none'}")
    for n, note in enumerate(run.get("notes") or (), start=1):
        put(f"N{n}", "note", str(note))
    for cycle in run.get("cycles") or ():
        if isinstance(cycle, Mapping) and "number" in cycle:
            put(f"C{cycle['number']}", "cycle",
                f"cycle {cycle['number']}: {cycle.get('outcome')}; Ghost observed {cycle.get('observed')} finding(s)")
    for fid in run.get("observed") or ():
        if isinstance(fid, str) and fid and fid not in out:  # a finding never replaces [R], [V], [N1]...
            put(fid, "finding", f"Ghost finding {fid} observed at the start")
    for fid in run.get("reobserved") or ():
        if isinstance(fid, str) and fid and fid not in out:
            put(fid, "finding", f"Ghost finding {fid} observed only at the end")
    unmeasured = run.get("unmeasured")
    if isinstance(unmeasured, (list, tuple)):
        put("U", "unmeasured", "not measured: " + (", ".join(map(str, unmeasured)) or "nothing listed in the record"))
    scan = run.get("ghost_scan")
    if isinstance(scan, Mapping):
        declined = declined_phrase(scan)
        put("G", "ghost_scan", f"Ghost scan {scan.get('status')}: {scan.get('files_scanned')} file(s) scanned, "
                               f"{scan.get('files_unparsable')} unparsable; gaps: "
                               f"{'; '.join(map(str, scan.get('gaps') or ())) or 'none'}"
                               + (f"; declined, so not run: {declined}" if _declined(scan) else ""))
    baseline = run.get("ghost_baseline")
    if isinstance(baseline, Mapping):
        put("B", "ghost_baseline", f"Ghost baseline before/after: {json.dumps(baseline, sort_keys=True)}")
    for n, line in enumerate(run.get("drafter_skipped") or (), start=1):
        put(f"D{n}", "drafter_skipped", str(line))
    for n, line in enumerate(run.get("informational") or (), start=1):
        put(f"I{n}", "informational", str(line))
    versions = run.get("versions")
    if isinstance(versions, Mapping):
        parts = []
        for name in ("warden", "ghost_tools", "swizzle", "assay"):
            v = versions.get(name)
            if isinstance(v, Mapping):
                parts.append(f"{name} {_version(v)}{_at(v)}{_mark(v)}")
        seats = versions.get("seats")
        if isinstance(seats, Mapping):
            for role, seat in seats.items():  # a seat that was not loaded is null in the record
                if isinstance(seat, Mapping):
                    parts.append(f"{role} seat {seat.get('spec')} {_version(seat)}{_at(seat)}{_mark(seat)}")
        # No parts are cut from this line: a part cut off would lose its dirty mark with it.
        put("W", "versions", "took part: " + ("; ".join(parts) or "unknown"), limit=4000)
        for n, join in enumerate(versions.get("joins") or (), start=1):
            if isinstance(join, Mapping):
                put(f"J{n}", "join", f"joined for Ghost: {join.get('path')}{_at(join)}{_mark(join)}")
    for key, prefix, kind in (("attacks", "A", "attack"), ("swizzle_proofs", "P", "proof")):
        rows = run.get(key)
        if isinstance(rows, (list, tuple)):
            for n, row in enumerate(rows, start=1):
                put(f"{prefix}{n}", kind, json.dumps(row, sort_keys=True) if isinstance(row, Mapping) else str(row))
    assay = run.get("assay")
    if isinstance(assay, Mapping):
        put("K", "assay", json.dumps(assay, sort_keys=True))
    for key, cid in (("held_digest", "H"), ("put_back", "PB"), ("converged", "CV"), ("finished", "FN"),
                     ("swizzle_sound", "SS"), ("contract", "CT"),
                     ("allow_uncommitted_instruments", "AU")):
        if key in run:
            put(cid, key, f"{key}: {run[key]!s}")
    return out


def forbidden_paths(run: Mapping[str, Any], target: Path | None = None) -> tuple[Path, ...]:
    """Where the Watcher must never write: the governed folder and every instrument or joined checkout
    the record names. Each is resolved; a path that does not exist is still forbidden by name."""
    out: list[Path] = []
    if target is not None:
        out.append(Path(target).expanduser().resolve())
    versions = run.get("versions")
    if isinstance(versions, Mapping):
        for name in ("ghost_tools", "swizzle", "assay"):
            v = versions.get(name)
            if isinstance(v, Mapping) and v.get("path"):
                out.append(Path(str(v["path"])).expanduser().resolve())
        for join in versions.get("joins") or ():
            if isinstance(join, Mapping) and join.get("path"):
                out.append(Path(str(join["path"])).expanduser().resolve())
    return tuple(dict.fromkeys(out))


def _bad(path: Any, what: str) -> UnreadableRecord:
    return UnreadableRecord(f"{path} is not a readable run record: {what}")


def _list_of(run: Mapping[str, Any], key: str, kind: type | tuple[type, ...], noun: str, path: Any) -> None:
    value = run.get(key)
    if value is None:
        return
    if not isinstance(value, list):
        raise _bad(path, f"{key} is {type(value).__name__}, not a list")
    for n, item in enumerate(value):
        if not isinstance(item, kind) or isinstance(item, bool):
            raise _bad(path, f"{key}[{n}] is {type(item).__name__}, not {noun}")


def _object_or_none(value: Any, name: str, path: Any) -> None:
    if value is not None and not isinstance(value, Mapping):
        raise _bad(path, f"{name} is {type(value).__name__}, not an object")


def _check_shapes(run: Mapping[str, Any], path: Any) -> None:
    """The fields cns.run/1 does not describe, but the Watcher reads: each must have the shape the index
    expects, or the record is refused by name. Missing and null are fine; wrong is not."""
    _list_of(run, "cycles", Mapping, "an object", path)
    for n, cycle in enumerate(run.get("cycles") or ()):
        number = cycle.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            raise _bad(path, f"cycles[{n}].number is {type(number).__name__}, not a whole number")
    _list_of(run, "reobserved", str, "text", path)
    _list_of(run, "informational", str, "text", path)
    _list_of(run, "drafter_skipped", str, "text", path)
    for key in ("attacks", "swizzle_proofs"):
        if run.get(key) is not None and not isinstance(run[key], list):
            raise _bad(path, f"{key} is {type(run[key]).__name__}, not a list")
    _object_or_none(run.get("ghost_baseline"), "ghost_baseline", path)
    _object_or_none(run.get("assay"), "assay", path)
    verdict = run.get("verdict") or {}
    if verdict.get("reasons") is not None and not isinstance(verdict["reasons"], list):
        raise _bad(path, f"verdict.reasons is {type(verdict['reasons']).__name__}, not a list")
    scan = run.get("ghost_scan") or {}
    if scan.get("gaps") is not None and not isinstance(scan["gaps"], list):
        raise _bad(path, f"ghost_scan.gaps is {type(scan['gaps']).__name__}, not a list")
    if scan.get("declined") is not None and not isinstance(scan["declined"], list):
        raise _bad(path, f"ghost_scan.declined is {type(scan['declined']).__name__}, not a list")
    versions = run.get("versions") or {}
    for name in ("warden", "ghost_tools", "swizzle", "assay"):
        entry = versions.get(name)
        _object_or_none(entry, f"versions.{name}", path)
        if isinstance(entry, Mapping) and entry.get("path") is not None and not isinstance(entry["path"], str):
            raise _bad(path, f"versions.{name}.path is {type(entry['path']).__name__}, not text")
    seats = versions.get("seats")
    _object_or_none(seats, "versions.seats", path)
    for role, seat in (seats or {}).items():
        _object_or_none(seat, f"versions.seats.{role}", path)
    joins = versions.get("joins")
    if joins is not None and not isinstance(joins, list):
        raise _bad(path, f"versions.joins is {type(joins).__name__}, not a list")
    for n, join in enumerate(joins or ()):
        if not isinstance(join, Mapping):
            raise _bad(path, f"versions.joins[{n}] is {type(join).__name__}, not an object")
        if join.get("path") is not None and not isinstance(join["path"], str):
            raise _bad(path, f"versions.joins[{n}].path is {type(join['path']).__name__}, not text")


def load(path: Path, target: Path | None = None) -> Evidence:
    """Read a Warden run record. Raises UnreadableRecord for anything that is not one: a file that is
    not JSON, a record the cns.run/1 contract refuses, or a field of the wrong shape. Never any other
    exception for a bad record."""
    try:
        run = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise UnreadableRecord(f"{path}: file not found") from err
    except OSError as err:
        raise UnreadableRecord(f"{path} cannot be read: {type(err).__name__}: {err}") from err
    except (ValueError, RecursionError) as err:
        raise UnreadableRecord(f"{path} cannot be read as JSON: {type(err).__name__}: {err}") from err
    if not isinstance(run, Mapping) or "decision" not in run:
        raise UnreadableRecord(f"{path} is not a Warden run record (no 'decision')")
    try:
        RunRecord.from_dict(run)  # the contract: cns.run/1, from the CNS repository
    except ValueError as err:
        raise UnreadableRecord(f"{path} is not a cns.run/1 record: {err}") from err
    _check_shapes(run, path)
    try:
        citations = index(run)
        forbidden = forbidden_paths(run, target)
    except (TypeError, ValueError, AttributeError, KeyError, RuntimeError, OSError) as err:
        # The shape checks above should make this unreachable. If a shape they missed gets here, the
        # record is still refused with a reason, never read in part and never a traceback.
        raise _bad(path, f"{type(err).__name__}: {err}") from err
    log.debug("read %s: decision %s, %d citable things, %d forbidden folders", path, run["decision"],
              len(citations), len(forbidden))
    return Evidence(run=run, citations=citations, forbidden_paths=forbidden)


__all__ = ["DIRTY_MARK", "UNREADABLE_MARK", "Citation", "Evidence", "UnreadableRecord", "clean", "declined_checks",
           "declined_phrase", "dirty_parts", "forbidden_paths", "index", "load", "unreadable_dirty_parts"]
