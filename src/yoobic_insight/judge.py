from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Literal

import yaml

from yoobic_insight.narrative import narrate
from yoobic_insight.payload import NarrativeResult, StoreWeekPayload, extract_flagged_kpis
from yoobic_insight.tags import Tag, generate_tags

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLDEN_SET_PATH = PROJECT_ROOT / "eval" / "golden_set.yaml"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "eval" / "reports" / "eval_v1.md"
PASS_THRESHOLD = 0.85
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(-?\d+(?:\.\d+)?)(%?)(?![A-Za-z0-9_])")


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Literal["pass", "fail", "skipped"]
    details: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "pass"


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    description: str
    narrative_text: str
    narrative_source: str
    check_results: list[CheckResult]
    llm_judge_result: CheckResult | None

    @property
    def deterministic_pass_rate(self) -> float:
        if not self.check_results:
            return 1.0
        return sum(result.passed for result in self.check_results) / len(self.check_results)


@dataclass(frozen=True)
class EvalReport:
    scenario_results: list[ScenarioResult]
    deterministic_pass_rate: float
    report_markdown: str
    report_path: Path


def numeric_grounding(payload: StoreWeekPayload, narrative_text: str) -> CheckResult:
    payload_numbers = _payload_numbers(payload.model_dump())
    missing: list[str] = []

    for match in NUMBER_PATTERN.finditer(narrative_text):
        raw_value = float(match.group(1))
        is_percent = match.group(2) == "%"
        if not _matches_payload_number(raw_value, is_percent, payload_numbers):
            missing.append(match.group(0))

    if missing:
        return CheckResult(
            name="numeric_grounding",
            status="fail",
            details=f"Numbers not grounded in payload: {', '.join(missing)}",
        )

    return CheckResult(name="numeric_grounding", status="pass")


def tag_coverage(payload: StoreWeekPayload, result: NarrativeResult) -> CheckResult:
    """All flags in payload.flags must appear in result.flags_narrated."""
    missing = [f for f in payload.flags if f not in result.flags_narrated]
    if missing:
        return CheckResult(
            name="tag_coverage",
            status="fail",
            details=f"Flags not reflected in narrative: {', '.join(sorted(missing))}",
        )
    return CheckResult(name="tag_coverage", status="pass")


def yoy_caveat_check(payload: StoreWeekPayload, result: NarrativeResult) -> CheckResult:
    """result.yoy_caveat_present must equal payload.ly_baseline_abnormal."""
    if result.yoy_caveat_present != payload.ly_baseline_abnormal:
        expected = payload.ly_baseline_abnormal
        got = result.yoy_caveat_present
        return CheckResult(
            name="yoy_caveat_check",
            status="fail",
            details=f"yoy_caveat_present={got} but ly_baseline_abnormal={expected}",
        )
    return CheckResult(name="yoy_caveat_check", status="pass")


def network_gap_check(payload: StoreWeekPayload, result: NarrativeResult) -> CheckResult:
    """If any flagged KPI has a negative store_vs_network value, the narrative
    must mention the network gap (result.network_gap_mentioned=True).
    """
    flagged_kpis = extract_flagged_kpis(payload.flags)
    requires_mention = any(
        (payload.store_vs_network.get(kpi) or 0.0) < 0.0
        for kpi in flagged_kpis
    )
    if requires_mention and not result.network_gap_mentioned:
        offending = [
            kpi for kpi in flagged_kpis if (payload.store_vs_network.get(kpi) or 0.0) < 0.0
        ]
        return CheckResult(
            name="network_gap_check",
            status="fail",
            details=f"Flagged KPIs below network median not mentioned: {', '.join(offending)}",
        )
    return CheckResult(name="network_gap_check", status="pass")


def no_hallucinated_flags(tags: list[Tag], narrative_text: str) -> CheckResult:
    normalized_text = _normalize_text(narrative_text)
    failures: list[str] = []

    rules = [
        (
            "decline_claim",
            ("decline", "declined", "fell", "drop", "dropped"),
            lambda tag: "decline" in tag.id,
        ),
        (
            "anomaly_claim",
            ("abnormal", "anomalous", "unusual", "outlier", "suspect"),
            lambda tag: "abnormal" in tag.id or "suspect" in tag.id,
        ),
        (
            "dq_claim",
            ("data quality", "caveat"),
            lambda tag: tag.id.startswith("dq_caveat_"),
        ),
        (
            "underperformance_claim",
            ("underperform", "below the weekly network benchmark", "below benchmark"),
            lambda tag: tag.id.startswith("network_underperform_"),
        ),
    ]

    for rule_name, phrases, predicate in rules:
        if not any(phrase in normalized_text for phrase in phrases):
            continue
        if not any(predicate(tag) for tag in tags):
            failures.append(rule_name)

    if failures:
        return CheckResult(
            name="no_hallucinated_flags",
            status="fail",
            details=f"Unsupported claim categories: {', '.join(failures)}",
        )

    return CheckResult(name="no_hallucinated_flags", status="pass")


def llm_judge(
    payload: StoreWeekPayload,
    narrative_text: str,
    judge_client: object | None,
) -> CheckResult:
    if judge_client is None:
        return CheckResult(name="llm_judge", status="skipped", details="Judge client unavailable.")

    prompt = (
        "Score this store-week narrative for faithfulness and usefulness.\n"
        "Reply with exactly one word: PASS or FAIL.\n\n"
        f"Payload JSON:\n{json.dumps(payload.model_dump(), sort_keys=True)}\n\n"
        f"Narrative:\n{narrative_text}\n"
    )
    try:
        verdict = judge_client.chat(
            "You are a strict evaluator for retail KPI narratives.",
            prompt,
            max_tokens=5,
        ).strip().upper()
    except Exception as exc:
        return CheckResult(name="llm_judge", status="skipped", details=str(exc))

    if verdict.startswith("PASS"):
        return CheckResult(name="llm_judge", status="pass")
    if verdict.startswith("FAIL"):
        return CheckResult(name="llm_judge", status="fail", details=verdict)
    return CheckResult(name="llm_judge", status="skipped", details=verdict)


def evaluate_golden_set(
    path: Path | str = DEFAULT_GOLDEN_SET_PATH,
    *,
    narrative_client: object | None = None,
    judge_client: object | None = None,
    report_path: Path | str = DEFAULT_REPORT_PATH,
) -> EvalReport:
    golden_set_path = Path(path)
    report_target = Path(report_path)
    raw_config = yaml.safe_load(golden_set_path.read_text(encoding="utf-8")) or {}
    scenario_entries = raw_config.get("scenarios", [])

    scenario_results: list[ScenarioResult] = []
    total_checks = 0
    passed_checks = 0

    for entry in scenario_entries:
        payload = StoreWeekPayload.model_validate(entry["payload"])
        tags = generate_tags(payload)
        narrative_result = narrate(payload, tags, narrative_client)
        deterministic_results = [
            numeric_grounding(payload, narrative_result.summary),
            tag_coverage(payload, narrative_result),
            yoy_caveat_check(payload, narrative_result),
            network_gap_check(payload, narrative_result),
            no_hallucinated_flags(tags, narrative_result.summary),
        ]
        judge_result = llm_judge(payload, narrative_result.summary, judge_client)

        total_checks += len(deterministic_results)
        passed_checks += sum(result.passed for result in deterministic_results)
        scenario_results.append(
            ScenarioResult(
                scenario_id=str(entry["id"]),
                description=str(entry.get("description", "")),
                narrative_text=narrative_result.summary,
                narrative_source=narrative_result.source,
                check_results=deterministic_results,
                llm_judge_result=judge_result,
            )
        )

    pass_rate = 1.0 if total_checks == 0 else passed_checks / total_checks
    markdown = _render_report(scenario_results, pass_rate)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.write_text(markdown, encoding="utf-8")

    return EvalReport(
        scenario_results=scenario_results,
        deterministic_pass_rate=pass_rate,
        report_markdown=markdown,
        report_path=report_target,
    )


def _render_report(scenario_results: list[ScenarioResult], pass_rate: float) -> str:
    lines = [
        "# Eval Report v1",
        "",
        f"Deterministic pass rate: {pass_rate:.1%}",
        f"Threshold: {PASS_THRESHOLD:.0%}",
        "",
        "| Scenario | Numeric grounding | Tag coverage | YoY caveat | Network gap | No hallucinated claims | LLM judge | Narrative excerpt |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for result in scenario_results:
        check_map = {check.name: check for check in result.check_results}
        llm_status = _status_badge(result.llm_judge_result) if result.llm_judge_result else "SKIP"
        excerpt = result.narrative_text.replace("\n", " ").strip()
        excerpt = excerpt[:117] + "..." if len(excerpt) > 120 else excerpt
        lines.append(
            "| {scenario} | {numeric} | {coverage} | {yoy} | {gap} | {hallucination} | {llm} | {excerpt} |".format(
                scenario=result.scenario_id,
                numeric=_status_badge(check_map["numeric_grounding"]),
                coverage=_status_badge(check_map["tag_coverage"]),
                yoy=_status_badge(check_map["yoy_caveat_check"]),
                gap=_status_badge(check_map["network_gap_check"]),
                hallucination=_status_badge(check_map["no_hallucinated_flags"]),
                llm=llm_status,
                excerpt=excerpt.replace("|", "\\|"),
            )
        )

    lines.extend(["", "## Notes", ""])
    for result in scenario_results:
        lines.append(f"- `{result.scenario_id}`: {result.description}")
        for check in result.check_results:
            if check.status == "fail" and check.details:
                lines.append(f"  - {check.name}: {check.details}")
        if result.llm_judge_result and result.llm_judge_result.status != "pass" and result.llm_judge_result.details:
            lines.append(f"  - llm_judge: {result.llm_judge_result.details}")

    return "\n".join(lines) + "\n"


def _status_badge(result: CheckResult) -> str:
    return {
        "pass": "PASS",
        "fail": "FAIL",
        "skipped": "SKIP",
    }[result.status]


def _matches_payload_number(value: float, is_percent: bool, payload_numbers: list[float]) -> bool:
    candidates = payload_numbers if not is_percent else payload_numbers + [number * 100 for number in payload_numbers]
    tolerance_floor = 1.0 if is_percent else 0.01
    for candidate in candidates:
        tolerance = max(tolerance_floor, abs(candidate) * 0.01)
        if abs(candidate - value) <= tolerance:
            return True
    return False


def _payload_numbers(value: Any) -> list[float]:
    numbers: list[float] = []

    if isinstance(value, bool):
        return numbers
    if isinstance(value, (int, float)):
        numbers.append(float(value))
        return numbers
    if isinstance(value, dict):
        for nested_value in value.values():
            numbers.extend(_payload_numbers(nested_value))
        return numbers
    if isinstance(value, list):
        for nested_value in value:
            numbers.extend(_payload_numbers(nested_value))
        return numbers

    return numbers


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()
