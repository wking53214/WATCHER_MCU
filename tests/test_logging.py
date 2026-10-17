"""Diagnostics go to standard error through the `watcher` logger; --verbose chooses how much."""
from __future__ import annotations

import logging
from pathlib import Path

from watcher.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


def test_by_default_only_the_account_and_one_status_line_are_written(capsys):
    assert main(["narrate", str(FIXTURE), "--no-model"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("# The Watcher's account")
    assert "DEBUG" not in captured.err and "INFO" not in captured.err


def test_verbose_shows_what_was_read_and_what_the_oath_did(capsys):
    assert main(["--verbose", "narrate", str(FIXTURE), "--no-model"]) == 0
    err = capsys.readouterr().err
    assert "DEBUG watcher.evidence: read " in err and "citable things" in err
    assert "INFO watcher.oath: oath: " in err and "kept" in err and "dropped" in err


def test_verbose_may_follow_the_subcommand_and_names_each_dropped_sentence(capsys):
    class Says:
        def narrate(self, *args):
            return "It is safe [R]. It ended ACCEPT_UNVERIFIED [R]."

    assert main(["narrate", str(FIXTURE), "-v"], narrator=Says()) == 0
    err = capsys.readouterr().err
    assert "dropped (status claim of its own: 'safe'): It is safe [R]." in err
    assert "asking " in err and "characters" in err


def test_the_prompt_and_the_record_are_never_logged(capsys):
    assert main(["-v", "narrate", str(FIXTURE), "--no-model"]) == 0
    err = capsys.readouterr().err
    assert "Ghost Tools observed" not in err and "ghost_tools" not in err


def test_repeated_calls_do_not_stack_handlers(capsys):
    for _ in range(3):
        main(["narrate", str(FIXTURE), "--no-model"])
    handlers = [h for h in logging.getLogger("watcher").handlers if isinstance(h, logging.StreamHandler)]
    assert len(handlers) == 1
    capsys.readouterr()
