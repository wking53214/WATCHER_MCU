"""The account says what a real Warden record says it did not do, from the record only.

`warden_0_13_6_declined_record.json` is a real record: a throwaway git target run through the whole circuit with
`warden tagteam TARGET --stack STACK --cns CNS --authorize x --reason y --scope documentation` (the way
`cns_composition.circuit_canary` runs it; the only edit is that the folder of the stack checkouts is shown as /stack).
Its `ghost_scan.declined` lists seven checks Warden did not run, `converged` is true while Ghost still observed 27
findings, and its `unmeasured` list is empty. The first version of the account said "not measured: nothing listed" and
"gaps: none" and dropped Warden's note that converged is not zero findings.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from watcher.cli import main
from watcher.evidence import DIRTY_MARK, UnreadableRecord, load
from watcher.narrate import prompt_for, template
from watcher.oath import enforce

REAL = Path(__file__).parent / "fixtures" / "warden_0_13_6_declined_record.json"
SEVEN = ["mutate", "kernel", "structure", "tests", "project", "secrets", "correlate"]


def _run() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(REAL.read_text(encoding="utf-8"))
    return result


def _load(run: dict[str, Any], tmp_path: Path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    return load(path)


def _section(account: str, name: str) -> str:
    return account.split(f"## {name}", 1)[1].split("\n## ", 1)[0]


def test_the_fixture_is_the_real_shape_the_audit_found():
    run = _run()
    assert run["ghost_scan"]["declined"] == SEVEN and run["ghost_scan"]["gaps"] == []
    assert run["unmeasured"] == [] and run["converged"] is True and run["cycles"][0]["observed"] == 27
    assert any("not zero findings" in note for note in run["notes"])


def test_the_account_names_every_declined_check_and_says_it_was_not_run():
    evidence = load(REAL)
    account = template(evidence)
    not_measured = _section(account, "What was not")
    assert "[G] Ghost declined 7 check(s): " + ", ".join(SEVEN) + "." in not_measured
    assert "A declined check was not run, so the absence of findings from it means nothing." in not_measured
    assert "declined, so not run: " + ", ".join(SEVEN) in evidence.citations["G"].text


def test_the_account_carries_that_converged_is_not_zero_findings():
    account = template(load(REAL))
    happened = _section(account, "What happened")
    assert "[CV] Converged is true and converged is not zero findings: Ghost still observed 27 finding(s) in " \
           "cycle 1 [C1]." in happened
    assert "Converged means no proposals left, not zero findings." in _section(account, "What was not")


def test_the_whole_account_passes_the_oath_and_the_oath_is_not_loosened():
    evidence = load(REAL)
    enforced = enforce(template(evidence), evidence.citations)
    assert enforced.dropped == ()
    kept = "\n".join(enforced.kept)
    assert "A declined check was not run" in kept and "not zero findings" in kept
    # the denylist still drops a status claim written in the same voice
    own = enforce("The run is safe [R]. The declined checks are all clear [G].", evidence.citations)
    assert own.kept == () and len(own.dropped) == 2


def test_the_model_is_shown_the_declined_checks_and_the_dirty_flag(tmp_path):
    run = _run()
    run["versions"]["warden"]["dirty"] = True
    prompt = prompt_for(_load(run, tmp_path))
    assert "declined, so not run: " + ", ".join(SEVEN) in prompt
    assert f"warden 0.13.6 at 0c1ea567f0b6 ({DIRTY_MARK})" in prompt


def test_nothing_is_added_when_the_record_declined_nothing(tmp_path):
    run = _run()
    run["ghost_scan"]["declined"] = []
    evidence = _load(run, tmp_path)
    assert "declined" not in evidence.citations["G"].text and "declined" not in template(evidence)
    del run["ghost_scan"]["declined"]
    assert "declined" not in template(_load(run, tmp_path))


def test_a_declined_list_of_the_wrong_shape_is_refused_by_name(tmp_path):
    run = _run()
    run["ghost_scan"]["declined"] = "mutate"
    with pytest.raises(UnreadableRecord, match=r"ghost_scan\.declined is str, not a list"):
        _load(run, tmp_path)


def test_converged_with_no_findings_seen_adds_no_claim_of_its_own(tmp_path):
    run = _run()
    run["cycles"][0]["observed"] = 0
    assert "[CV]" not in template(_load(run, tmp_path))
    run = _run()
    run["converged"] = False
    assert "[CV]" not in template(_load(run, tmp_path))


def test_dirty_parts_are_named_wherever_the_record_flags_them(tmp_path):
    run = _run()
    run["versions"]["warden"]["dirty"] = True
    run["versions"]["seats"]["judge"]["dirty"] = True
    run["versions"]["joins"][2]["dirty"] = True
    evidence = _load(run, tmp_path)
    assert evidence.citations["W"].text.count(DIRTY_MARK) == 2
    assert evidence.citations["J3"].text.endswith(f"({DIRTY_MARK})")
    assert DIRTY_MARK not in evidence.citations["J1"].text
    account = template(evidence)
    line = next(ln for ln in account.splitlines() if "(dirty: true)" in ln)
    assert line.startswith("- [W][J3] ") and "in warden, judge seat, join /stack/ASSAY;" in line
    assert "the commit shown for each is not the whole of what ran." in line
    assert f"({DIRTY_MARK})" in _section(account, "Who took part")
    enforced = enforce(account, evidence.citations)
    assert enforced.dropped == ()


def test_a_flag_that_is_not_true_is_not_reported_as_dirty(tmp_path):
    original = _run()
    assert "dirty: true" not in template(load(REAL))
    run = copy.deepcopy(original)
    run["versions"]["warden"]["dirty"] = None
    run["versions"]["swizzle"]["dirty"] = "yes"
    evidence = _load(run, tmp_path)
    assert DIRTY_MARK not in evidence.citations["W"].text and "dirty: true" not in template(evidence)


def test_the_command_line_account_says_it_too(tmp_path, capsys):
    out = tmp_path / "account.md"
    assert main(["narrate", str(REAL), "--no-model", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Ghost declined 7 check(s)" in text and "converged is not zero findings" in text
    assert "Nothing. Every sentence cited the record" in text
    assert capsys.readouterr().err.count("account written") == 1


# [CV] describes the FINAL cycle: the earlier cycles are listed as [C<n>] lines, and a cycle that observed findings
# before the last one is not what the run ended with. The first version took the last cycle that had observed
# anything, so a run whose cycle 1 observed 2 findings and whose cycle 2 observed none was said to have "still
# observed 2 in cycle 1".
TAGTEAM = Path(__file__).parent / "fixtures" / "warden_tagteam_seats_run.json"


def _cv_line(run: dict[str, Any], tmp_path: Path) -> str | None:
    lines = [ln for ln in template(_load(run, tmp_path)).splitlines() if ln.startswith("- [CV]")]
    assert len(lines) <= 1
    return lines[0] if lines else None


def _cycles(*observed: int) -> list[dict[str, Any]]:
    return [{"number": n, "outcome": "APPLIED", "observed": k} for n, k in enumerate(observed, start=1)]


def test_a_real_clean_run_whose_final_cycle_observed_nothing_says_nothing_of_findings_left(tmp_path):
    run = json.loads(TAGTEAM.read_text(encoding="utf-8"))
    assert run["converged"] is True and [c["observed"] for c in run["cycles"]] == [1, 0]
    assert _cv_line(run, tmp_path) is None


def test_cycle_one_observing_two_and_cycle_two_observing_none_makes_no_false_claim(tmp_path):
    run = _run()
    run["cycles"] = _cycles(2, 0)
    assert _cv_line(run, tmp_path) is None
    assert "still observed 2" not in template(_load(run, tmp_path))


def test_the_line_names_the_final_cycle_and_what_it_observed(tmp_path):
    run = _run()
    run["cycles"] = _cycles(5, 3, 1)
    assert _cv_line(run, tmp_path) == ("- [CV] Converged is true and converged is not zero findings: Ghost still "
                                       "observed 1 finding(s) in cycle 3 [C3].")
    run["cycles"] = _cycles(0, 0, 4)
    line = _cv_line(run, tmp_path)
    assert line is not None and "observed 4 finding(s) in cycle 3 [C3]" in line
    run["cycles"] = _cycles(*range(1, 11))
    line = _cv_line(run, tmp_path)
    assert line is not None and "observed 10 finding(s) in cycle 10 [C10]" in line


def test_the_line_follows_the_list_order_not_the_cycle_numbers(tmp_path):
    run = _run()
    run["cycles"] = [{"number": 2, "outcome": "APPLIED", "observed": 6},
                     {"number": 1, "outcome": "APPLIED", "observed": 0}]
    assert _cv_line(run, tmp_path) is None  # the last cycle in the record observed none


def test_a_final_cycle_with_no_count_adds_no_claim(tmp_path):
    run = _run()
    run["cycles"] = [{"number": 1, "outcome": "APPLIED", "observed": 4},
                     {"number": 2, "outcome": "APPLIED", "observed": None}]
    assert _cv_line(run, tmp_path) is None
    run["cycles"] = []
    assert _cv_line(run, tmp_path) is None
