"""The real Warden writes a run record and the Watcher narrates it.

Needs Warden installed, so the default run deselects it (`-m 'not e2e'`); the `warden-e2e` CI job
selects it with `-m e2e` after installing Warden at a pinned commit. If Warden is missing there, the
test fails: a job that exists to prove the writer and the reader agree must not pass without the writer.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from watcher.cli import main

pytestmark = pytest.mark.e2e


def _find_warden() -> str | None:
    """The `warden` of the interpreter running the tests first (its venv's bin folder, so a venv that is not
    activated still works), then the PATH."""
    bindir = Path(sys.executable).parent
    for name in ("warden", "warden.exe"):
        candidate = bindir / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which("warden")


def _warden(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    exe = _find_warden()
    assert exe is not None, "warden is not installed: this test needs the real Warden writer"
    return subprocess.run([exe, *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=120)


def test_the_installed_warden_is_the_tested_one():
    from importlib import metadata

    assert metadata.version("warden") == "0.13.6", "the e2e job tests the Warden that tests/test_pins.py names"


def test_a_record_from_a_target_that_does_not_exist(tmp_path, capsys):
    result = _warden("tagteam", str(tmp_path / "no-such-folder"), cwd=tmp_path)
    assert result.returncode == 2, result.stderr
    record = tmp_path / "run.json"
    record.write_text(result.stdout, encoding="utf-8")
    assert json.loads(result.stdout)["schema"] == "cns.run/1"
    out = tmp_path / "account.md"
    assert main(["narrate", str(record), "--no-model", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "**USAGE_ERROR** [R]" in text and "Nothing was run" in text
    assert "Traceback" not in capsys.readouterr().err


def test_a_full_record_from_a_real_run_with_seats_and_cycles(tmp_path):
    """`_run_team` writes the long form (cycles, versions, unmeasured...). No drafter is given, so the run
    observes and stops; the record is still the full shape the reader must accept."""
    target = tmp_path / "project"
    target.mkdir()
    git = ["git", "-c", "user.email=ci@example.invalid", "-c", "user.name=ci"]
    (target / "a.py").write_text("x = 1\n", encoding="utf-8")
    for step in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "init"]):
        subprocess.run([*git, *step], cwd=target, check=True, capture_output=True)
    result = _warden("tagteam", str(target), "--authorize", "A Person", "--reason", "e2e", "--scope", "code",
                     cwd=tmp_path)
    record = json.loads(result.stdout)
    assert record["schema"] == "cns.run/1" and "versions" in record and "cycles" in record
    path = tmp_path / "run.json"
    path.write_text(result.stdout, encoding="utf-8")
    out = tmp_path / "account.md"
    assert main(["narrate", str(path), "--no-model", "--target", str(target), "--out", str(out)]) == 0
    assert f"**{record['decision']}** [R]" in out.read_text(encoding="utf-8")


def test_the_module_entry_point_agrees(tmp_path):
    result = _warden("tagteam", str(tmp_path / "missing"), cwd=tmp_path)
    record = tmp_path / "run.json"
    record.write_text(result.stdout, encoding="utf-8")
    cmd = [sys.executable, "-m", "watcher.cli", "narrate", str(record), "--no-model"]
    shown = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    assert shown.returncode == 0, shown.stderr


def test_the_oaths_standard_sentences_are_in_the_installed_wardens_source():
    """`watcher.oath.WARDEN_STANDARD` names sentences Warden writes; each must still be a string in Warden's code."""
    import ast
    import importlib.util

    from watcher.oath import WARDEN_STANDARD

    spec = importlib.util.find_spec("warden")
    assert spec is not None and spec.submodule_search_locations, "warden is not installed: this test needs it"
    strings: list[str] = []
    for path in Path(spec.submodule_search_locations[0]).glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append(" ".join(node.value.lower().split()))
    for fragment in WARDEN_STANDARD:
        assert any(fragment in text for text in strings), fragment
