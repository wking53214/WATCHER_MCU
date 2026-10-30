"""The oath, enforced: a sentence survives only if it cites the record and claims no status of its own.

This is the whole safety case. People believe fluent prose more than JSON, so the prose is allowed
through only where it points at something in the JSON. Three things drop a sentence:

1. No citation. The sentence names nothing in the record.
2. A citation that is not in the record. Worse than none: it looks like evidence and is not.
3. A status claim of its own: "production ready", "production-grade", "ready for production",
   "battle-tested", "fully tested", "100% coverage", "enterprise grade", "safe", "bulletproof",
   "hardened" and the like. The circuit's own scanner reports those labels for re-verification; the
   Watcher does not get to make them, cited or not. The sentence is read as a person reads it on a
   rendered page, so other dashes, lookalike letters, entities, markup, invisible characters, bidirectional
   overrides, a citation tag set into the label and letters set apart ("s a f e") do not hide a label.
   Approvals read the same way: "approved", "LGTM", "looks good", "ship it", "good to go", "all clear",
   "no issues", "reliable", "robust". A label that is plainly denied ("not production ready", "nothing was
   approved", "cannot be applied safely"), or "no issues" reported by a named part of the circuit ("Ghost
   reported no issues"), is a description and is kept; a denial of a bad thing ("not unsafe") is not.
   Warden's own standard sentences are allowed by exact text (`WARDEN_STANDARD`).

Headings are structure, not claims; a short heading with no claim in it is kept. Nothing else is.
"""

from __future__ import annotations

import html
import itertools
import logging
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ._homoglyphs import PAIRS

log = logging.getLogger(__name__)

#: An id in square brackets. The ids come from `watcher.evidence.index`.
CITATION = re.compile(r"\[([A-Za-z][A-Za-z0-9:_.-]*)\]")

#: Labels a reader would take as a verdict. They are matched against the sentence as a person reads it
#: (see `_as_read`: entities decoded, NFKC, casefolded, accents and invisible characters gone, every
#: dash a hyphen, Cyrillic, Greek and small-capital lookalikes folded to Latin). Words of one label
#: may be joined by spaces, hyphens, dots or slashes. Mirrors Ghost Tools' unverified_status_claim
#: and goes further: a label the Watcher may not make includes "safe", whether or not a citation follows.
_SEP = r"[\s\-./\u00b7]*"


_STATUS_CLAIMS = (
    # ready / grade / quality, in the production and enterprise senses
    r"prod(?:uction)?" + _SEP + r"(?:ready|grade|quality|worthy|proven|hardened|tested|safe|stable)",
    r"ready" + _SEP + r"(?:for|to|4|2)" + _SEP  # "ready 4 production": a digit for a word
    + r"(?:prod(?:uction)?|deploy(?:ment|ed|ing)?|releas(?:e|ed|ing)|ship(?:ping)?|merg(?:e|ing)|launch|go"
    + _SEP + r"live)",
    r"(?:deploy(?:ment)?|releas(?:e)?|ship|merge|launch|go" + _SEP + r"live)" + _SEP + r"ready",
    r"(?:shipp?|deploy|merge?|releas(?:ee?)?)able",  # shippable, shipable, mergeable, mergable, releasable, releaseable
    r"enterprise" + _SEP + r"(?:grade|ready|class|quality)",
    r"(?:industrial|military|commercial)" + _SEP + r"(?:grade|strength)",
    # tested
    r"battle" + _SEP + r"(?:tested|proven|hardened)",
    r"(?:fully|well|thoroughly|extensively|exhaustively|completely)" + _SEP + r"(?:tested|verified|validated|covered)",
    r"100" + _SEP + r"(?:%|per" + _SEP + r"cent)" + _SEP
    + r"(?:test" + _SEP + r")?(?:coverage|tested|covered|verified)",
    r"(?:complete|full|total)" + _SEP + r"(?:test" + _SEP + r")?coverage",
    # sound, free of defects
    r"bullet" + _SEP + r"proof",
    r"fool" + _SEP + r"proof",
    r"rock" + _SEP + r"solid",
    r"(?:bug|defect|error|regression|vulnerability|issue|flaw)" + _SEP + r"free",
    r"(?:verified|proven|guaranteed|certified)" + _SEP + r"(?:safe|correct|secure|sound)",
)

#: A mark that is a sign-off by itself: check marks, thumbs up, 100, OK, rocket, green circle. It is never excused.
_MARKS = re.compile(r"[\u2705\u2714\u2713\u2611\U0001F44D\U0001F4AF\U0001F197\U0001F680\U0001F7E2]")

#: "No issues", "zero known bugs": the sign-off of a reviewer, and also what Ghost reports when a scan finds
#: nothing. In the second case the sentence says who reported it (`_attributed`) and is kept; in the first it is a
#: label. Bounded by non-letters.
_NO_FINDINGS = (
    r"(?:no|zero)" + _SEP + r"(?:known" + _SEP
    + r")?(?:issues|problems|concerns|bugs|defects|vulnerabilit(?:y|ies)|flaws|blockers|showstoppers"
    + r"|red" + _SEP + r"flags|regressions|objections)"
)

#: Where the technical sense of "secure" is not a verdict: "a secure hash call", "secure cookie flag", "Secure Shell".
#: A closed list: a noun that is not here leaves "secure" a label.
_SECURE_NOUNS = (
    "hash", "hashes", "hashing", "cookie", "cookies", "shell", "random", "boot", "enclave", "channel", "channels",
    "connection", "connections", "socket", "sockets", "transport", "protocol", "protocols", "flag", "flags",
    "context", "contexts", "erase", "delete", "wipe", "storage", "store", "vault", "string", "token", "tokens",
    "ssl", "tls", "ssh", "https", "ftp", "ldap", "smtp", "imap", "key", "keys", "keyring", "credential",
    "credentials", "password", "passwords", "compare", "comparison",
)

#: Single words that are a verdict by themselves. They must stand alone: "unsafe" and "safety" are not "safe".
_WORD_CLAIMS = (
    "safe", "safely", r"secure(?!\s+(?:" + "|".join(_SECURE_NOUNS) + r")(?![a-z0-9]))", "bulletproof", "hardened",
    "flawless", "foolproof", "bombproof",
    "approved", "lgtm", "trustworthy", "reliable", "robust", "dependable",
)
#: Approval and all-clear phrases, also bounded by non-letters. These are what a reviewer's sign-off sounds like.
_PHRASE_CLAIMS = (
    r"ship" + _SEP + r"it",
    r"look(?:s|ed|ing)?" + _SEP + r"(?:good|great|fine|ok|okay|solid|clean|correct)",
    r"all" + _SEP + r"(?:clear|good|fine|ok|okay)",
    r"good" + _SEP + r"to" + _SEP + r"go",
    r"(?:ok|okay)" + _SEP + r"(?:for|to)" + _SEP
    + r"(?:prod(?:uction)?|use|deploy(?:ment)?|merge|releas(?:e)?|ship(?:ping)?|launch)",
    r"(?:free" + _SEP + r"of|without)" + _SEP + r"(?:any" + _SEP + r")?(?:known" + _SEP
    + r")?(?:bugs?|defects?|regressions?|vulnerabilit(?:y|ies)|flaws?)",
    r"(?:can|may|could|should)" + _SEP + r"go" + _SEP + r"live",
    r"(?:rest|sleep|breathe)" + _SEP + r"(?:easy|easily|well)",
    r"nothing" + _SEP + r"to" + _SEP + r"(?:worry|fear)",
    r"no" + _SEP + r"(?:cause|reason|need)" + _SEP + r"(?:for|to)" + _SEP + r"(?:concern|alarm|worry)",
    r"green" + _SEP + r"light",
    r"thumbs" + _SEP + r"up",
)


def _alternatives(*, bounded: bool, findings: bool = False) -> re.Pattern[str]:
    """The label matcher. `bounded` keeps the single words and phrases from matching inside longer words; the
    loose form is for letters that were spread apart and squeezed together, where a boundary means nothing.
    With `findings`, the matcher for "no issues" and its kin instead."""
    start, end = (r"(?<![a-z0-9])", r"(?![a-z0-9])") if bounded else ("", "")
    if findings:
        return re.compile(f"{start}(?:{_NO_FINDINGS}){end}")
    words = f"(?:{'|'.join(_WORD_CLAIMS)})"
    phrases = [f"(?:{p})" for p in _PHRASE_CLAIMS]
    return re.compile("|".join([f"(?:{p})" for p in _STATUS_CLAIMS] + [f"{start}(?:{words}|{'|'.join(phrases)}){end}"]))


_LABELS = _alternatives(bounded=True)
_FINDINGS = _alternatives(bounded=True, findings=True)
#: The loose forms, for letters set apart and squeezed together: every label, none of them excused.
_SQUEEZED_LABELS = re.compile(
    _alternatives(bounded=False).pattern + "|" + _alternatives(bounded=False, findings=True).pattern
)

#: Sign-offs in some other languages. This is a short list of the commonest, not a translation of the denylist:
#: a paraphrase, or a language that is not here, is kept if it cites the record. They are read in the text as it
#: is (`lookalikes=False`), since folding Cyrillic or Greek letters to Latin would turn these words into noise.
_FOREIGN_WORDS = (
    "es seguro", "esta seguro", "aprobado", "listo para produccion", "lista para produccion", "aprovado",
    "pronto para producao", "approuve", "pret pour la production", "sans probleme", "sicher", "freigegeben",
    "produktionsreif", "genehmigt", "kein problem", "in ordnung", "approvato",
    "\u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e", "\u043e\u0434\u043e\u0431\u0440\u0435\u043d\u043e",
    "\u0433\u043e\u0442\u043e\u0432\u043e \u043a \u043f\u0440\u043e\u0434\u0430\u043a\u0448\u0435\u043d\u0443",
)
#: Languages written without spaces between words: no word boundary to look for.
_FOREIGN_RUNS = (
    "\u5b89\u5168", "\u5df2\u6279\u51c6", "\u6279\u51c6", "\u53ef\u4ee5\u53d1\u5e03", "\u53ef\u53d1\u5e03",
    "\u627f\u8a8d", "\u554f\u984c\u3042\u308a\u307e\u305b\u3093", "\uc548\uc804", "\uc2b9\uc778",
)


def _foreign() -> re.Pattern[str]:
    def plain(text: str) -> str:
        return re.escape(_as_read(text, lookalikes=False))

    words = "|".join(plain(w).replace(r"\ ", r"\s+") for w in _FOREIGN_WORDS)
    runs = "|".join(plain(w) for w in _FOREIGN_RUNS)
    return re.compile(rf"(?<!\w)(?:{words})(?!\w)|{runs}")

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

#: Lookalikes written out by hand, folded to the Latin letter a reader sees. Lowercase only: the text is
#: casefolded first. `_HOMOGLYPHS` adds to these from the Unicode names and from the confusables data.
_CONFUSABLES = {
    # Cyrillic
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u043a": "k", "\u043c": "m", "\u0442": "t", "\u043d": "h", "\u0432": "b", "\u0456": "i", "\u0458": "j",
    "\u0455": "s", "\u0501": "d", "\u051b": "q", "\u051d": "w", "\u04bb": "h", "\u04cf": "l", "\u0491": "r",
    "\u0433": "r", "\u0438": "u", "\u0457": "i", "\u0454": "e", "\u04e9": "o", "\u0461": "w",
    # Greek
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03bd": "v", "\u03c5": "u", "\u03c4": "t", "\u03b9": "i",
    "\u03ba": "k", "\u03c7": "x", "\u03b5": "e", "\u03b7": "n", "\u03b2": "b", "\u03b3": "y", "\u03c9": "w",
    "\u03c2": "s", "\u03f2": "c", "\u03f3": "j", "\u03bc": "u", "\u03b6": "z", "\u03c0": "n", "\u03c3": "o",
    # Latin letters that are not decomposed, and small capitals
    "\u0131": "i", "\u0142": "l", "\u00f8": "o", "\u0111": "d", "\u0261": "g", "\u0269": "i", "\u0251": "a",
    "\u1d00": "a", "\u0299": "b", "\u1d04": "c", "\u1d05": "d", "\u1d07": "e", "\ua730": "f", "\u0262": "g",
    "\u029c": "h", "\u026a": "i", "\u1d0a": "j", "\u1d0b": "k", "\u029f": "l", "\u1d0d": "m", "\u0274": "n",
    "\u1d0f": "o", "\u1d18": "p", "\u0280": "r", "\ua731": "s", "\u1d1b": "t", "\u1d1c": "u", "\u1d20": "v",
    "\u1d21": "w", "\u028f": "y", "\u1d22": "z",
}
#: Where the names of Unicode characters say which letter they are, `_named_letters` finds them: the negative
#: circled and squared letters, the regional indicators, the small capitals, the modifier letters, and every Latin
#: letter "with" a stroke, hook or bar that has no decomposition. Only these blocks are searched (the whole of
#: Unicode takes half a second); each range is one where such letters are known to live.
_NAME_RANGES = (
    (0x00C0, 0x036F), (0x1D00, 0x1DBF), (0x1E00, 0x1EFF), (0x2070, 0x209F), (0x2100, 0x214F), (0x2460, 0x24FF),
    (0x2C60, 0x2C7F), (0xA720, 0xA7FF), (0xAB30, 0xAB6F), (0xFF00, 0xFFEF), (0x10780, 0x107BF), (0x1D400, 0x1D7FF),
    (0x1F100, 0x1F1FF),
)
_LETTER_NAME = re.compile(
    r"^(?:NEGATIVE (?:CIRCLED|SQUARED)|SQUARED|CIRCLED|PARENTHESIZED|REGIONAL INDICATOR SYMBOL"
    r"|MODIFIER LETTER (?:SMALL|CAPITAL)|LATIN LETTER SMALL CAPITAL|LATIN (?:CAPITAL|SMALL) LETTER"
    r"|LATIN (?:CAPITAL|SMALL))"
    r"(?: LATIN)?(?: (?:CAPITAL|SMALL))?(?: LETTER)? ([A-Z])(?: WITH [A-Z ]+)?$"
)
#: Lookalikes that neither the names nor the confusables data give. The reading is the letter a reader sees, or
#: the one the character spells when read aloud: Armenian seh looks like "u" and is the sound "s".
_SUPPLEMENT = {"\u0493": "f", "\u057d": "su"}


def _named_letters() -> dict[str, str]:
    out: dict[str, str] = {}
    for lo, hi in _NAME_RANGES:
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            match = _LETTER_NAME.match(unicodedata.name(ch, ""))
            if match:
                out.setdefault(ch, match.group(1).lower())
    return out


def _homoglyphs() -> dict[str, str]:
    """Every lookalike and the letters it may stand for, the most likely first: by hand, by name, from the Unicode
    confusables data (`watcher._homoglyphs`, generated by tools/make_homoglyphs.py), then the supplement."""
    table: dict[str, str] = {}

    def add(ch: str, letters: str) -> None:
        for letter in letters:
            if letter not in table.get(ch, ""):
                table[ch] = table.get(ch, "") + letter

    for ch, letter in _CONFUSABLES.items():
        add(ch, letter)
    for ch, letter in _named_letters().items():
        add(ch, letter)
    pairs = "".join(PAIRS)
    for i in range(0, len(pairs), 2):
        add(pairs[i], pairs[i + 1])
    for ch, letters in _SUPPLEMENT.items():
        add(ch, letters)
    return table


_HOMOGLYPHS = _homoglyphs()
#: A lookalike with more than one reading ("\u0406" is an "i" and an "l"): the sentence is read once for each.
_AMBIGUOUS = frozenset(ch for ch, letters in _HOMOGLYPHS.items() if len(letters) > 1)
#: Digits and symbols used as letters ("pr0duct10n r3ady"). Applied as a second reading, so that real
#: numbers ("100% coverage") are still read as numbers by the first.
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_DROPPED_CATEGORIES = frozenset({"Mn", "Me", "Cf", "Co", "Cs", "Cn"})
#: Characters that draw nothing, or only a gap, whatever their category. The Unicode property
#: Default_Ignorable_Code_Point is not in `unicodedata`, so its ranges are listed here (Unicode 15.1,
#: DerivedCoreProperties). Most are format or mark characters the category test already drops, but the Hangul
#: fillers are letters (Lo) and the braille blank is a symbol (So), so only a list catches them.
#: tests/test_oath.py holds its own copy of the ranges and checks every character in them.
_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F),
    (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
)
#: Blank-looking characters that are not ignorable by the Unicode property but draw a gap or nothing: the
#: braille blank. Together with the Hangul fillers (which draw a gap in some fonts and nothing in others) they
#: are read both ways: as nothing (so "sa<filler>fe" is "safe") and as a space (so "is<filler>safe" is "is safe").
_BLANKS = frozenset("\u115f\u1160\u3164\uffa0\u2800")
_IGNORABLE = frozenset(chr(cp) for lo, hi in _DEFAULT_IGNORABLE for cp in range(lo, hi + 1)) - _BLANKS
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->")
_EMPHASIS = re.compile(r"[*_`~\\]")
#: Bidirectional controls. A right-to-left override makes the stored letters "efas" display as "safe".
_BIDI_RTL = frozenset("\u202b\u202e\u2067")  # RLE, RLO, RLI
_BIDI_LTR = frozenset("\u202a\u202d\u2066\u2068")  # LRE, LRO, LRI, FSI
_BIDI_END = frozenset("\u202c\u2069")  # PDF, PDI
_BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
#: Three or more single letters set apart ("s a f e", "s.a.f.e", "s - a - f - e"): a run a reader joins up.
_SPACED = re.compile(r"(?<![a-z0-9])[a-z](?:[\s.,;:|/\-\u00b7]+[a-z]){2,}(?![a-z0-9])")
_SPACING = re.compile(r"[\s.,;:|/\-\u00b7]+")


@dataclass(frozen=True)
class Dropped:
    sentence: str
    reason: str


@dataclass(frozen=True)
class Enforced:
    kept: tuple[str, ...]
    dropped: tuple[Dropped, ...]

    @property
    def ratio(self) -> float:
        total = len(self.kept) + len(self.dropped)
        return 1.0 if total == 0 else len(self.kept) / total


def _fold(text: str, blank: str = "", alt: int = 0, lookalikes: bool = True) -> str:
    """One character at a time: marks and invisible characters vanish, every dash is a hyphen, a lookalike
    is the letter it imitates, any other control or separator is a space. A blank filler (see `_BLANKS`) becomes
    `blank`: the caller reads the sentence with it as nothing and with it as a space."""
    out: list[str] = []
    for ch in text:
        if ch in _BLANKS:
            out.append(blank)
            continue
        cat = unicodedata.category(ch)
        if cat in _DROPPED_CATEGORIES or ch in _IGNORABLE:
            continue
        if cat == "Pd" or ch == "\u2212":
            out.append("-")
        elif cat in ("Cc", "Zs", "Zl", "Zp"):
            out.append(" ")
        else:
            letters = _HOMOGLYPHS.get(ch) if lookalikes else None
            out.append(letters[min(alt, len(letters) - 1)] if letters else ch)
    return "".join(out)


def _bidi_visual(text: str) -> str:
    """The order a reader sees, for text that carries bidirectional embeddings or overrides: what sits between
    a right-to-left start and its end is shown reversed, and a nested level keeps the units of the level it
    sits in. The stored order is read as well, so this can only add a reading."""
    levels: list[list[str]] = [[]]  # each level is a list of units: one character, or a finished nested level
    rtl: list[bool] = [False]

    def close() -> None:
        chunk, was_rtl = levels.pop(), rtl.pop()
        if was_rtl == rtl[-1]:
            levels[-1].extend(chunk)  # same direction as the level around it: the outer reversal covers it
        else:
            levels[-1].append("".join(reversed(chunk) if was_rtl else chunk))

    for ch in text:
        if ch in _BIDI_RTL or ch in _BIDI_LTR:
            levels.append([])
            rtl.append(ch in _BIDI_RTL)
        elif ch in _BIDI_END and len(levels) > 1:
            close()
        else:
            levels[-1].append(ch)
    while len(levels) > 1:  # a start with no end runs to the end of the sentence
        close()
    return "".join(levels[0])


def _bidi_naive(text: str) -> str:
    """The cruder reading of the same controls: everything after the first right-to-left start is reversed, whatever
    is nested in it. A renderer that does not follow the full algorithm (a terminal, a log viewer) can show this
    where the algorithm itself would show `_bidi_visual`, so a label hidden either way is read."""
    start = re.search("[\u202b\u202e\u2067]", text)
    if start is None:
        return text
    return _BIDI.sub("", text[: start.start()]) + _BIDI.sub("", text[start.end() :])[::-1]


def _prepared(text: str) -> str:
    """Entities decoded, markup and links removed: the text of a rendered page, before any letter is touched."""
    return _MARKDOWN_LINK.sub(r"\1", _HTML_TAG.sub("", html.unescape(text)))


def _as_read(text: str, *, order: str = "stored", blank: str = "", alt: int = 0, prepared: bool = False,
             lookalikes: bool = True) -> str:
    """The sentence as a person reads it on a rendered page: entities decoded, markup, links and emphasis
    markers gone, NFKC, casefolded, accents and invisible characters gone, every dash a hyphen, lookalike
    letters folded to Latin. With `order` "visual" or "naive", text under a bidirectional override is first put
    in the order it is displayed (see `_bidi_visual`, `_bidi_naive`). `prepared` says `_prepared` has already been
    applied. Without `lookalikes` the letters of other alphabets are left as they are (for labels in them)."""
    if not prepared:
        text = _prepared(text)
    if order == "visual":
        text = _bidi_visual(text)
    elif order == "naive":
        text = _bidi_naive(text)
    text = _EMPHASIS.sub("", unicodedata.normalize("NFKC", text)).casefold()
    return _fold(unicodedata.normalize("NFKD", text), blank, alt, lookalikes).casefold()


def _squeezed(reading: str) -> str:
    """Runs of single letters set apart, joined up and set out on their own: "it is s a f e" gives "safe". Every
    such run is returned, so a letter that belongs to the word before ("a s a f e") cannot hide the label."""
    return " ".join(_SPACING.sub("", m.group(0)) for m in _SPACED.finditer(reading))


def sentences(text: str) -> list[str]:
    """Lines, then sentences within a line. A bullet or a heading is one unit; a paragraph is split
    at sentence ends. Blank lines vanish."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING.match(stripped) or stripped.startswith(("-", "*", "•")):
            out.append(stripped)
            continue
        out.extend(s.strip() for s in _SENTENCE_END.split(stripped) if s.strip())
    return out


_FOREIGN = _foreign()


#: Sentences Warden itself writes, which say that nothing was approved or that something could not be done
#: safely. They are fragments of the exact strings in Warden 0.16.3 (cb45681); each is taken out of the reading
#: before the labels are looked for, so it cannot be mistaken for the Watcher grading a run, and it hides only
#: itself. The negation rule (`_negated`) keeps these too; the list is the exact-text check beside it, and
#: tests/test_oath.py holds the sources.
WARDEN_STANDARD = (
    "nothing was approved",  # warden/cli.py, warden/tagteam.py: "Warden failed with X. Nothing was approved."
    "the run was stopped and nothing was approved",  # warden/tagteam.py
    "the run is an error and nothing was approved",  # warden/tagteam.py
    "the held result cannot be applied safely",  # warden/held.py
    "warden could not make a safe place for its lock and journal",  # warden/runstate.py
    "the lock file could not be opened safely",  # warden/runstate.py
)
_STANDARD = re.compile("|".join(r"\s+".join(map(re.escape, text.split())) for text in WARDEN_STANDARD))

#: Words that turn what follows them into a denial. A label is honest ("not production ready", "cannot be applied
#: safely", "nothing was approved") when one of these is among the few words before it, in the same clause.
_NEGATORS = frozenset({
    "not", "no", "never", "cannot", "nothing", "nobody", "none", "neither", "nor", "without", "hardly", "barely",
    "scarcely", "cant", "dont", "isnt", "wasnt", "arent", "werent", "doesnt", "didnt", "wont", "wouldnt",
    "shouldnt", "couldnt", "hasnt", "havent", "hadnt", "aint",
})
#: A word after a negator that cancels it: "not only safe", "no doubt it is safe", "no problem, it is safe",
#: "nobody doubts it is safe", "nothing stops it being ready", "nothing is more reliable".
_NOT_NEGATING = frozenset({
    "only", "just", "merely", "simply", "even", "doubt", "doubts", "question", "wonder", "worry", "worries",
    "hesitation", "reservation", "reservations", "mistake", "surprise", "less", "more", "better", "problem",
    "problems", "way", "issue", "issues", "fear", "sweat", "disputes", "denies", "questions", "contests",
    "objects", "stops", "stop", "prevents", "prevent", "blocks", "block", "stopping", "preventing", "blocking",
    "hinders", "holds", "keeps", "forbids", "bars",
})
#: Words that start a new clause: a denial before one of them does not reach what comes after it.
_CLAUSE_STARTS = frozenset({
    "and", "but", "or", "so", "yet", "then", "because", "since", "while", "whereas", "though", "although",
    "however", "therefore", "thus", "hence", "which", "that", "when",
})
_NEGATION_WINDOW = 4
_CLAUSE_BREAK = re.compile(r"[.,;:!?()\[\]{}|\n\u2026]|\s-+\s")
_WORD = re.compile(r"[a-z]+(?:['\u2019][a-z]+)?")
_LOOKBACK = 240  # characters of context; a clause longer than this has been cut short


def _negated(before: str) -> bool:
    """Whether a label that starts after `before` is denied: a negator within `_NEGATION_WINDOW` words before it,
    in the same clause, and not cancelled ("not only"). The window is short on purpose: a denial that is far
    from the label is not about it, and the cost of being wrong is a status claim let through."""
    words = _WORD.findall(_CLAUSE_BREAK.split(before[-_LOOKBACK:])[-1])
    for k in range(len(words) - 1, -1, -1):
        if words[k] in _CLAUSE_STARTS:
            words = words[k + 1 :]
            break
    window = words[-_NEGATION_WINDOW:]
    denials = 0
    for k, word in enumerate(window):
        if word in _NEGATORS or word.endswith(("n't", "n\u2019t")):
            if _NOT_NEGATING.intersection(window[k + 1 : k + 3]):
                continue
            denials += 1
    return denials % 2 == 1  # "not not safe" is "safe"


#: What an instrument or a seat of the circuit is called, for "Ghost reported no issues". The record is not here:
#: "the record shows no issues" is the Watcher reading the record, not a part of the circuit reporting.
_SOURCES = r"(?:ghost(?:[ _]tools)?|swizzle|assay|warden|judge|drafter|burnish|scan(?:ner)?|suite)"
_REPORTS = (
    r"(?:reported|reports|reporting|found|finds|lists|listed|flagged|flags|observed|observes|recorded|records|says"
    r"|said|shows|showed|noted|notes|returned|returns|detected|detects|logged|logs)"
)
_REPORTED_BEFORE = re.compile(
    rf"(?<![a-z0-9]){_SOURCES}(?![a-z0-9])(?:\s+[a-z0-9_.'-]+){{0,6}}?\s+{_REPORTS}\s+(?:that\s+)?"
    rf"(?:(?:there|it)\s+(?:were|was|are|is)\s+)?$"
)
_REPORTED_AFTER = re.compile(
    rf"^(?:\s+[a-z0-9_.'-]+){{0,3}}?\s+(?:was\s+|were\s+|are\s+|is\s+|been\s+)?{_REPORTS}\s+by\s+{_SOURCES}(?![a-z0-9])"
)
_FIRST_PERSON = re.compile(r"(?<![a-z0-9])(?:i|we|my|our|me|us|watcher)(?![a-z0-9])")


def _attributed(before: str, after: str) -> bool:
    """Whether "no issues" is a report of what a named part of the circuit found ("Ghost reported no issues",
    "no known bugs were reported by Ghost") and not the Watcher's own sign-off. The Watcher is never the source."""
    clause_before = _CLAUSE_BREAK.split(before[-_LOOKBACK:])[-1]
    if _FIRST_PERSON.search(clause_before):
        return False
    clause_after = _CLAUSE_BREAK.split(after[:_LOOKBACK])[0]
    return bool(_REPORTED_BEFORE.search(clause_before) or _REPORTED_AFTER.match(clause_after))


#: "Not unsafe", "never risky": a denial of a bad thing is a good-thing claim, so it is never excused.
_DOUBLE = re.compile(
    r"(?<![a-z0-9])(?:not|never|nothing|isn't|wasn't|aren't|weren't|isnt|wasnt|arent|werent)\s+(?:[a-z']+\s+){0,2}"
    r"(?:unsafe|insecure|unreliable|untrustworthy|unsound|dangerous|risky)(?![a-z0-9])"
)


def _scan(reading: str) -> str:
    """The first label in one reading that is not excused, or empty."""
    reading = _STANDARD.sub(" ", reading)
    for m in _LABELS.finditer(reading):
        if not _negated(reading[: m.start()]):
            return m.group(0)
    for m in _FINDINGS.finditer(reading):
        before = reading[: m.start()]
        if not _negated(before) and not _attributed(before, reading[m.end() :]):
            return m.group(0)
    found = _DOUBLE.search(reading) or _MARKS.search(reading)
    if found:
        return found.group(0)
    squeezed = _SQUEEZED_LABELS.search(_squeezed(reading))
    return squeezed.group(0) if squeezed else ""


def _citation_variants(text: str) -> list[str]:
    """The sentence as it stands, and with its `[id]` tags taken out (joining the letters either side, and leaving
    a space), because a tag set into a label ("sa[R]fe", "production [R] ready") is not part of what a reader
    takes the label to say. The tag stays in the first reading, since "[safe]" looks like a tag and is not one."""
    if not CITATION.search(text):
        return [text]
    return list(dict.fromkeys([text, CITATION.sub("", text), CITATION.sub(" ", text)]))


def status_claim(sentence: str) -> str:
    """The status label a sentence makes on its own, or empty. A label inside a citation's quoted
    text is still a claim here: the Watcher repeats nothing it cannot cite as a report of a label.
    The sentence is read as written, with digits and symbols read as the letters they stand for ("pr0duction
    r3ady" is caught and "100% coverage" is still a number), with letters set apart joined up ("s a f e"), and,
    when it carries bidirectional controls, in the order it is displayed (letters stored as "efas" after a
    right-to-left override show as "safe").
    """
    for text in _citation_variants(_prepared(sentence)):
        blanks = ("", " ") if _BLANKS.intersection(unicodedata.normalize("NFKC", text)) else ("",)
        orders = ("stored", "visual", "naive") if _BIDI.search(text) else ("stored",)
        normal = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", text)).casefold()
        alts = (0, 1) if _AMBIGUOUS.intersection(normal) else (0,)
        for order, blank, alt in itertools.product(orders, blanks, alts):
            if alt == 0:
                found = _FOREIGN.search(_as_read(text, order=order, blank=blank, prepared=True, lookalikes=False))
                if found:
                    return found.group(0)
            read = _as_read(text, order=order, blank=blank, alt=alt, prepared=True)
            for reading in (read, read.translate(_LEET)):
                claim = _scan(reading)
                if claim:
                    return claim
    return ""


_LEADER = re.compile(r"^(?:[-*\u2022]+|#{1,6}|\d+[.)])\s*")
_TERMINAL = (".", "!", "?", ":", ";")
_EDGE_WORDS = 8


def _bare(unit: str) -> str:
    """A line as the words it holds: no bullet or heading mark, no `[id]` tags."""
    return CITATION.sub("", _LEADER.sub("", unit.strip())).strip()


def _split_labels(units: list[str], claimed: list[bool]) -> dict[int, str]:
    """Labels set across lines, which no one line holds: a bullet for each letter of "safe", "sa" over "fe",
    "production" at the end of one line and "ready" at the start of the next. Returns the index of every line
    that is part of such a label, with the label. A line that is a claim by itself is not looked at again, and a
    pair is only read at its seam, so an honest line is not dropped for what its neighbour says."""
    bare = [_bare(u) for u in units]
    found: dict[int, str] = {}
    ends = [" ".join(b.split()[-_EDGE_WORDS:]) for b in bare]  # what a label that starts on this line could use
    starts = [" ".join(b.split()[:_EDGE_WORDS]) for b in bare]  # and what one that ends on this line could use
    seen: dict[str, bool] = {}

    def by_itself(text: str) -> bool:
        if text not in seen:
            seen[text] = bool(status_claim(text))
        return seen[text]

    for i in range(len(units) - 1):
        if claimed[i] or claimed[i + 1] or not bare[i] or not bare[i + 1] or bare[i].endswith(_TERMINAL):
            continue
        if by_itself(ends[i]) or by_itself(starts[i + 1]):
            continue
        for joiner in ("", " "):
            claim = status_claim(ends[i] + joiner + starts[i + 1])
            if claim:
                found[i] = found[i + 1] = claim
                break
    live = [k for k in range(len(units)) if bare[k]]  # a bare "1." or "-" is a mark, not a word
    i = 0
    while i < len(live):  # a run of lines of one or two letters each: the letters of a word, a bullet apiece
        j = i
        while j < len(live) and not claimed[live[j]] and len(bare[live[j]]) <= 2:
            j += 1
        if j - i >= 3:
            run = live[i:j]
            body = [bare[k] for k in run]
            before = live[i - 1] if i > 0 and not claimed[live[i - 1]] else None  # "It is s" over "a", "f", "e"
            for lead in ([None, before] if before is not None else [None]):
                for joiner in ("", " "):
                    text = joiner.join(body) if lead is None else ends[lead] + joiner + joiner.join(body)
                    claim = status_claim(text)
                    if claim:
                        for k in run if lead is None else [lead, *run]:
                            found[k] = claim
                        break
                else:
                    continue
                break
        i = max(j, i + 1)
    return found


def enforce(text: str, citations: Mapping[str, object], headings_allowed: bool = True) -> Enforced:
    """Keep the sentences that cite the record and make no status claim; drop the rest, with reasons."""
    kept: list[str] = []
    dropped: list[Dropped] = []
    known = set(citations)
    units = sentences(text)
    claims = [status_claim(u) for u in units]
    split = _split_labels(units, [bool(c) for c in claims])
    for n, sentence in enumerate(units):
        claim = claims[n]
        if claim:
            dropped.append(Dropped(sentence, f"status claim of its own: {claim!r}"))
            continue
        if n in split:
            dropped.append(Dropped(sentence, f"status claim of its own, set across lines: {split[n]!r}"))
            continue
        ids = CITATION.findall(sentence)
        if not ids:
            if headings_allowed and _HEADING.match(sentence) and len(sentence) <= 80:
                kept.append(sentence)
            else:
                dropped.append(Dropped(sentence, "cites nothing in the record"))
            continue
        unknown = [i for i in ids if i not in known]
        if unknown:
            dropped.append(Dropped(sentence, f"cites what is not in the record: {', '.join(unknown)}"))
            continue
        kept.append(sentence)
    for d in dropped:
        log.debug("dropped (%s): %.80s", d.reason, d.sentence)
    log.info("oath: %d kept, %d dropped", len(kept), len(dropped))
    return Enforced(tuple(kept), tuple(dropped))


def cited_ids(kept: Iterable[str]) -> list[str]:
    """Every id the kept sentences cite, in first-seen order."""
    out: list[str] = []
    for sentence in kept:
        for cid in CITATION.findall(sentence):
            if cid not in out:
                out.append(cid)
    return out


__all__ = ["CITATION", "Dropped", "Enforced", "cited_ids", "enforce", "sentences", "status_claim"]
