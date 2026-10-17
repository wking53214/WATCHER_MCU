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


# --- the audited bypasses, and the ones found beside them ------------------------------------------------------

@pytest.mark.parametrize("line", [
    # other dashes (U+2010 hyphen, U+2011, en and em dash, minus sign, figure dash, horizontal bar, wave dash)
    "This is production\u2010ready [R].",
    "This is production\u2011ready [R].",
    "This is production\u2013ready [R].",
    "This is production\u2014ready [R].",
    "This is production\u2212ready [R].",
    "This is production\u2012ready [R].",
    "This is production\u2015ready [R].",
    "This is production\u301cready [R].",
    "This is battle\u2010tested [R].",
    "This is enterprise\u2013grade [R].",
    # lookalike letters: Cyrillic, Greek, small capitals, fullwidth
    "This is produ\u0441tion ready [R].",
    "This is pr\u043eduction ready [R].",
    "This is \u0440roduction ready [R].",
    "This is production r\u0435ady [R].",
    "This is production re\u0430dy [R].",
    "This is \u03c1roduction ready [R].",
    "This is pr\u03bfduction ready [R].",
    "This is \u1d18\u0280\u1d0f\u1d05\u1d1c\u1d04\u1d1b\u026a\u1d0f\u0274 \u0280\u1d07\u1d00\u1d05\u028f [R].",
    "This is \uff50\uff52\uff4f\uff44\uff55\uff43\uff54\uff49\uff4f\uff4e \uff52\uff45\uff41\uff44\uff59 [R].",
    "This is " + "".join(chr(0x1D41A + ord(c) - 97) for c in "production") + " ready [R].",  # mathematical bold
    # phrase order and wording
    "The code is ready for production [R].",
    "It is Ready For Prod [N1].",
    "Ready to ship [R].",
    "Release-ready [R].",
    "It is production-grade [R].",
    "It is production grade [R].",
    "It is production quality [R].",
    "It is production\u2011proven [R].",
    "Enterprise-ready [R].",
    "It is battle tested [R].",
    "It is well-tested [R].",
    "It is thoroughly tested [R].",
    "It is fully verified [R].",
    "Complete test coverage [R].",
    "100 percent coverage [R].",
    "It is bulletproof [R].",
    "It is bullet-proof [R].",
    "It is hardened [R].",
    "It is rock solid [R].",
    "It is bug-free [R].",
    "It is flawless [R].",
    "There are no known bugs [R].",
    "Safe to deploy [R].",
    # a cited claim is still a claim
    "The run passed and is safe [R].",
    "The change is safe [N1].",
    "The run is secure [R].",
    "Nothing here is unsafe, it is safe [R].",
    # markup, entities, escapes and separators that a rendered page would hide
    "This is production&#8208;ready [R].",
    "This is production&ndash;ready [R].",
    "This is production&nbsp;ready [R].",
    "This is production<wbr>ready [R].",
    "This is production<!-- x -->ready [R].",
    "This is [production](https://example.invalid) ready [R].",
    "This is production\\-ready [R].",
    "This is production.ready [R].",
    "This is production/ready [R].",
    "This is `production` _ready_ [R].",
    "This is pro\u0336duction ready [R].",
    "This is pr\u00f3duction ready [R].",
    "This is production\u200b ready [R].",
    "This is production \u202eready [R].",
    # digits and symbols for letters
    "This is pr0duction r3ady [R].",
    "This is pr0duct10n-r3@dy [R].",
    "This is s4fe [R].",
    "This is b4ttle-t3sted [R].",
    "This is f\u03c5lly tested [R].",
])
def test_status_claims_are_dropped_through_every_disguise(line):
    out = enforce(line, INDEX)
    assert out.kept == (), line
    assert out.dropped[0].reason.startswith("status claim of its own"), line


@pytest.mark.parametrize("line", [
    "The run ended ACCEPT_UNVERIFIED [R].",
    "The Judge said INSUFFICIENT [N1].",
    "1117 passed, 0 failed, 5 skipped [N1].",
    "Ghost observed 213 findings [R].",
    "The reproduction is ready to read [R].",
    "Safety was not measured [R].",
    "The change is unsafe to assume [R].",
    "Ghost found one thing [ghost-1b3766cb418b].",
    "The suite covered 100 files [N1].",
    "The production folder was not touched [R].",
    "Nothing was released [R].",
])
def test_honest_sentences_are_not_caught_by_the_wider_net(line):
    out = enforce(line, INDEX)
    assert out.kept == (line,) and out.dropped == ()


def test_the_reason_names_the_label_as_a_person_reads_it():
    out = enforce("It is production\u2010ready [R].", INDEX)
    assert out.dropped[0].reason == "status claim of its own: 'production-ready'"


def test_a_real_percent_is_still_a_number_to_the_first_reading():
    assert status_claim("100% coverage") and status_claim("100 % test coverage")
    assert status_claim("coverage is 87%") == ""
