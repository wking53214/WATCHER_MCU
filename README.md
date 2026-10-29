# WATCHER_MCU

## WHAT THIS IS

The Watcher reads the JSON record that `warden tagteam` prints at the end of a run and writes a plain-words account of it
for a person. It can use a Claude model through the official SDK, or write the account from a template with no model.
It has no authority: nothing in the circuit reads what it writes, and every sentence it keeps cites a measurement in the
record by id, or is dropped before anyone reads it.

**Status: released from the circuit (2026-10-29).** The Watcher was the narrator seat in the Horsemen circuit, and the owner has released it from the circuit. Released means removed from the circuit and nothing else: the code, the tests, the history and the CI are intact, and the Watcher still works on its own as described below. The reason, with the evidence: nothing in the circuit reads what it writes. What remains usable on its own: `watcher narrate` on any run record. In the circuit, Warden 0.15.0 lets a pinned manifest leave the Watcher out; until the pins move, the circuit still installs it. The Watcher is free to be reborn elsewhere; that is the owner's intent, not a plan or a promise.

Version `0.3.10` (reads `cns.run/1`). Apache-2.0. Copyright 2026 William N. King.

## WHY IT EXISTS

The circuit (Ghost Tools, SWIZZLE, Warden, the Drafter, the Judge, Burnish, ASSAY) is designed so that
no model grades anything; this repository does not check that of the others. Its output is JSON that a
person has to read. People trust fluent prose more than JSON, and that is exactly why a model has
never been allowed near the verdict: a paraphrase would be believed over the measurement.

The Watcher is the one place a model is allowed, under one rule: **AI may describe, never grade.**
The rule is not a prompt. It is enforced after the model writes, by code that drops every sentence
the record does not back.

## HOW TO INSTALL AND RUN

Python 3.11 or newer. Install from a checkout, not by a bare name: names in this stack, such as `cns`, belong to other
projects on PyPI. The install fetches CNS from its git URL, so it needs network access to github.com:

```
git clone https://github.com/wking53214/WATCHER_MCU
cd WATCHER_MCU
python -m venv .venv && . .venv/bin/activate
pip install -e .                 # add '.[dev]' to get pytest, ruff and mypy
watcher narrate run.json --no-model                  # the template account on standard output, no model, no credentials
watcher narrate run.json --out account.md            # an account written by a model (needs credentials, see below)
watcher --verbose narrate run.json --no-model        # diagnostics on standard error
```

`run.json` is what `warden tagteam` prints. To install the real Warden beside the Watcher, check out the tested commit
named below and install both in one command, which is what the CI jobs do (`pip check` is clean after it):

```
git clone https://github.com/wking53214/WARDEN
git -C WARDEN checkout fe9c8b35778de680d04b2a57775ac6a6831f4799
pip install -e . ./WARDEN
pip check
```

The one dependency on the circuit is the `cns.run/1` contract from the CNS repository, installed from its git URL
pinned by the release tag `v2.1.0`
(the tag peels to `fde931ffa89aebec95647742256ad53033bd3d02`). Migration note: the pin moved from `v1.9.0` to
`v2.0.0` in 0.3.8, and from `v2.0.0` to `v2.1.0` in 0.3.11. The Watcher imports only `cns.run`, and the suite passes
against the installed 2.1.0 with no change to the Watcher's code. `tests/test_pins.py` fails if the installed CNS is not the pinned one. CNS is a public repository:
https://github.com/wking53214/CNS.

CI runs the end-to-end job and the co-install job against Warden 0.15.1 (not tagged) at commit
`fe9c8b35778de680d04b2a57775ac6a6831f4799` (the tested set; it may be one or more
commits behind WARDEN's branch head). That Warden commit pins the same CNS (`v2.1.0`, `fde931f`), so both jobs
install the Watcher and Warden together with full dependency resolution, then run `pip check`; exactly one CNS is
installed, the pinned one. To bump Warden, change the commit in both jobs of
`.github/workflows/tests.yml` and here; `tests/test_pins.py` fails if they disagree.

To run the checks CI runs: `python -m ruff check .`, `python -m mypy` and `pytest -q`. The end-to-end tests are
deselected by default and need the real Warden: `pytest -q -m e2e tests/test_warden_e2e.py`.

## WHAT IT DOES

`--out` writes into an existing folder only. A missing folder is refused (exit 2), not created, so a typo
cannot make the Watcher build a directory tree somewhere unintended; pass `--create-out-dir` to have it
create the folder and its parents. The folder checks (the governed folder, every checkout the record names,
the record itself) run first and are not lifted by the flag. The file is written to a temporary file in the same
folder and moved into place, so a write that fails leaves no partial account, no temporary file, and an earlier
account at the same path whole (a symlink at `--out` is written through). The move replaces its target, so an `--out`
that exists and is not a regular file (a folder, a named pipe, a device node, or a symlink that resolves to one) is
refused (exit 2, one line, nothing written, no temporary file); it is checked again just before the move. An existing
file keeps its permission bits (a private `0600` account stays `0600`); a new file gets the ordinary default. The write
is not synced to disk, so a crash of the machine mid-write is not covered.

`run.json` is the JSON `warden tagteam` prints. It must be a `cns.run/1` record: the contract is
`RunRecord` in the CNS repository, and a record that predates it, names another version, or has a
field the contract refuses (a null reason, an unknown decision) is refused with the reason, not read
in part. The account is Markdown:

1. **The account.** The kept sentences. Each carries at least one id in square brackets: `[R]` the
   decision, `[V]` the Judge's verdict, `[N7]` a note, `[C1]` a cycle, `[ghost-1b3766cb418b]` a
   finding, `[U]` the unmeasured list, `[G]` the scan summary, `[J3]` a checkout joined for Ghost,
   `[W]` what took part, `[CV]` the `converged` flag, `[PB]` `put_back`, `[FN]` `finished`, `[SS]`
   `swizzle_sound`, `[D1]` a line of `drafter_skipped`, `[I1]` a line of `informational`.
2. **Dropped by the oath.** Every sentence that was written and not kept, with its reason: cites
   nothing, cites what is not in the record, or claims a status of its own.
3. **Citations used.** The ids the account cites, each with the text in the record it points at.
4. **The oath.**

The default model is the one `watcher narrate --help` shows. Credentials come from `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or an `ant auth login` profile.
Without any, `watcher` exits 3 and says so; `--no-model` writes the same shape of account from the
record alone, deterministically. What it says about what was not done, from the record only: the
`unmeasured` list as the record gives it (`[U]`); the checks in `ghost_scan.declined` (`[G]`), named, with the
sentence that a declined check was not run, so the absence of findings from it means nothing (a record can list
nothing as unmeasured and still decline checks, and the account says both; a declined name that holds a status label
or text that reads as a citation is left out of the list alone, with the number left out, and the other names stay);
any part of `versions` (Warden,
the instruments, the seats, each joined checkout) whose `dirty` flag is `true`, marked "DIRTY: uncommitted
changes" in `[W]` and `[J<n>]` and named in a line of its own (`null` means the record could not tell, and
is not reported as dirty; `false` is clean; any other value, such as the text "true" or the number 1, is not a flag
the Watcher can read, so the part is marked "DIRTY OR UNREADABLE" and treated as possibly dirty); a commit the record
does not hold is shown as "commit not recorded", not as "None"; and, when `converged` is true while the final cycle of the record still observed findings (the last one in its list), that converged
is not zero findings (`[CV]`), together with Warden's own note saying so. The account also lists every cycle
of the record (`[C1]`, `[C2]`, ... with no cap), says when `put_back` or `finished` is true, says that
`swizzle_sound` is false (SWIZZLE's proofs did not hold) or null (no result) and shows the notes that say a step
failed, was skipped, was not run or was not enforced (for example a SWIZZLE proofs note with "3 FAILED"). The lines of
`drafter_skipped` and `informational`, which Warden says are information and not gaps, are in a section of their own
labelled so. It names the finding ids of `observed` (at the start) and `reobserved` (at the end), the first 20 of each
and a count of the rest. `--model` chooses the Claude model; `--effort` is one of low, medium, high, xhigh, max.

Text the record supplies cannot add structure to the account. Every string taken from the record and shown (the
declined checks, a joined path, a seat's role and spec, the Judge's decision, the notes, every citation) is reduced
to one plain line first: each run of whitespace, a newline included, is one space, any other control character is a
space, and bidirectional controls are removed; a string over 400 characters is cut. A value such as
`"\n## Heading\n- [R] ..."` therefore stays inside the bullet that quotes it, and the oath reads the line that is
rendered. A record value that quotes `[id]` text is still read by the oath as a citation: an id the record lacks drops
the line, and the dropped section says so.

## EXIT CODES

| Code | Meaning |
|---|---|
| 0 | An account was written (or printed). |
| 1 | An internal error, a bug in the Watcher, reported in one line (`--verbose` adds the traceback). Nothing was written. A malformed record is never this; it is 2. |
| 2 | Usage: a record that is missing ("file not found"), unreadable or malformed (not JSON, not `cns.run/1`, a field of the wrong shape), a `--target` that does not exist or is not a folder, an `--out` inside a forbidden folder or on top of the record it reads, an `--out` that exists and is not a regular file, an `--out` whose folder does not exist (unless `--create-out-dir` is given), an `--out` that cannot be written, a bad option, an account that could not be delivered on standard output (it is closed, or a write to it fails, as on a full device). |
| 3 | No account could be had from a model: no credentials and no `--no-model`, the model could not be reached (connection, timeout, API error, or a response that cannot be decoded as JSON or is not a message) or it declined. Nothing was written. |
| 4 | The oath dropped every sentence, so there is no account to give. The file is still written and shows what was dropped. |

Delivery on standard output (no `--out`): if the reader goes away (`watcher narrate RECORD | head`, a broken pipe), nothing
is printed on standard error and the exit code stays the one earned, 0 or 4. If standard output is closed, or a write to
it fails for any other reason, one plain line goes to standard error and the exit code is 2, whatever the account was,
because an account that was not delivered was not given. If standard error is also unusable, that line is lost and the
exit code is unchanged. `tests/test_delivery.py` holds all of this.

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
| It claims no status of its own | `oath.status_claim`: "production ready", "production-grade", "ready for production", "battle-tested", "fully tested", "enterprise grade", "100% coverage", "safe", "bulletproof", "hardened", "mergeable" and their kin, and the sign-offs a reviewer gives ("approved", "LGTM", "looks good", "ship it", "good to go", "all clear", "no issues", "no blockers", "free of defects", "can go live", "rest easy", "OK for production use", "trustworthy", "reliable", "robust", check-mark and thumbs-up emoji, a short list in other languages), cited or not, drop. The sentence is read the way a person reads a rendered page: entities decoded, markup and emphasis removed, NFKC, case folded, accents and every Unicode default-ignorable character gone (the Hangul fillers and the braille blank are read both as nothing and as a gap), every Unicode dash a hyphen, lookalike letters folded to Latin (a table built from the Unicode names and the Unicode confusables data: Cyrillic, Greek, Armenian, Cherokee, small capitals, negative circled and squared letters, regional indicators, letters with hooks and strokes), digits used as letters read as letters, single letters set apart ("s a f e") joined up, an `[id]` citation tag set into the label taken out, text under a bidirectional override read in the order stored, in the order the algorithm displays it and in a cruder reversed order, and lines read at their seams (one bullet per letter, "production" at the end of one line and "ready" at the start of the next). A label is excused only where it is a description: plainly denied ("not production ready", "nothing was approved"), "no issues" reported by a named part of the circuit ("Ghost reported no issues"), "secure" before a technical noun ("secure hash call"), or one of Warden's own standard sentences by exact text. See WHAT DOES NOT WORK / NOT PROVEN for the limits. |
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

## WHAT WORKS

Each line names the test file that shows it. The suite runs in the `check` CI job on Python 3.11, 3.12 and 3.13 beside
`ruff` and `mypy` in strict mode.

- `tests/test_oath.py`: cited sentences survive; uncited, falsely cited and status-claiming ones are
  dropped with the reason, through emphasis, invisible characters (every default-ignorable character,
  the Hangul fillers and the braille blank), other Unicode dashes, lookalike letters (including the negative
  circled and squared letters, regional indicators and Cherokee), entities, markup, digit-for-letter
  spelling, spaced-out letters, a citation inside the label, labels set across lines, bidirectional
  overrides (nested too) and a citation after the claim ("is safe [R]"); approvals, all-clears and the
  other sign-offs in a table; a table of honest sentences that the filter keeps (denied labels, reports by
  a named instrument, Warden's own sentences) and a table of look-alikes of those that it still drops.
- `tests/test_evidence.py`: a real run record (SWIZZLE, joined through a stack manifest)
  indexes every kind of thing with stable ids; forbidden paths are the governed folder and every
  checkout the record names; the instruments and the Drafter, Burnish and Judge seats of a record
  written by Warden's own writer are all listed as having taken part.
- `tests/test_refusals.py`: a table of malformed fields (wrong type for every field the index reads)
  is exit 2 with one line and no traceback; an unreachable model is exit 3; `--out` on top of the
  record is refused however it is spelled.
- `tests/test_docs.py`, `tests/test_pins.py`: the README exit-code table matches the code, the
  version agrees across the package, the changelog and the README, the installed CNS is the pinned one.
- `tests/test_warden_e2e.py`: the real Warden writes a record (for a target that does not exist, and for a small git
  project run with no Drafter) and the Watcher narrates it; the installed Warden is the tested one; each of Warden's own
  standard sentences that the oath allows is still a string in Warden's source. It runs in the `warden-e2e` CI job and
  was also run on 3.11, 3.12 and 3.13 against Warden 0.13.10 for this release. The `coinstall-warden` job checks that pip
  resolves the Watcher and Warden together and that `pip check` is clean.
- `tests/test_narrate_and_cli.py`: the model is shown the index and the oath only; what it writes is
  filtered and the filtering is shown; an emptied account is exit 4; the CLI refuses an `--out`
  inside the governed folder or a named checkout and leaves it untouched; without credentials it
  exits 3 and writes nothing; the SDK request is the documented shape (no thinking override, server
  fallbacks on) and a refusal becomes an error.
- `tests/test_charter.py`: the source imports nothing of the circuit, only `cli.py` writes, and only
  the account; no subprocess, no network of its own.
- `tests/test_account_honesty.py`, `tests/test_account_completeness.py`, `tests/test_minor_fixes.py`: on real records, the
  template account names every declined check and says it was not run, names dirty parts, says when `converged` is not
  zero findings, lists every cycle, and says when `put_back`, `finished` or a failed SWIZZLE proof is in the record.
- `tests/test_delivery.py`: a reader that left keeps the earned exit code, and a closed or failing standard output is one
  plain line and exit 2, never a traceback or an "internal error".
- `tests/test_atomic_out.py`, `tests/test_record_text.py`: `--out` never replaces a file that is not a regular one and
  keeps permission bits; a value in the record cannot add a heading or a bullet to the account.
- `tests/test_readme_ledger.py`: the sections named in this README exist, the tests named here exist, the versions and dates in the
  ledger match the CHANGELOG, the numbers named here match the code, and the README uses none of a short list of
  marketing words.

## WHAT DOES NOT WORK / NOT PROVEN

- That the account lists everything that was not measured. It states the three things above from the record
  (`unmeasured`, `ghost_scan.declined`, `dirty: true`) and that converged is not zero findings when the record
  shows findings left. It says nothing about what a declined check would have found, and it reports only what
  the record holds: a record that lists nothing and declines nothing gets no such line, which is not proof
  that everything ran. The template account also keeps only the notes whose text mentions a suite, an
  observation, a gap, "not measured", uncommitted instruments, "not zero findings", "failed", "not sound",
  "not run", "not enforced" or "skipped"; the other notes are in
  the record and in the model's prompt, not in the template. Of the finding ids the record lists, the template
  names the first 20 distinct ones of `observed` and of `reobserved` and says how many more the record holds; a
  record's cycles are all listed, with no cap.
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
  dropped are "all clear of edits", "all good checks are listed", a keyword quoted as a keyword ("a 'robust' keyword"), "hardened-runtime flag", "safe-mode flag", "OK to use the cached baseline" and "no problems
  collecting them". "No issues" and its kin are excused only when the clause names Ghost, Ghost Tools, SWIZZLE,
  ASSAY, Warden, the Judge, the Drafter, Burnish, a scan, a scanner or the suite as the one that reported
  it, and never when it says "I", "we", "our" or the Watcher. "Secure" is excused before a closed list of
  technical nouns (hash, cookie, shell, random, channel, connection, socket, token, key and so on). Warden's
  own sentences are excused by exact text: "Nothing was approved", "The run was stopped and nothing was
  approved", "The run is an ERROR and nothing was approved", "the held result cannot be applied safely",
  "Warden could not make a safe place for its lock and journal", "the lock file could not be opened safely"
  (strings in Warden 0.15.1 at fe9c8b3; `tests/test_warden_e2e.py` checks they are still in the installed
  Warden). A new sentence of Warden's that grades or denies in other words is not covered until it is added.
  The disguises it does read through are listed above and tested. The citation requirement and the shown "dropped"
  appendix are the other defences; a reader should still check the cited text.
- The real Warden is exercised in the end-to-end tests only through a record for a target that does not exist and a
  record for a small git project run with no Drafter. No end-to-end test runs a full governed loop to an ACCEPT or a
  held result. The records of such runs in the tests are saved files in `tests/fixtures`, described in the test docstrings
  and the CHANGELOG as taken from real runs; the CI run does not produce them live.
- The cases where SWIZZLE's proofs failed (`swizzle_sound` false, a "3 FAILED" note) use real saved records with those
  fields set by hand. They are not from a real failing Warden run.
- The end-to-end and co-install CI jobs run on Python 3.13 only. The end-to-end tests were run by hand on 3.11 and 3.12
  for this release, which is not a CI result.
- Sentences with no citation are dropped by the oath, but nothing here shows that the template account reads well.

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
  instrument and joined paths are refused from the record alone. A `--target` that does not exist, or is a file and not a folder, is refused
  (exit 2), because a guard on a folder that is not there would let `--out` into the real one under another name.
  The Watcher does not check that `--target` is the folder that was governed, only that it exists and is a folder.
- The status-claim filter is a denylist, so a paraphrase that is not listed passes if it cites the record (see
  WHAT DOES NOT WORK / NOT PROVEN for what it does and does not read). Each of these was tried with a citation and is
  kept today: "All green [R].", "Everything checks out, nothing left to do [R].", "This is solid [R].", "No further action
  is required [R].", "Nothing is wrong [R].", "Cleared for release [R].". They read as a grade and are not dropped.
  `tests/test_oath_known_gaps.py` holds this as a known gap: it fails the day one of them is dropped, so this list can
  be corrected then.
- The Watcher reads `ghost_scan.declined`, the `dirty` flags and the gap lists from the record itself
  (`watcher/evidence.py`) and uses `RunRecord.from_dict` only to refuse a record that is not `cns.run/1`. CNS 2.0.0's
  `RunRecord` has `declined`, `gaps()` and `dirty_parts()` that answer the same questions. Nothing compares the two, so
  they can drift apart. The Watcher was not changed to call them.
- The account is written to a temporary file and moved into place, but the write is not synced to disk, so a crash of
  the machine in the middle of a write is not covered.

## WHAT BROKE AND HOW IT WAS FIXED

Newest first. Each entry says what was wrong, how it was found when the history says, the version that fixed it, and
what now stops it coming back: a named test, or "no test yet". The sources are `CHANGELOG.md`, `git log` and the tests.
Where a fix was wrong or overstated and corrected later, the entry says so. Open problems are under KNOWN DEFECTS.

**0.3.9** (2026-10-24)
- *A gone reader was reported as a bug in the Watcher.* `watcher narrate RECORD --no-model | head -c0` printed
  "internal error: BrokenPipeError ... Nothing was written." and exited 1, which the exit table says means a bug in the
  Watcher; a closed standard output gave the same message for an `AttributeError`. Found by the round-6 audit
  (2026-10-23/24) and reproduced before the change, with and without `PYTHONUNBUFFERED=1`. Now a broken pipe keeps the
  earned code and prints nothing, and any other failed delivery is one line and exit 2. Guard:
  `tests/test_delivery.py::test_a_reader_that_left_keeps_the_earned_code_and_prints_nothing`,
  `tests/test_delivery.py::test_a_closed_standard_output_is_one_plain_line_and_exit_2` and
  `tests/test_delivery.py::test_a_write_that_fails_for_another_reason_is_one_plain_line_and_exit_2`.
- *The README's self-hosting text was stale* ("no fresh run is recorded yet") after the full circuit governed this
  repository twice. It now cites the recorded runs. Guard:
  `tests/test_readme_ledger.py::test_self_hosting_holds_the_recorded_numbers_and_says_what_the_record_does_not_mean`.
- *One caveat was written twice* (that `--target` is not checked against the folder that was governed). One remains.
  No test yet.

**0.3.7** (2026-10-22)
- *`--out` replaced whatever stood at its path.* The atomic write added in 0.3.6 moved the account into place with
  `os.replace`, so a named pipe or a device node (or a symlink resolving to one) was swapped for a regular file, a folder
  gave a raw `IsADirectoryError`, and an existing `0600` account was rewritten as `0644`. Now
  such a target is refused (exit 2, nothing written) and permission bits are kept. Guard:
  `tests/test_atomic_out.py::test_a_named_pipe_at_out_is_refused_and_stays_a_named_pipe` and
  `tests/test_atomic_out.py::test_an_existing_file_keeps_its_permission_bits`.
- *Text from the record could add structure to the account.* The declined line, the dirty line and the Judge's decision
  were built from raw record strings, so a declined entry holding a newline, a heading and a fake `[R]` bullet made a
  heading and a bullet that the oath kept as a fact. Every such string is now reduced to one plain line. Guard:
  `tests/test_record_text.py::test_the_reported_example_makes_no_heading_and_no_bullet`.
- *The account left out facts the record states.* It listed only the first three cycles, and said nothing of
  `swizzle_sound` false, a failed-proofs note, `put_back`, `finished`, `drafter_skipped`, `informational` or the finding
  ids. Guard: `tests/test_account_completeness.py::test_every_cycle_of_the_record_is_listed_not_only_the_first_three`
  and `tests/test_account_completeness.py::test_swizzle_sound_false_and_a_failed_proofs_note_are_in_what_was_not`.
- *The `[CV]` line described the wrong cycle.* It named the last cycle that had observed anything, so cycle 1 observing
  2 and cycle 2 observing 0 gave "still observed 2 in cycle 1", which is false. It now describes the final cycle of
  the record. Guard:
  `tests/test_account_honesty.py::test_cycle_one_observing_two_and_cycle_two_observing_none_makes_no_false_claim`.
- *Four small defects.* A missing commit rendered as "at None"; a `dirty` value other than the boolean true was ignored;
  `--target` could be a file; one declined name that tripped the oath dropped the whole `[G]` line. Guard:
  `tests/test_minor_fixes.py::test_a_commit_the_record_does_not_hold_is_said_not_to_be_recorded`,
  `tests/test_minor_fixes.py::test_a_target_that_is_a_file_is_refused_with_one_line_and_nothing_is_written` and
  `tests/test_minor_fixes.py::test_one_offending_declined_name_is_dropped_alone_and_the_rest_are_shown`.

**0.3.6** (2026-10-21)
- *The account said nothing was missing while Warden had declined seven checks.* On a real record it printed "not
  measured: nothing listed" and "gaps: none" while `ghost_scan.declined` listed seven checks Warden did not run;
  dirty flags and Warden's note that converged is not zero findings were also dropped. Found by the circuit audit.
  Guard: `tests/test_account_honesty.py::test_the_account_names_every_declined_check_and_says_it_was_not_run` and
  `tests/test_account_honesty.py::test_dirty_parts_are_named_wherever_the_record_flags_them`.
- *A `--target` that does not exist exited 0 and guarded nothing,* so a mistyped path let `--out` write into the folder
  really governed. Now exit 2. Guard:
  `tests/test_refusals.py::test_a_target_that_does_not_exist_is_refused_with_one_line_and_nothing_is_written`.
- *`--out` could leave a partial file.* It is now written to a temporary file and moved into place. This fix caused
  the 0.3.7 `--out` defect above. Guard:
  `tests/test_atomic_out.py::test_a_write_that_fails_half_way_leaves_no_partial_file_and_no_temporary`.

**0.3.4** (2026-10-21)
- *Installing the Watcher with Warden needed `--no-deps`.* In 0.3.3 the tested Warden commit still required an older CNS,
  and pip reported `ResolutionImpossible`, so CI installed Warden with `--no-deps` as a stopgap. 0.3.4 tested a Warden
  that pins the same CNS and removed the workaround. Guard:
  `tests/test_pins.py::test_the_warden_jobs_resolve_dependencies_and_are_blocking`.

**0.3.2** (2026-10-21)
- *The status filter kept sign-offs and disguised labels.* "mergeable" and "shippable" never matched; Hangul fillers and
  the braille blank hid a label; lookalike letters, a citation set into a label, and a label set across lines got
  past it; sign-offs such as "free of defects" and "can go live" were kept. All were fixed in this release. Guard:
  `tests/test_oath.py::test_the_able_words_are_status_claims`,
  `tests/test_oath.py::test_fillers_that_draw_nothing_do_not_hide_a_label`,
  `tests/test_oath.py::test_a_citation_inside_a_label_does_not_hide_it`,
  `tests/test_oath.py::test_a_label_set_across_lines_drops_every_line_of_it` and
  `tests/test_oath.py::test_more_sign_offs_are_status_claims_even_when_cited`.
- *The filter dropped honest sentences.* It did not read negation, so "Nothing was approved" and "not production ready"
  were dropped. A label with a negator among the four words before it is now a description and is kept. Guard:
  `tests/test_oath.py::test_a_denied_label_or_a_report_of_one_is_not_a_status_claim`.
- *The 0.3.1 changelog overstated.* It said honest sentences near these words "are still kept". That was too strong, for
  the reason above. The CHANGELOG now carries the correction. No test for the changelog text.

**0.3.1** (2026-10-17)
- *A response the SDK could not decode gave exit 1 ("internal error").* Now exit 3 and nothing is written. Guard:
  `tests/test_refusals.py::test_a_200_the_sdk_cannot_decode_is_exit_3_and_nothing_is_written`.
- *The filter kept cited sign-offs* such as "ship it", "LGTM", "approved", "looks good" and "OK for production use", and
  did not join letters set apart or read text under a bidirectional override. Guard:
  `tests/test_oath.py::test_approvals_and_all_clears_are_status_claims_even_when_cited`.
- *A missing record was reported as "cannot be read as JSON: FileNotFoundError",* and `--out` silently created a missing
  folder. Now "file not found" (exit 2), and a missing folder is refused unless `--create-out-dir` is given. Guard:
  `tests/test_refusals.py::test_a_missing_record_says_file_not_found_and_is_exit_2` and
  `tests/test_refusals.py::test_a_missing_out_folder_is_refused_and_nothing_is_created`.
- *The co-install CI job was informational,* with a title saying it was red until Warden pinned CNS by commit. It is
  blocking now. Guard: `tests/test_pins.py::test_the_warden_jobs_resolve_dependencies_and_are_blocking`.

**0.3.0** (2026-10-17)
- *The CNS pin was a tag (v1.6.0) that silently downgraded CNS* when the Watcher was installed after the other
  repositories of the circuit, and installing the Watcher with Warden did not resolve. Guard:
  `tests/test_pins.py::test_the_installed_cns_is_the_pinned_one`.
- *A record with a field of the wrong shape crashed with a `TypeError` and exit 1,* and an API error gave a traceback.
  Now exit 2 and exit 3, one line each. Guard:
  `tests/test_refusals.py::test_a_malformed_field_is_exit_2_never_a_traceback` and
  `tests/test_refusals.py::test_an_unreachable_model_is_exit_3_with_the_documented_message`.
- *`--out` could overwrite the record being read,* also through a symlink, a relative path or a hard link. Guard:
  `tests/test_refusals.py::test_out_may_not_be_the_record_itself`.
- *A finding id in a record could replace the decision citation.* Guard:
  `tests/test_refusals.py::test_a_finding_id_cannot_replace_the_decision`.
- *An empty `unmeasured` list was reported as "every check ran",* which a run that ended before it began did not earn.
  It now says "nothing listed in the record". Guard: `tests/test_evidence.py::test_the_real_record_indexes_every_kind_of_thing`.

## SELF-HOSTING

The full circuit has governed a fresh clone of this repository, twice. The record is the CNS repository's
`docs/evidence/SELFHOSTING_2026-10-23.md`, which is on the CNS branch `claude/horsemen-production-status-5wsndb` until it
is merged (https://github.com/wking53214/CNS/blob/claude/horsemen-production-status-5wsndb/docs/evidence/SELFHOSTING_2026-10-23.md);
the run records are copied beside it. Both runs were at version 0.3.8, commit `b25d8522301005ba764783927f43abfeb9f18f5c`.
Run 1 had Burnish 0.3.11 as the finisher and run 2 had Burnish 0.3.12. Each ended with decision ACCEPT: the suite was
701 passed with 0 skipped, Ghost reported 41 findings at the start and 41 at the end with none new, and 7 checks were
declined (mutate, kernel, structure, tests, project, secrets, correlate), which makes 7 gaps. The finisher's README edit
was kept each time. What this does not mean: an ACCEPT that carries 7 gaps does not mean there are no secrets, no weak
tests, no mutation survivors and no structural problems, because those checks did not run; and the 41 findings still
stand, because the Judge measures "none new". The runs cover that commit only, not the commits after it, and a person
did not review the kept README edit.

## CEILINGS CODE CANNOT FIX

- The repository is young. Its history starts on 2026-10-14.
- It has one human maintainer, and most commits were written with an AI assistant (the commit trailers say so).
- It has no known outside users.
- The owner released it from the Horsemen circuit on 2026-10-29 (see the status note under WHAT THIS IS). Nothing in it was removed, and it keeps working on its own.
- Releases are tagged by the owner, not by the code. Check the repository's tags and releases on GitHub for what exists.

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2026 William N. King.
