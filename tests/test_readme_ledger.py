"""The README keeps the sections it promises, and what it names exists.

A claim of "works" in the README names a test file, a test, a CI job or a command. This file fails if a named test is
gone, if the ledger cites a version or a date the CHANGELOG does not have, if a number the README states drifts from
the code, or if marketing words come back.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from watcher import evidence, narrate, oath

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

REQUIRED_HEADINGS = (
    "## WHAT THIS IS",
    "## HOW TO INSTALL AND RUN",
    "## WHAT WORKS",
    "## WHAT DOES NOT WORK / NOT PROVEN",
    "## KNOWN DEFECTS",
    "## WHAT BROKE AND HOW IT WAS FIXED",
    "## SELF-HOSTING",
    "## CEILINGS CODE CANNOT FIX",
)
BANNED_WORDS = ("robust", "powerful", "production-ready", "production ready", "seamless", "comprehensive", "blazing",
                "enterprise", "battle-tested", "state-of-the-art")


def section(title: str) -> str:
    start = README.index(f"## {title}\n")
    following = re.search(r"^## ", README[start + 1:], re.MULTILINE)
    return README[start:start + 1 + following.start()] if following else README[start:]


def test_the_readme_keeps_the_sections_it_promises_once_each_in_order():
    positions = [README.index(heading + "\n") for heading in REQUIRED_HEADINGS]
    assert positions == sorted(positions)
    assert all(README.count(heading + "\n") == 1 for heading in REQUIRED_HEADINGS)


def test_every_test_the_readme_names_exists():
    named = set(re.findall(r"`(tests/test_\w+\.py)(?:::(\w+))?`", README))
    assert named, "the README names no tests"
    for path, function in named:
        source = (ROOT / path).read_text(encoding="utf-8")
        if function:
            assert re.search(rf"^\s*(?:async )?def {function}\(", source, re.MULTILINE), f"{path}::{function}"


def test_every_ledger_entry_names_a_guard_or_says_no_test_yet():
    ledger = section("WHAT BROKE AND HOW IT WAS FIXED")
    entries = re.split(r"\n(?=- \*)", ledger)[1:]
    assert entries
    for entry in entries:
        text = " ".join(entry.split())
        assert "Guard:" in text or "no test" in text.lower() or "No test" in text, text[:80]


def test_every_version_and_date_in_the_ledger_matches_the_changelog():
    ledger = section("WHAT BROKE AND HOW IT WAS FIXED")
    headings = dict(re.findall(r"^## \[([^\]]+)\] - (\d{4}-\d{2}-\d{2})", CHANGELOG, re.MULTILINE))
    cited = re.findall(r"^\*\*(\d+\.\d+\.\d+)\*\* \((\d{4}-\d{2}-\d{2})\)$", ledger, re.MULTILINE)
    assert cited
    for version, date in cited:
        assert headings.get(version) == date, (version, date)
    mentioned = set(re.findall(r"\b0\.\d+\.\d+\b", ledger))
    assert mentioned <= set(headings), mentioned - set(headings)
    assert [v for v, _ in cited] == sorted((v for v, _ in cited), key=lambda v: tuple(map(int, v.split("."))),
                                           reverse=True), "newest first"


def test_every_ci_job_the_readme_names_is_in_the_workflow():
    jobs = set(re.findall(r"`(check|warden-e2e|coinstall-warden)`", README))
    assert jobs == {"check", "warden-e2e", "coinstall-warden"}
    for job in jobs:
        assert re.search(rf"^  {job}:", WORKFLOW, re.MULTILINE), job


def test_the_numbers_the_readme_states_are_the_numbers_in_the_code():
    flat = " ".join(README.split())
    assert f"the first {narrate.FINDING_IDS_SHOWN} of each" in flat
    assert f"string over {inspect.signature(evidence.clean).parameters['limit'].default} characters is cut" in flat
    assert "(eight words each side)" in flat and oath._EDGE_WORDS == 8
    assert "within four words" in flat or "four words before it" in flat
    assert oath._NEGATION_WINDOW == 4


def test_the_readme_uses_no_marketing_words_outside_quoted_labels():
    """The oath table quotes the labels it drops; those quotes are the only place such words may stand."""
    unquoted = "\n".join(re.sub(r'"[^"\n]*"', "", line) for line in README.splitlines())
    lowered = unquoted.lower()
    found = [word for word in BANNED_WORDS if word in lowered]
    assert not found, found


#: Copied from the CNS repository, docs/evidence/SELFHOSTING_2026-10-23.md (WATCHER_MCU rows, run 1 and run 2). The
#: README states exactly these, so a change to either must change both.
SELFHOSTING_COMMIT = "b25d8522301005ba764783927f43abfeb9f18f5c"
SELFHOSTING_VERSION = "0.3.8"
SELFHOSTING_SUITE = "701 passed with 0 skipped"
SELFHOSTING_FINDINGS = "41 findings at the start and 41 at the end"
SELFHOSTING_DECLINED = ("mutate", "kernel", "structure", "tests", "project", "secrets", "correlate")


def test_self_hosting_holds_the_recorded_numbers_and_says_what_the_record_does_not_mean():
    text = " ".join(section("SELF-HOSTING").split())
    assert "docs/evidence/SELFHOSTING_2026-10-23.md" in text and "until it is merged" in text
    assert SELFHOSTING_COMMIT in text and f"version {SELFHOSTING_VERSION}" in text
    assert SELFHOSTING_SUITE in text and SELFHOSTING_FINDINGS in text
    assert "7 checks were declined" in text and "7 gaps" in text
    assert all(name in text for name in SELFHOSTING_DECLINED) and len(SELFHOSTING_DECLINED) == 7
    assert "decision ACCEPT" in text and "Burnish 0.3.11" in text and "Burnish 0.3.12" in text
    assert "does not mean there are no secrets, no weak tests" in text
    assert "no fresh run" not in text


def test_the_readme_does_not_say_whether_release_tags_exist():
    ceilings = " ".join(section("CEILINGS CODE CANNOT FIX").split())
    assert "Check the repository's tags and releases on GitHub for what exists." in ceilings
    without_warden_lines = re.sub(r"Warden \d+\.\d+\.\d+ \(not tagged\)", "", README)
    assert not re.search(r"(?i)\b(no release|no tag|not tagged|tags? exist)", without_warden_lines), (
        "a claim about tags goes stale; the Warden commit line is the only exception")
    preamble = CHANGELOG.split("\n## [", 1)[0]
    assert not re.search(r"(?i)\b(no release|no tag|not tagged|tags? exist)", preamble), preamble


def test_the_install_section_never_installs_a_bare_name():
    install = section("HOW TO INSTALL AND RUN")
    for command in re.findall(r"^pip install (.+)$", install, re.MULTILINE):
        assert command.split()[0] in {"-e"}, command
