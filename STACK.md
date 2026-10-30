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
`cns.run/1`. CNS is installed from its git URL, pinned by the release tag `v2.2.0`
(a lightweight tag, so the tag is the commit `ce6bd05578a7a3e3cafa0cfa1e9a2cca8a5f171f`); installing the Watcher needs access to that repository.
CI tests the Watcher against Warden 0.16.3 (not tagged) at commit `cb45681ea80f845fb8f23bb091bda7f587c6a547` (the tested
set, possibly behind WARDEN's branch head). That Warden commit pins the same CNS (`v2.2.0`, `ce6bd05`), so CI installs
the Watcher and Warden together with full dependency resolution and `pip check` is clean.
