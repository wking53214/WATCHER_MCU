# The circuit, and where the Watcher stands

Seven repositories make the circuit; the Watcher is outside it, downstream, with nothing coming back.

| Repository | Role |
|---|---|
| ASSAY | the answer key: specimens with known failure modes |
| ghost_tools | the scanner: Ghost reports, never writes |
| SWIZZLE | the attacker: proves, grades Ghost against ASSAY, attacks Warden |
| WARDEN | the governor: the only writer, the only orchestrator |
| DRAFTER | proposes fixes, never writes |
| JUDGE | reads the evidence, says ACCEPT, REJECT or INSUFFICIENT |
| BURNISH | the finisher: writes only through Warden |
| **WATCHER_MCU** | **reads Warden's record, tells a person, interferes with nothing** |

Run the circuit, then the Watcher:

```
warden tagteam PATH --stack FOLDER --stack-manifest stack.json --authorize "Your Name" --reason "why" --scope code > run.json
watcher narrate run.json --target PATH --out account.md
```

CNS holds the interoperability contracts. No repository in the circuit modifies it. The Watcher reads
the run record through it: `watcher.evidence` imports `cns.run` and refuses any record that is not
`cns.run/1`. CNS is installed from its git URL, pinned to the full commit of release `v1.8.0`, the same
pin every repository of the circuit uses; installing the Watcher needs access to that repository.
CI tests the Watcher against WARDEN 0.13.1 at commit `ec551d8e10f82b6e3e681593a97011ae517d360b` (the tested
set, possibly behind WARDEN's branch head); both repositories pin the same CNS commit.
