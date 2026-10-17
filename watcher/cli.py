"""`watcher narrate RUN.json [--out FILE]`: the account of one run, for a person.

Exit codes (the README table is tested against this list):
  0  an account was written (or printed).
  1  an internal error: a bug in the Watcher, reported in one line (add --verbose for the traceback).
     Nothing was written. A malformed record is never this; it is 2.
  2  usage: an unreadable or malformed record, an --out inside a forbidden folder or on top of the
     record itself, an --out that cannot be written, a bad option.
  3  no account could be had from a model: no credentials and --no-model was not given, the model
     could not be reached (connection, timeout, an API error, a response that cannot be decoded or is not
     a message) or it declined. Nothing was written.
  4  the oath dropped every sentence, so there is no account to give (the file still shows what was
     dropped).

Diagnostics go to standard error through the `watcher` logger; --verbose turns on the detail.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .evidence import Evidence, UnreadableRecord, load
from .narrate import (
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    AnthropicNarrator,
    ModelResponseError,
    Narrator,
    Refused,
    credentials_present,
    narrate,
)
from .oath import enforce
from .report import render

EFFORTS = ("low", "medium", "high", "xhigh", "max")

#: The exit codes, by name. The docstring above and the README table list the same numbers.
EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_NO_MODEL, EXIT_NOTHING_KEPT = 0, 1, 2, 3, 4

log = logging.getLogger("watcher")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="watcher", description="The Watcher: sees every run, interferes with none.")
    p.add_argument("--version", action="version", version=f"watcher {__version__}")
    p.add_argument("--verbose", "-v", action="store_true", help="log diagnostics (what was read, what was dropped) "
                   "to standard error, and show the traceback of an internal error")
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
    n.add_argument("--verbose", "-v", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    n.add_argument("--no-model", action="store_true",
                   help="write the account from the record alone, deterministically, without a model")
    return p


def _inside(path: Path, folders: Sequence[Path]) -> Path | None:
    real = path.expanduser().resolve()
    for folder in folders:
        if real == folder or real.is_relative_to(folder):
            return folder
    return None


def _is_input(out: Path, inputs: Sequence[Path]) -> Path | None:
    """The input file `out` would overwrite, if any: the same resolved path, a symlink to it, or a hard link."""
    real = out.expanduser().resolve()
    for source in inputs:
        if real == source.expanduser().resolve():
            return source
        try:
            if out.exists() and os.path.samefile(out, source):
                return source
        except OSError:
            continue
    return None


#: The handler `main` installs on the `watcher` logger; replaced on each call so tests and embedders do not stack them.
_handler: logging.Handler | None = None


def _configure_logging(verbose: bool) -> None:
    global _handler
    logger = logging.getLogger("watcher")
    if _handler is not None:
        logger.removeHandler(_handler)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("watcher: %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG if verbose else logging.WARNING)


def _model_errors() -> tuple[type[BaseException], ...]:
    """What means "no model could be reached": the SDK's own errors (connection, timeout, status, a missing
    credential) and a response that cannot be decoded or is not a message, as a tuple for `except`. Imported
    here so `--no-model` needs no SDK."""
    try:
        import anthropic
    except ImportError:  # pragma: no cover - the SDK is a declared dependency
        return (ModelResponseError,)
    return (anthropic.AnthropicError, ModelResponseError)


def write_account(evidence: Evidence, narrator: Narrator | None, model: str, effort: str) -> tuple[str, int]:
    """The rendered account and the exit code: 0, or 4 when nothing survived the oath."""
    raw = narrate(evidence, narrator, model=model, effort=effort)
    enforced = enforce(raw, evidence.citations)
    text = render(evidence, enforced, model=model, narrator_used=narrator is not None)
    return text, (EXIT_OK if enforced.kept else EXIT_NOTHING_KEPT)


def _narrate(args: argparse.Namespace, narrator: Narrator | None) -> int:
    try:
        evidence = load(args.record, args.target)
    except UnreadableRecord as err:
        print(f"watcher: {err}", file=sys.stderr)
        return EXIT_USAGE
    if args.out is not None:
        hit = _inside(args.out, evidence.forbidden_paths)
        if hit is not None:
            print(f"watcher: refused: --out {args.out} is inside {hit}, which the Watcher never writes into",
                  file=sys.stderr)
            return EXIT_USAGE
        source = _is_input(args.out, [args.record])
        if source is not None:
            print(f"watcher: refused: --out {args.out} is the record it was asked to read ({source}); "
                  "the Watcher never overwrites what it reads", file=sys.stderr)
            return EXIT_USAGE
    if args.no_model:
        narrator = None
    elif narrator is None:
        if credentials_present():
            narrator = AnthropicNarrator()
        else:
            print("watcher: no model credentials (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an `ant auth login` "
                  "profile). Pass --no-model for the template account.", file=sys.stderr)
            return EXIT_NO_MODEL
    log.debug("narrating with %s", f"model {args.model} at effort {args.effort}" if narrator else "the template")
    try:
        text, code = write_account(evidence, narrator, args.model, args.effort)
    except Refused as err:
        print(f"watcher: {err}. No account was written.", file=sys.stderr)
        return EXIT_NO_MODEL
    except _model_errors() as err:
        log.debug("the model request failed", exc_info=True)
        print(f"watcher: no model could be reached ({type(err).__name__}: {err}). No account was written. "
              "Pass --no-model for the template account.", file=sys.stderr)
        return EXIT_NO_MODEL
    if args.out is None:
        sys.stdout.write(text)
    else:
        try:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        except OSError as err:
            print(f"watcher: cannot write {args.out}: {type(err).__name__}: {err}", file=sys.stderr)
            return EXIT_USAGE
        print(f"watcher: account written to {args.out}" + (" (nothing survived the oath)" if code == 4 else ""),
              file=sys.stderr)
    return code


def main(argv: Sequence[str] | None = None, narrator: Narrator | None = None) -> int:
    args = _parser().parse_args(argv)
    _configure_logging(args.verbose)
    try:
        return _narrate(args, narrator)
    except Exception as err:
        log.debug("internal error", exc_info=True)
        print(f"watcher: internal error: {type(err).__name__}: {err}. Nothing was written. "
              "Re-run with --verbose for the traceback.", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
