from __future__ import annotations

from types import SimpleNamespace

import pytest

from yoobic_insight.llm import LLMClient, LLMUnavailableError
from yoobic_insight.narrative import _build_prompt, narrate
from yoobic_insight.payload import StoreWeekPayload
from yoobic_insight.tags import Tag


def test_llm_client_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, *, api_key: str, max_retries: int) -> None:
            captured["api_key"] = api_key
            captured["max_retries"] = max_retries
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="Narrative text"))]
                    )
                )
            )

    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr("yoobic_insight.llm.OpenAI", FakeOpenAI)

    client = LLMClient()

    assert client.model == "test-model"
    assert captured == {"api_key": "env-key", "max_retries": 0}


def test_llm_client_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMUnavailableError, match="OPENAI_API_KEY is not set"):
        LLMClient()


def test_llm_client_chat_performs_single_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeOpenAI:
        def __init__(self, *, api_key: str, max_retries: int) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _record_call(calls, kwargs)
                )
            )

    monkeypatch.setattr("yoobic_insight.llm.OpenAI", FakeOpenAI)

    client = LLMClient(api_key="direct-key", model="phase-7-model")

    text = client.chat("system prompt", "user prompt", max_tokens=123)

    assert text == "stubbed narrative"
    assert calls == [
        {
            "model": "phase-7-model",
            "messages": [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
            "max_tokens": 123,
        }
    ]


def test_build_prompt_serializes_payload_and_tags_and_forbids_number_invention() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    system_prompt, user_prompt = _build_prompt(payload, tags)

    assert "Do not invent numbers." in user_prompt
    assert '"store_alias": "STORE_01"' in user_prompt
    assert '"id": "sales_yoy_strong_decline"' in user_prompt
    assert "Narrate the listed tags only." in system_prompt


def test_narrate_returns_llm_result_with_stub_client() -> None:
    payload = _sample_payload()
    tags = _sample_tags()
    seen: dict[str, object] = {}

    class StubClient:
        model = "stub-model"

        def chat(self, system: str, user: str, max_tokens: int) -> str:
            seen["system"] = system
            seen["user"] = user
            seen["max_tokens"] = max_tokens
            return "LLM summary"

    result = narrate(payload, tags, StubClient())

    assert result.model_dump() == {
        "text": "LLM summary",
        "source": "llm",
        "model": "stub-model",
        "tags_used": ["sales_yoy_strong_decline", "traffic_drove_decline"],
    }
    assert seen["max_tokens"] == 300
    assert "Do not invent numbers." in str(seen["user"])


def test_narrate_falls_back_when_client_is_none() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    result = narrate(payload, tags, None)

    assert result.model_dump() == {
        "text": (
            "STORE_01 week 21 of 2025 summary. "
            "Net sales fell sharply year over year. "
            "traffic was the dominant driver of the sales decline."
        ),
        "source": "fallback",
        "model": None,
        "tags_used": ["sales_yoy_strong_decline", "traffic_drove_decline"],
    }


def test_narrate_falls_back_when_client_raises_error() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    class RaisingClient:
        model = "broken-model"

        def chat(self, system: str, user: str, max_tokens: int) -> str:
            raise LLMUnavailableError("network unavailable")

    result = narrate(payload, tags, RaisingClient())

    assert result.source == "fallback"
    assert result.model is None
    assert result.text.startswith("STORE_01 week 21 of 2025 summary.")


def _record_call(
    calls: list[dict[str, object]],
    kwargs: dict[str, object],
) -> SimpleNamespace:
    calls.append(kwargs)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="stubbed narrative"))]
    )


def _sample_payload() -> StoreWeekPayload:
    return StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=21,
        kpis={"net_sales": 600.0, "traffic": 80.0},
        yoy={"net_sales": -0.25},
        network_median={"net_sales": 800.0, "traffic": 100.0},
        network_mad={"net_sales": 50.0, "traffic": 10.0},
        store_vs_network={"net_sales": -200.0, "traffic": -20.0},
        driver_attribution={
            "traffic": 70.0,
            "conversion_rate": 20.0,
            "units_per_txn": 5.0,
            "avg_selling_price": 5.0,
        },
        flags=[],
        dq_caveats=[],
        has_ly_baseline=False,
    )


def _sample_tags() -> list[Tag]:
    return [
        Tag(
            id="traffic_drove_decline",
            severity=2,
            kpi="traffic",
            message_template="traffic was the dominant driver of the sales decline.",
        ),
        Tag(
            id="sales_yoy_strong_decline",
            severity=1,
            kpi="net_sales",
            message_template="Net sales fell sharply year over year.",
        ),
    ]
