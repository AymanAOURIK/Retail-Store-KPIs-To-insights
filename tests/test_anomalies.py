from __future__ import annotations

import numpy as np
import pandas as pd

from yoobic_insight.anomalies import flag_current_week, flag_ly_baseline, modified_zscore


def test_modified_zscore_uses_standard_formula_when_mad_is_non_zero() -> None:
    values = np.array([10.0, 11.0, 12.0])

    scores = modified_zscore(values)

    np.testing.assert_allclose(scores, np.array([-0.6745, 0.0, 0.6745]))


def test_modified_zscore_falls_back_to_absolute_deviation_when_mad_is_zero() -> None:
    values = np.array([10.0, 10.0, 14.0])

    scores = modified_zscore(values)

    np.testing.assert_allclose(scores, np.array([0.0, 0.0, 4.0]))


def test_flag_current_week_flags_outlier_using_only_past_store_history() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2025, "Week": 1, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 2, "traffic": 101, "gross_transactions": 20.2, "gross_quantity": 40.4, "net_sales": 404.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 3, "traffic": 102, "gross_transactions": 20.4, "gross_quantity": 40.8, "net_sales": 408.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 4, "traffic": 110, "gross_transactions": 22, "gross_quantity": 44, "net_sales": 440.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 5, "traffic": 1000, "gross_transactions": 200, "gross_quantity": 400, "net_sales": 4000.0},
        ]
    )

    flags = flag_current_week(frame, store="Store_A", year=2025, week=4)

    assert "current_week_anomalous_traffic" in flags


def test_flag_current_week_does_not_flag_constant_history_or_target() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2025, "Week": 1, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 2, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 3, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 4, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
        ]
    )

    assert flag_current_week(frame, store="Store_A", year=2025, week=4) == []


def _make_store_history(
    store: str,
    year: int,
    weeks: list[int],
    traffic_values: list[float],
) -> list[dict]:
    """Build minimal rows with net_sales proportional to traffic for test fixtures."""
    rows = []
    for week, traffic in zip(weeks, traffic_values):
        gt = traffic * 0.2
        gq = gt * 2.0
        rows.append({
            "Store Name": store,
            "Year": year,
            "Week": week,
            "traffic": traffic,
            "gross_transactions": gt,
            "gross_quantity": gq,
            "net_sales": traffic * 10.0,
        })
    return rows


def test_flag_ly_baseline_returns_empty_when_insufficient_ly_history() -> None:
    # Only 5 LY weeks — below the 12-week minimum
    rows = _make_store_history("Store_A", 2024, list(range(1, 6)), [100.0] * 5)
    rows.append({
        "Store Name": "Store_A", "Year": 2025, "Week": 1,
        "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 1000.0,
    })
    frame = pd.DataFrame(rows)

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=1)

    assert flags == []


def test_flag_ly_baseline_flags_store_own_ly_history_outlier() -> None:
    # 20 normal weeks in 2024 (traffic~100), but W10 was 400 (z >> 3.0)
    normal_weeks = [w for w in range(1, 21) if w != 10]
    normal_traffic = [100.0] * len(normal_weeks)
    rows = _make_store_history("Store_A", 2024, normal_weeks, normal_traffic)
    rows += _make_store_history("Store_A", 2024, [10], [400.0])  # LY target week: spike
    rows.append({
        "Store Name": "Store_A", "Year": 2025, "Week": 10,
        "traffic": 105, "gross_transactions": 21, "gross_quantity": 42, "net_sales": 1050.0,
    })
    frame = pd.DataFrame(rows)

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=10)

    assert "ly_baseline_abnormal_traffic" in flags


def test_flag_ly_baseline_does_not_flag_normal_ly_value() -> None:
    # Regression test for audit finding: Store_A 2024 W48 net_sales with z~1.01
    # 47 normal LY weeks at net_sales~100, W48 at 115 → z < 3.0 → should NOT be flagged.
    normal_weeks = list(range(1, 48))  # W1-W47
    normal_traffic = [100.0] * len(normal_weeks)
    rows = _make_store_history("Store_A", 2024, normal_weeks, normal_traffic)
    # W48: net_sales=115*10=1150, history net_sales≈100*10=1000; MAD≈0 initially
    # Use varying history to get realistic MAD: alternate 95-105
    rows = []
    for i, w in enumerate(range(1, 48)):
        traffic = 95.0 + (i % 2) * 10.0  # alternates 95, 105
        rows.append({
            "Store Name": "Store_A", "Year": 2024, "Week": w,
            "traffic": traffic, "gross_transactions": traffic * 0.2,
            "gross_quantity": traffic * 0.4, "net_sales": traffic * 10.0,
        })
    # W48 slightly elevated: net_sales=1150, typical ~1000, MAD~50, z~2.0 < 3.0
    rows.append({
        "Store Name": "Store_A", "Year": 2024, "Week": 48,
        "traffic": 115.0, "gross_transactions": 23.0, "gross_quantity": 46.0, "net_sales": 1150.0,
    })
    rows.append({
        "Store Name": "Store_A", "Year": 2025, "Week": 48,
        "traffic": 110, "gross_transactions": 22, "gross_quantity": 44, "net_sales": 1100.0,
    })
    frame = pd.DataFrame(rows)

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=48)

    # net_sales z ≈ (1150 - median) / MAD * 0.6745 < 3.0 → should NOT be flagged
    assert "ly_baseline_abnormal_net_sales" not in flags
    assert "ly_baseline_abnormal_traffic" not in flags


def test_flag_ly_baseline_constant_history_does_not_flag_matching_value() -> None:
    rows = _make_store_history("Store_A", 2024, list(range(1, 21)), [100.0] * 20)
    rows.append({
        "Store Name": "Store_A", "Year": 2025, "Week": 10,
        "traffic": 100.0, "gross_transactions": 20.0, "gross_quantity": 40.0, "net_sales": 1000.0,
    })
    frame = pd.DataFrame(rows)

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=10)

    assert flags == []


def test_flag_ly_baseline_constant_history_flags_different_value() -> None:
    rows = _make_store_history("Store_A", 2024, [w for w in range(1, 21) if w != 10], [100.0] * 19)
    rows += _make_store_history("Store_A", 2024, [10], [130.0])
    rows.append({
        "Store Name": "Store_A", "Year": 2025, "Week": 10,
        "traffic": 100.0, "gross_transactions": 20.0, "gross_quantity": 40.0, "net_sales": 1000.0,
    })
    frame = pd.DataFrame(rows)

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=10)

    assert "ly_baseline_abnormal_traffic" in flags
    assert "ly_baseline_abnormal_net_sales" in flags
