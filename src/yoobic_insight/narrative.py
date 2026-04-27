from __future__ import annotations

import json
from pathlib import Path

from yoobic_insight.llm import LLMUnavailableError
from yoobic_insight.payload import NarrativeResult, StoreWeekPayload
from yoobic_insight.tags import Tag

PROMPT_PATH = Path(__file__).resolve().parents[2] / "eval" / "prompts" / "v1_narrative.md"


def narrate(
    payload: StoreWeekPayload,
    tags: list[Tag],
    client: object | None,
) -> NarrativeResult:
    ordered_tags = sorted(tags, key=lambda tag: (tag.severity, tag.id))
    if client is None:
        return _rule_based_narrative(payload, ordered_tags)

    system_prompt, user_prompt = _build_prompt(payload, ordered_tags)
    try:
        text = client.chat(system_prompt, user_prompt, max_tokens=300)
    except LLMUnavailableError:
        return _rule_based_narrative(payload, ordered_tags)

    return NarrativeResult(
        text=text,
        source="llm",
        model=getattr(client, "model", None),
        tags_used=[tag.id for tag in ordered_tags],
    )


def _rule_based_narrative(payload: StoreWeekPayload, tags: list[Tag]) -> NarrativeResult:
    ordered_tags = sorted(tags, key=lambda tag: (tag.severity, tag.id))
    sentences = [f"{payload.store_alias} week {payload.week} of {payload.year} summary."]
    if ordered_tags:
        sentences.extend(tag.message_template for tag in ordered_tags)
    else:
        sentences.append("No headline tags were triggered for this store-week.")

    return NarrativeResult(
        text=" ".join(sentences),
        source="fallback",
        model=None,
        tags_used=[tag.id for tag in ordered_tags],
    )


def _build_prompt(payload: StoreWeekPayload, tags: list[Tag]) -> tuple[str, str]:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    payload_json = json.dumps(payload.model_dump(), indent=2, sort_keys=True)
    tags_json = json.dumps(
        [
            {
                "id": tag.id,
                "severity": tag.severity,
                "kpi": tag.kpi,
                "message_template": tag.message_template,
            }
            for tag in sorted(tags, key=lambda tag: (tag.severity, tag.id))
        ],
        indent=2,
        sort_keys=True,
    )
    user_prompt = (
        "Narrate the listed tags only.\n"
        "Do not invent numbers.\n\n"
        f"Payload JSON:\n{payload_json}\n\n"
        f"Tags JSON:\n{tags_json}\n"
    )
    return system_prompt, user_prompt
