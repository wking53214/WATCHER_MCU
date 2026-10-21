"""`--out` is written through a temporary file in the same folder and moved into place, so a failure leaves no
partial account and no temporary file, and an account already at `--out` is not lost."""
from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from watcher.cli import EXIT_USAGE, main

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


def _args(out: Path) -> list[str]:
    return ["narrate", str(FIXTURE), "--no-model", "--out", str(out)]


def test_a_write_that_fails_half_way_leaves_no_partial_file_and_no_temporary(tmp_path, monkeypatch, capsys):
    real_write = Path.write_text

    def half_then_fail(self, data, *args, **kwargs):
        real_write(self, data[: len(data) // 2], *args, **kwargs)  # the disk fills up part of the way through
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(Path, "write_text", half_then_fail)
    out = tmp_path / "account.md"
    assert main(_args(out)) == EXIT_USAGE
    assert list(tmp_path.iterdir()) == [], "neither a partial account nor a temporary file is left"
    err = capsys.readouterr().err
    assert "cannot write" in err and "No space left" in err and "Traceback" not in err


def test_a_failure_to_move_it_into_place_leaves_the_old_account_whole(tmp_path, monkeypatch):
    out = tmp_path / "account.md"
    out.write_text("the earlier account\n", encoding="utf-8")

    def refuse(src, dst):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(os, "replace", refuse)
    assert main(_args(out)) == EXIT_USAGE
    assert out.read_text(encoding="utf-8") == "the earlier account\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["account.md"]


def test_an_interrupt_while_writing_also_cleans_up(tmp_path, monkeypatch):
    def interrupted(self, data, *args, **kwargs):
        self.touch()
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "write_text", interrupted)
    with pytest.raises(KeyboardInterrupt):
        main(_args(tmp_path / "account.md"))
    assert list(tmp_path.iterdir()) == []


def test_a_good_write_replaces_the_old_file_and_leaves_nothing_else(tmp_path):
    out = tmp_path / "account.md"
    out.write_text("EARLIER-ACCOUNT", encoding="utf-8")
    assert main(_args(out)) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# The Watcher's account") and "EARLIER-ACCOUNT" not in text
    assert [p.name for p in tmp_path.iterdir()] == ["account.md"]


def test_the_file_is_created_with_the_ordinary_permissions_of_a_new_file(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    out = tmp_path / "account.md"
    assert main(_args(out)) == 0
    assert out.stat().st_mode & 0o777 == plain.stat().st_mode & 0o777


def test_a_symlink_at_out_is_written_through_not_replaced(tmp_path):
    real = tmp_path / "real.md"
    real.write_text("EARLIER-ACCOUNT", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(real)
    assert main(_args(link)) == 0
    assert link.is_symlink() and real.read_text(encoding="utf-8").startswith("# The Watcher's account")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["link.md", "real.md"]


def test_create_out_dir_still_writes_into_the_new_folder(tmp_path):
    out = tmp_path / "a" / "b" / "account.md"
    assert main([*_args(out), "--create-out-dir"]) == 0
    assert [p.name for p in out.parent.iterdir()] == ["account.md"]
