"""The oath is enforced mechanically: cited sentences survive, everything else is dropped with a reason."""
from __future__ import annotations

import re

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


# --- approvals, sign-offs and all-clears; letters set apart; bidirectional controls -----------------------------

RLO, LRO, PDF, RLI, PDI = "\u202e", "\u202d", "\u202c", "\u2067", "\u2069"


@pytest.mark.parametrize("line", [
    "Ship it [R].",
    "ship-it [R].",
    "LGTM [R].",
    "L.G.T.M [R].",
    "The change is approved [R].",
    "Approved [N1].",
    "This looks good [R].",
    "It looks good to me [R].",
    "The diff looked fine [N1].",
    "Looking solid [R].",
    "All clear [R].",
    "all good [R].",
    "There are no issues with this change [R].",
    "No issues found [R].",
    "Zero known problems [R].",
    "The code is trustworthy [R].",
    "Reliable and robust [R].",
    "It is dependable [R].",
    "OK for production use [R].",
    "ok to merge [N1].",
    "Okay for release [R].",
    "Good to go [R].",
    "good-to-go [R].",
    "This is g\u043e\u043ed to g\u043e [R].",  # Cyrillic o
    "LGTM&nbsp;[R]",
    "**Approved**: [R]",
    "L\u200bG\u200bT\u200bM [R].",
    "Ship\u2011it [R].",
])
def test_approvals_and_all_clears_are_status_claims_even_when_cited(line):
    out = enforce(line, INDEX)
    assert out.kept == (), line
    assert out.dropped[0].reason.startswith("status claim of its own"), line


@pytest.mark.parametrize("line", [
    "s a f e [R].",
    "It is s a f e [R].",
    "It is s.a.f.e [R].",
    "It is s - a - f - e [R].",
    "It is s  a  f  e [R].",
    "It is S A F E [R].",
    "It is s\u00b7a\u00b7f\u00b7e [R].",
    "It is a s a f e [R].",  # the article runs into the word
    "It is s,a,f,e [R].",
    "It is s a f e t y [R].",  # a loose reading of squeezed letters errs on the side of dropping
    "p r o d u c t i o n   r e a d y [R].",
    "It is p.r.o.d.u.c.t.i.o.n-r.e.a.d.y [R].",
    "It is b a t t l e - t e s t e d [R].",
    "L G T M [R].",
    "a p p r o v e d [R].",
    "s 4 f e [R].",
    "It is s\u200b a\u200b f\u200b e [R].",
    "It is \u0455 \u0430 f \u0435 [R].",  # Cyrillic lookalikes, spaced
    "It is \uff53 \uff41 \uff46 \uff45 [R].",  # fullwidth, spaced
])
def test_letters_set_apart_are_joined_up_before_the_labels_are_looked_for(line):
    out = enforce(line, INDEX)
    assert out.kept == (), line
    assert out.dropped[0].reason.startswith("status claim of its own"), line


@pytest.mark.parametrize("line", [
    "It is sa" + RLO + "fe [R].",  # a control inside the word
    "It is s" + RLO + "a" + PDF + "fe [R].",
    "It is " + RLO + "efas" + PDF + " [R].",  # stored backwards, shown as "safe"
    "It is " + RLO + "efas [R].",  # the override is never closed
    "It is " + RLO + "efas" + "\u2069 [R].",
    "It is " + RLI + "efas" + PDI + " [R].",
    "It is \u202b" + "efas" + PDF + " [R].",
    "This is " + RLO + "ydaer noitcudorp" + PDF + " [R].",
    "Status: " + RLO + "devorppa" + PDF + " [R].",
    "Status: " + RLO + "ti pihs" + PDF + " [R].",
    "Status: " + RLO + "mtgl" + PDF + " [R].",
    "A " + LRO + "safe" + PDF + " change [R].",  # a left-to-right override leaves the order alone
    "It is s&#8238;afe [R].",  # the control as an entity
    "It is &#8238;efas&#8236; [R].",
    "It is " + RLO + "e" + RLO + "fa" + PDF + "s" + PDF + " [R].",
])
def test_bidirectional_controls_do_not_hide_a_label(line):
    out = enforce(line, INDEX)
    assert out.kept == (), repr(line)
    assert out.dropped[0].reason.startswith("status claim of its own"), repr(line)


@pytest.mark.parametrize("line", [
    "The run ended ACCEPT_UNVERIFIED [R].",
    "The Judge approves nothing [R].",  # "approves" is not "approved"
    "Nothing was decided by the Watcher [R].",
    "It does not look at the code [R].",
    "Ghost looked at 213 files [N1].",
    "The suite ran in 3 seconds [N1].",
    "Ghost found 3 findings and the Judge said INSUFFICIENT [N1].",
    "Item A B passed in 2 of 3 cycles [R].",
    "Plan A, B and C were run [R].",
    "See notes [N1] [R] for the decision.",
    "The cycle ended in a tie [R].",
    "Safety was not measured [R].",
    "The change is unsafe to assume [R].",
    "A reliability test was not run [R].",
    "Robustness was not measured [R].",
    "An unreliable result [R].",
    "Shipping did not happen [R].",
    "The ship sailed with it [R].",
    "All files were scanned [N1].",
    "All three cycles ended [R].",
    "Allowed to go ahead only with a reason [R].",
    "A good deal of the output was cut [R].",
    "No findings were observed [R].",
])
def test_honest_sentences_survive_the_approval_phrases_and_the_spaced_letter_check(line):
    out = enforce(line, INDEX)
    assert out.kept == (line,) and out.dropped == (), line


def test_a_long_run_of_single_letters_is_read_in_time():
    import time

    start = time.monotonic()
    out = enforce("a " * 20000 + "[R]. " + "x." * 20000 + " [R]", INDEX)
    assert time.monotonic() - start < 5
    assert out.ratio >= 0


# --- round 3: "mergeable", and the fillers that draw nothing ------------------------------------------------------

@pytest.mark.parametrize("word", ["mergeable", "mergable", "shippable", "shipable", "deployable", "releasable",
                                  "releaseable", "Mergeable", "MERGEABLE"])
def test_the_able_words_are_status_claims(word):
    out = enforce(f"The change is {word} [R].", INDEX)
    assert out.kept == () and out.dropped[0].reason.startswith("status claim of its own"), word


#: Default_Ignorable_Code_Point, from the Unicode Character Database (DerivedCoreProperties.txt, 15.1), written out
#: here separately from the code under test.
IGNORABLE_RANGES = [
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F),
    (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
]
FILLERS = ["ᅟ", "ᅠ", "ㅤ", "ﾠ", "⠀"]


@pytest.mark.parametrize("filler", FILLERS, ids=[f"U+{ord(f):04X}" for f in FILLERS])
@pytest.mark.parametrize("template", ["sa{}fe", "pro{}duction ready", "L{}GTM", "app{}roved", "ship{}it"])
def test_fillers_that_draw_nothing_do_not_hide_a_label(filler, template):
    assert status_claim(template.format(filler)), (template, hex(ord(filler)))


@pytest.mark.parametrize("filler", FILLERS, ids=[f"U+{ord(f):04X}" for f in FILLERS])
def test_a_filler_that_draws_a_gap_is_also_read_as_a_gap(filler):
    assert status_claim(f"It is{filler}safe [R]") == "safe"
    assert status_claim(f"It is{filler}{filler}production{filler}ready [R]")


def test_every_default_ignorable_character_is_stripped():
    for lo, hi in IGNORABLE_RANGES:
        for cp in range(lo, hi + 1):
            assert status_claim("sa" + chr(cp) + "fe") == "safe", hex(cp)


def test_every_format_character_in_unicode_is_stripped():
    import unicodedata

    for cp in range(0x110000):
        if unicodedata.category(chr(cp)) == "Cf":
            assert status_claim("sa" + chr(cp) + "fe") == "safe", hex(cp)


def test_the_fillers_in_an_entity_are_stripped_too():
    assert status_claim("sa&#x3164;fe [R]") and status_claim("sa&#10240;fe [R]") and status_claim("sa&#xFFA0;fe")


def test_a_filler_in_an_honest_sentence_changes_nothing():
    line = "Ghostㅤobserved 213⠀findings [R]."
    assert enforce(line, INDEX).kept == (line,)


# --- round 3: letter forms NFKC does not fold -----------------------------------------------------------------

def _lettered(prefix: str, letters: str) -> list[str]:
    import unicodedata

    return [unicodedata.lookup(f"{prefix} {c}") for c in letters]


def _word(prefix: str, word: str) -> str:
    return "".join(_lettered(prefix, word.upper()))


LOOKALIKES = {
    "negative circled safe": _word("NEGATIVE CIRCLED LATIN CAPITAL LETTER", "safe"),
    "negative squared safe": _word("NEGATIVE SQUARED LATIN CAPITAL LETTER", "safe"),
    "negative circled lgtm": _word("NEGATIVE CIRCLED LATIN CAPITAL LETTER", "lgtm"),
    "negative squared approved": _word("NEGATIVE SQUARED LATIN CAPITAL LETTER", "approved"),
    "regional indicators safe": _word("REGIONAL INDICATOR SYMBOL LETTER", "safe"),
    "regional indicators lgtm": _word("REGIONAL INDICATOR SYMBOL LETTER", "lgtm"),
    "cherokee safe": "ᏚᎪϜᎬ",
    "cherokee lgtm": "ᏞᏀᎢᎷ",
    "armenian s": "սafe",
    "digamma f": "saϝe",
    "capital digamma f": "saϜe",
    "f with hook": "saƒe",
    "cyrillic ghe with stroke": "saғe",
    "s with hook": "ʂafe",
    "small capital s": "ꜱafe",
    "fullwidth s": "Ｓafe",
    "cyrillic dze": "ѕafe",
    "cyrillic a and e": "sаfе",
    "greek": "sαfε",
    "cherokee in a phrase": "This is ᏚᎪϜᎬ [R].",
    "cherokee in a phrase 2": "ᏞᏀᎢᎷ [R]",
    "negative squared in a phrase": "This is " + _word("NEGATIVE SQUARED LATIN CAPITAL LETTER", "safe") + " [R].",
    "regional indicator words": _word("REGIONAL INDICATOR SYMBOL LETTER", "approved"),
}


@pytest.mark.parametrize("text", list(LOOKALIKES.values()), ids=list(LOOKALIKES))
def test_letter_forms_nfkc_does_not_fold_are_read_as_the_letters_they_show(text):
    assert status_claim(text), text
    out = enforce(text if "[R]" in text else text + " [R].", INDEX)
    assert out.kept == (), text


def test_every_negative_circled_squared_and_regional_letter_folds_to_its_letter():
    import unicodedata

    from watcher.oath import _as_read

    seen = 0
    for cp in range(0x1F100, 0x1F200):
        match = re.fullmatch(
            r"(?:NEGATIVE (?:CIRCLED|SQUARED) LATIN CAPITAL LETTER|REGIONAL INDICATOR SYMBOL LETTER) ([A-Z])",
            unicodedata.name(chr(cp), ""),
        )
        if match:
            seen += 1
            assert _as_read(chr(cp)) == match.group(1).lower(), hex(cp)
    assert seen == 78  # 26 letters in each of the three sets


def test_every_latin_letter_with_a_hook_stroke_or_bar_folds_to_its_base_letter():
    import unicodedata

    from watcher.oath import _as_read

    for cp in range(0x0180, 0x0250):
        name = unicodedata.name(chr(cp), "")
        match = re.fullmatch(r"LATIN (?:CAPITAL|SMALL) LETTER ([A-Z]) WITH (?:HOOK|STROKE|BAR)", name)
        if match:
            assert _as_read(chr(cp)) == match.group(1).lower(), name


def test_the_generated_table_is_well_formed_and_holds_the_cherokee_lookalikes():
    from watcher._homoglyphs import PAIRS

    pairs = "".join(PAIRS)
    assert len(pairs) % 2 == 0 and len(pairs) > 2000
    for i in range(0, len(pairs), 2):
        assert not pairs[i].isascii() and pairs[i + 1].isascii() and pairs[i + 1].isalnum(), pairs[i : i + 2]
        assert pairs[i + 1] == pairs[i + 1].lower()
    assert "ᏚS".lower() in pairs and "Ꭺa" in pairs


@pytest.mark.parametrize("line", [
    "Ghost видел 3 файла [R].",  # Russian words
    "Το τεστ πέρασε [R].",  # Greek words
    "ᎠᎡᎢ Ꭳ [R].",  # Cherokee letters that spell nothing here
    "Հայերեն [R].",  # Armenian
    "Ghost found 3 files and the Judge said INSUFFICIENT ✅✅ [N1].".replace("✅✅", ""),
])
def test_ordinary_text_in_other_alphabets_is_not_turned_into_a_label(line):
    assert enforce(line, INDEX).kept == (line,)


# --- round 3: a citation set into the label, and a label set across lines ------------------------------------------

@pytest.mark.parametrize("line", [
    "This repository is production [R] ready.",
    "Ship [R] it.",
    "It is sa[R]fe.",
    "L[R]GTM.",
    "This is production[N1]ready.",
    "It is battle [R]-[N1] tested.",
    "It is s[R] a[R] f[R] e.",
    "It is[R]safe.",
    "It is prod[ghost-1b3766cb418b]uction ready.",
    "Production [R] ready [N1].",
])
def test_a_citation_inside_a_label_does_not_hide_it(line):
    out = enforce(line, INDEX)
    assert out.kept == (), line
    assert out.dropped[0].reason.startswith("status claim of its own"), line


def test_a_bracketed_word_that_is_not_a_tag_is_still_read():
    assert status_claim("It is [safe] [R].") == "safe"


def test_a_citation_is_still_required_for_a_kept_sentence():
    assert enforce("It ended REJECT.", INDEX).kept == ()
    assert enforce("It ended REJECT [S9].", INDEX).dropped[0].reason == "cites what is not in the record: S9"
    assert enforce("It ended REJECT [R].", INDEX).kept == ("It ended REJECT [R].",)


@pytest.mark.parametrize("text", [
    "- s [R]\n- a [R]\n- f [R]\n- e [R]",
    "- s\n- a\n- f\n- e",
    "- S [R]\n- A [R]\n- F [R]\n- E [R]",
    "* s [R]\n* a [R]\n* f [R]\n* e [R]",
    "1. s [R]\n2. a [R]\n3. f [R]\n4. e [R]",
    "- sa [R]\n- fe [R]",
    "- Verdict: ship [R]\n- it [R]",
    "This run is production [R]\nready [R]",
    "This run is production\nready [R]",
    "\n".join(f"- {c} [R]" for c in "production ready" if c != " "),
    "- L [R]\n- G [R]\n- T [R]\n- M [R]",
    "- It is s [R]\n- a [R]\n- f [R]\n- e [R]",
])
def test_a_label_set_across_lines_drops_every_line_of_it(text):
    out = enforce(text, INDEX)
    assert out.kept == (), text
    # a bare "1." has nothing to cite and says so; every line that carries a letter is dropped as the label
    lettered = [d for d in out.dropped if re.search(r"[a-z]", d.sentence, re.I)]
    assert all("status claim of its own" in d.reason for d in lettered), text


def test_the_reason_for_a_label_set_across_lines_says_so():
    out = enforce("- s [R]\n- a [R]\n- f [R]\n- e [R]", INDEX)
    assert {d.reason for d in out.dropped} == {"status claim of its own, set across lines: 'safe'"}


@pytest.mark.parametrize("text", [
    "- Ghost observed 3 findings [R]\n- The Judge said INSUFFICIENT [V]".replace("[V]", "[N1]"),
    "- Plan A [R]\n- B [R]\n- C [R]",
    "- 3 [R]\n- 5 [R]\n- 7 [R]",
    "The decision was ACCEPT [R].\nIt is ready for the Judge.".replace("It is ready for the Judge.", "Next [N1]."),
    "- The run is a [R]\n- ship that sailed [N1]",
    "- Nothing here was the production [R]\n- readiness of anything [N1]",
])
def test_neighbouring_lines_that_are_honest_are_kept(text):
    out = enforce(text, INDEX)
    assert out.dropped == (), text
