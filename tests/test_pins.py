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


WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_every_ci_job_that_checks_out_warden_uses_one_full_commit_that_the_readme_names():
    text = _workflow()
    refs = re.findall(r"repository: wking53214/WARDEN\s+ref: (\S+)", text)
    assert len(refs) == 2 and len(set(refs)) == 1, "the e2e and co-install jobs test the same Warden"
    assert re.fullmatch(r"[0-9a-f]{40}", refs[0]), "a sibling checkout is pinned to a full commit"
    assert refs[0] in (ROOT / "README.md").read_text(encoding="utf-8")
    assert refs[0] in (ROOT / "STACK.md").read_text(encoding="utf-8")


#: The tested Warden: WARDEN 0.13.4 (its warden/__init__.py says so at this commit). Bump with the workflow.
WARDEN_PIN = "36e98433f4928b7d12905f02b56e55ee1943b56e"
WARDEN_VERSION = "0.13.4"


def test_the_pinned_warden_is_the_expected_commit_and_every_doc_names_its_version():
    refs = re.findall(r"repository: wking53214/WARDEN\s+ref: (\S+)", _workflow())
    assert refs == [WARDEN_PIN, WARDEN_PIN]
    for doc in ("README.md", "STACK.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert f"WARDEN {WARDEN_VERSION} at commit" in " ".join(text.split()), doc


def test_the_warden_jobs_resolve_dependencies_and_are_blocking():
    text = _workflow()
    assert "--no-deps" not in text and "continue-on-error" not in text
    assert "pip check" in text and "pip install . ./_warden" in text


def test_every_action_is_pinned_by_commit_with_its_tag_in_a_comment():
    uses = re.findall(r"^\s*- uses: (\S+)(.*)$", _workflow(), flags=re.MULTILINE)
    assert uses
    for ref, rest in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), ref
        assert re.search(r"#\s*v\d+\.\d+\.\d+", rest), ref
