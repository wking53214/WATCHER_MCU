"""The generic port (`watcher.port`): one call through the Watcher's SDK path, as plain mappings. Offline: every
narrator here is a fake, no credential is read and nothing is sent anywhere."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import watcher
from watcher import port
from watcher.narrate import DEFAULT_EFFORT, AnthropicNarrator, ModelResponseError, Refused

RESPONSE_KEYS = {"text", "provider_id", "provider_kind", "adapter_version", "model_requested", "model_reported",
                 "finish_reason", "usage", "request_digest", "response_digest", "is_live"}


def _request(**changes: Any) -> dict[str, Any]:
    request: dict[str, Any] = {"instructions": "Answer in JSON.", "inputs": ["first excerpt", "second excerpt"],
                               "model": "model-x", "max_output_tokens": 300, "request_digest": "d" * 64}
    request.update(changes)
    return request


class FakeNarrator:
    """Stands in for `AnthropicNarrator.complete`: records what it was asked, then answers or raises."""

    def __init__(self, answer: Any = None, error: BaseException | None = None) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.answer = answer if answer is not None else {
            "text": "the answer", "model": "model-x-2026", "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 3}}
        self.error = error

    def complete(self, system, prompt, model, effort, max_tokens):
        self.calls.append((system, prompt, model, effort, max_tokens))
        if self.error is not None:
            raise self.error
        return self.answer


def test_a_valid_request_makes_one_call_and_returns_every_field():
    narrator = FakeNarrator()
    request = _request()
    before = dict(request)
    response = port.complete(request, narrator)
    assert set(response) == RESPONSE_KEYS and request == before
    assert response == {
        "text": "the answer", "provider_id": "watcher_mcu", "provider_kind": "watcher_mcu",
        "adapter_version": watcher.__version__, "model_requested": "model-x", "model_reported": "model-x-2026",
        "finish_reason": "end_turn", "usage": {"input_tokens": 12, "output_tokens": 3},
        "request_digest": "d" * 64, "response_digest": hashlib.sha256(b"the answer").hexdigest(), "is_live": True}
    assert narrator.calls == [("Answer in JSON.", "first excerpt\n\nsecond excerpt", "model-x", DEFAULT_EFFORT, 300)]


def test_the_digest_is_of_the_utf8_text_and_the_text_is_not_filtered():
    text = "production ready, no citation, café"  # the oath would drop this; the port does not apply the oath
    response = port.complete(_request(), FakeNarrator({"text": text}))
    assert response["text"] == text
    assert response["response_digest"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert response["model_reported"] is None and response["finish_reason"] == "unknown" and response["usage"] is None


def test_effort_is_passed_on_and_empty_instructions_send_no_system_prompt():
    narrator = FakeNarrator()
    port.complete(_request(effort="low", instructions="", max_output_tokens=port.MAX_OUTPUT_TOKENS), narrator)
    assert narrator.calls == [(None, "first excerpt\n\nsecond excerpt", "model-x", "low", port.MAX_OUTPUT_TOKENS)]


BAD_SHAPES: list[tuple[str, Any]] = [
    ("not a mapping", ["instructions"]),
    ("unknown key", _request(tools=[])),
    ("unknown key that is not a string", {**_request(), 7: "x"}),
    ("missing instructions", {k: v for k, v in _request().items() if k != "instructions"}),
    ("missing inputs", {k: v for k, v in _request().items() if k != "inputs"}),
    ("missing model", {k: v for k, v in _request().items() if k != "model"}),
    ("missing max_output_tokens", {k: v for k, v in _request().items() if k != "max_output_tokens"}),
    ("missing request_digest", {k: v for k, v in _request().items() if k != "request_digest"}),
    ("instructions not a string", _request(instructions=None)),
    ("inputs not a list", _request(inputs="one string")),
    ("inputs a tuple", _request(inputs=("a",))),
    ("inputs empty", _request(inputs=[])),
    ("an empty input", _request(inputs=["a", ""])),
    ("an input that is not a string", _request(inputs=["a", 5])),
    ("an input that is not UTF-8 text", _request(inputs=["\ud800"])),
    ("model empty", _request(model="")),
    ("model not a string", _request(model=5)),
    ("tokens zero", _request(max_output_tokens=0)),
    ("tokens negative", _request(max_output_tokens=-1)),
    ("tokens a bool", _request(max_output_tokens=True)),
    ("tokens a float", _request(max_output_tokens=10.0)),
    ("tokens a string", _request(max_output_tokens="10")),
    ("effort unknown", _request(effort="extreme")),
    ("effort null", _request(effort=None)),
    ("request_digest empty", _request(request_digest="")),
    ("request_digest not a string", _request(request_digest=5)),
]


@pytest.mark.parametrize(("name", "request_"), BAD_SHAPES, ids=[name for name, _ in BAD_SHAPES])
def test_a_request_of_the_wrong_shape_is_a_format_error_and_nothing_is_sent(name, request_):
    narrator = FakeNarrator()
    with pytest.raises(port.PortFormatError) as caught:
        port.complete(request_, narrator)
    assert caught.value.code == "format" and narrator.calls == []


def test_too_much_input_or_output_is_too_large_and_nothing_is_sent():
    narrator = FakeNarrator()
    at_the_cap = "x" * (port.MAX_INPUT_BYTES - len("Answer in JSON."))
    port.complete(_request(inputs=[at_the_cap]), narrator)
    assert len(narrator.calls) == 1
    for request in (_request(inputs=[at_the_cap + "x"]),
                    _request(inputs=["é" * (port.MAX_INPUT_BYTES // 2)]),  # bytes are counted, not characters
                    _request(instructions="y" * port.MAX_INPUT_BYTES),
                    _request(max_output_tokens=port.MAX_OUTPUT_TOKENS + 1)):
        with pytest.raises(port.PortTooLarge) as caught:
            port.complete(request, narrator)
        assert caught.value.code == "too_large"
    assert len(narrator.calls) == 1


def test_a_refusal_is_refused():
    with pytest.raises(port.PortRefused, match="declined") as caught:
        port.complete(_request(), FakeNarrator(error=Refused("the model declined (cyber)")))
    assert caught.value.code == "refused" and isinstance(caught.value.__cause__, Refused)


def test_a_response_that_cannot_be_used_is_unavailable():
    with pytest.raises(port.PortUnavailable, match="not a message") as caught:
        port.complete(_request(), FakeNarrator(error=ModelResponseError("the response is not a message (str)")))
    assert caught.value.code == "unavailable"
    for answer in ("a string", {"model": "m"}, {"text": 5}, {"text": "\ud800"}):
        with pytest.raises(port.PortUnavailable, match="no text"):
            port.complete(_request(), FakeNarrator(answer))


class FakeSDKError(Exception):
    """Stands in for the SDK's error base class, which `cli._model_errors()` names when the SDK is installed."""

    status_code = 401


def test_an_sdk_error_is_unavailable_and_its_text_is_not_repeated(monkeypatch):
    monkeypatch.setattr(port, "_model_errors", lambda: (FakeSDKError, ModelResponseError))
    narrator = FakeNarrator(error=FakeSDKError("invalid x-api-key sk-secret-value"))
    with pytest.raises(port.PortUnavailable) as caught:
        port.complete(_request(), narrator)
    assert caught.value.code == "unavailable"
    assert str(caught.value) == "the model could not be reached (FakeSDKError, status 401)"
    assert "sk-secret-value" not in str(caught.value) and "sk-secret-value" not in repr(caught.value)


def test_an_error_that_is_none_of_these_is_not_swallowed():
    with pytest.raises(ZeroDivisionError):
        port.complete(_request(), FakeNarrator(error=ZeroDivisionError("a defect")))


def test_without_credentials_it_is_unavailable_and_no_narrator_is_made(monkeypatch):
    def no_narrator(*args: Any) -> None:
        raise AssertionError("no narrator may be made without credentials")

    monkeypatch.setattr(port, "credentials_present", lambda: False)
    monkeypatch.setattr(port, "AnthropicNarrator", no_narrator)
    with pytest.raises(port.PortUnavailable, match="no credentials") as caught:
        port.complete(_request())
    assert caught.value.code == "unavailable"


def test_an_invalid_request_is_refused_before_credentials_are_looked_for(monkeypatch):
    def not_looked_for() -> bool:
        raise AssertionError("credentials were looked for")

    monkeypatch.setattr(port, "credentials_present", not_looked_for)
    with pytest.raises(port.PortFormatError):
        port.complete(_request(extra=1))
    with pytest.raises(port.PortTooLarge):
        port.complete(_request(max_output_tokens=port.MAX_OUTPUT_TOKENS + 1))


def test_with_credentials_the_sdk_narrator_is_the_default(monkeypatch):
    made = []

    def narrator() -> FakeNarrator:
        made.append(FakeNarrator())
        return made[-1]

    monkeypatch.setattr(port, "credentials_present", lambda: True)
    monkeypatch.setattr(port, "AnthropicNarrator", narrator)
    assert port.complete(_request())["text"] == "the answer" and len(made) == 1 and len(made[0].calls) == 1


def test_every_error_has_its_stable_code():
    codes = {cls.__name__: cls.code for cls in (port.PortFormatError, port.PortTooLarge, port.PortRefused,
                                                port.PortUnavailable)}
    assert codes == {"PortFormatError": "format", "PortTooLarge": "too_large", "PortRefused": "refused",
                     "PortUnavailable": "unavailable"}
    assert all(issubclass(cls, port.PortError) for cls in (port.PortFormatError, port.PortTooLarge, port.PortRefused,
                                                           port.PortUnavailable))


def _sdk_client(response: Any, seen: dict[str, Any]) -> Any:
    def create(**kw: Any) -> Any:
        seen.update(kw)
        return response

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))


def test_through_the_sdk_narrator_the_port_reports_what_the_api_reported():
    seen: dict[str, Any] = {}
    response = SimpleNamespace(
        stop_reason="max_tokens", model="claude-reported", usage=SimpleNamespace(input_tokens=40, output_tokens=7),
        content=(SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="one"),
                 SimpleNamespace(type="text", text="two")))
    got = port.complete(_request(effort="xhigh"), AnthropicNarrator(_sdk_client(response, seen)))
    assert got["text"] == "one\ntwo" and got["model_reported"] == "claude-reported"
    assert got["finish_reason"] == "max_tokens" and got["usage"] == {"input_tokens": 40, "output_tokens": 7}
    assert seen["model"] == "model-x" and seen["max_tokens"] == 300 and seen["system"] == "Answer in JSON."
    assert seen["messages"] == [{"role": "user", "content": "first excerpt\n\nsecond excerpt"}]
    assert seen["output_config"] == {"effort": "xhigh"} and seen["fallbacks"] == "default"
    assert "tools" not in seen and "stream" not in seen and "thinking" not in seen


def test_through_the_sdk_narrator_what_the_api_does_not_report_is_none_and_no_system_is_sent():
    seen: dict[str, Any] = {}
    response = SimpleNamespace(stop_reason=None, content=[SimpleNamespace(type="text", text="only")])
    got = port.complete(_request(instructions=""), AnthropicNarrator(_sdk_client(response, seen)))
    assert got["model_reported"] is None and got["finish_reason"] == "unknown" and got["usage"] is None
    assert "system" not in seen
    half = SimpleNamespace(stop_reason="end_turn", content=[], usage=SimpleNamespace(input_tokens=1))
    assert port.complete(_request(), AnthropicNarrator(_sdk_client(half, {})))["usage"] is None


def test_through_the_sdk_narrator_a_refusal_and_an_unusable_body_keep_their_codes():
    refusal = SimpleNamespace(stop_reason="refusal", stop_details=SimpleNamespace(category="cyber"), content=())
    with pytest.raises(port.PortRefused, match="cyber"):
        port.complete(_request(), AnthropicNarrator(_sdk_client(refusal, {})))
    with pytest.raises(port.PortUnavailable, match="not a message"):
        port.complete(_request(), AnthropicNarrator(_sdk_client("<html>proxy error</html>", {})))

    def undecodable(**kw: Any) -> Any:
        raise ValueError("Expecting value: line 1 column 1 (char 0)")

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=undecodable)))
    with pytest.raises(port.PortUnavailable, match="could not be decoded"):
        port.complete(_request(), AnthropicNarrator(client))


def test_narrate_still_sends_the_narration_limit_through_the_shared_call():
    seen: dict[str, Any] = {}
    response = SimpleNamespace(stop_reason="end_turn", content=(SimpleNamespace(type="text", text="one [R]."),))
    assert AnthropicNarrator(_sdk_client(response, seen)).narrate("sys", "prompt", "m", "high") == "one [R]."
    assert seen["max_tokens"] == 16000 and seen["system"] == "sys" and port.MAX_OUTPUT_TOKENS == 16000


def test_the_port_reads_no_credential_and_imports_no_sdk_of_its_own():
    source = (Path(port.__file__)).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert imported == {"__future__", "hashlib", "collections", "typing"}
    assert "environ" not in source and "API_KEY" not in source and "AUTH_TOKEN" not in source
