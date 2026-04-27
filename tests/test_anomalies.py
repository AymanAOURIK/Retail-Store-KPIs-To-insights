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


def test_flag_ly_baseline_flags_previous_year_same_week_network_outlier() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2024, "Week": 10, "traffic": 300, "gross_transactions": 60, "gross_quantity": 120, "net_sales": 1200.0},
            {"Store Name": "Store_B", "Year": 2024, "Week": 10, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_C", "Year": 2024, "Week": 10, "traffic": 102, "gross_transactions": 20.4, "gross_quantity": 40.8, "net_sales": 408.0},
            {"Store Name": "Store_D", "Year": 2024, "Week": 10, "traffic": 98, "gross_transactions": 19.6, "gross_quantity": 39.2, "net_sales": 392.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 10, "traffic": 101, "gross_transactions": 20.2, "gross_quantity": 40.4, "net_sales": 404.0},
        ]
    )

    flags = flag_ly_baseline(frame, store="Store_A", year=2025, week=10)

    assert "ly_baseline_abnormal_traffic" in flags
