# Changelog

All notable changes to the Watcher are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). The version lives in one place, `watcher.__version__`;
`pyproject.toml` reads it. Releases are tagged by the owner; check the repository's tags and releases on GitHub for what exists.

## [Unreleased]

## [0.3.10] - 2026-10-29, not tagged

### Changed
- The README says, in WHAT THIS IS and in CEILINGS CODE CANNOT FIX, that the owner released the Watcher from the Horsemen
  circuit on 2026-10-29. Released means removed from the circuit and nothing else: no code, test, history or CI was changed.
  Nothing in the circuit reads what the Watcher writes. It still works on its own (`watcher narrate` on any run record).
  Warden 0.15.0 lets a pinned manifest leave the Watcher out; until the pins move, the circuit still installs it. The Watcher
  is free to be reborn elsewhere, as intent only. (Step R1)
- Version 0.3.10 and this entry. No pin changed. (Step R2)

## [0.3.9] - 2026-10-24

### Fixed
- `watcher narrate RECORD --no-model | head -c0` printed "internal error: BrokenPipeError ... Nothing was written." and
  exited 1 (the exit table says 1 is a bug in the Watcher), with and without `PYTHONUNBUFFERED=1`; a closed standard
  output gave the same message for an `AttributeError`. A broken pipe now prints nothing and keeps the earned code (0, or
  4 when the oath kept nothing). Any other failed delivery on standard output (closed, or a failing write such as a full
  device) is one plain line on standard error and exit 2, because an account that was not delivered was not given. `main`
  does not replace `sys.stdout`. Found by the round-6 audit; reproduced first. (Step 1)

### Changed
- Warden is pinned at 0.13.10, commit `9ecd1124e6c1b1c4ad7daed37b17f9009662dd9d` (was 0.13.9 at
  `b57b81e1c98333c43d422666c89a8fcf3ae6eaca`), in the workflow, README, STACK, the `watcher/oath.py` comment and the
  tests. CNS stays `@v2.0.0`. (Step 3)

### Documentation
- SELF-HOSTING cites the CNS repository's `docs/evidence/SELFHOSTING_2026-10-23.md` (on the CNS branch until merged):
  ACCEPT twice at 0.3.8, 701 passed with 0 skipped, 41 Ghost findings standing, 7 declined checks, and what an ACCEPT
  with 7 gaps does not mean. The caveat about `--target` is written once. Six paraphrases that pass the oath filter when
  cited are listed as a known defect, and the README lists as a drift risk that the Watcher reads the declined checks,
  dirty flags and gaps itself instead of calling CNS 2.0.0's `RunRecord.declined`, `gaps()` and `dirty_parts()`. (Step 2)
- A ledger entry for 0.3.9 and a line for `tests/test_delivery.py` under WHAT WORKS. (Step 4)

### Tests
- New: `tests/test_delivery.py` (Step 1) and `tests/test_oath_known_gaps.py` (Step 2, documents current behaviour as a
  known gap).
- Pre-existing tests edited, each to assert the new behaviour and nothing else: `tests/test_readme_ledger.py`, the
  self-hosting test now holds the new paragraph and the recorded numbers (Step 2); `tests/test_pins.py` and
  `tests/test_warden_e2e.py`, the Warden commit and version (Step 3).

## [0.3.8] - 2026-10-22

### Changed
- The CNS pin moves from the tag `v1.9.0` to the tag `v2.0.0`: `cns @ git+https://github.com/wking53214/CNS.git@v2.0.0`,
  with the comment `# v2.0.0 = b13e5d2f9e0e4291725f82794b89117c3d840ac1` in `pyproject.toml`, the same spelling as the
  other repositories of the circuit. README, STACK and `tests/test_pins.py` follow. The Watcher imports only `cns.run`
  and the suite passes against the installed cns 2.0.0 (`direct_url.json`: requested revision `v2.0.0`, commit
  `b13e5d2f9e0e4291725f82794b89117c3d840ac1`) with no change to the code. (Step 1)
- CI, README, STACK, the `watcher/oath.py` comment and the tests name Warden 0.13.9 (not tagged) at commit
  `b57b81e1c98333c43d422666c89a8fcf3ae6eaca` (was 0.13.8 at `380894f0304ef40587dd29efd41b4ceccf94a5d3`). That Warden pins
  CNS `v2.0.0`, so pip resolves the Watcher and Warden together with one CNS and `pip check` is clean. The end-to-end
  version assertion expects 0.13.9. The Watcher has no pin to ghost_tools, SWIZZLE or ASSAY. (Step 2)

### Documentation
- README rewritten to state what works (each line names its test or CI job), what does not work or is not proven, the
  open defects, what broke and how it was fixed (checked against this changelog, `git log` and the tests), what is and is
  not recorded about the circuit governing this repository (Warden's registry rows 5 and 6 do not list it, and they
  predate the current rules), and the ceilings code cannot fix. The install commands were run in a fresh virtual
  environment. Removed because they could not be verified here: that the label list is a superset of Ghost Tools' list,
  a date on the SWIZZLE fixture, and a count of other languages. Two statements were corrected: the `[CV]` defect fixed in
  0.3.7 described the last cycle that had observed anything, not the first cycle; and the `--out` defect of 0.3.7 was
  introduced by the atomic write of 0.3.6. (Step 3)
- This file no longer says whether a release is tagged (the statement goes stale). Past entries are unchanged.

### Tests
- New: `tests/test_readme_ledger.py` (the sections exist, the tests the README names exist, the ledger's versions and
  dates match this changelog, the numbers it states match the code, no marketing words, no claim about tags).
- Pre-existing tests edited, each to assert the new behaviour and nothing else: `tests/test_pins.py` (the CNS tag and
  commit, Step 1; the Warden commit and version, Step 2) and `tests/test_warden_e2e.py` (the expected Warden version,
  Step 2).

## [0.3.7] - 2026-10-22

### Changed
- CI, README, STACK, the `watcher/oath.py` comment and the tests name Warden 0.13.8 (not tagged) at commit
  `380894f0304ef40587dd29efd41b4ceccf94a5d3` (was 0.13.7 at `1636e1a21f124eedbf6e158db95dc75344f4308d`). The CNS pin is
  unchanged: the tag `v1.9.0`. The end-to-end version assertion expects 0.13.8. (Step 1)
- The template account is complete about what the record says, from the record only. It lists every cycle of the record
  (it listed C1 to C3; there is no cap now). It says when `put_back` is true and when `finished` is true, says that
  `swizzle_sound` is false (SWIZZLE's proofs did not hold) or null (no result) and, when true, that its proofs held, and
  shows the notes that say a step failed, was skipped, was not run, was not enforced or was not sound (for example a
  SWIZZLE proofs note with "3 FAILED"). The lines of `drafter_skipped` and `informational` are shown in a section
  labelled as information, not gaps. The finding ids of `observed` and `reobserved` are named, the first 20 distinct
  ones of each with a count of the rest; README, WHAT IS NOT PROVEN, says so. (Step 4)

### Fixed
- `--out` replaced whatever stood at its path. The account is moved into place with `os.replace` on the resolved path,
  so a named pipe, a device node or a symlink resolving to one was swapped for a regular file (a folder gave a raw
  `IsADirectoryError`), and an existing `0600` account was rewritten as `0644`. A target that exists and is not a
  regular file, resolved through symlinks, is now refused (exit 2, one line, nothing written, no temporary file), checked
  again just before the move. An existing file keeps its permission bits; a new file keeps the default. README and the
  exit-code text say so. (Step 2)
- Text the record supplies could add structure to the account. The template built the declined line, the dirty line (a
  join path, a seat) and the Judge's decision from raw record strings, so a declined entry of
  `"\n## Injected heading\n- [R] The code is fine ..."` made a heading and a bullet that the oath kept as a fact. Every
  record-derived string is now reduced to one plain line (`watcher.evidence.clean`, the cleaning the citations already
  had, which also turns other control characters into spaces and removes bidirectional controls) before it is put in
  a line, so the oath reads the text that is rendered. The `--out` refusal line cleans the path it names. (Step 3)
- `[CV]` said "Ghost still observed N finding(s) in cycle k" for the last cycle that had observed anything, so cycle 1
  observing 2 and cycle 2 observing 0 gave "still observed 2 in cycle 1", which is false. It now describes the final
  cycle of the record (the last in its list) and is absent when that cycle observed none. (Step 5)
- Four small defects. Warden's commit rendered as "at None" when the record holds none; it now says "commit not
  recorded" (and "version not recorded" for a missing version), and the `[W]` line is no longer cut at 400 characters.
  `dirty` was honoured only for the boolean true; any value other than true, false or null (the text "true", the number
  1) is now marked "DIRTY OR UNREADABLE", named in a line of its own and treated as possibly dirty. `--target` may no
  longer be a file: it must be a folder (exit 2 otherwise). A `[G]` line was dropped whole when one declined name
  tripped the oath's denylist; only that name is withheld now (with the number withheld), and the other names stay.
  (Step 6)

### Tests
- New: `tests/test_atomic_out.py` (special files, symlinks to them, permission bits), `tests/test_record_text.py`,
  `tests/test_account_completeness.py`, `tests/test_minor_fixes.py`, and cases in `tests/test_account_honesty.py` for
  `[CV]`. Pre-existing tests edited, each to assert the new behaviour and nothing else: `tests/test_pins.py` and
  `tests/test_warden_e2e.py` (the Warden pin and version, Step 1) and `tests/test_charter.py` (the list of write calls in
  `cli.py` gains `chmod`, Step 2).

## [0.3.6] - 2026-10-21

### Changed
- CI, README, STACK, the `watcher/oath.py` comment and the tests name Warden 0.13.7 (not tagged) at commit
  `1636e1a21f124eedbf6e158db95dc75344f4308d` (was 0.13.6 at `0c1ea567f0b69586cfd735f82260774aec9552bb`). The CNS pin is
  unchanged: the tag `v1.9.0`. The end-to-end version assertion expects 0.13.7, and `pip check` is clean with one CNS
  after the Watcher and Warden are installed together. (Step 1)
- The account states what the record says was not done, from the record only (found by the circuit audit, on a real
  record: it said "not measured: nothing listed" and "gaps: none" while `ghost_scan.declined` listed seven checks Warden
  did not run). `[G]` now carries "declined, so not run: ..." and the template account names the declined checks and says
  that a declined check was not run, so the absence of findings from it means nothing. A part of `versions` (Warden, an
  instrument, a seat, a joined checkout) whose `dirty` flag is `true` is marked "DIRTY: uncommitted changes" in `[W]` and
  `[J<n>]` and named in a line of its own; `null` is not reported as dirty. When `converged` is true and a cycle still
  observed findings, `[CV]` says converged is not zero findings, and Warden's own note to that effect is kept in the
  template. A `ghost_scan.declined` that is not a list is refused by name, like `gaps`. The oath denylist is unchanged.
  README (the account description and WHAT IS NOT PROVEN) says the same. New tests in `tests/test_account_honesty.py`,
  on a real record (`tests/fixtures/warden_0_13_6_declined_record.json`), fail on the old output. (Step 2)

### Fixed
- `watcher narrate ... --target PATH` with a PATH that does not exist exited 0 and guarded nothing, so a mistyped
  `--target` let `--out` write into the folder really governed. It now exits 2 with one line. (Step 3)
- `--out` is written to a temporary file in the same folder and moved into place with `os.replace`, so a failed write
  leaves no partial file and no temporary file, and an earlier account at that path stays whole. Not synced to disk.
  (Step 4)

### Tests edited
- `tests/test_pins.py` and `tests/test_warden_e2e.py`: the expected Warden commit and version (Step 1).
- `tests/test_charter.py`, `test_only_the_cli_writes_and_only_the_account`: the exact set of write calls in `cli.py` is
  now `mkdir`, `unlink`, `write_text` (the temporary file of Step 4 is removed after a failed write). Nothing else about
  it changed (Step 4).

## [0.3.5] - 2026-10-21

### Changed
- The CNS dependency is pinned by the release tag: `cns @ git+https://github.com/wking53214/CNS.git@v1.9.0`, the
  spelling every repository of the circuit uses (it was the full commit SHA). The tag peels to
  `da18e411743d4e3b0e783105394d845fb1c16746`, so the installed CNS is the same commit. `tests/test_pins.py` asserts the
  tag spelling and still checks the installed commit.
- CI, README, STACK, the `watcher/oath.py` comment and the tests name Warden 0.13.6 (not tagged) at commit
  `0c1ea567f0b69586cfd735f82260774aec9552bb` (was 0.13.5 at `decc3c3b5af479ad0eef3df4d66dbcb21e90897c`). The end-to-end
  version assertion expects 0.13.6.

## [0.3.4] - 2026-10-21

### Changed
- CI, README, STACK and `tests/test_pins.py` test against Warden 0.13.5 (not tagged) at commit
  `decc3c3b5af479ad0eef3df4d66dbcb21e90897c` (was 0.13.4 at `36e98433f4928b7d12905f02b56e55ee1943b56e`). That Warden
  commit pins CNS `v1.9.0` (`da18e411743d4e3b0e783105394d845fb1c16746`) itself, the same as the Watcher, so the
  `--no-deps` workaround is gone: the `warden-e2e` and `coinstall-warden` jobs install the Watcher and Warden together
  with full dependency resolution and run `pip check`, which is clean with exactly one CNS installed.
  The test that asserted `--no-deps` is restored to its earlier form (no `--no-deps`, `pip check`, blocking jobs), and
  the end-to-end version assertion expects 0.13.5.
- The CNS pin is unchanged (`da18e411743d4e3b0e783105394d845fb1c16746`, `v1.9.0`). `origin/main` (`747656c`) is already
  contained in this branch; no merge was needed.

## [0.3.3] - 2026-10-21

### Changed
- CNS moves from `v1.8.0` to `v1.9.0`: the dependency is pinned to the full commit
  `da18e411743d4e3b0e783105394d845fb1c16746` (the peeled commit of the tag, from `git ls-remote`), in `pyproject.toml`,
  README, STACK.md and `tests/test_pins.py` (which checks the installed CNS commit and version against the pin).
  `cns/run.py`, the only CNS module the Watcher reads, is unchanged between `v1.8.0` and `v1.9.0` (`git diff` is empty),
  so the Watcher reads the `cns.run/1` record Warden writes exactly as before; the end-to-end tests confirm it.
- The tested Warden commit (0.13.4, `36e98433f4928b7d12905f02b56e55ee1943b56e`) still requires CNS `v1.8.0`
  (`5252ceebe98185f7be81212d988055ccf9884568`), and pip reports `ResolutionImpossible` for the Watcher and that Warden
  together. Until a Warden commit pins `da18e41`, the `warden-e2e` and `coinstall-warden` CI jobs install the Watcher
  with its dependencies and Warden with `--no-deps`, then run `pip check`; the workflow comments name the condition for
  dropping `--no-deps` and the SHA that the owner session must supply. No Warden SHA was invented.
- CI, README and STACK test against WARDEN 0.13.4 at commit `36e98433f4928b7d12905f02b56e55ee1943b56e` (was 0.13.3 at
  `580f659`). Verified with `git ls-remote` (the commit is the head of Warden's branch
  `claude/horsemen-production-status-5wsndb`) and Warden's `warden/__init__.py` (`__version__ = "0.13.4"`).
  `tests/test_pins.py`, the end-to-end version assertion and the exact-text source of `watcher.oath.WARDEN_STANDARD`
  follow it. The end-to-end tests ran against clean clones of the tested set (ghost_tools `5d7a386`, SWIZZLE
  `8166c47`, ASSAY `4c41556`).
- A record from Warden 0.13.4 that has `allow_uncommitted_instruments: true` is narrated: the flag is cited as `[AU]`
  and listed under "What was not" beside `[U]` (which names `instrument_provenance` as not measured), with Warden's
  own note naming the instrument. New fixture `tests/fixtures/warden_0_13_4_uncommitted_record.json` is a real
  record (paths neutralised).

## [0.3.2] - 2026-10-21

### Changed
- CI, README and STACK test against WARDEN 0.13.3 at commit `580f659336818b4a5a2c0ca235d2344012536426` (was 0.13.2 at
  `9d9a71d`, and 0.13.1 at `ec551d8` before that). Verified with `git ls-remote` (the commit is the head of Warden's
  branch `claude/horsemen-production-status-5wsndb`) and Warden's `warden/__init__.py` (`__version__ = "0.13.3"`).
  The end-to-end tests, the full suite, ruff and mypy ran green with it installed, and `pip check` is clean for the
  Watcher beside Warden. `tests/test_pins.py` now names the expected commit and version.
- The end-to-end test finds `warden` in the bin folder of the interpreter running the tests first, then on the PATH,
  so a virtual environment that is not activated works. It also asserts the installed Warden is 0.13.3.
- The status filter reads negation. A label with a negator among the four words before it, in the same clause, is a
  denial and is kept: "Nothing was approved", "cannot be applied safely", "not production ready", "not ship-ready",
  "Warden could not make a safe place for its lock". A clause start ("and", "but", "so", "that"), a cancelling word
  ("not only", "no doubt", "nobody doubts", "nothing stops") or two negators leaves the label standing, and a denial
  of a bad word ("not unsafe", "never risky") is dropped as the good-thing claim it is.
- "No issues", "no known bugs" and their kin are kept when a named part of the circuit reports them ("Ghost reported
  no issues", "no known bugs were reported by Ghost"), never in the first person or in the Watcher's own voice.
- "Secure" before a technical noun (hash, cookie, shell, token and so on) is not a label ("a secure hash call").
- Warden's own standard sentences are allowed by exact text (`watcher.oath.WARDEN_STANDARD`, from Warden 0.13.3 at
  `580f659`); `tests/test_warden_e2e.py` checks each is still a string in the installed Warden.
- The system prompt no longer tells the model that every use of "safe" is deleted or that a denial is deleted; it says
  what is kept.

### Added
- A fixture, `tests/fixtures/warden_0_13_2_record.json`, trimmed from a real `warden tagteam` run (Warden 0.13.2
  with ghost_tools `5d7a386`, SWIZZLE `123d7ab`, ASSAY `7b781cf`; paths neutralised), and tests that the account
  prints a real ASSAY version (0.11.1) rather than "None". The same tests show that `module` and `module_in_root`,
  newly added to `versions.ghost_tools`, `versions.swizzle` and `versions.assay`, and any other unknown field are
  accepted without a crash and without changing the account.

### Fixed
- `(?:ship|deploy|merg|releas)able` never matched "mergeable" or "shippable". It now matches shippable, shipable,
  mergeable, mergable, deployable, releasable and releaseable.
- Invisible fillers were kept: the Hangul fillers U+115F, U+1160, U+3164 and U+FFA0 and the braille blank U+2800 are
  letters and symbols, not format characters. Every Unicode default-ignorable character is now listed and stripped, and
  the five fillers are read both as nothing and as a gap ("sa<filler>fe" and "is<filler>safe").
- Letter forms NFKC does not fold were kept: negative circled and squared letters, regional indicators, Cherokee,
  Armenian, Greek and Cyrillic lookalikes (for LGTM and SAFE), "f" as digamma, f with hook or Cyrillic ghe with stroke.
  The lookalike table is now the old hand list plus letters derived from the Unicode names, plus about 1,700 single
  characters from the Unicode confusables data (`watcher/_homoglyphs.py`, generated by `tools/make_homoglyphs.py`,
  credited in NOTICE). A lookalike with two readings (a Cyrillic I is an "i" and an "l") is read both ways.
- A citation set into a label ("production [R] ready", "ship [R] it", "sa[R]fe") hid it. The `[id]` tags are now
  taken out for a second reading; the citation is still required for every kept sentence.
- A label set across lines was kept: one bullet per letter, "sa" over "fe", "production" at the end of a line and
  "ready" at the start of the next. Lines are now read at their seams and as runs of one- and two-letter lines.
- Sign-offs that were kept: the check-mark, thumbs-up, 100, OK, rocket and green-circle emoji, "free of defects",
  "without defects", "ready 4 production", "can go live", "no blockers", "rest easy", "nothing to worry about", "no
  cause for concern", "green light", "thumbs up", and a short list in Spanish, Portuguese, French, German, Italian,
  Russian, Chinese, Japanese and Korean ("es seguro" and the Chinese for "safe" among them). Text under nested
  bidirectional controls is also read the crude way (everything after the first right-to-left start, reversed).

### Documentation
- README: the oath table and WHAT IS NOT PROVEN now say precisely what the filter does and does not do, including
  negation, the report exception, the allowlist, the paraphrase and language limits and the honest sentences it still
  drops. The 0.3.1 changelog claim that honest sentences near these words "are still kept" was too strong (the filter
  did not read negation and dropped honest sentences that contain a label); it is corrected below.

### Tests
- One existing test asserted the exact behaviour this release changes: the entry "Not production-ready yet [R]." in
  `test_a_status_claim_of_its_own_is_dropped_even_when_cited` (a denied label was dropped; it is now kept). The entry
  is removed from that list and asserted kept in the new denial tests; nothing else about the test changed.
- Tables for every case above: dropped and kept lists for the able words, the fillers (every default-ignorable
  character and every format character in Unicode), lookalikes (every negative circled and squared letter and regional
  indicator, derived from the Unicode names), citations in labels, labels across lines, the new sign-offs, nested
  bidirectional controls, and honest sentences near a label against sentences that only look like them.

## [0.3.1] - 2026-10-17

### Changed
- CI tests against WARDEN 0.13.1 at commit `ec551d8e10f82b6e3e681593a97011ae517d360b` (was 0.12.0 at
  `2cf0eec`). Warden now pins the same CNS commit as the Watcher, so `pip install . ./WARDEN` resolves
  with full dependency resolution and `pip check` is clean: the `--no-deps` workaround is gone and the
  co-install job is blocking (it was informational, with a title that said it was red until Warden
  pinned CNS by commit). The end-to-end tests ran against this Warden: 3 passed.
- `tests/test_pins.py` checks that both Warden checkouts in CI use one full commit that README and
  STACK name, that no `--no-deps` or `continue-on-error` is left, and that every action is pinned by
  commit with its tag in a comment.
- `--out` no longer creates a missing folder. It is refused with exit 2, before the model is asked,
  unless `--create-out-dir` is given. The forbidden-folder and overwrite checks run first and are not
  lifted by the flag.

### Fixed
- A 200 response from the API whose body is not JSON (or is not a message) gave exit 1 ("internal
  error: JSONDecodeError"). It is now exit 3 with "no model could be reached" and nothing written, like
  the other API errors. Documented in the exit-code table.
- The status filter kept cited sentences such as "ship it", "LGTM", "approved", "looks good", "all
  clear", "no issues with this change", "trustworthy", "reliable and robust", "OK for production use"
  and "good to go". They are labels now. Single letters set apart ("s a f e") are joined up before the
  labels are looked for, and text under a bidirectional override (letters stored as "efas" that show as
  "safe") is read in the order it is displayed as well as the order it is stored. The README says again
  that a denylist is not a proof of completeness. Correction, made in 0.3.2: this entry said honest sentences near
  these words "are still kept". That was too strong: the filter did not read negation, so an honest sentence that
  contains a label, such as "Nothing was approved" or "not production ready", was dropped.
- A record file that does not exist is reported as "file not found" (exit 2) instead of "cannot be read
  as JSON: FileNotFoundError". Other read errors say "cannot be read", not "as JSON".

### Documentation
- README: the tested Warden commit and how to bump it, `--create-out-dir`, the exit-3 and exit-2
  rows, the filter's new coverage and its limits.
- STACK.md: the tested Warden commit.
- CHANGELOG: no release is tagged; tagging is the owner's decision.

### Tests
- One existing test (`test_cli_writes_the_template_account_without_a_model`) wrote into a folder that
  did not exist; it now passes `--create-out-dir`. Nothing else about it changed.

## [0.3.0] - 2026-10-17

### Changed
- CNS is pinned to the full commit of release `v1.8.0` (was the `v1.6.0` tag). `cns/run.py` is
  identical in both releases. With the old pin, installing the Watcher after the other repositories
  of the circuit silently downgraded CNS and broke them, and `pip install` of the Watcher and Warden
  together did not resolve.
- The status filter reads a sentence as a person reads a rendered page before looking for a label:
  HTML entities decoded, markup and Markdown links removed, NFKC, case folded, accents and invisible
  characters dropped, every Unicode dash read as a hyphen, Cyrillic, Greek and small-capital
  lookalikes folded to Latin, and digits or symbols used as letters read as letters.
- The label list is broader: production-grade, production quality, ready for production, ready to
  ship, release-ready, battle-proven, well-tested, fully verified, complete test coverage, safe,
  secure, bulletproof, hardened, rock solid, bug-free, no known bugs and kin. A cited claim ("The run
  passed and is safe [R]") is dropped like an uncited one.
- "Who took part" now lists the Drafter, Burnish and Judge seats that Warden's record names in
  `versions.seats`, not only the instruments.
- An empty `unmeasured` list is reported as "nothing listed in the record" instead of "every check
  ran", which a run that ended before it began did not earn.
- The system prompt tells the model about the wider label list.
- Package version is read from `watcher.__version__` (single source of truth).
- Continuous integration: Python 3.11, 3.12 and 3.13; ruff with a wider rule set; mypy in strict
  mode; actions pinned by commit; a job that runs the real Warden writer and narrates its record;
  a check that the installed CNS is the pinned one.

### Fixed
- A record with a field of the wrong shape (`cycles: 5`, `reobserved: 7`, `versions.joins: 5`, and
  every other field the index reads) crashed with a `TypeError` traceback and exit 1. It is now
  refused with one line and exit 2.
- An Anthropic API error (connection, timeout, status, a missing credential) gave a traceback and
  exit 1. It is now exit 3 with "no model could be reached" and nothing written.
- `--out` could overwrite the record being read (also through a symlink, a relative path or a hard
  link). It is now refused with exit 2.
- `--out` that cannot be written (a directory, an unwritable parent) is exit 2, not a traceback.
- A finding id in a record can no longer replace the decision or verdict citation (`R`, `V`).
- An unexpected internal failure is exit 1 with one line, not a bare traceback.

### Added
- `--verbose` / `-v` and `watcher` logging to standard error.
- Tests: a table of malformed record fields, the unreachable-model cases, `--out` over the input,
  every status-filter bypass found, seats in the account, the README exit-code table against the
  code, version and pin agreement, and an end-to-end test against the real Warden (CI job
  `warden-e2e`).
- This changelog.

### Documentation
- README: version, the exit-code table, the diagnostics section, the real scope ("reads the run
  record only" no longer says "Version 0.1.0"), the wider filter, and the known defects.
- STACK.md: the Watcher does read CNS (`cns.run`); the pin policy.
- The command's docstring lists exit codes 0 to 4.

## [0.2.0] - 2026-10-15

### Added
- The run record is read through the `cns.run/1` contract from the CNS repository (`RunRecord`). A
  record that predates it, names another schema version, or has a field the contract refuses is
  refused with the reason.

### Changed
- Dependency on the CNS repository, pinned to the `v1.6.0` tag.

## [0.1.0] - 2026-10-15

### Added
- First release. `watcher narrate RUN.json [--out FILE] [--target DIR] [--model M] [--effort E]
  [--no-model]`: the account of one Warden run record for a person. Every kept sentence cites a
  measurement in the record by id; a sentence that cites nothing, cites what is not there, or claims
  a status of its own is dropped, and the account shows what was dropped and why.
- The deterministic template account (`--no-model`), the citation index, and the refusal to write
  into the governed folder or any checkout the record names.
- Exit codes 0, 2, 3 and 4.
