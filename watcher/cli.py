"""`watcher narrate RUN.json [--out FILE]`: the account of one run, for a person.

Exit codes (the README table is tested against this list):
  0  an account was written (or printed).
  1  an internal error: a bug in the Watcher, reported in one line (add --verbose for the traceback).
     Nothing was written. A malformed record is never this; it is 2.
  2  usage: a record that is missing, unreadable or malformed, a --target that does not exist or is not a folder,
     an --out inside a forbidden folder or on top of the record itself, an --out that exists and is not a regular
     file (a folder, a named pipe, a device, or a symlink that resolves to one), an --out whose folder does not
     exist (unless --create-out-dir is given), an --out that cannot be written, a bad option; also an account
     that could not be delivered on standard output (it is closed, or a write to it fails, as on a full device).
     A reader that went away (a broken pipe, as in `watcher narrate RECORD | head`) is not an error: the exit
     code stays the one earned, 0 or 4, and nothing is printed.
  3  no account could be had from a model: no credentials and --no-model was not given, the model
     could not be reached (connection, timeout, an API error, a response that cannot be decoded or is not
     a message) or it declined. Nothing was written.
  4  the oath dropped every sentence, so there is no account to give (the file still shows what was
     dropped).

Diagnostics go to standard error through the `watcher` logger; --verbose turns on the detail.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import secrets
import stat
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .evidence import Evidence, UnreadableRecord, clean, load
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

#: What `_deliver` answers when the reader of standard output went away (a broken pipe).
_READER_LEFT = "reader left"


def _say(line: str) -> None:
    """One line on standard error. If standard error is unusable too, the line is lost and nothing else changes."""
    with contextlib.suppress(OSError, ValueError, AttributeError):
        print(line, file=sys.stderr)


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
    n.add_argument("--create-out-dir", action="store_true",
                   help="create the folder of --out (and its parents) when it does not exist; without this a "
                        "missing folder is refused")
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


def _not_regular(path: Path) -> str:
    """What `path` is when it exists and is not a regular file, else "". A symlink is followed, as the write
    follows it. A path that does not exist (yet) is fine; one that cannot be looked at is not safe to replace."""
    try:
        mode = os.stat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return ""
    except OSError as err:
        return f"something that cannot be examined ({err.strerror or type(err).__name__})"
    if stat.S_ISREG(mode):
        return ""
    for check, name in ((stat.S_ISDIR, "a folder"), (stat.S_ISFIFO, "a named pipe (FIFO)"),
                        (stat.S_ISCHR, "a character device"), (stat.S_ISBLK, "a block device"),
                        (stat.S_ISSOCK, "a socket")):
        if check(mode):
            return name
    return "not a regular file"


def _write_atomically(path: Path, text: str) -> None:
    """Write `text` to `path` through a temporary file in the same folder, then `os.replace` it into place, so a
    failure at any point leaves no partial file at `path` and no temporary file behind. A symlink at `path` is
    written through, as a plain write would. The rename would swap a folder, a named pipe or a device node for a
    regular file, so a target that exists and is not a regular file is refused (before anything is written, and
    again just before the rename), and an existing file keeps its permission bits. Durability against a crash of
    the machine is not claimed."""
    dest = Path(os.path.realpath(path))
    kind = _not_regular(dest)
    if kind:
        raise OSError(f"{str(path)!r} is {kind}, not a regular file, so it was not replaced")
    tmp = dest.with_name(f".watcher-{secrets.token_hex(6)}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        # An existing file keeps its bits; a new file keeps the mode it was created with.
        with contextlib.suppress(FileNotFoundError, NotADirectoryError):
            tmp.chmod(stat.S_IMODE(os.stat(dest).st_mode))
        kind = _not_regular(dest)
        if kind:
            raise OSError(f"{str(path)!r} became {kind}, not a regular file, so it was not replaced")
        os.replace(tmp, dest)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def _deliver(text: str) -> str | None:
    """Print `text` on standard output: None when delivered, `_READER_LEFT` on a broken pipe, else why it was not.

    The text is flushed here, inside the guard, so a failure of the buffered write is seen now and not at interpreter
    exit. After a failed write on the process's real standard output the stream is closed, which drops the bytes that
    could not be written; otherwise the interpreter tries them again at exit and ends with status 120."""
    out = sys.stdout
    if out is None:
        return "standard output is closed"
    try:
        out.write(text)
        out.flush()
        return None
    except BrokenPipeError:
        failure = _READER_LEFT
    except (OSError, ValueError) as err:  # ValueError: the stream was closed under us
        failure = f"{type(err).__name__}: {err}"
    real = sys.__stdout__
    if real is not None and out is real:
        with contextlib.suppress(OSError, ValueError):
            real.close()
    return failure


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
    if args.target is not None and not args.target.expanduser().exists():
        # A guard built on a folder that is not there protects nothing: --out could be inside the real one.
        print(f"watcher: refused: --target {args.target} does not exist, so it cannot be guarded; "
              "give the folder that was governed", file=sys.stderr)
        return EXIT_USAGE
    if args.target is not None and not args.target.expanduser().is_dir():
        # The guard is a folder: --out is refused when it is inside it. A file guards nothing.
        print(f"watcher: refused: --target {args.target} is not a folder, so it cannot be guarded; "
              "give the folder that was governed", file=sys.stderr)
        return EXIT_USAGE
    if args.out is not None:
        hit = _inside(args.out, evidence.forbidden_paths)
        if hit is not None:
            print(f"watcher: refused: --out {args.out} is inside {clean(hit)}, which the Watcher never writes into",
                  file=sys.stderr)
            return EXIT_USAGE
        source = _is_input(args.out, [args.record])
        if source is not None:
            print(f"watcher: refused: --out {args.out} is the record it was asked to read ({source}); "
                  "the Watcher never overwrites what it reads", file=sys.stderr)
            return EXIT_USAGE
        kind = _not_regular(Path(os.path.realpath(args.out)))
        if kind:
            print(f"watcher: refused: --out {args.out} is {kind}, not a regular file, and the Watcher replaces "
                  "its target when it writes; name a regular file or a path that does not exist yet",
                  file=sys.stderr)
            return EXIT_USAGE
        if not args.out.parent.is_dir() and not args.create_out_dir:
            print(f"watcher: refused: the folder for --out ({args.out.parent}) does not exist; create it, or pass "
                  "--create-out-dir to have the Watcher create it", file=sys.stderr)
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
        failure = _deliver(text)
        if failure is not None and failure != _READER_LEFT:
            _say(f"watcher: the account could not be delivered on standard output ({failure}). Nothing was given.")
            return EXIT_USAGE
        # A reader that left (`watcher narrate RECORD | head`) chose to stop reading: the earned code stays.
    else:
        try:
            if args.create_out_dir:
                args.out.parent.mkdir(parents=True, exist_ok=True)
            _write_atomically(args.out, text)
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
