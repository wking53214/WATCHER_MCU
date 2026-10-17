"""The CNS the Watcher runs against is the one it declares: a different one breaks the rest of the circuit."""
from __future__ import annotations

import json
import re
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"cns @ git\+https://github\.com/wking53214/CNS\.git@([0-9a-f]{40})\"\]\s*#\s*(v\d+\.\d+\.\d+)")


def _declared() -> tuple[str, str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = PIN.search(text)
    assert match, "the CNS dependency must be a full 40-character commit with its release tag in a comment"
    return match.group(1), match.group(2)


def test_cns_is_pinned_to_a_full_commit_with_its_tag():
    sha, tag = _declared()
    assert tag == "v1.8.0" and len(sha) == 40
    assert tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]


def test_the_installed_cns_is_the_pinned_one():
    sha, tag = _declared()
    assert metadata.version("cns") == tag.lstrip("v")
    direct = metadata.distribution("cns").read_text("direct_url.json")
    if direct is not None:  # installed from git: the commit must be the pinned one, not a moved tag or branch
        assert json.loads(direct).get("vcs_info", {}).get("commit_id") == sha
