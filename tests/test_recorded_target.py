"""The record names the governed folder (Warden's `versions.target.path`), and the Watcher guards it.

An older record does not name one: it needs `--target` before `--out` is accepted. A `--target` that disagrees with
the record is refused, so the caller cannot point the guard at the wrong folder."""
from __future__ import annotations

import json
from pathlib import Path

from watcher.cli import EXIT_OK, EXIT_USAGE, main
from watcher.evidence import load, recorded_target

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


def _record(tmp_path: Path, governed: Path | None) -> Path:
    run = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if governed is not None:
        run["versions"]["target"] = {"path": str(governed)}
    path = tmp_path / "record.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    return path


def test_the_recorded_folder_is_read_and_forbidden(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    record = _record(tmp_path, governed)
    run = json.loads(record.read_text(encoding="utf-8"))
    assert recorded_target(run) == governed.resolve()
    assert governed.resolve() in load(record).forbidden_paths


def test_an_out_inside_the_recorded_folder_is_refused_with_no_target_given(tmp_path, capsys):
    governed = tmp_path / "governed"
    governed.mkdir()
    out = governed / "account.md"
    code = main(["narrate", str(_record(tmp_path, governed)), "--no-model", "--out", str(out)])
    assert code == EXIT_USAGE and not out.exists()
    assert "never writes into" in capsys.readouterr().err


def test_a_target_that_is_not_the_recorded_folder_is_refused_and_nothing_is_written(tmp_path, capsys):
    governed, other = tmp_path / "governed", tmp_path / "other"
    governed.mkdir()
    other.mkdir()
    out = tmp_path / "account.md"
    code = main(["narrate", str(_record(tmp_path, governed)), "--no-model", "--target", str(other), "--out", str(out)])
    assert code == EXIT_USAGE and not out.exists()
    assert "not the folder the record says was governed" in capsys.readouterr().err


def test_a_target_that_is_the_recorded_folder_is_accepted(tmp_path):
    governed = tmp_path / "governed"
    governed.mkdir()
    link = tmp_path / "link"
    link.symlink_to(governed)
    out = tmp_path / "account.md"
    assert main(["narrate", str(_record(tmp_path, governed)), "--no-model", "--target", str(link),
                 "--out", str(out)]) == EXIT_OK
    assert out.exists()


def test_an_older_record_with_out_and_no_target_is_refused(tmp_path, capsys):
    out = tmp_path / "account.md"
    code = main(["narrate", str(_record(tmp_path, None)), "--no-model", "--out", str(out)])
    assert code == EXIT_USAGE and not out.exists()
    assert "does not name the folder that was governed" in capsys.readouterr().err


def test_an_older_record_without_out_is_still_narrated_to_the_screen(tmp_path):
    assert main(["narrate", str(_record(tmp_path, None)), "--no-model"]) == EXIT_OK
