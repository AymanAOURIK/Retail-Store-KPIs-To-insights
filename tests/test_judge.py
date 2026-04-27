from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from yoobic_insight.judge import evaluate_golden_set, no_hallucinated_flags, numeric_grounding, tag_coverage
from yoobic_insight.payload import StoreWeekPayload
from yoobic_insight.tags import Tag, generate_tags


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


def test_tag_coverage_requires_high_severity_tags_in_narrative() -> None:
    payload = _sample_payload()
    tags = generate_tags(payload)

    result = tag_coverage(tags, "STORE_03 week 18 of 2025 summary.")

    assert result.status == "fail"
    assert "ly_baseline_suspect_conversion_rate" in result.details


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
    # Force-empty so load_dotenv (override=False) cannot re-populate from a developer's local .env.
    sanitized_env["OPENAI_API_KEY"] = ""
    sanitized_env["JUDGE_MODEL"] = ""
    sanitized_env["PYTHONPATH"] = str(project_root / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "yoobic_insight.eval",
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
    assert "fallback=12" in completed.stdout
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
        has_ly_baseline=True,
    )
