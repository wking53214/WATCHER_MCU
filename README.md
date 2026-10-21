# WATCHER_MCU

The Watcher sees every run of the circuit and is sworn not to interfere.

It is an AI entity (Claude, through the official SDK) that reads the record Warden prints at the end
of a run and tells a person what happened in plain words. It has no authority and no reach: nothing
in the circuit reads what it writes, it cannot touch a verdict, a finding, a file or a baseline, and
every sentence it keeps cites a measurement in the record by id. A sentence that cites nothing,
cites something that is not there, or makes a status claim of its own is dropped before anyone reads
it, and the account says how many were dropped and why.

Version `0.3.2` (reads `cns.run/1`). Apache-2.0. Copyright 2026 William N. King.

## WHY IT EXISTS

The circuit (Ghost Tools, SWIZZLE, Warden, the Drafter, the Judge, Burnish, ASSAY) is deterministic
on purpose: the referee is not a player, and no model grades anything. Its output is JSON that a
person has to read. People trust fluent prose more than JSON, and that is exactly why a model has
never been allowed near the verdict: a paraphrase would be believed over the measurement.

The Watcher is the one place a model is allowed, under one rule: **AI may describe, never grade.**
The rule is not a prompt. It is enforced after the model writes, by code that drops every sentence
the record does not back.

## WHAT IT DOES

```
pip install -e .
watcher narrate run.json --out account.md
watcher narrate run.json --no-model          # the template account, no model, no credentials
watcher --verbose narrate run.json --no-model   # diagnostics on standard error
```

`--out` writes into an existing folder only. A missing folder is refused (exit 2), not created, so a typo
cannot make the Watcher build a directory tree somewhere unintended; pass `--create-out-dir` to have it
create the folder and its parents. The folder checks (the governed folder, every checkout the record names,
the record itself) run first and are not lifted by the flag.

The one dependency on the circuit is the `cns.run/1` contract from the CNS repository, installed from
its git URL pinned to the full commit of release `v1.8.0` (the pin every repository of the circuit
uses, so `pip install` of the Watcher beside Warden, the Judge, the Drafter and Burnish resolves to
one CNS). `tests/test_pins.py` fails if the installed CNS is not the pinned one. Installing needs
access to that repository.

CI runs the end-to-end job and the co-install job against WARDEN 0.13.4 at commit
`36e98433f4928b7d12905f02b56e55ee1943b56e` (the tested set; it may be one or more commits behind
WARDEN's branch head). Warden pins the same CNS commit, so `pip install . ./WARDEN` resolves with full
dependency resolution and `pip check` is clean. To bump it, change the commit in both jobs of
`.github/workflows/tests.yml` and here; `tests/test_pins.py` fails if they disagree.

`run.json` is the JSON `warden tagteam` prints. It must be a `cns.run/1` record: the contract is
`RunRecord` in the CNS repository, and a record that predates it, names another version, or has a
field the contract refuses (a null reason, an unknown decision) is refused with the reason, not read
in part. The account is Markdown:

1. **The account.** The kept sentences. Each carries at least one id in square brackets: `[R]` the
   decision, `[V]` the Judge's verdict, `[N7]` a note, `[C1]` a cycle, `[ghost-1b3766cb418b]` a
   finding, `[U]` the unmeasured list, `[G]` the scan summary, `[J3]` a checkout joined for Ghost,
   `[W]` what took part.
2. **Dropped by the oath.** Every sentence that was written and not kept, with its reason: cites
   nothing, cites what is not in the record, or claims a status of its own.
3. **Citations used.** The ids the account cites, each with the text in the record it points at.
4. **The oath.**

Credentials come from `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or an `ant auth login` profile.
Without any, `watcher` exits 3 and says so; `--no-model` writes the same shape of account from the
record alone, deterministically. `--model` chooses the Claude model (`watcher narrate --help` shows the
default); `--effort` low to max.

## EXIT CODES

| Code | Meaning |
|---|---|
| 0 | An account was written (or printed). |
| 1 | An internal error, a bug in the Watcher, reported in one line (`--verbose` adds the traceback). Nothing was written. A malformed record is never this; it is 2. |
| 2 | Usage: a record that is missing ("file not found"), unreadable or malformed (not JSON, not `cns.run/1`, a field of the wrong shape), an `--out` inside a forbidden folder or on top of the record it reads, an `--out` whose folder does not exist (unless `--create-out-dir` is given), an `--out` that cannot be written, a bad option. |
| 3 | No account could be had from a model: no credentials and no `--no-model`, the model could not be reached (connection, timeout, API error, or a response that cannot be decoded as JSON or is not a message) or it declined. Nothing was written. |
| 4 | The oath dropped every sentence, so there is no account to give. The file is still written and shows what was dropped. |

`tests/test_docs.py` fails if this table and the code disagree.

## DIAGNOSTICS

The Watcher logs through the standard `logging` module under the name `watcher`, to standard error.
By default only warnings appear. `--verbose` (or `-v`, before or after `narrate`) shows what was read,
how many citable things the record holds, what was sent to the model (its size, never the record) and
every sentence the oath dropped with its reason.

## THE OATH, AS CODE

| The promise | Where it is kept |
|---|---|
| It reads the run record and nothing else | `narrate.prompt_for` shows the model the citation index only. No file, no diff, no repository. |
| It writes nothing into the governed folder or any checkout the record names | `cli.main` resolves `--out` against the governed folder (`--target`) and every instrument and joined path in `versions`, and refuses with exit 2. `tests/test_charter.py` reads the source: only `cli.py` writes, and only the account. |
| It refuses to overwrite what it reads | `cli.main` refuses (exit 2) an `--out` that resolves to the record, through a symlink, a relative spelling or a hard link. |
| Nothing in the circuit reads it | Warden, the Judge, Ghost, SWIZZLE and the seats have no input for it. Not ignored: structurally absent. The Watcher imports none of them (`test_charter.py`). |
| Every kept sentence cites the record | `oath.enforce`: no citation, drop; unknown citation, drop. |
| It claims no status of its own | `oath.status_claim`: "production ready", "production-grade", "ready for production", "battle-tested", "fully tested", "enterprise grade", "100% coverage", "safe", "bulletproof", "hardened", "mergeable" and their kin, and the sign-offs a reviewer gives ("approved", "LGTM", "looks good", "ship it", "good to go", "all clear", "no issues", "no blockers", "free of defects", "can go live", "rest easy", "OK for production use", "trustworthy", "reliable", "robust", check-mark and thumbs-up emoji, a short list in nine other languages), cited or not, drop. The sentence is read the way a person reads a rendered page: entities decoded, markup and emphasis removed, NFKC, case folded, accents and every Unicode default-ignorable character gone (the Hangul fillers and the braille blank are read both as nothing and as a gap), every Unicode dash a hyphen, lookalike letters folded to Latin (a table built from the Unicode names and the Unicode confusables data: Cyrillic, Greek, Armenian, Cherokee, small capitals, negative circled and squared letters, regional indicators, letters with hooks and strokes), digits used as letters read as letters, single letters set apart ("s a f e") joined up, an `[id]` citation tag set into the label taken out, text under a bidirectional override read in the order stored, in the order the algorithm displays it and in a cruder reversed order, and lines read at their seams (one bullet per letter, "production" at the end of one line and "ready" at the start of the next). A label is excused only where it is a description: plainly denied ("not production ready", "nothing was approved"), "no issues" reported by a named part of the circuit ("Ghost reported no issues"), "secure" before a technical noun ("secure hash call"), or one of Warden's own standard sentences by exact text. See WHAT IS NOT PROVEN for the limits. A superset of the labels Ghost Tools reports for re-verification. |
| It is a description, never a grade | The system prompt says so; the filter makes an uncited grade vanish; the account's first line repeats the decision as recorded, cited. |
| A refusal is an empty account, not a quiet one | A model that declines (safety classifier) exits 3 with no file written. An account the oath empties exits 4 and still shows what was dropped. |

## WHAT IT IS NOT

- Not a seat. Warden never loads it; `warden tagteam` runs to its end without it.
- Not an instrument. It measures nothing; it cannot run the suite, Ghost or SWIZZLE.
- Not a judge. It can say "the Judge said INSUFFICIENT [V]"; it cannot say "this is fine".
- Not a reader of code. The Watcher reads the run record only. Reading files is a later
  decision and would be read-only, with the same citation rule applied to file ids.

## HOW IT FITS THE CIRCUIT

```
SWIZZLE prove -> ASSAY grade -> loop (Ghost, Drafter, suite, apply) -> Burnish -> governor -> Judge
                                                                                          |
                                                                              run.json (Warden)
                                                                                          |
                                                                                   WATCHER_MCU -> account.md (for a person)
```

The arrow into the Watcher is the only one. Nothing comes back.

## WHAT IS PROVEN

- `tests/test_oath.py`: cited sentences survive; uncited, falsely cited and status-claiming ones are
  dropped with the reason, through emphasis, invisible characters (every default-ignorable character,
  the Hangul fillers and the braille blank), other Unicode dashes, lookalike letters (including the negative
  circled and squared letters, regional indicators and Cherokee), entities, markup, digit-for-letter
  spelling, spaced-out letters, a citation inside the label, labels set across lines, bidirectional
  overrides (nested too) and a citation after the claim ("is safe [R]"); approvals, all-clears and the
  other sign-offs in a table; a table of honest sentences that the filter keeps (denied labels, reports by
  a named instrument, Warden's own sentences) and a table of look-alikes of those that it still drops.
- `tests/test_evidence.py`: a real run record (SWIZZLE, 2026-10-15, joined through a stack manifest)
  indexes every kind of thing with stable ids; forbidden paths are the governed folder and every
  checkout the record names; the instruments and the Drafter, Burnish and Judge seats of a record
  written by Warden's own writer are all listed as having taken part.
- `tests/test_refusals.py`: a table of malformed fields (wrong type for every field the index reads)
  is exit 2 with one line and no traceback; an unreachable model is exit 3; `--out` on top of the
  record is refused however it is spelled.
- `tests/test_docs.py`, `tests/test_pins.py`: the README exit-code table matches the code, the
  version agrees across the package, the changelog and the README, the installed CNS is the pinned one.
- `tests/test_warden_e2e.py`: in CI, the real Warden writes a record and the Watcher narrates it.
- `tests/test_narrate_and_cli.py`: the model is shown the index and the oath only; what it writes is
  filtered and the filtering is shown; an emptied account is exit 4; the CLI refuses an `--out`
  inside the governed folder or a named checkout and leaves it untouched; without credentials it
  exits 3 and writes nothing; the SDK request is the documented shape (no thinking override, server
  fallbacks on) and a refusal becomes an error.
- `tests/test_charter.py`: the source imports nothing of the circuit, only `cli.py` writes, and only
  the account; no subprocess, no network of its own.

## WHAT IS NOT PROVEN

- That the model writes a good account. It is trusted to write, never to be right; the oath bounds
  what reaches a reader, not how useful it is. No live run against the API is in the tests (none is
  possible without a key), so the request shape is tested against a fake client only.
- That the status-claim list is complete. It is a denylist of labels and phrases, so it is not a proof and
  cannot be one. What it does, precisely: a sentence is dropped when any reading of it (as written, with
  the citation tags removed, with fillers as gaps, with lookalikes read their second way, in each bidirectional
  order, with digits read as letters) holds a label that is not excused, or when letters set apart or lines
  set across a seam make one. What it does not do:
  - Paraphrases. "Nothing to worry about" and "green light" are listed; "you can rely on it", "this is
    fine", "in good shape" and the like are not, and are kept if they cite the record. A single word of
    praise ("good", "fine", "correct", "complete", "passes", "verified") is not a label either: honest
    sentences use those words constantly, and the citation requirement is the defence there.
  - Other languages. A short list of the commonest sign-offs in Spanish, Portuguese, French, German, Italian,
    Russian, Chinese, Japanese and Korean is read; any other language, and any paraphrase in these, is kept.
    Paraphrases in other languages can never be complete.
  - Every lookalike. The table is the Unicode confusables data (UTR #39, as shipped in
    `watcher/_homoglyphs.py`, generated by `tools/make_homoglyphs.py`), the Unicode names of letter forms
    (read at import from the Python in use, so a newer Python knows newer characters), and a small hand list;
    a lookalike in none of them is not folded. Mixed-script spellings that put two characters in place of one
    ("rn" for "m") are not folded.
  - Labels spread over three or more long lines. Lines are read at the seam of two neighbours (eight words
    each side) and as runs of one- and two-letter lines; a label broken across three longer lines is not joined.
  - Bidirectional text in every renderer. Three orders are read (stored, the Unicode algorithm, and a crude
    reversal after the first right-to-left start); a renderer that orders differently from all three can show a
    label the filter did not see.
  - Truth. "Ghost reported no issues [G]" is kept because a named part of the circuit is the subject; the
    filter checks the form of the sentence, not that Ghost said it. The citation appendix is how a reader checks.
  How a label is excused, and where that goes wrong. A label is a denial, and kept, when a negator ("not",
  "no", "never", "cannot", "nothing", "nobody", "without", "n't") is among the four words before it in the
  same clause. A clause start ("and", "but", "so", "that", a comma, a colon) ends the reach; a cancelling word
  after the negator ("not only", "no doubt", "nobody doubts", "nothing stops", "nothing is more") and two
  negators ("not not safe") leave the label standing; a denial of a bad word ("not unsafe", "never risky",
  "nothing here is unsafe") is dropped as a claim. This is a rule of thumb, not a parser. It can let a claim
  through: a sentence in which a negator within four words does not deny the label, in a form the
  cancelling words do not name. It can drop an honest sentence: the ones the audit found that are still
  dropped are "all clear of edits", "all good checks are listed", a keyword quoted as a keyword ("a 'robust'
  keyword"), "hardened-runtime flag", "safe-mode flag", "OK to use the cached baseline" and "no problems
  collecting them". "No issues" and its kin are excused only when the clause names Ghost, Ghost Tools, SWIZZLE,
  ASSAY, Warden, the Judge, the Drafter, Burnish, a scan, a scanner or the suite as the one that reported
  it, and never when it says "I", "we", "our" or the Watcher. "Secure" is excused before a closed list of
  technical nouns (hash, cookie, shell, random, channel, connection, socket, token, key and so on). Warden's
  own sentences are excused by exact text: "Nothing was approved", "The run was stopped and nothing was
  approved", "The run is an ERROR and nothing was approved", "the held result cannot be applied safely",
  "Warden could not make a safe place for its lock and journal", "the lock file could not be opened safely"
  (strings in Warden 0.13.4 at 36e9843; `tests/test_warden_e2e.py` checks they are still in the installed
  Warden). A new sentence of Warden's that grades or denies in other words is not covered until it is added.
  The disguises it does read through are listed above and tested. It is a superset of Ghost Tools' list as of
  2026-10-15, and a new label there should be added here. The citation requirement and the shown "dropped"
  appendix are the other defences; a reader should still check the cited text.

## KNOWN DEFECTS

- The oath checks sentences, not arguments. A kept sentence can cite the right id and still
  paraphrase it badly; the citations appendix exists so a reader can check.
- A heading is kept without a citation when it is short and claims no status. A model that wants to
  editorialize could do it in headings. The account shows headings as headings.
- An empty `unmeasured` list is reported as "the record lists nothing as unmeasured". A run that ended
  before it began (for example `USAGE_ERROR`) also has an empty list; read the decision first.
- A sentence that quotes a label without denying it (for example a finding named "robust", or the Judge's
  reason quoted as "safe to merge") is dropped, like any other use of it. A quoted denial ("cannot be shown
  safe") is kept.
- `--target` is needed for the governed folder because Warden's record does not name it; the
  instrument and joined paths are refused from the record alone.
