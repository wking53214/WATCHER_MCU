"""A run record becomes a citation index; nothing is interpreted, everything citable is named."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from watcher.evidence import Evidence, UnreadableRecord, forbidden_paths, index, load

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


WARDEN_0_13_2_RUN = Path(__file__).parent / "fixtures" / "warden_0_13_2_record.json"


def test_a_real_0_13_2_record_names_a_real_assay_version():
    """A trimmed record from a real `warden tagteam` (Warden 0.13.2 with the tested ghost_tools, SWIZZLE and
    ASSAY; paths neutralised). Warden 0.13.2 reads ASSAY's dynamic version, so the account prints it."""
    run = json.loads(WARDEN_0_13_2_RUN.read_text(encoding="utf-8"))
    assert run["versions"]["assay"]["version"] == "0.11.1"
    text = index(run)["W"].text
    assert "assay 0.11.1 at 7b781cf9cb2b" in text and "assay None" not in text
    for name in ("warden 0.13.2", "ghost_tools 1.10.1 at 5d7a38638b12", "swizzle 0.8.1 at 123d7aba5d91"):
        assert name in text, name


def test_the_account_of_a_0_13_2_record_prints_the_assay_version(tmp_path):
    from watcher.narrate import template

    account = template(load(WARDEN_0_13_2_RUN))
    assert "assay 0.11.1" in account and "assay None" not in account


def test_module_fields_added_by_0_13_2_are_accepted_and_do_not_change_the_account():
    """`module` and `module_in_root` are new on versions.ghost_tools/swizzle/assay. The Watcher accepts fields it
    does not know: they are loaded, not cited, and the instrument folders stay forbidden to write into."""
    run = json.loads(WARDEN_0_13_2_RUN.read_text(encoding="utf-8"))
    for name in ("ghost_tools", "swizzle", "assay"):
        assert isinstance(run["versions"][name]["module"], str) and run["versions"][name]["module_in_root"] is True
    with_fields = index(run)["W"].text
    for name in ("ghost_tools", "swizzle", "assay"):
        del run["versions"][name]["module"], run["versions"][name]["module_in_root"]
    assert index(run)["W"].text == with_fields
    assert {p.name for p in forbidden_paths(run)} == {"ghost_tools", "SWIZZLE", "ASSAY"}


def test_unknown_extra_fields_in_versions_are_accepted(tmp_path):
    run = json.loads(WARDEN_0_13_2_RUN.read_text(encoding="utf-8"))
    for name in ("warden", "ghost_tools", "swizzle", "assay"):
        run["versions"][name]["some_future_field"] = {"nested": [1, 2, 3]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    assert "assay 0.11.1" in load(path).citations["W"].text


WARDEN_0_13_4_UNCOMMITTED = Path(__file__).parent / "fixtures" / "warden_0_13_4_uncommitted_record.json"


def test_a_run_that_allowed_an_unnamed_instrument_says_so_and_names_it_as_not_measured():
    """A real Warden 0.13.4 record (ghost_tools given as a copy with no git history, `--allow-uncommitted-instruments`):
    `allow_uncommitted_instruments` is true and `instrument_provenance` is in `unmeasured`. The account names it as
    not measured, says the flag was on, and carries Warden's own note naming the instrument."""
    from watcher.narrate import template

    run = json.loads(WARDEN_0_13_4_UNCOMMITTED.read_text(encoding="utf-8"))
    assert run["allow_uncommitted_instruments"] is True and "instrument_provenance" in run["unmeasured"]
    evidence = load(WARDEN_0_13_4_UNCOMMITTED)
    assert "instrument_provenance" in evidence.citations["U"].text
    assert evidence.citations["AU"].text == "allow_uncommitted_instruments: True"
    account = template(evidence)
    not_measured = account.split("## What was not", 1)[1].split("## Who took part", 1)[0]
    assert "[U] not measured: " in not_measured and "instrument_provenance" in not_measured
    assert "[AU] allow_uncommitted_instruments: True" in not_measured
    assert "ghost_tools. Their results are not verified measurements" in not_measured


def test_a_record_that_did_not_allow_it_has_no_such_line():
    from watcher.narrate import template

    run = json.loads(WARDEN_0_13_4_UNCOMMITTED.read_text(encoding="utf-8"))
    run["allow_uncommitted_instruments"] = False
    run["unmeasured"] = [name for name in run["unmeasured"] if name != "instrument_provenance"]
    run["notes"] = run["notes"][1:]
    account = template(Evidence(run=run, citations=index(run)))
    assert "[AU]" not in account and "instrument_provenance" not in account
