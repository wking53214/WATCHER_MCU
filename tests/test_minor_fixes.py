"""Four small defects of the account, each found on a real record or a real run:

* a commit the record does not hold (Warden run from a copy that is not a git checkout writes `commit: null`) was
  shown as "at None";
* a `dirty` flag that is not a JSON boolean ("true", 1) was ignored, so the part looked clean;
* `--target` could be a file, which guards nothing;
* one declined check that the oath would drop (a status label) made it drop the whole [G] line, so the account said
  nothing of the other checks.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from watcher.cli import EXIT_USAGE, main
from watcher.evidence import DIRTY_MARK, UNREADABLE_MARK, declined_checks, load
from watcher.narrate import template
from watcher.oath import enforce

FIXTURES = Path(__file__).parent / "fixtures"
DECLINED = FIXTURES / "warden_0_13_6_declined_record.json"
JOINED = FIXTURES / "swizzle_joined_run.json"


def _run(path: Path = DECLINED) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _write(run: dict[str, Any], tmp_path: Path, name: str = "run.json") -> Path:
    record = tmp_path / name
    record.write_text(json.dumps(run), encoding="utf-8")
    return record


def _account(run: dict[str, Any], tmp_path: Path) -> str:
    evidence = load(_write(run, tmp_path))
    raw = template(evidence)
    assert enforce(raw, evidence.citations).dropped == ()
    return raw


# -- a commit that is not recorded ------------------------------------------------------------------------------------


def test_a_commit_the_record_does_not_hold_is_said_not_to_be_recorded(tmp_path):
    run = _run()
    run["versions"]["warden"]["commit"] = None
    run["versions"]["joins"][0]["commit"] = None
    run["versions"]["seats"]["judge"]["commit"] = ""
    evidence = load(_write(run, tmp_path))
    w = evidence.citations["W"].text
    assert "warden 0.13.6, commit not recorded;" in w and "None" not in w
    assert "judge seat judge.seat:Judge 0.4.7, commit not recorded" in w
    assert evidence.citations["J1"].text == "joined for Ghost: /stack/ghost_tools, commit not recorded"
    assert "None" not in template(evidence)


def test_a_commit_that_is_recorded_is_shown_as_before(tmp_path):
    evidence = load(DECLINED)
    assert "warden 0.13.6 at 0c1ea567f0b6;" in evidence.citations["W"].text
    assert evidence.citations["J1"].text == "joined for Ghost: /stack/ghost_tools at c2ada82d2f6c"


def test_a_version_the_record_does_not_hold_is_said_not_to_be_recorded():
    evidence = load(JOINED)
    assert "assay version not recorded at e68f8a070516" in evidence.citations["W"].text
    assert "None" not in evidence.citations["W"].text


# -- a dirty flag that is not a boolean ------------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["true", "True", "yes", 1, 0, "false", "", [], {}, [True], 1.0])
def test_a_dirty_flag_that_is_not_true_false_or_null_is_treated_as_possibly_dirty_and_said_so(tmp_path, flag):
    run = _run()
    run["versions"]["swizzle"]["dirty"] = flag
    run["versions"]["seats"]["judge"]["dirty"] = flag
    run["versions"]["joins"][1]["dirty"] = flag
    evidence = load(_write(run, tmp_path))
    kind = type(flag).__name__
    mark = f"({UNREADABLE_MARK}: the dirty flag is {kind}, not true or false)"
    assert evidence.citations["W"].text.count(mark) == 2
    assert evidence.citations["J2"].text.endswith(mark)
    assert DIRTY_MARK not in evidence.citations["W"].text, "it is not claimed to be dirty, only unreadable"
    account = template(evidence)
    line = next(ln for ln in account.splitlines() if ln.startswith("- [W][J2] " + UNREADABLE_MARK + " (the dirty flag"))
    assert "in swizzle, judge seat, join /stack/SWIZZLE;" in line
    assert "whether the commit shown for each is the whole of what ran is not known." in line
    assert enforce(account, evidence.citations).dropped == ()


@pytest.mark.parametrize("flag", [False, None])
def test_false_and_null_are_still_not_reported(tmp_path, flag):
    run = _run()
    run["versions"]["swizzle"]["dirty"] = flag
    evidence = load(_write(run, tmp_path))
    assert UNREADABLE_MARK not in evidence.citations["W"].text and DIRTY_MARK not in evidence.citations["W"].text
    assert UNREADABLE_MARK not in template(evidence)
    del run["versions"]["swizzle"]["dirty"]  # a key that is missing is unknown, like null
    assert UNREADABLE_MARK not in template(load(_write(run, tmp_path)))


def test_true_is_still_dirty_and_the_two_cases_get_a_line_each(tmp_path):
    run = _run()
    run["versions"]["warden"]["dirty"] = True
    run["versions"]["swizzle"]["dirty"] = "true"
    account = _account(run, tmp_path)
    assert f"- [W] {DIRTY_MARK} (dirty: true) in warden; " in account
    assert f"- [W] {UNREADABLE_MARK} (the dirty flag is not true or false) in swizzle; " in account


# -- --target that is a file ----------------------------------------------------------------------------------------


def test_a_target_that_is_a_file_is_refused_with_one_line_and_nothing_is_written(tmp_path, capsys):
    target = tmp_path / "not-a-folder.txt"
    target.write_text("x", encoding="utf-8")
    out = tmp_path / "account.md"
    assert main(["narrate", str(DECLINED), "--no-model", "--target", str(target), "--out", str(out)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "is not a folder" in err and "Traceback" not in err
    assert not out.exists()


def test_a_target_that_is_a_folder_or_a_link_to_one_is_still_accepted(tmp_path):
    folder = tmp_path / "governed"
    folder.mkdir()
    link = tmp_path / "link"
    link.symlink_to(folder)
    for target in (folder, link):
        out = tmp_path / f"account-{target.name}.md"
        assert main(["narrate", str(DECLINED), "--no-model", "--target", str(target), "--out", str(out)]) == 0
    assert main(["narrate", str(DECLINED), "--no-model", "--target", str(folder / "inside.md"),
                 "--out", str(tmp_path / "x.md")]) == EXIT_USAGE  # missing: still refused, as before


def test_a_target_that_does_not_exist_keeps_its_own_message(tmp_path, capsys):
    missing = tmp_path / "nope"
    assert not missing.exists()
    assert main(["narrate", str(DECLINED), "--no-model", "--target", str(missing)]) == EXIT_USAGE
    assert "does not exist" in capsys.readouterr().err


# -- one declined name that the oath would drop -----------------------------------------------------------------------


SEVEN = ["mutate", "kernel", "structure", "tests", "project", "secrets", "correlate"]


def test_one_offending_declined_name_is_dropped_alone_and_the_rest_are_shown(tmp_path):
    run = _run()
    run["ghost_scan"]["declined"] = ["mutate", "kernel", "production ready", "tests", "project", "secrets", "correlate"]
    evidence = load(_write(run, tmp_path))
    account = template(evidence)
    assert enforce(account, evidence.citations).dropped == (), "nothing is dropped, the offender was never repeated"
    line = next(ln for ln in account.splitlines() if ln.startswith("- [G] Ghost declined"))
    assert line.startswith("- [G] Ghost declined 7 check(s): mutate, kernel, tests, project, secrets, correlate; "
                           "1 name(s) not shown here because they hold a label or a citation tag, the record has them.")
    assert "production ready" not in account
    assert "production ready" not in "\n".join(c.text for c in evidence.citations.values()), "nor in the index"
    assert "declined, so not run: mutate, kernel, tests, project, secrets, correlate; 1 name(s)" in \
        evidence.citations["G"].text


def test_several_offenders_and_a_label_split_across_names_are_withheld_the_rest_stay(tmp_path):
    run = _run()
    run["ghost_scan"]["declined"] = ["mutate", "safe", "s", "a", "f", "e", "bulletproof", "[ZZ9]", "kernel"]
    evidence = load(_write(run, tmp_path))
    shown, withheld = declined_checks(run["ghost_scan"])
    assert shown == ["mutate", "s", "a", "f", "kernel"] and withheld == 4  # the "e" that would spell "safe" is withheld
    account = template(evidence)
    assert enforce(account, evidence.citations).dropped == ()
    assert "mutate" in account and "kernel" in account and "bulletproof" not in account and "ZZ9" not in account


def test_when_every_name_is_withheld_the_line_still_says_that_checks_were_declined(tmp_path):
    run = _run()
    run["ghost_scan"]["declined"] = ["safe", "approved"]
    evidence = load(_write(run, tmp_path))
    account = template(evidence)
    assert enforce(account, evidence.citations).dropped == ()
    assert "- [G] Ghost declined 2 check(s): 2 name(s) not shown here because" in account
    assert "A declined check was not run, so the absence of findings from it means nothing." in account


def test_a_plain_list_is_unchanged(tmp_path):
    run = _run()
    evidence = load(_write(run, tmp_path))
    assert declined_checks(run["ghost_scan"]) == (SEVEN, 0)
    assert "[G] Ghost declined 7 check(s): " + ", ".join(SEVEN) + "." in template(evidence)
    run2 = copy.deepcopy(run)
    run2["ghost_scan"]["declined"] = []
    assert declined_checks(run2["ghost_scan"]) == ([], 0)


def test_a_name_that_denies_a_label_is_still_shown(tmp_path):
    """The oath keeps a label that is plainly denied, so such a name is not withheld: the rule is the oath's."""
    run = _run()
    run["ghost_scan"]["declined"] = ["mutate", "not safe"]
    assert declined_checks(run["ghost_scan"]) == (["mutate", "not safe"], 0)
