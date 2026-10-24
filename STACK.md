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
`cns.run/1`. CNS is installed from its git URL, pinned by the release tag `v2.0.0`
(the tag peels to `b13e5d2f9e0e4291725f82794b89117c3d840ac1`); installing the Watcher needs access to that repository.
CI tests the Watcher against Warden 0.13.10 (not tagged) at commit `9ecd1124e6c1b1c4ad7daed37b17f9009662dd9d` (the tested
set, possibly behind WARDEN's branch head). That Warden commit pins the same CNS (`v2.0.0`, `b13e5d2`), so CI installs
the Watcher and Warden together with full dependency resolution and `pip check` is clean.
