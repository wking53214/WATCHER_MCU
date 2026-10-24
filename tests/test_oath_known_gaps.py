"""Known gaps of the status-claim filter, held so the README cannot drift from what the code does.

The filter is a denylist. A paraphrase that is not on it passes when it cites the record, however much it reads as a
grade. These six were tried against the real filter in the round-6 audit and are kept today. This file documents that
as a KNOWN GAP: it asserts the current behaviour. If a phrase starts being dropped, the test fails; then remove the
phrase here and from KNOWN DEFECTS in the README (and add the new label to `watcher/oath.py`). It is not a promise that
the phrases are acceptable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from watcher.evidence import load
from watcher.oath import enforce

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"
README = (ROOT / "README.md").read_text(encoding="utf-8")

PARAPHRASES = (
    "All green",
    "Everything checks out, nothing left to do",
    "This is solid",
    "No further action is required",
    "Nothing is wrong",
    "Cleared for release",
)


@pytest.mark.parametrize("phrase", PARAPHRASES)
def test_a_cited_paraphrase_that_reads_as_a_grade_is_kept_today(phrase):
    evidence = load(FIXTURE)
    result = enforce(f"{phrase} [R].", evidence.citations)
    assert result.kept == (f"{phrase} [R].",), "now dropped: move it out of the known gap (README KNOWN DEFECTS)"


def test_the_readme_lists_exactly_these_paraphrases_as_a_known_defect():
    known = README.split("## KNOWN DEFECTS", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r'"([^"]+) \[R\]\."', " ".join(known.split()))
    assert listed == list(PARAPHRASES)


def test_cns_has_the_record_methods_the_readme_says_the_watcher_does_not_call():
    from cns.run import RunRecord

    for name in ("declined", "gaps", "dirty_parts"):
        assert hasattr(RunRecord, name), name
    source = (ROOT / "watcher" / "evidence.py").read_text(encoding="utf-8")
    assert "RunRecord.from_dict" in source
    assert ".gaps(" not in source and ".dirty_parts(" not in source and "record.declined" not in source
