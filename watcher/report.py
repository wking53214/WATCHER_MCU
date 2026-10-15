"""The account as a person reads it: the kept sentences, what was dropped and why, the index, the oath."""

from __future__ import annotations

from . import OATH, __version__
from .evidence import Evidence
from .oath import Enforced, cited_ids


def render(evidence: Evidence, enforced: Enforced, *, model: str, narrator_used: bool) -> str:
    run = evidence.run
    lines = [
        "# The Watcher's account",
        "",
        f"Run decision as recorded: **{run.get('decision')}** [R]. "
        f"Written by {'the model ' + model if narrator_used else 'the template (no model)'}, "
        f"Watcher {__version__}.",
        "",
    ]
    lines.extend(enforced.kept)
    lines += ["", "## Dropped by the oath", ""]
    if enforced.dropped:
        lines.append(f"{len(enforced.dropped)} sentence(s) were written and not kept:")
        lines.append("")
        for d in enforced.dropped:
            shown = d.sentence if len(d.sentence) <= 160 else d.sentence[:157] + "..."
            lines.append(f"- {d.reason}: \"{shown}\"")
    else:
        lines.append("Nothing. Every sentence cited the record and claimed no status of its own.")
    lines += ["", "## Citations used", ""]
    for cid in cited_ids(enforced.kept):
        c = evidence.cited(cid)
        if c is not None:
            lines.append(f"- [{cid}] {c.kind}: {c.text}")
    lines += ["", "## The oath", "", OATH, ""]
    return "\n".join(lines)


__all__ = ["render"]
