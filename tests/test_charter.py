"""The charter, read from the source: the Watcher imports nothing of the circuit and never writes a
file except the one account it is asked for."""
from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "watcher"
CIRCUIT = {"warden", "ghost_buster", "ghost_tools", "swizzle", "drafter", "judge", "burnish", "assay",
           "assay_production"}
WRITERS = {"write_text", "write_bytes", "unlink", "rmdir", "rename", "mkdir", "chmod", "touch", "symlink_to"}


def _modules():
    return sorted(PACKAGE.glob("*.py"))


def test_there_is_source_to_read():
    assert {p.name for p in _modules()} >= {"cli.py", "evidence.py", "narrate.py", "oath.py", "report.py"}


def test_the_watcher_imports_no_part_of_the_circuit():
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in CIRCUIT, f"{path.name} imports {name}"


def test_only_the_cli_writes_and_only_the_account():
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr in WRITERS]
        if path.name == "cli.py":
            # mkdir for --create-out-dir; write_text and unlink for the account written through a temporary file
            # that is removed again if the write fails (the account is then moved into place with os.replace)
            assert sorted(calls) == ["mkdir", "unlink", "write_text"]
        else:
            assert calls == [], f"{path.name} writes: {calls}"


def test_no_subprocess_no_network_of_its_own():
    for path in _modules():
        text = path.read_text(encoding="utf-8")
        assert "subprocess" not in text and "urllib" not in text and "requests" not in text and "httpx" not in text
