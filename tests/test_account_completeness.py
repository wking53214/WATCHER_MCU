"""The template account says everything the record says about what happened and what was not done.

It used to show only cycles 1 to 3 (the default allows ten), and it said nothing of `swizzle_sound: false`, of a note
that SWIZZLE's proofs FAILED, of `put_back`, `finished`, `drafter_skipped`, `informational`, or of the ids of the
findings. The records here are real ones (`swizzle_joined_run.json` has put_back, finished and drafter_skipped set;
`warden_0_13_6_declined_record.json` has neither) with the fields a case is about set by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from watcher.cli import main
from watcher.evidence import load
from watcher.narrate import FINDING_IDS_SHOWN, template
from watcher.oath import enforce

FIXTURES = Path(__file__).parent / "fixtures"
JOINED = FIXTURES / "swizzle_joined_run.json"
DECLINED = FIXTURES / "warden_0_13_6_declined_record.json"


def _run(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _account(run: dict[str, Any], tmp_path: Path) -> str:
    record = tmp_path / "run.json"
    record.write_text(json.dumps(run), encoding="utf-8")
    evidence = load(record)
    raw = template(evidence)
    assert enforce(raw, evidence.citations).dropped == (), "the oath keeps every line of the template"
    return raw


def _section(account: str, name: str) -> str:
    return account.split(f"## {name}", 1)[1].split("\n## ", 1)[0]


def _cycles(count: int, observed_last: int = 0) -> list[dict[str, Any]]:
    return [{"number": n, "outcome": "APPLIED" if n < count else "NOTHING_TO_PROPOSE",
             "observed": 3 if n < count else observed_last} for n in range(1, count + 1)]


def test_every_cycle_of_the_record_is_listed_not_only_the_first_three(tmp_path):
    run = _run(DECLINED)
    run["cycles"] = _cycles(10)
    happened = _section(_account(run, tmp_path), "What happened")
    for n in range(1, 11):
        assert f"- [C{n}] cycle {n}: " in happened
    assert "- [C10] cycle 10: NOTHING_TO_PROPOSE; Ghost observed 0 finding(s)" in happened
    assert happened.index("[C1]") < happened.index("[C2]") < happened.index("[C10]")


def test_a_run_of_more_cycles_than_the_default_allows_is_still_listed_whole(tmp_path):
    run = _run(DECLINED)
    run["cycles"] = _cycles(25)
    happened = _section(_account(run, tmp_path), "What happened")
    assert len(re.findall(r"^- \[C\d+\] cycle ", happened, flags=re.MULTILINE)) == 25


def test_a_record_with_no_cycles_lists_none(tmp_path):
    run = _run(DECLINED)
    run["cycles"] = []
    assert "- [C" not in _account(run, tmp_path)


def test_swizzle_sound_false_and_a_failed_proofs_note_are_in_what_was_not(tmp_path):
    run = _run(DECLINED)
    run["swizzle_sound"] = False
    run["notes"].append("SWIZZLE proofs: not sound (exit 1): 3 FAILED, 9 passed")
    account = _account(run, tmp_path)
    not_done = _section(account, "What was not")
    assert "- [SS] swizzle_sound is false: SWIZZLE's proofs did not hold." in not_done
    assert "3 FAILED, 9 passed" in not_done
    assert "swizzle_sound" not in _section(account, "What was measured")
    assert "swizzle_sound" not in _section(_account(_run(DECLINED), tmp_path), "What was not")


def test_swizzle_sound_true_is_a_measurement_and_null_is_said_to_be_no_result(tmp_path):
    run = _run(DECLINED)
    assert run["swizzle_sound"] is True
    measured = _section(_account(run, tmp_path), "What was measured")
    assert "- [SS] swizzle_sound is true: SWIZZLE's proofs held." in measured
    run["swizzle_sound"] = None
    account = _account(run, tmp_path)
    assert "no result of SWIZZLE's proofs" in _section(account, "What was not")
    del run["swizzle_sound"]
    assert "[SS]" not in _account(run, tmp_path)


def test_a_proof_note_that_failed_is_shown_once(tmp_path):
    run = _run(DECLINED)
    run["notes"].append("Rule 7 suite converged: 3 FAILED, 9 passed")  # a suite line is already "measured"
    account = _account(run, tmp_path)
    assert account.count("3 FAILED, 9 passed") == 1
    assert "3 FAILED, 9 passed" in _section(account, "What was measured")


def test_put_back_and_finished_are_said_when_true_and_only_then(tmp_path):
    account = _account(_run(JOINED), tmp_path)
    happened = _section(account, "What happened")
    assert "- [PB] put_back is true: edits had been made and the whole tree was restored because the run did not end " \
           "accepted." in happened
    assert "- [FN] finished is true: the finishing change was applied." in happened
    plain = _account(_run(DECLINED), tmp_path)
    assert "[PB]" not in plain and "[FN]" not in plain


def test_drafter_skipped_and_informational_lines_are_information_not_gaps(tmp_path):
    run = _run(JOINED)
    assert len(run["drafter_skipped"]) == 3
    run["informational"] = ["ghost_version_unverified"]
    account = _account(run, tmp_path)
    info = _section(account, "Information, not gaps")
    assert info.count("(information, not a gap): ") == 4
    assert "- [D1] The Drafter left a finding alone (information, not a gap): skipped ghost-908a8251eb9f: " in info
    assert "- [I1] Warden noted (information, not a gap): ghost_version_unverified" in info
    assert "[D1]" not in _section(account, "What was not") and "[I1]" not in _section(account, "What was not")
    assert "Information, not gaps" not in _account(_run(DECLINED), tmp_path)


def test_finding_ids_are_shown_with_the_count_when_the_record_has_them(tmp_path):
    run = _run(DECLINED)
    ids = list(dict.fromkeys(run["observed"]))
    account = _account(run, tmp_path)
    measured = _section(account, "What was measured")
    start = next(line for line in measured.splitlines() if "observed at the start" in line)
    assert start.startswith("- [" + ids[0] + "][" + ids[1] + "]")
    assert f"({len(ids)} distinct)" in start and ids[0] in start
    assert f"{len(ids) - FINDING_IDS_SHOWN} more are not shown, the record lists them" in start
    assert start.count("[ghost-") == FINDING_IDS_SHOWN and ids[FINDING_IDS_SHOWN - 1] in start
    assert ids[FINDING_IDS_SHOWN] not in start
    assert any("observed at the end" in line for line in measured.splitlines())


def test_a_short_list_of_ids_is_shown_whole_and_an_empty_one_not_at_all(tmp_path):
    run = _run(DECLINED)
    run["observed"] = ["ghost-aaaa", "ghost-bbbb", "ghost-aaaa"]
    run["reobserved"] = []
    account = _account(run, tmp_path)
    expected = ("- [ghost-aaaa][ghost-bbbb] Ghost finding id(s) observed at the start (2 distinct): "
                "ghost-aaaa, ghost-bbbb.")
    assert expected in account
    assert "observed at the end" not in account


def test_an_id_that_cannot_be_cited_is_not_named(tmp_path):
    run = _run(DECLINED)
    run["observed"] = ["ghost-ok", "R", "bad id\n## Injected", "[x]", ""]
    account = _account(run, tmp_path)
    line = next(ln for ln in account.splitlines() if "observed at the start" in ln)
    assert line == "- [ghost-ok] Ghost finding id(s) observed at the start (1 distinct): ghost-ok."
    assert "## Injected" not in account


def test_the_whole_account_of_a_real_record_keeps_every_line_and_the_command_line_agrees(tmp_path, capsys):
    out = tmp_path / "account.md"
    assert main(["narrate", str(JOINED), "--no-model", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Nothing. Every sentence cited the record" in text
    assert "[PB]" in text and "[FN]" in text and "[D3]" in text
    assert capsys.readouterr().err.count("account written") == 1
