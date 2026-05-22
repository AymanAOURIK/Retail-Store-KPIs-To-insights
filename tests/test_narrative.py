from __future__ import annotations

import pytest

from retails_insight.llm import LLMClient, LLMUnavailableError
from retails_insight.narrative import NARRATIVE_RESPONSE_SCHEMA, _build_prompt, narrate
from retails_insight.payload import NarrativeResult, StoreWeekPayload
from retails_insight.tags import Tag


def test_llm_client_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

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
    monkeypatch.setattr("retails_insight.llm.OpenAI", FakeOpenAI)

    client = LLMClient()

    assert client.model == "test-model"
    assert captured == {"api_key": "env-key", "max_retries": 0}


def test_llm_client_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMUnavailableError, match="OPENAI_API_KEY is not set"):
        LLMClient()


def test_llm_client_chat_performs_single_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    calls: list[dict[str, object]] = []

    class FakeOpenAI:
        def __init__(self, *, api_key: str, max_retries: int) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _record_call(calls, kwargs)
                )
            )

    monkeypatch.setattr("retails_insight.llm.OpenAI", FakeOpenAI)

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
    assert "retail store" in system_prompt
    assert "manager" in system_prompt


def test_narrate_returns_llm_result_with_stub_client() -> None:
    import json

    payload = _sample_payload()
    tags = _sample_tags()
    seen: dict[str, object] = {}

    llm_output = {
        "summary": "LLM summary",
        "flags_narrated": [],
        "yoy_caveat_present": False,
        "network_gap_mentioned": False,
        "dominant_driver_cited": "traffic",
    }

    class StubClient:
        model = "stub-model"

        def chat_json(self, system: str, user: str, schema: dict, max_tokens: int) -> dict:
            seen["system"] = system
            seen["user"] = user
            seen["max_tokens"] = max_tokens
            return llm_output

    result = narrate(payload, tags, StubClient())

    assert result.model_dump() == {
        "summary": "LLM summary",
        "flags_narrated": [],
        "yoy_caveat_present": False,
        "network_gap_mentioned": False,
        "dominant_driver_cited": "traffic",
        "source": "llm",
        "model": "stub-model",
        "tags_used": ["sales_yoy_strong_decline", "traffic_drove_decline"],
    }
    assert seen["max_tokens"] == 500
    assert "Do not invent numbers." in str(seen["user"])


def test_narrate_falls_back_when_client_is_none() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    result = narrate(payload, tags, None)

    assert result.source == "fallback"
    assert result.model is None
    assert "STORE_01" in result.summary
    assert "Net sales fell sharply year over year." in result.summary
    assert result.yoy_caveat_present is False
    assert result.dominant_driver_cited == "traffic"


def test_narrate_falls_back_when_client_raises_error() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    class RaisingClient:
        model = "broken-model"

        def chat_json(self, system: str, user: str, schema: dict, max_tokens: int) -> dict:
            raise LLMUnavailableError("network unavailable")

    result = narrate(payload, tags, RaisingClient())

    assert result.source == "fallback"
    assert result.model is None
    assert "STORE_01" in result.summary


def test_narrate_propagates_unexpected_exceptions() -> None:
    payload = _sample_payload()
    tags = _sample_tags()

    class BuggyClient:
        model = "buggy-model"

        def chat_json(self, system: str, user: str, schema: dict, max_tokens: int) -> dict:
            raise ValueError("unexpected programming error")

    with pytest.raises(ValueError, match="unexpected programming error"):
        narrate(payload, tags, BuggyClient())


def test_fallback_adds_yoy_caveat_when_ly_baseline_abnormal() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_02",
        year=2025,
        week=12,
        kpis={},
        yoy={"net_sales": 0.31},
        network_median={},
        network_mad={},
        store_vs_network={},
        driver_attribution={},
        flags=[],
        dq_caveats=[],
        ly_baseline_abnormal=True,
    )

    result = narrate(payload, [], None)

    assert result.yoy_caveat_present is True
    assert "misleading" in result.summary.lower() or "unusual" in result.summary.lower()


def test_fallback_includes_ly_flags_in_flags_narrated() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_03",
        year=2025,
        week=18,
        kpis={},
        yoy={},
        network_median={},
        network_mad={},
        store_vs_network={},
        driver_attribution={},
        flags=["ly_baseline_abnormal_conversion_rate"],
        dq_caveats=[],
        ly_baseline_abnormal=True,
    )
    tags = [
        Tag(
            id="ly_baseline_suspect_conversion_rate",
            severity=1,
            kpi="conversion_rate",
            message_template="Last year's conversion rate baseline may be abnormal.",
        )
    ]

    result = narrate(payload, tags, None)

    assert "ly_baseline_abnormal_conversion_rate" in result.flags_narrated
    assert result.yoy_caveat_present is True


def _record_call(
    calls: list[dict[str, object]],
    kwargs: dict[str, object],
) -> object:
    from types import SimpleNamespace

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
        ly_baseline_abnormal=False,
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
