"""The narrator is trusted to write, never to be right; the CLI never writes where it must not."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from watcher import OATH
from watcher.cli import main, write_account
from watcher.evidence import load
from watcher.narrate import SYSTEM, AnthropicNarrator, Refused, narrate, prompt_for, template
from watcher.oath import enforce

FIXTURE = Path(__file__).parent / "fixtures" / "swizzle_joined_run.json"


class Scripted:
    """A narrator that says whatever the test wrote, and remembers what it was asked."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[tuple[str, str, str, str]] = []

    def narrate(self, system, prompt, model, effort):
        self.calls.append((system, prompt, model, effort))
        return self.text


def test_the_template_account_passes_the_oath_whole():
    e = load(FIXTURE)
    out = enforce(template(e), e.citations)
    assert out.dropped == () and len(out.kept) >= 8
    assert any("[R]" in s for s in out.kept) and any("[U]" in s for s in out.kept)


def test_the_model_is_shown_only_the_index_and_told_the_oath():
    e = load(FIXTURE)
    s = Scripted("It ended ACCEPT_UNVERIFIED [R].")
    narrate(e, s, model="m", effort="low")
    system, prompt, model, effort = s.calls[0]
    assert system == SYSTEM and (model, effort) == ("m", "low")
    assert prompt == prompt_for(e)
    assert "[R] decision:" in prompt and "[V] verdict:" in prompt
    assert "edits" not in prompt and "SNEAK" not in prompt  # nothing but the index
    assert "square brackets" in SYSTEM and "never grade" in SYSTEM


def test_what_the_model_writes_is_filtered_and_the_filtering_is_shown():
    e = load(FIXTURE)
    s = Scripted("## Account\nThe run was held [R]. Trust me, it is fine. This code is production ready [R]. "
                 "The suite passed [S99].")
    text, code = write_account(e, s, "m", "high")
    assert code == 0
    assert "The run was held [R]." in text
    assert "Trust me" not in text.split("## Dropped by the oath")[0]
    dropped = text.split("## Dropped by the oath")[1].split("## Citations used")[0]
    assert "3 sentence(s) were written and not kept" in dropped
    assert "cites nothing" in dropped and "status claim" in dropped and "not in the record: S99" in dropped
    assert "- [R] decision:" in text and OATH in text


def test_an_account_with_nothing_left_is_exit_4_not_a_pretty_blank():
    e = load(FIXTURE)
    text, code = write_account(e, Scripted("Everything is wonderful."), "m", "high")
    assert code == 4 and "1 sentence(s) were written and not kept" in text


def test_cli_writes_the_template_account_without_a_model(tmp_path, capsys):
    out = tmp_path / "reports" / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out), "--no-model", "--create-out-dir"]) == 0
    assert out.read_text(encoding="utf-8").startswith("# The Watcher's account")
    assert "the template (no model)" in out.read_text(encoding="utf-8")
    assert "account written to" in capsys.readouterr().err


def test_cli_refuses_to_write_into_the_governed_folder_or_a_named_checkout(tmp_path, capsys):
    target = tmp_path / "proj"
    target.mkdir()
    code = main(["narrate", str(FIXTURE), "--out", str(target / "WATCHER.md"), "--target", str(target), "--no-model"])
    assert code == 2 and "never writes into" in capsys.readouterr().err
    assert list(target.iterdir()) == []
    run = json.loads(FIXTURE.read_text(encoding="utf-8"))
    joined = Path(run["versions"]["joins"][0]["path"])
    code = main(["narrate", str(FIXTURE), "--out", str(joined / "x.md"), "--no-model"])
    assert code == 2 and "never writes into" in capsys.readouterr().err


def test_cli_without_credentials_says_so_and_writes_nothing(tmp_path, monkeypatch, capsys):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    out = tmp_path / "account.md"
    assert main(["narrate", str(FIXTURE), "--out", str(out)]) == 3
    assert "no model credentials" in capsys.readouterr().err and not out.exists()


def test_cli_uses_an_injected_narrator_and_prints_to_stdout(capsys):
    assert main(["narrate", str(FIXTURE)], narrator=Scripted("Held, unjudged [R].")) == 0
    assert "Held, unjudged [R]." in capsys.readouterr().out


def test_cli_reports_a_refusal_as_no_account(capsys):
    class Declines:
        def narrate(self, *a):
            raise Refused("the model declined (cyber)")
    assert main(["narrate", str(FIXTURE)], narrator=Declines()) == 3
    assert "No account was written" in capsys.readouterr().err


def test_cli_rejects_a_record_that_is_not_one(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert main(["narrate", str(bad), "--no-model"]) == 2
    assert "not a Warden run record" in capsys.readouterr().err


def test_the_sdk_narrator_asks_for_the_right_request_and_reads_text_blocks():
    seen = {}

    class Block:
        def __init__(self, type, text=""):
            self.type, self.text = type, text

    class Response:
        stop_reason = "end_turn"
        content = (Block("thinking"), Block("text", "one [R]."), Block("text", "two [V]."))

    class Messages:
        def create(self, **kw):
            seen.update(kw)
            return Response()

    class Beta:
        messages = Messages()

    class Client:
        beta = Beta()

    text = AnthropicNarrator(Client()).narrate("sys", "prompt", "claude-x", "xhigh")
    assert text == "one [R].\ntwo [V]."
    assert seen["model"] == "claude-x" and seen["system"] == "sys" and seen["output_config"] == {"effort": "xhigh"}
    assert seen["messages"] == [{"role": "user", "content": "prompt"}] and seen["fallbacks"] == "default"
    assert "thinking" not in seen  # the model's default; never disabled, never budgeted


def test_the_sdk_narrator_turns_a_refusal_into_an_error():
    class Details:
        category = "cyber"

    class Response:
        stop_reason = "refusal"
        stop_details = Details()
        content = ()

    class Messages:
        @staticmethod
        def create(**kw):
            return Response()

    class Beta:
        messages = Messages()

    class Client:
        beta = Beta()

    with pytest.raises(Refused, match="cyber"):
        AnthropicNarrator(Client()).narrate("s", "p", "m", "high")


def test_the_cli_narrates_a_real_0_13_2_record_with_an_assay_version(tmp_path):
    record = Path(__file__).parent / "fixtures" / "warden_0_13_2_record.json"
    out = tmp_path / "account.md"
    assert main(["narrate", str(record), "--no-model", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "assay 0.11.1" in text and "assay None" not in text
