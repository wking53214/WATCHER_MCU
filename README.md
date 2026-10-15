# WATCHER_MCU

The Watcher sees every run of the circuit and is sworn not to interfere.

It is an AI entity (Claude, through the official SDK) that reads the record Warden prints at the end
of a run and tells a person what happened in plain words. It has no authority and no reach: nothing
in the circuit reads what it writes, it cannot touch a verdict, a finding, a file or a baseline, and
every sentence it keeps cites a measurement in the record by id. A sentence that cites nothing,
cites something that is not there, or makes a status claim of its own is dropped before anyone reads
it, and the account says how many were dropped and why.

Version `0.2.0` (reads `cns.run/1`). Apache-2.0. Copyright 2026 William N. King.

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
```

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
record alone, deterministically. `--model` chooses the Claude model (default `claude-fable-5-1`, the
model that wrote the Watcher; `claude-opus-5-5` is the ordinary choice); `--effort` low to max.

## THE OATH, AS CODE

| The promise | Where it is kept |
|---|---|
| It reads the run record and nothing else | `narrate.prompt_for` shows the model the citation index only. No file, no diff, no repository. |
| It writes nothing into the governed folder or any checkout the record names | `cli.main` resolves `--out` against the governed folder (`--target`) and every instrument and joined path in `versions`, and refuses with exit 2. `tests/test_charter.py` reads the source: only `cli.py` writes, and only the account. |
| Nothing in the circuit reads it | Warden, the Judge, Ghost, SWIZZLE and the seats have no input for it. Not ignored: structurally absent. The Watcher imports none of them (`test_charter.py`). |
| Every kept sentence cites the record | `oath.enforce`: no citation, drop; unknown citation, drop. |
| It claims no status of its own | `oath.status_claim`: "production ready", "battle-tested", "fully tested", "enterprise grade", "100% coverage", read the way a person reads them (NFKC, emphasis and invisible characters stripped), drop. The same labels Ghost Tools reports for re-verification. |
| It is a description, never a grade | The system prompt says so; the filter makes an uncited grade vanish; the account's first line repeats the decision as recorded, cited. |
| A refusal is an empty account, not a quiet one | A model that declines (safety classifier) exits 3 with no file written. An account the oath empties exits 4 and still shows what was dropped. |

## WHAT IT IS NOT

- Not a seat. Warden never loads it; `warden tagteam` runs to its end without it.
- Not an instrument. It measures nothing; it cannot run the suite, Ghost or SWIZZLE.
- Not a judge. It can say "the Judge said INSUFFICIENT [V]"; it cannot say "this is fine".
- Not a reader of code. Version 0.1.0 reads the run record only. Reading files is a later
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
  dropped with the reason, through emphasis and invisible characters; headings are structure.
- `tests/test_evidence.py`: a real run record (SWIZZLE, 2026-10-15, joined through a stack manifest)
  indexes every kind of thing with stable ids; forbidden paths are the governed folder and every
  checkout the record names.
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
- That the status-claim list is complete. It mirrors Ghost Tools' list on 2026-10-15; a new label
  needs adding in both places.

## KNOWN DEFECTS

- The oath checks sentences, not arguments. A kept sentence can cite the right id and still
  paraphrase it badly; the citations appendix exists so a reader can check.
- A heading is kept without a citation when it is short and claims no status. A model that wants to
  editorialize could do it in headings. The account shows headings as headings.
- `--target` is needed for the governed folder because Warden's record does not name it; the
  instrument and joined paths are refused from the record alone.
