# Changelog

All notable changes to the Watcher are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). The version lives in one place, `watcher.__version__`;
`pyproject.toml` reads it. No release of this repository is tagged; tagging is the owner's decision.

## [Unreleased]

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
