"""`--out` is written through a temporary file in the same folder and moved into place, so a failure leaves no
partial account and no temporary file, and an account already at `--out` is not lost."""
from __future__ import annotations

import errno
import os
import stat
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


# --out must never replace a file that is not a regular one. Every special file below is made inside tmp_path
# (a FIFO, a folder, links to them); nothing in these tests names a device path.


def _refused(capsys) -> str:
    err: str = capsys.readouterr().err
    assert err.count("\n") == 1, f"one line, not a traceback: {err!r}"
    assert "refused" in err and "not a regular file" in err and "Traceback" not in err
    return err


def test_a_named_pipe_at_out_is_refused_and_stays_a_named_pipe(tmp_path, capsys):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    assert main(_args(fifo)) == EXIT_USAGE
    assert "named pipe" in _refused(capsys)
    assert stat.S_ISFIFO(os.stat(fifo).st_mode), "the pipe was not replaced by a regular file"
    assert [p.name for p in tmp_path.iterdir()] == ["pipe"], "nothing written, no temporary file"


def test_a_folder_at_out_is_refused_in_one_line_and_left_alone(tmp_path, capsys):
    folder = tmp_path / "account.md"
    folder.mkdir()
    (folder / "keep.txt").write_text("kept", encoding="utf-8")
    assert main(_args(folder)) == EXIT_USAGE
    assert "a folder" in _refused(capsys)
    assert [p.name for p in tmp_path.iterdir()] == ["account.md"] and [p.name for p in folder.iterdir()] == ["keep.txt"]


@pytest.mark.parametrize("kind", ["pipe", "folder"])
def test_a_symlink_that_resolves_to_a_special_file_is_refused_too(tmp_path, capsys, kind):
    real = tmp_path / "real"
    if kind == "pipe":
        os.mkfifo(real)
    else:
        real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    before = os.stat(real).st_mode
    assert main(_args(link)) == EXIT_USAGE
    _refused(capsys)
    assert link.is_symlink() and os.stat(real).st_mode == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["link", "real"]


def test_a_chain_of_links_to_a_pipe_is_followed_all_the_way(tmp_path, capsys):
    os.mkfifo(tmp_path / "pipe")
    (tmp_path / "one").symlink_to("pipe")
    (tmp_path / "two").symlink_to("one")
    assert main(_args(tmp_path / "two")) == EXIT_USAGE
    _refused(capsys)
    assert stat.S_ISFIFO(os.stat(tmp_path / "pipe").st_mode)


def test_a_special_file_is_refused_before_the_missing_folder_or_the_model_matter(tmp_path, capsys):
    """The refusal comes with the other --out checks, so a model is never asked for an account that cannot land."""

    class Boom:
        def narrate(self, system, prompt, model, effort):
            raise AssertionError("the model must not be asked")

    os.mkfifo(tmp_path / "pipe")
    assert main(["narrate", str(FIXTURE), "--out", str(tmp_path / "pipe")], narrator=Boom()) == EXIT_USAGE
    _refused(capsys)


def test_a_target_that_becomes_a_pipe_while_the_account_is_written_is_not_replaced(tmp_path, monkeypatch, capsys):
    """The pre-check passed (nothing was there); before the rename a pipe appears. The rename must not swap it."""
    out = tmp_path / "account.md"
    real_write = Path.write_text

    def write_then_swap(self, data, *args, **kwargs):
        real_write(self, data, *args, **kwargs)
        os.mkfifo(out)

    monkeypatch.setattr(Path, "write_text", write_then_swap)
    assert main(_args(out)) == EXIT_USAGE
    assert "became a named pipe" in capsys.readouterr().err
    assert stat.S_ISFIFO(os.stat(out).st_mode)
    assert [p.name for p in tmp_path.iterdir()] == ["account.md"], "the temporary file is gone"


@pytest.mark.parametrize("mode", [0o600, 0o640, 0o444, 0o755])
def test_an_existing_file_keeps_its_permission_bits(tmp_path, mode):
    out = tmp_path / "account.md"
    out.write_text("EARLIER-ACCOUNT", encoding="utf-8")
    out.chmod(mode)
    assert main(_args(out)) == 0
    assert stat.S_IMODE(os.stat(out).st_mode) == mode
    assert out.read_text(encoding="utf-8").startswith("# The Watcher's account")
    assert [p.name for p in tmp_path.iterdir()] == ["account.md"]


def test_a_symlink_to_a_private_file_keeps_that_files_bits_and_stays_a_symlink(tmp_path):
    real = tmp_path / "real.md"
    real.write_text("EARLIER-ACCOUNT", encoding="utf-8")
    real.chmod(0o600)
    link = tmp_path / "link.md"
    link.symlink_to(real)
    assert main(_args(link)) == 0
    assert link.is_symlink() and stat.S_IMODE(os.stat(real).st_mode) == 0o600
    assert real.read_text(encoding="utf-8").startswith("# The Watcher's account")


def test_a_dangling_symlink_still_creates_its_target_with_the_default_bits(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to("created-by-the-write.md")
    assert main(_args(link)) == 0
    made = tmp_path / "created-by-the-write.md"
    assert made.read_text(encoding="utf-8").startswith("# The Watcher's account")
    assert os.stat(made).st_mode & 0o777 == plain.stat().st_mode & 0o777
