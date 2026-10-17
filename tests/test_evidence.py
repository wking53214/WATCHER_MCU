"""A run record becomes a citation index; nothing is interpreted, everything citable is named."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from watcher.evidence import UnreadableRecord, forbidden_paths, index, load

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


def _run() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_the_real_record_indexes_every_kind_of_thing():
    c = index(_run())
    kinds = {cit.kind for cit in c.values()}
    assert {"decision", "verdict", "note", "cycle", "finding", "unmeasured", "ghost_scan", "versions", "join"} <= kinds
    assert c["R"].text.startswith("decision ACCEPT_UNVERIFIED")
    assert "INSUFFICIENT" in c["V"].text
    assert c["U"].text == "not measured: nothing listed in the record"
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


WARDEN_RUN = Path(__file__).parent / "fixtures" / "warden_tagteam_seats_run.json"


def test_who_took_part_includes_the_seats_warden_names():
    """The record Warden's own writer produced (`_run_team`) names the instruments in `versions` and the
    Drafter, Burnish and Judge seats in `versions.seats`. All of them took part; the account says so."""
    run = json.loads(WARDEN_RUN.read_text(encoding="utf-8"))
    assert set(run["versions"]["seats"]) == {"drafter", "finisher", "judge"}
    text = index(run)["W"].text
    for name in ("warden 0.12.0 at 2cf0eeccf839", "ghost_tools 1.9.1 at dd1b8039a9b3", "swizzle 0.7.1 at 9eb2a10ed1a0",
                 "assay 0.10.0 at 4da3919f19a0",
                 "drafter seat drafter.seat:Drafter 0.1.0 at cd4235e063ff",
                 "finisher seat burnish.finisher:Burnish 0.2.0 at a814159947f7",
                 "judge seat judge.seat:Judge 0.3.0 at 86c55b551534"):
        assert name in text, name


def test_a_seat_that_was_not_loaded_is_not_listed():
    run = json.loads(WARDEN_RUN.read_text(encoding="utf-8"))
    run["versions"]["seats"]["drafter"] = None
    text = index(run)["W"].text
    assert "drafter seat" not in text and "judge seat" in text


def test_the_template_account_names_the_seats(tmp_path):
    from watcher.narrate import template
    from watcher.oath import enforce

    e = load(WARDEN_RUN)
    account = template(e)
    assert "judge seat judge.seat:Judge" in account and "finisher seat burnish.finisher:Burnish" in account
    out = enforce(account, e.citations)
    assert out.dropped == ()
