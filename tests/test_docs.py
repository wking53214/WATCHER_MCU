"""What the documentation says is checked against what the code does."""
from __future__ import annotations

import re
import tomllib
from importlib import metadata
from pathlib import Path

import watcher
from watcher import cli

ROOT = Path(__file__).resolve().parent.parent


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _code_exit_codes() -> set[int]:
    return {cli.EXIT_OK, cli.EXIT_INTERNAL, cli.EXIT_USAGE, cli.EXIT_NO_MODEL, cli.EXIT_NOTHING_KEPT}


def test_the_readme_exit_code_table_matches_the_code():
    section = _readme().split("## EXIT CODES", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\|\s*(\d+)\s*\|", section, flags=re.MULTILINE)
    assert sorted(int(r) for r in rows) == sorted(_code_exit_codes())
    assert len(rows) == len(set(rows))


def test_the_cli_docstring_lists_every_exit_code():
    doc = cli.__doc__ or ""
    listed = {int(n) for n in re.findall(r"^\s{2}(\d)\s{2}\S", doc, flags=re.MULTILINE)}
    assert listed == _code_exit_codes()


def test_every_value_main_can_return_is_a_documented_code():
    """main() returns only constants from the list: read the source for any other integer return."""
    source = (ROOT / "watcher" / "cli.py").read_text(encoding="utf-8")
    returned = set(re.findall(r"^\s+return (\d+)\s*$", source, flags=re.MULTILINE))
    assert returned == set()  # every return is a named constant, none a bare number


def test_the_version_is_one_number_everywhere():
    assert metadata.version("watcher-mcu") == watcher.__version__
    assert f"Version `{watcher.__version__}`" in _readme()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    first = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, flags=re.MULTILINE)
    assert first is not None and first.group(1) == watcher.__version__
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "version" not in project and "version" in project["dynamic"]


def test_the_docs_say_nothing_that_is_no_longer_true():
    readme, stack = _readme(), (ROOT / "STACK.md").read_text(encoding="utf-8")
    assert "Version 0.1.0 reads" not in readme
    assert "does not read it" not in stack and "cns.run" in stack
    for text in (readme, stack, (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")):
        assert chr(0x2014) not in text


def test_the_readme_names_every_standard_warden_sentence_the_oath_allows():
    from watcher.oath import WARDEN_STANDARD

    text = " ".join(_readme().lower().split())
    for fragment in WARDEN_STANDARD:
        assert fragment in text, fragment
