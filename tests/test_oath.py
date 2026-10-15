"""The oath is enforced mechanically: cited sentences survive, everything else is dropped with a reason."""
from __future__ import annotations

import pytest

from watcher.oath import cited_ids, enforce, sentences, status_claim

INDEX = {"R": object(), "N1": object(), "ghost-1b3766cb418b": object()}


def test_a_sentence_without_a_citation_is_dropped_and_says_so():
    out = enforce("The run went well. It ended ACCEPT [R].", INDEX)
    assert out.kept == ("It ended ACCEPT [R].",)
    assert len(out.dropped) == 1 and out.dropped[0].reason == "cites nothing in the record"


def test_a_citation_that_is_not_in_the_record_drops_the_sentence():
    out = enforce("The suite was green [S9]. Ghost found one thing [ghost-1b3766cb418b].", INDEX)
    assert out.kept == ("Ghost found one thing [ghost-1b3766cb418b].",)
    assert out.dropped[0].reason == "cites what is not in the record: S9"


@pytest.mark.parametrize("line", [
    "This repository is production ready [R].",
    "It is battle-tested [N1].",
    "Not production-ready yet [R].",
    "Produc­tion ready [R].",
    "**Fully** tested [N1].",
    "We have 100 % coverage [R].",
    "Enterprise grade [R].",
])
def test_a_status_claim_of_its_own_is_dropped_even_when_cited(line):
    out = enforce(line, INDEX)
    assert out.kept == () and out.dropped[0].reason.startswith("status claim of its own")


def test_a_short_heading_is_structure_not_a_claim():
    out = enforce("## What happened\nIt ended ACCEPT [R].\n## " + "x" * 90, INDEX)
    assert out.kept == ("## What happened", "It ended ACCEPT [R].")
    assert len(out.dropped) == 1


def test_a_heading_with_a_status_claim_is_still_dropped():
    out = enforce("## Production ready", INDEX)
    assert out.kept == () and "status claim" in out.dropped[0].reason


def test_bullets_and_paragraphs_split_as_a_reader_would():
    text = "- first [R]\n- second\nOne thing [N1]. Another thing. A third [R]!"
    assert sentences(text) == ["- first [R]", "- second", "One thing [N1].", "Another thing.", "A third [R]!"]
    out = enforce(text, INDEX)
    assert out.kept == ("- first [R]", "One thing [N1].", "A third [R]!")


def test_status_claim_reads_through_emphasis_and_invisible_characters():
    assert status_claim("__Battle__-_tested_") and status_claim("Pro​duction ready")
    assert status_claim("The feature is ready.") == ""


def test_cited_ids_are_in_first_seen_order_without_repeats():
    assert cited_ids(["a [R] b [N1]", "c [R]", "d [ghost-1b3766cb418b]"]) == ["R", "N1", "ghost-1b3766cb418b"]


def test_ratio_counts_kept_against_all():
    out = enforce("x [R]. y. z [R].", INDEX)
    assert out.ratio == pytest.approx(2 / 3)
    assert enforce("", INDEX).ratio == 1.0
