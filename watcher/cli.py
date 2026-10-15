"""`watcher narrate RUN.json [--out FILE]`: the account of one run, for a person.

Exit codes: 0 an account was written; 2 usage (unreadable record, an --out inside a forbidden
folder, a bad option); 3 no model could be reached and --no-model was not given; 4 the oath dropped
every sentence, so there is no account to give.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .evidence import Evidence, UnreadableRecord, load
from .narrate import DEFAULT_EFFORT, DEFAULT_MODEL, AnthropicNarrator, Narrator, Refused, credentials_present, narrate
from .oath import enforce
from .report import render

EFFORTS = ("low", "medium", "high", "xhigh", "max")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="watcher", description="The Watcher: sees every run, interferes with none.")
    p.add_argument("--version", action="version", version=f"watcher {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    n = sub.add_parser("narrate", help="write the account of one Warden run record")
    n.add_argument("record", type=Path, help="the JSON Warden printed at the end of `warden tagteam`")
    n.add_argument("--out", type=Path, default=None,
                   help="where to write the account (Markdown). Without it, standard output. Never inside "
                        "the governed folder or any checkout the record names")
    n.add_argument("--target", type=Path, default=None,
                   help="the folder that was governed, so an --out inside it is refused (the record does not "
                        "always name it)")
    n.add_argument("--model", default=DEFAULT_MODEL, help=f"the Claude model (default {DEFAULT_MODEL})")
    n.add_argument("--effort", default=DEFAULT_EFFORT, choices=EFFORTS)
    n.add_argument("--no-model", action="store_true",
                   help="write the account from the record alone, deterministically, without a model")
    return p


def _inside(path: Path, folders: Sequence[Path]) -> Optional[Path]:
    real = path.expanduser().resolve()
    for folder in folders:
        if real == folder or real.is_relative_to(folder):
            return folder
    return None


def write_account(evidence: Evidence, narrator: Optional[Narrator], model: str, effort: str) -> tuple[str, int]:
    """The rendered account and the exit code: 0, or 4 when nothing survived the oath."""
    raw = narrate(evidence, narrator, model=model, effort=effort)
    enforced = enforce(raw, evidence.citations)
    text = render(evidence, enforced, model=model, narrator_used=narrator is not None)
    return text, (0 if enforced.kept else 4)


def main(argv: Optional[Sequence[str]] = None, narrator: Optional[Narrator] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = load(args.record, args.target)
    except UnreadableRecord as err:
        print(f"watcher: {err}", file=sys.stderr)
        return 2
    if args.out is not None:
        hit = _inside(args.out, evidence.forbidden_paths)
        if hit is not None:
            print(f"watcher: refused: --out {args.out} is inside {hit}, which the Watcher never writes into",
                  file=sys.stderr)
            return 2
    if args.no_model:
        narrator = None
    elif narrator is None:
        if credentials_present():
            narrator = AnthropicNarrator()
        else:
            print("watcher: no model credentials (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an `ant auth login` "
                  "profile). Pass --no-model for the template account.", file=sys.stderr)
            return 3
    try:
        text, code = write_account(evidence, narrator, args.model, args.effort)
    except Refused as err:
        print(f"watcher: {err}. No account was written.", file=sys.stderr)
        return 3
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"watcher: account written to {args.out}" + (" (nothing survived the oath)" if code == 4 else ""),
              file=sys.stderr)
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
