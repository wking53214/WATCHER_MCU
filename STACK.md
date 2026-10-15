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

CNS (private) holds the interoperability contracts. No repository in the circuit modifies it, and the
Watcher does not read it.
