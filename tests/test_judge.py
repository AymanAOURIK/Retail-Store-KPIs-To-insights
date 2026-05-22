from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from retails_insight.judge import (
    evaluate_golden_set,
    network_gap_check,
    no_hallucinated_flags,
    numeric_grounding,
    tag_coverage,
    yoy_caveat_check,
)
from retails_insight.payload import NarrativeResult, StoreWeekPayload
from retails_insight.tags import Tag, generate_tags


def _make_result(**kwargs) -> NarrativeResult:
    defaults = dict(
        summary="STORE_03 week 18 of 2025 summary.",
        flags_narrated=[],
        yoy_caveat_present=False,
        network_gap_mentioned=False,
        dominant_driver_cited=None,
        source="fallback",
        model=None,
        tags_used=[],
    )
    defaults.update(kwargs)
    return NarrativeResult(**defaults)


def test_numeric_grounding_accepts_payload_numbers_and_percentage_rendering() -> None:
    payload = _sample_payload()

    result = numeric_grounding(
        payload,
        "STORE_03 week 18 of 2025 summary. Net sales improved 1.2% year over year.",
    )

    assert result.passed is True


def test_numeric_grounding_fails_for_number_not_in_payload() -> None:
    payload = _sample_payload()

    result = numeric_grounding(payload, "STORE_03 week 18 of 2025 summary. Sales improved 99%.")

    assert result.status == "fail"
    assert "99%" in result.details


def test_tag_coverage_fails_when_flag_not_in_flags_narrated() -> None:
    payload = _sample_payload()
    # payload.flags = ["ly_baseline_abnormal_conversion_rate"]
    result = _make_result(flags_narrated=[])

    check = tag_coverage(payload, result)

    assert check.status == "fail"
    assert "ly_baseline_abnormal_conversion_rate" in check.details


def test_tag_coverage_passes_when_all_flags_narrated() -> None:
    payload = _sample_payload()
    result = _make_result(flags_narrated=["ly_baseline_abnormal_conversion_rate"])

    check = tag_coverage(payload, result)

    assert check.passed


def test_tag_coverage_passes_when_no_flags() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=10,
        kpis={},
        yoy={},
        network_median={},
        network_mad={},
        store_vs_network={},
        driver_attribution={},
        flags=[],
        dq_caveats=[],
        ly_baseline_abnormal=False,
    )
    result = _make_result(flags_narrated=[])

    assert tag_coverage(payload, result).passed


def test_yoy_caveat_check_passes_when_matching() -> None:
    payload = _sample_payload()  # ly_baseline_abnormal=True
    result = _make_result(yoy_caveat_present=True)

    assert yoy_caveat_check(payload, result).passed


def test_yoy_caveat_check_fails_when_mismatch() -> None:
    payload = _sample_payload()  # ly_baseline_abnormal=True
    result = _make_result(yoy_caveat_present=False)

    check = yoy_caveat_check(payload, result)

    assert check.status == "fail"
    assert "yoy_caveat_present=False" in check.details


def test_network_gap_check_passes_trivially_when_no_flags() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=10,
        kpis={},
        yoy={},
        network_median={},
        network_mad={},
        store_vs_network={"net_sales": -50.0},
        driver_attribution={},
        flags=[],
        dq_caveats=[],
        ly_baseline_abnormal=False,
    )
    result = _make_result(network_gap_mentioned=False)

    assert network_gap_check(payload, result).passed


def test_network_gap_check_fails_when_flagged_kpi_is_below_network_and_not_mentioned() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=10,
        kpis={},
        yoy={},
        network_median={},
        network_mad={},
        store_vs_network={"traffic": -25.0},
        driver_attribution={},
        flags=["ly_baseline_abnormal_traffic"],
        dq_caveats=[],
        ly_baseline_abnormal=True,
    )
    result = _make_result(network_gap_mentioned=False)

    check = network_gap_check(payload, result)

    assert check.status == "fail"
    assert "traffic" in check.details


def test_network_gap_check_passes_when_flagged_kpi_gap_is_positive() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=10,
        kpis={},
        yoy={},
        network_median={},
        network_mad={},
        store_vs_network={"traffic": 5.0},
        driver_attribution={},
        flags=["ly_baseline_abnormal_traffic"],
        dq_caveats=[],
        ly_baseline_abnormal=True,
    )
    result = _make_result(network_gap_mentioned=False)

    assert network_gap_check(payload, result).passed


def test_no_hallucinated_flags_rejects_unsupported_decline_claims() -> None:
    result = no_hallucinated_flags(
        tags=[
            Tag(
                id="network_underperform_traffic",
                severity=3,
                kpi="traffic",
                message_template="traffic was below the weekly network benchmark.",
            )
        ],
        narrative_text="Traffic declined sharply and looked unusual.",
    )

    assert result.status == "fail"
    assert "decline_claim" in result.details
    assert "anomaly_claim" in result.details


def test_evaluate_golden_set_writes_report_and_passes_without_api_key(tmp_path: Path) -> None:
    report_path = tmp_path / "eval_report.md"

    report = evaluate_golden_set(report_path=report_path)

    assert report.deterministic_pass_rate == 1.0
    assert report.report_path == report_path
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "store_g_2025_w21_dq" in report_text
    assert "early_2024_no_ly_baseline" in report_text
    assert "strong_week_positive_yoy" in report_text
    assert "ly_caveat_no_other_flags" in report_text
    assert "ly_abnormal_traffic_below_network" in report_text
    assert "Deterministic pass rate: 100.0%" in report_text


def test_module_entrypoint_supports_python_dash_m(tmp_path: Path) -> None:
    report_path = tmp_path / "subprocess_eval.md"
    golden_set_path = Path("eval/golden_set.yaml").resolve()
    project_root = Path(__file__).resolve().parents[1]

    sanitized_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"OPENAI_API_KEY", "JUDGE_MODEL"}
    }
    sanitized_env["OPENAI_API_KEY"] = ""
    sanitized_env["JUDGE_MODEL"] = ""
    sanitized_env["PYTHONPATH"] = str(project_root / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "retails_insight.eval",
            "--golden-set",
            str(golden_set_path),
            "--report-path",
            str(report_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=sanitized_env,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Deterministic pass rate: 100.0%" in completed.stdout
    assert "fallback=15" in completed.stdout
    assert report_path.exists()


def _sample_payload() -> StoreWeekPayload:
    return StoreWeekPayload(
        store_alias="STORE_03",
        year=2025,
        week=18,
        kpis={"net_sales": 905.0, "conversion_rate": 0.24},
        yoy={"net_sales": 0.012, "conversion_rate": 0.004},
        network_median={"net_sales": 900.0, "conversion_rate": 0.24},
        network_mad={"net_sales": 30.0, "conversion_rate": 0.01},
        store_vs_network={"net_sales": 5.0, "conversion_rate": 0.0},
        driver_attribution={
            "traffic": 10.0,
            "conversion_rate": 20.0,
            "units_per_txn": 30.0,
            "avg_selling_price": 40.0,
        },
        flags=["ly_baseline_abnormal_conversion_rate"],
        dq_caveats=[],
        ly_baseline_abnormal=True,
    )
