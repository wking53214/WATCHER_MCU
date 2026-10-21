"""The CLI refuses cleanly: a malformed record, a request that cannot be answered and an --out that would
destroy what was read are exit codes with one line on standard error, never a traceback."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import pytest

from watcher.cli import EXIT_INTERNAL, EXIT_NO_MODEL, EXIT_USAGE, main
from watcher.evidence import UnreadableRecord, load

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"
SEATS = Path(__file__).parent / "fixtures" / "warden_tagteam_seats_run.json"


def _run(path: Path = FIXTURE) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _write(tmp_path: Path, record: dict[str, Any], name: str = "run.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _set(record: dict[str, Any], dotted: str, value: Any) -> dict[str, Any]:
    out = copy.deepcopy(record)
    node: Any = out
    *parents, last = dotted.split(".")
    for key in parents:
        node = node[int(key)] if isinstance(node, list) else node[key]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return out


#: Every field the index reads, with a shape it cannot take. Each must be refused with exit 2.
MALFORMED = [
    ("cycles", 5),
    ("cycles", "one"),
    ("cycles", {"number": 1}),
    ("cycles", [5]),
    ("cycles", ["x"]),
    ("cycles", [{"outcome": "APPLIED"}]),
    ("cycles", [{"number": "1"}]),
    ("cycles", [{"number": True}]),
    ("cycles.0.number", [1]),
    ("cycles.0.number", 1.5),
    ("reobserved", 7),
    ("reobserved", "ghost-aaaa"),
    ("reobserved", {"a": 1}),
    ("reobserved", [1, 2]),
    ("reobserved", [None]),
    ("informational", 3),
    ("informational", [1]),
    ("drafter_skipped", 3),
    ("drafter_skipped", [{"x": 1}]),
    ("attacks", 9),
    ("attacks", "all held"),
    ("swizzle_proofs", 12),
    ("swizzle_proofs", {"a": 1}),
    ("ghost_baseline", 4),
    ("ghost_baseline", [1]),
    ("assay", "ok"),
    ("assay", [1]),
    ("verdict", 3),
    ("verdict", "ACCEPT"),
    ("verdict.reasons", 5),
    ("verdict.reasons", "one reason"),
    ("ghost_scan", "ok"),
    ("ghost_scan.gaps", 2),
    ("ghost_scan.gaps", "none"),
    ("notes", 5),
    ("notes", [1, 2]),
    ("unmeasured", 5),
    ("unmeasured", [None]),
    ("observed", 7),
    ("observed", [3]),
    ("versions", 5),
    ("versions", [1]),
    ("versions.joins", 5),
    ("versions.joins", "x"),
    ("versions.joins", {"path": "/x"}),
    ("versions.joins", [5]),
    ("versions.joins", ["/x"]),
    ("versions.joins.0", 7),
    ("versions.joins.0.path", 7),
    ("versions.joins.0.path", ["/x"]),
    ("versions.ghost_tools", 5),
    ("versions.ghost_tools", "x"),
    ("versions.ghost_tools.path", 5),
    ("versions.swizzle", [1]),
    ("versions.assay", True),
    ("versions.assay.path", {"a": 1}),
    ("versions.warden", 5),
    ("versions.seats", 5),
    ("versions.seats", [1]),
    ("versions.seats.drafter", 5),
    ("versions.seats.judge", "judge.seat:Judge"),
    ("versions.seats.finisher", [1]),
    ("decision", 5),
    ("decision", None),
    ("reason", 5),
    ("converged", "yes"),
    ("put_back", 1),
    ("held_digest", 5),
]


@pytest.mark.parametrize(("field", "value"), MALFORMED, ids=[f"{f}={v!r}" for f, v in MALFORMED])
def test_a_malformed_field_is_exit_2_never_a_traceback(tmp_path, capsys, field, value):
    # the seats shape comes from the record Warden's own writer made; the others from the joined record
    base = _run(SEATS) if field.startswith("versions.seats") else _run()
    path = _write(tmp_path, _set(base, field, value))
    code = main(["narrate", str(path), "--no-model"])
    err = capsys.readouterr().err
    assert code == EXIT_USAGE
    assert err.startswith("watcher: ") and "Traceback" not in err and len(err.splitlines()) == 1


@pytest.mark.parametrize(("field", "value"), [("cycles", 5), ("reobserved", 7), ("versions.joins", 5)])
def test_the_audited_crashes_are_unreadable_records(tmp_path, field, value):
    path = _write(tmp_path, _set(_run(), field, value))
    with pytest.raises(UnreadableRecord, match=field.split(".")[-1]):
        load(path)


@pytest.mark.parametrize("text", ["", "null", "5", '"x"', "[]", "{", "[[[[[[[[", "\x00", "{\"decision\": }"])
def test_text_that_is_not_a_record_is_exit_2(tmp_path, capsys, text):
    path = tmp_path / "x.json"
    path.write_text(text, encoding="utf-8")
    assert main(["narrate", str(path), "--no-model"]) == EXIT_USAGE
    assert "Traceback" not in capsys.readouterr().err


def test_deeply_nested_json_and_binary_and_a_directory_are_exit_2(tmp_path, capsys):
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
    binary = tmp_path / "bin.json"
    binary.write_bytes(b"\xff\xfe\x00\x80")
    for path in (deep, binary, tmp_path, tmp_path / "missing.json"):
        assert main(["narrate", str(path), "--no-model"]) == EXIT_USAGE
    assert "Traceback" not in capsys.readouterr().err


def test_a_finding_id_cannot_replace_the_decision(tmp_path):
    record = _run()
    record["observed"] = ["R", "V"]
    citations = load(_write(tmp_path, record)).citations
    assert citations["R"].kind == "decision" and citations["V"].kind == "verdict"


def test_null_optional_fields_are_still_readable(tmp_path):
    record = _run()
    for key in ("cycles", "reobserved", "informational", "drafter_skipped", "attacks", "swizzle_proofs",
                "ghost_baseline", "assay"):
        record[key] = None
    record["versions"]["joins"] = None
    record["versions"]["seats"] = {"drafter": None, "judge": None}
    assert main(["narrate", str(_write(tmp_path, record)), "--no-model"]) == 0


# --- the model cannot be reached --------------------------------------------------------------------------------

def _request() -> Any:
    return SimpleNamespace(method="POST", url="https://api.anthropic.example/v1/messages")


class Raises:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def narrate(self, *args: Any) -> str:
        raise self.error


def _errors() -> list[BaseException]:
    response: Any = SimpleNamespace(status_code=529, headers={}, request=_request())
    return [
        anthropic.APIConnectionError(request=_request()),
        anthropic.APITimeoutError(request=_request()),
        anthropic.InternalServerError("overloaded", response=response, body=None),
        anthropic.AnthropicError("Could not resolve authentication method"),
    ]


@pytest.mark.parametrize("error", _errors(), ids=lambda e: type(e).__name__)
def test_an_unreachable_model_is_exit_3_with_the_documented_message(tmp_path, capsys, error):
    out = tmp_path / "account.md"
    code = main(["narrate", str(FIXTURE), "--out", str(out)], narrator=Raises(error))
    err = capsys.readouterr().err
    assert code == EXIT_NO_MODEL
    assert "no model could be reached" in err and "No account was written" in err and "--no-model" in err
    assert "Traceback" not in err and not out.exists()


def test_the_sdk_narrator_with_a_failing_client_is_exit_3(capsys):
    from watcher.narrate import AnthropicNarrator

    class Messages:
        @staticmethod
        def create(**kw: Any) -> Any:
            raise anthropic.APIConnectionError(request=_request())

    client = SimpleNamespace(beta=SimpleNamespace(messages=Messages()))
    assert main(["narrate", str(FIXTURE)], narrator=AnthropicNarrator(client)) == EXIT_NO_MODEL
    assert "no model could be reached" in capsys.readouterr().err


def _client_that(result: Any) -> Any:
    """A fake SDK client whose request raises `result` if it is an exception, else returns it."""

    class Messages:
        @staticmethod
        def create(**kw: Any) -> Any:
            if isinstance(result, BaseException):
                raise result
            return result

    return SimpleNamespace(beta=SimpleNamespace(messages=Messages()))


def _block(**kw: Any) -> Any:
    return SimpleNamespace(**kw)


#: What the SDK does with a 200 whose body is not what it expects: json.JSONDecodeError escapes for a JSON content
#: type with a bad body, and a plain str comes back for any other content type. Others are wrong shapes.
UNDECODABLE: list[Any] = [
    json.JSONDecodeError("Expecting value", "<html>oops</html>", 0),
    ValueError("not JSON"),
    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    "<html>an error page that came with a 200</html>",
    None,
    SimpleNamespace(stop_reason="end_turn"),
    SimpleNamespace(stop_reason="end_turn", content=None),
    SimpleNamespace(stop_reason="end_turn", content="text"),
    SimpleNamespace(stop_reason="end_turn", content=[_block(type="text")]),
    SimpleNamespace(stop_reason="end_turn", content=[_block(type="text", text=5)]),
]


@pytest.mark.parametrize("result", UNDECODABLE, ids=[type(r).__name__ for r in UNDECODABLE])
def test_a_200_the_sdk_cannot_decode_is_exit_3_and_nothing_is_written(tmp_path, capsys, result):
    from watcher.narrate import AnthropicNarrator

    out = tmp_path / "account.md"
    narrator = AnthropicNarrator(_client_that(result))
    code = main(["narrate", str(FIXTURE), "--out", str(out)], narrator=narrator)
    err = capsys.readouterr().err
    assert code == EXIT_NO_MODEL
    assert "no model could be reached" in err and "No account was written" in err and "--no-model" in err
    assert "internal error" not in err and "Traceback" not in err and not out.exists()


def test_a_well_formed_response_is_still_an_account(tmp_path):
    from watcher.narrate import AnthropicNarrator

    response = SimpleNamespace(stop_reason="end_turn", content=[_block(type="text", text="Held [R].")])
    out = tmp_path / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out)], narrator=AnthropicNarrator(_client_that(response))) == 0
    assert "Held [R]." in out.read_text(encoding="utf-8")


def test_an_unexpected_failure_is_exit_1_in_one_line_and_verbose_shows_why(capsys):
    boom = Raises(RuntimeError("boom"))
    assert main(["narrate", str(FIXTURE)], narrator=boom) == EXIT_INTERNAL
    err = capsys.readouterr().err
    assert "internal error: RuntimeError: boom" in err and "Traceback" not in err
    assert main(["--verbose", "narrate", str(FIXTURE)], narrator=boom) == EXIT_INTERNAL
    assert "Traceback" in capsys.readouterr().err


# --- --out must not destroy what was read ------------------------------------------------------------------------

def test_out_may_not_be_the_record_itself(tmp_path, capsys):
    path = _write(tmp_path, _run())
    before = path.read_bytes()
    assert main(["narrate", str(path), "--out", str(path), "--no-model"]) == EXIT_USAGE
    assert "never overwrites what it reads" in capsys.readouterr().err
    assert path.read_bytes() == before


def test_out_may_not_reach_the_record_by_another_spelling(tmp_path, monkeypatch, capsys):
    path = _write(tmp_path, _run())
    before = path.read_bytes()
    (tmp_path / "sub").mkdir()
    monkeypatch.chdir(tmp_path)
    spellings = [tmp_path / "sub" / ".." / "run.json", Path("run.json"), Path("./sub/../run.json")]
    link = tmp_path / "link.json"
    link.symlink_to(path)
    hard = tmp_path / "hard.json"
    os.link(path, hard)
    for out in [*spellings, link, hard]:
        assert main(["narrate", "run.json", "--out", str(out), "--no-model"]) == EXIT_USAGE, out
    assert path.read_bytes() == before
    assert "Traceback" not in capsys.readouterr().err


def test_out_that_cannot_be_written_is_exit_2(tmp_path, capsys):
    assert main(["narrate", str(FIXTURE), "--out", str(tmp_path), "--no-model"]) == EXIT_USAGE
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert main(["narrate", str(FIXTURE), "--out", str(blocker / "a.md"), "--no-model"]) == EXIT_USAGE
    assert "Traceback" not in capsys.readouterr().err


def test_a_different_out_is_still_written_and_the_record_untouched(tmp_path):
    path = _write(tmp_path, _run())
    before = path.read_bytes()
    out = tmp_path / "account.md"
    assert main(["narrate", str(path), "--out", str(out), "--no-model"]) == 0
    assert out.is_file() and path.read_bytes() == before


# --- --out does not create folders on its own --------------------------------------------------------------------

def test_a_missing_out_folder_is_refused_and_nothing_is_created(tmp_path, capsys):
    out = tmp_path / "no" / "such" / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out), "--no-model"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "does not exist" in err and "--create-out-dir" in err and "Traceback" not in err
    assert not (tmp_path / "no").exists()


def test_a_missing_out_folder_is_refused_before_the_model_is_asked(tmp_path, capsys):
    narrator = Raises(RuntimeError("the model must not be asked"))
    out = tmp_path / "missing" / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out)], narrator=narrator) == EXIT_USAGE
    assert "internal error" not in capsys.readouterr().err and not out.parent.exists()


def test_create_out_dir_creates_the_folder_and_its_parents(tmp_path):
    out = tmp_path / "a" / "b" / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out), "--no-model", "--create-out-dir"]) == 0
    assert out.read_text(encoding="utf-8").startswith("# The Watcher's account")


def test_create_out_dir_does_not_lift_the_forbidden_folders(tmp_path, capsys):
    governed = tmp_path / "governed"
    governed.mkdir()
    out = governed / "new" / "account.md"
    args = ["narrate", str(FIXTURE), "--target", str(governed), "--out", str(out), "--no-model", "--create-out-dir"]
    assert main(args) == EXIT_USAGE
    assert "never writes into" in capsys.readouterr().err and not out.parent.exists()


def test_an_existing_out_folder_needs_no_flag(tmp_path):
    assert main(["narrate", str(FIXTURE), "--out", str(tmp_path / "account.md"), "--no-model"]) == 0


def test_an_out_folder_that_is_a_file_is_exit_2_with_or_without_the_flag(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    for extra in ([], ["--create-out-dir"]):
        assert main(["narrate", str(FIXTURE), "--out", str(blocker / "a.md"), "--no-model", *extra]) == EXIT_USAGE
    assert "Traceback" not in capsys.readouterr().err


# --- a record that is not there ----------------------------------------------------------------------------------

def test_a_missing_record_says_file_not_found_and_is_exit_2(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert main(["narrate", str(missing), "--no-model"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert f"{missing}: file not found" in err and "JSON" not in err and "FileNotFoundError" not in err
    with pytest.raises(UnreadableRecord, match="file not found"):
        load(missing)


def test_a_record_that_is_a_folder_is_not_called_json(tmp_path, capsys):
    assert main(["narrate", str(tmp_path), "--no-model"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "cannot be read:" in err and "JSON" not in err


def test_a_target_that_does_not_exist_is_refused_with_one_line_and_nothing_is_written(tmp_path, capsys):
    """A mistyped `--target` used to exit 0 and guard nothing: `--out` could go into the folder really governed."""
    real = tmp_path / "project"
    real.mkdir()
    typo = tmp_path / "projcet"
    assert not typo.exists()
    out = real / "WATCHER.md"
    code = main(["narrate", str(FIXTURE), "--target", str(typo), "--out", str(out), "--no-model"])
    err = capsys.readouterr().err
    assert code == 2 and not out.exists() and list(real.iterdir()) == []
    assert err.count("\n") == 1 and f"--target {typo} does not exist" in err
    # also without --out: a record read with a target that is not there is not a quiet success
    assert main(["narrate", str(FIXTURE), "--target", str(typo), "--no-model"]) == 2
    assert capsys.readouterr().out == ""


def test_a_target_that_exists_is_still_accepted(tmp_path):
    real = tmp_path / "project"
    real.mkdir()
    assert main(["narrate", str(FIXTURE), "--target", str(real), "--out", str(tmp_path / "a.md"), "--no-model"]) == 0
