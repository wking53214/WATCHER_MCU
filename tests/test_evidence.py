"""A run record becomes a citation index; nothing is interpreted, everything citable is named."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from watcher.evidence import UnreadableRecord, forbidden_paths, index, load

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


def _run() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_the_real_record_indexes_every_kind_of_thing():
    c = index(_run())
    kinds = {cit.kind for cit in c.values()}
    assert {"decision", "verdict", "note", "cycle", "finding", "unmeasured", "ghost_scan", "versions", "join"} <= kinds
    assert c["R"].text.startswith("decision ACCEPT_UNVERIFIED")
    assert "INSUFFICIENT" in c["V"].text
    assert c["U"].text == "not measured: nothing; every check ran"
    assert c["C1"].text == "cycle 1: NOTHING_TO_PROPOSE; Ghost observed 213 finding(s)"
    assert sum(1 for cit in c.values() if cit.kind == "join") == 6


def test_ids_are_stable_for_the_same_record():
    first = list(index(_run()))
    again = list(index(_run()))
    assert again == first
    assert first[:3] == ["R", "V", "N1"] and first[-1] == "CT"


def test_findings_keep_ghosts_own_ids_and_late_findings_are_marked():
    run = _run()
    run["observed"] = ["ghost-aaaa"]
    run["reobserved"] = ["ghost-aaaa", "ghost-bbbb"]
    c = index(run)
    assert c["ghost-aaaa"].text.endswith("at the start") and c["ghost-bbbb"].text.endswith("only at the end")


def test_long_text_is_cut_and_whitespace_collapsed():
    run = _run()
    run["notes"] = ["a   b\n\nc " + "x" * 600]
    assert len(index(run)["N1"].text) == 400 and index(run)["N1"].text.startswith("a b c x")


def test_forbidden_paths_are_the_governed_folder_and_every_checkout_the_record_names(tmp_path):
    run = _run()
    paths = forbidden_paths(run, tmp_path / "proj")
    assert paths[0] == (tmp_path / "proj").resolve()
    assert any(p.name == "ghost_tools" for p in paths) and any(p.name == "WARDEN" for p in paths)
    assert len(paths) == len(set(paths))


def test_load_refuses_what_is_not_a_record(tmp_path):
    (tmp_path / "x.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(UnreadableRecord, match="no 'decision'"):
        load(tmp_path / "x.json")
    (tmp_path / "y.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(UnreadableRecord, match="cannot be read"):
        load(tmp_path / "y.json")
    with pytest.raises(UnreadableRecord):
        load(tmp_path / "missing.json")


def test_load_gives_the_record_its_index_and_its_forbidden_paths(tmp_path):
    e = load(FIXTURE, tmp_path)
    assert e.run["decision"] == "ACCEPT_UNVERIFIED" and e.cited("R") is not None and e.cited("nope") is None
    assert tmp_path.resolve() in e.forbidden_paths


def test_a_record_is_read_only_through_the_cns_contract(tmp_path):
    """The Watcher reads the run record as cns.run/1 says it is, and refuses what it cannot read."""
    good = _run()
    (tmp_path / "good.json").write_text(json.dumps(good), encoding="utf-8")
    assert load(tmp_path / "good.json").run["schema"] == "cns.run/1"
    cases = [
        ("predates the contract", None, "missing schema"),
        ("another version", {"schema": "cns.run/0"}, "schema is 'cns.run/0'"),
        ("null reason", {"reason": None}, "reason is missing or null"),
        ("unknown decision", {"decision": "PROBABLY_FINE"}, "not one Warden ends a run with"),
    ]
    for label, change, message in cases:
        record = dict(good)
        if change is None:
            del record["schema"]
        else:
            record.update(change)
        path = tmp_path / (label.replace(" ", "_") + ".json")
        path.write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(UnreadableRecord, match=message):
            load(path)
