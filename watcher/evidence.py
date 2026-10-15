"""The record of a run, turned into things a sentence can cite.

Warden prints one JSON object at the end of `warden tagteam`. This module reads it and gives every
measurable thing in it an id: the decision, the Judge's verdict, each note, each cycle, each
finding Ghost observed, each checkout joined, the unmeasured list, the scan summary. The ids are
what the narrator may cite and what the oath checks against. Nothing here interprets; it only
names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


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

    def cited(self, id: str) -> Optional[Citation]:
        return self.citations.get(id)


class UnreadableRecord(ValueError):
    """The file is not a Warden run record."""


def _clean(value: Any, limit: int = 400) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def index(run: Mapping[str, Any]) -> dict[str, Citation]:
    """Every citable thing in a run record, keyed by id. Ids are stable for a given record."""
    out: dict[str, Citation] = {}

    def put(cid: str, kind: str, text: str) -> None:
        out[cid] = Citation(cid, kind, _clean(text))

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
        if isinstance(fid, str) and fid:
            put(fid, "finding", f"Ghost finding {fid} observed at the start")
    for fid in run.get("reobserved") or ():
        if isinstance(fid, str) and fid and fid not in out:
            put(fid, "finding", f"Ghost finding {fid} observed only at the end")
    unmeasured = run.get("unmeasured")
    if isinstance(unmeasured, (list, tuple)):
        put("U", "unmeasured", "not measured: " + (", ".join(map(str, unmeasured)) or "nothing; every check ran"))
    scan = run.get("ghost_scan")
    if isinstance(scan, Mapping):
        put("G", "ghost_scan", f"Ghost scan {scan.get('status')}: {scan.get('files_scanned')} file(s) scanned, "
                               f"{scan.get('files_unparsable')} unparsable; gaps: "
                               f"{'; '.join(map(str, scan.get('gaps') or ())) or 'none'}")
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
                parts.append(f"{name} {v.get('version')} at {str(v.get('commit'))[:12]}")
        put("W", "versions", "took part: " + ("; ".join(parts) or "unknown"))
        for n, join in enumerate(versions.get("joins") or (), start=1):
            if isinstance(join, Mapping):
                put(f"J{n}", "join", f"joined for Ghost: {join.get('path')} at {str(join.get('commit'))[:12]}")
    for key, prefix, kind in (("attacks", "A", "attack"), ("swizzle_proofs", "P", "proof")):
        rows = run.get(key)
        if isinstance(rows, (list, tuple)):
            for n, row in enumerate(rows, start=1):
                put(f"{prefix}{n}", kind, json.dumps(row, sort_keys=True) if isinstance(row, Mapping) else str(row))
    assay = run.get("assay")
    if isinstance(assay, Mapping):
        put("K", "assay", json.dumps(assay, sort_keys=True))
    for key, cid in (("held_digest", "H"), ("put_back", "PB"), ("converged", "CV"), ("finished", "FN"),
                     ("swizzle_sound", "SS"), ("contract", "CT")):
        if key in run:
            put(cid, key, f"{key}: {run[key]!s}")
    return out


def forbidden_paths(run: Mapping[str, Any], target: Optional[Path] = None) -> tuple[Path, ...]:
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


def load(path: Path, target: Optional[Path] = None) -> Evidence:
    """Read a Warden run record. Raises UnreadableRecord for anything that is not one."""
    try:
        run = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise UnreadableRecord(f"{path} cannot be read as JSON: {type(err).__name__}: {err}") from err
    if not isinstance(run, Mapping) or "decision" not in run:
        raise UnreadableRecord(f"{path} is not a Warden run record (no 'decision')")
    return Evidence(run=run, citations=index(run), forbidden_paths=forbidden_paths(run, target))


__all__ = ["Citation", "Evidence", "UnreadableRecord", "index", "forbidden_paths", "load"]
