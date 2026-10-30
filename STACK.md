# The circuit, and where the Watcher stands

Five repositories make the circuit; the Watcher is not one of them. It was never a seat of the circuit Warden runs:
it narrates a Warden run record, downstream, with nothing coming back. It is released from the circuit's roster by
owner ruling (2026-10-29), along with DRAFTER and BURNISH; nothing was deleted and each still works on its own. CNS's `contracts/warden-stack.json` does not name the Watcher, and the header comment of `contracts/install-stack.txt` mentions it only as released and not installed.

| Repository | Role |
|---|---|
| ASSAY | the answer key: specimens with known failure modes (an instrument, not released) |
| ghost_tools | the scanner: Ghost observes and reports, never writes |
| SWIZZLE | the attacker: proves, grades Ghost against ASSAY, attacks Warden |
| WARDEN | the governor: applies, measures, refuses and puts the tree back; the only writer; any actor's real change enters through its claim seat (`--claim-commit` or `--claim-diff`) |
| JUDGE | reads the evidence, says ACCEPT, REJECT or INSUFFICIENT (Warden reports INSUFFICIENT as a hold) |
| **WATCHER_MCU** | **not part of the circuit: reads Warden's record, tells a person, interferes with nothing** |

DRAFTER and BURNISH are released from the circuit too. A bare `--stack` still requires all six checkouts (drafter and
burnish included); only a pinned `--stack-manifest` that omits them, with a folder that lacks them, runs without them, and
the run record lists `released_seats`. Every Warden run declines eight Ghost checks (mutate, kernel, structure, tests,
project, secrets, correlate, ledger) since ghost_tools 1.10.11; text that says seven describes a dated earlier run.

Run the circuit, then the Watcher:

```
warden tagteam PATH --stack FOLDER --stack-manifest stack.json --claim-commit SHA --authorize "Your Name" --reason "why" --scope code > run.json
watcher narrate run.json --target PATH --out account.md
```

CNS holds the interoperability contracts. No repository in the circuit modifies it. The Watcher reads
the run record through it: `watcher.evidence` imports `cns.run` and refuses any record that is not
`cns.run/1`. CNS is installed from its git URL, pinned by the release tag `v2.2.0`
(a lightweight tag, so the tag is the commit `ce6bd05578a7a3e3cafa0cfa1e9a2cca8a5f171f`); installing the Watcher needs access to that repository.
CI tests the Watcher against Warden 0.16.4 (not tagged) at commit `57f7bb7b12314f0ba30697cff9a846c749e3d606` (the tested
set, possibly behind WARDEN's branch head). That Warden commit pins the same CNS (`v2.2.0`, `ce6bd05`), so CI installs
the Watcher and Warden together with full dependency resolution and `pip check` is clean.
