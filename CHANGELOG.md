# Changelog

All notable changes to the Watcher are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). The version lives in one place, `watcher.__version__`;
`pyproject.toml` reads it.

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
