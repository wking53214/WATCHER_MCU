"""The CNS the Watcher runs against is the one it declares: a different one breaks the rest of the circuit."""
from __future__ import annotations

import json
import re
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"cns @ git\+https://github\.com/wking53214/CNS\.git@(v\d+\.\d+\.\d+)\"\]")
#: The commit the tag v1.9.0 peels to (git ls-remote ... 'refs/tags/v1.9.0^{}'); the installed CNS must be this commit.
CNS_COMMIT = "da18e411743d4e3b0e783105394d845fb1c16746"


def _declared() -> tuple[str, str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = PIN.search(text)
    assert match, "the CNS dependency must be pinned by its release tag, spelled as the rest of the circuit does"
    return CNS_COMMIT, match.group(1)


def test_cns_is_pinned_by_its_release_tag():
    sha, tag = _declared()
    assert tag == "v1.9.0" and len(sha) == 40
    assert sha == "da18e411743d4e3b0e783105394d845fb1c16746"
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    assert "cns @ git+https://github.com/wking53214/CNS.git@v1.9.0" in deps


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


#: The tested Warden: Warden 0.13.7, not tagged (its warden/__init__.py says so at this commit). Bump with the workflow.
WARDEN_PIN = "1636e1a21f124eedbf6e158db95dc75344f4308d"
WARDEN_VERSION = "0.13.7"


def test_the_pinned_warden_is_the_expected_commit_and_every_doc_names_its_version():
    refs = re.findall(r"repository: wking53214/WARDEN\s+ref: (\S+)", _workflow())
    assert refs == [WARDEN_PIN, WARDEN_PIN]
    for doc in ("README.md", "STACK.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert f"Warden {WARDEN_VERSION} (not tagged) at commit" in " ".join(text.split()), doc


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
