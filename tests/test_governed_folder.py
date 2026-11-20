"""Warden's record names the folder it governed (`governed_folder`); the Watcher checks `--target` against it.

A `--target` that points elsewhere is refused. A record that names no folder is refused when
`--out` is given and there is no `--target`, because a guard that does not know the folder guards
nothing. With no `--out` nothing is written, so nothing is guarded.
"""
import json
from pathlib import Path

from watcher import cli

DECLINED = Path(__file__).parent / "fixtures" / "warden_0_13_6_declined_record.json"


def record(tmp_path, governed):
    run = json.loads(DECLINED.read_text(encoding="utf-8"))
    if governed is not None:
        run["governed_folder"] = governed
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    return path


def narrate(*args):
    return cli.main(["narrate", "--no-model", *map(str, args)])


def test_a_record_that_names_its_folder_needs_no_target(tmp_path):
    folder = tmp_path / "governed"
    folder.mkdir()
    out = tmp_path / "account.md"
    assert narrate(record(tmp_path, str(folder)), "--out", out) == 0 and out.exists()


def test_an_out_inside_the_folder_the_record_names_is_refused_without_a_target(tmp_path, capsys):
    folder = tmp_path / "governed"
    folder.mkdir()
    out = folder / "account.md"
    assert narrate(record(tmp_path, str(folder)), "--out", out) == 2
    assert not out.exists() and "never writes into" in capsys.readouterr().err


def test_a_target_that_is_not_the_recorded_folder_is_refused_and_nothing_is_written(tmp_path, capsys):
    governed, other = tmp_path / "governed", tmp_path / "other"
    governed.mkdir(), other.mkdir()
    out = tmp_path / "account.md"
    assert narrate(record(tmp_path, str(governed)), "--target", other, "--out", out) == 2
    assert not out.exists() and "is not the folder the record says was governed" in capsys.readouterr().err


def test_a_target_that_is_the_recorded_folder_is_accepted(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    out = tmp_path / "account.md"
    assert narrate(record(tmp_path, str(governed)), "--target", governed, "--out", out) == 0


def test_a_record_that_names_no_folder_is_refused_with_an_out_and_no_target(tmp_path, capsys):
    out = tmp_path / "account.md"
    assert narrate(record(tmp_path, None), "--out", out) == 2
    assert not out.exists() and "does not name the folder that was governed" in capsys.readouterr().err


def test_a_record_that_names_no_folder_is_accepted_with_a_target(tmp_path):
    folder = tmp_path / "governed"
    folder.mkdir()
    assert narrate(record(tmp_path, None), "--target", folder, "--out", tmp_path / "account.md") == 0


def test_without_an_out_nothing_is_written_so_no_folder_is_needed(tmp_path, capsys):
    assert narrate(record(tmp_path, None)) == 0
    assert capsys.readouterr().out.strip()


def test_a_governed_folder_that_is_not_text_is_an_unreadable_record(tmp_path):
    assert narrate(record(tmp_path, 7)) == 2
