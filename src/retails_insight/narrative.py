from __future__ import annotations

import json
from pathlib import Path

from retails_insight.llm import LLMUnavailableError
from retails_insight.payload import NarrativeResult, StoreWeekPayload, extract_flagged_kpis
from retails_insight.tags import Tag

PROMPT_PATH = Path(__file__).resolve().parents[2] / "eval" / "prompts" / "v2_narrative.md"

NARRATIVE_RESPONSE_SCHEMA: dict = {
    "name": "narrative_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "flags_narrated": {"type": "array", "items": {"type": "string"}},
            "yoy_caveat_present": {"type": "boolean"},
            "network_gap_mentioned": {"type": "boolean"},
            "dominant_driver_cited": {"type": ["string", "null"]},
        },
        "required": [
            "summary",
            "flags_narrated",
            "yoy_caveat_present",
            "network_gap_mentioned",
            "dominant_driver_cited",
        ],
        "additionalProperties": False,
    },
}


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
        parsed = client.chat_json(system_prompt, user_prompt, NARRATIVE_RESPONSE_SCHEMA, max_tokens=500)
    except LLMUnavailableError:
        return _rule_based_narrative(payload, ordered_tags)

    return NarrativeResult(
        summary=parsed["summary"],
        flags_narrated=parsed["flags_narrated"],
        yoy_caveat_present=bool(parsed["yoy_caveat_present"]),
        network_gap_mentioned=bool(parsed["network_gap_mentioned"]),
        dominant_driver_cited=parsed.get("dominant_driver_cited"),
        source="llm",
        model=getattr(client, "model", None),
        tags_used=[tag.id for tag in ordered_tags],
    )


def _rule_based_narrative(payload: StoreWeekPayload, tags: list[Tag]) -> NarrativeResult:
    ordered_tags = sorted(tags, key=lambda tag: (tag.severity, tag.id))

    if ordered_tags:
        sentences = [f"{payload.store_alias} — Week {payload.week}, {payload.year}."]
        sentences.extend(tag.message_template for tag in ordered_tags)
    else:
        sentences = [
            f"Week {payload.week} of {payload.year} was a steady week for {payload.store_alias}.",
            "All tracked metrics came in within the expected range across the store network.",
        ]

    if payload.ly_baseline_abnormal:
        sentences.append(
            "Year-over-year comparisons may be misleading because last year's same-week baseline was not representative for this store."
        )
    elif not ordered_tags:
        sentences.append("No performance alerts were raised.")

    summary = " ".join(sentences)

    # flags_narrated: flags that the rule-based path addresses via ly_baseline tags
    flags_narrated = [f for f in payload.flags if f.startswith("ly_baseline_abnormal_")]

    # yoy_caveat_present: fallback adds caveat exactly when ly_baseline_abnormal is True
    yoy_caveat_present = payload.ly_baseline_abnormal

    # network_gap_mentioned: True when a network_underperform tag fired (its message is in the text)
    network_gap_mentioned = any(tag.id.startswith("network_underperform_") for tag in ordered_tags)

    # dominant_driver_cited: extract from *_drove_decline tags
    dominant_driver_cited = next(
        (tag.kpi for tag in ordered_tags if tag.id.endswith("_drove_decline") and tag.kpi),
        None,
    )

    return NarrativeResult(
        summary=summary,
        flags_narrated=flags_narrated,
        yoy_caveat_present=yoy_caveat_present,
        network_gap_mentioned=network_gap_mentioned,
        dominant_driver_cited=dominant_driver_cited,
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
        "Do not invent numbers.\n\n"
        f"Payload JSON:\n{payload_json}\n\n"
        f"Tags JSON:\n{tags_json}\n\n"
        "Respond with a JSON object:\n"
        '- "summary": 3–5 sentence prose narrative following all rules\n'
        '- "flags_narrated": list of flag IDs from payload.flags that your summary addresses\n'
        '- "yoy_caveat_present": true if the summary warns that YoY is unreliable due to abnormal LY baseline\n'
        '- "network_gap_mentioned": true if the summary mentions a store vs network gap\n'
        '- "dominant_driver_cited": driver KPI name cited (e.g. "traffic") or null\n'
    )
    return system_prompt, user_prompt
