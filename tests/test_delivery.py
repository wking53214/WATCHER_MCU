"""Delivering the account on standard output: a reader that left keeps the earned code, any other failure is one line.

`watcher narrate RECORD --no-model | head -c0` used to end in "internal error: BrokenPipeError ... Nothing was written."
and exit 1, which the README says is a bug in the Watcher. The rules now (the same as the Judge's):

- the reader went away (a broken pipe): nothing on standard error, and the exit code is the one earned (0, or 4 when the
  oath kept nothing);
- standard output is closed, or a write to it fails for any other reason (a full device): one plain line on standard
  error, no traceback, exit 2, whatever the account was, because an account that was not delivered was not given;
- `main` does not replace the caller's `sys.stdout`.

No test opens a device node: a gone reader is a pipe whose read end this test closed, a closed standard output is a
descriptor closed in the child, and a full device is a stream that raises ENOSPC.
"""
from __future__ import annotations

import errno
import os
import subprocess
import sys
from pathlib import Path

import pytest

from watcher.cli import EXIT_NOTHING_KEPT, EXIT_OK, EXIT_USAGE, main

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"
COMMAND = [sys.executable, "-m", "watcher.cli", "narrate", str(FIXTURE), "--no-model"]


class Scripted:
    def __init__(self, text: str) -> None:
        self.text = text

    def narrate(self, system, prompt, model, effort):
        return self.text


class Failing:
    """A standard output whose writes fail the way a full device or a gone reader does."""

    def __init__(self, error: OSError) -> None:
        self.error = error
        self.closed = False

    def write(self, text: str) -> int:
        raise self.error

    def flush(self) -> None:
        raise self.error


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    env.update(extra)
    return env


@pytest.mark.parametrize("unbuffered", [False, True])
def test_a_reader_that_left_keeps_the_earned_code_and_prints_nothing(unbuffered):
    read_end, write_end = os.pipe()
    os.close(read_end)  # nobody will ever read: the first write is a broken pipe
    try:
        extra = {"PYTHONUNBUFFERED": "1"} if unbuffered else {}
        done = subprocess.run(COMMAND, stdout=write_end, stderr=subprocess.PIPE, env=_env(**extra), check=False,
                              timeout=120)
    finally:
        os.close(write_end)
    assert done.returncode == EXIT_OK, done.stderr
    assert done.stderr == b"", done.stderr


def test_a_closed_standard_output_is_one_plain_line_and_exit_2():
    done = subprocess.run(COMMAND, capture_output=True, env=_env(), check=False,
                          timeout=120, preexec_fn=lambda: os.close(1))
    assert done.returncode == EXIT_USAGE, done.stderr
    lines = done.stderr.decode().strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("watcher: the account could not be delivered"), lines
    assert b"Traceback" not in done.stderr and b"internal error" not in done.stderr


def test_a_write_that_fails_for_another_reason_is_one_plain_line_and_exit_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdout", Failing(OSError(errno.ENOSPC, "No space left on device")))
    assert main(["narrate", str(FIXTURE), "--no-model"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "No space left on device" in err and "could not be delivered" in err
    assert "internal error" not in err and "Traceback" not in err


def test_a_broken_pipe_keeps_exit_4_when_the_oath_kept_nothing(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdout", Failing(BrokenPipeError(errno.EPIPE, "Broken pipe")))
    assert main(["narrate", str(FIXTURE)], narrator=Scripted("Everything is wonderful.")) == EXIT_NOTHING_KEPT
    assert capsys.readouterr().err == ""


def test_a_broken_pipe_keeps_exit_0_in_process(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdout", Failing(BrokenPipeError(errno.EPIPE, "Broken pipe")))
    assert main(["narrate", str(FIXTURE), "--no-model"]) == EXIT_OK
    assert capsys.readouterr().err == ""


def test_main_leaves_the_callers_standard_output_in_place(monkeypatch):
    stream = Failing(BrokenPipeError(errno.EPIPE, "Broken pipe"))
    monkeypatch.setattr(sys, "stdout", stream)
    main(["narrate", str(FIXTURE), "--no-model"])
    assert sys.stdout is stream


def test_a_delivered_account_is_still_exit_0_and_complete(capsys):
    assert main(["narrate", str(FIXTURE), "--no-model"]) == EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("# The Watcher's account") and out.endswith("\n")
