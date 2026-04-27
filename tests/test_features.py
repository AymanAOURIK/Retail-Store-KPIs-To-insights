from __future__ import annotations

import math

import pandas as pd

from yoobic_insight.features import (
    compute_kpi_tree,
    compute_network_reference,
    compute_store_vs_network,
    compute_yoy,
    percentile_rank_in_network,
)


def test_compute_yoy_uses_strict_like_for_like_week_intersection() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2024, "Week": 1, "traffic": 100, "gross_transactions": 20, "gross_quantity": 30, "net_sales": 300.0},
            {"Store Name": "Store_A", "Year": 2024, "Week": 2, "traffic": 120, "gross_transactions": 24, "gross_quantity": 36, "net_sales": 360.0},
            {"Store Name": "Store_A", "Year": 2024, "Week": 3, "traffic": 150, "gross_transactions": 30, "gross_quantity": 45, "net_sales": 450.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 1, "traffic": 110, "gross_transactions": 22, "gross_quantity": 33, "net_sales": 330.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 3, "traffic": 165, "gross_transactions": 33, "gross_quantity": 49.5, "net_sales": 495.0},
            {"Store Name": "Store_B", "Year": 2024, "Week": 1, "traffic": 90, "gross_transactions": 18, "gross_quantity": 27, "net_sales": 270.0},
            {"Store Name": "Store_B", "Year": 2025, "Week": 1, "traffic": 99, "gross_transactions": 19.8, "gross_quantity": 29.7, "net_sales": 297.0},
        ]
    )

    yoy = compute_yoy(frame)

    store_a = yoy.loc[yoy["Store Name"] == "Store_A", ["Year", "Week"]]
    assert store_a.to_dict("records") == [
        {"Year": 2025, "Week": 1},
        {"Year": 2025, "Week": 3},
    ]
    assert not ((yoy["Store Name"] == "Store_A") & (yoy["Week"] == 2)).any()


def test_compute_kpi_tree_returns_nan_for_zero_denominators() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2025, "Week": 1, "traffic": 0, "gross_transactions": 5, "gross_quantity": 0, "net_sales": 0.0},
            {"Store Name": "Store_B", "Year": 2025, "Week": 1, "traffic": 10, "gross_transactions": 0, "gross_quantity": 5, "net_sales": 25.0},
        ]
    )

    result = compute_kpi_tree(frame)

    assert math.isnan(result.loc[0, "conversion_rate"])
    assert math.isnan(result.loc[0, "avg_selling_price"])
    assert math.isnan(result.loc[1, "units_per_txn"])
    assert math.isnan(result.loc[1, "avg_txn_value"])


def test_compute_yoy_returns_nan_when_previous_value_is_zero_or_missing() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2024, "Week": 1, "traffic": 0, "gross_transactions": 0, "gross_quantity": 0, "net_sales": 0.0},
            {"Store Name": "Store_A", "Year": 2025, "Week": 1, "traffic": 10, "gross_transactions": 5, "gross_quantity": 6, "net_sales": 60.0},
        ]
    )

    yoy = compute_yoy(frame)

    assert math.isnan(yoy.loc[0, "traffic_yoy"])
    assert math.isnan(yoy.loc[0, "net_sales_yoy"])
    assert math.isnan(yoy.loc[0, "conversion_rate_yoy"])


def test_network_reference_and_store_vs_network_use_weekly_median_and_mad() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2025, "Week": 10, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_B", "Year": 2025, "Week": 10, "traffic": 200, "gross_transactions": 40, "gross_quantity": 80, "net_sales": 800.0},
            {"Store Name": "Store_C", "Year": 2025, "Week": 10, "traffic": 300, "gross_transactions": 60, "gross_quantity": 120, "net_sales": 1200.0},
        ]
    )

    ref = compute_network_reference(frame)
    gaps = compute_store_vs_network(frame, ref)

    assert ref.loc[0, "traffic_median"] == 200
    assert ref.loc[0, "traffic_mad"] == 100
    assert gaps.loc[gaps["Store Name"] == "Store_A", "traffic_vs_network"].iloc[0] == -100
    assert gaps.loc[gaps["Store Name"] == "Store_C", "traffic_vs_network"].iloc[0] == 100


def test_percentile_rank_in_network_returns_weekly_percentiles() -> None:
    frame = pd.DataFrame(
        [
            {"Store Name": "Store_A", "Year": 2025, "Week": 10, "traffic": 100, "gross_transactions": 20, "gross_quantity": 40, "net_sales": 400.0},
            {"Store Name": "Store_B", "Year": 2025, "Week": 10, "traffic": 200, "gross_transactions": 40, "gross_quantity": 80, "net_sales": 800.0},
            {"Store Name": "Store_C", "Year": 2025, "Week": 10, "traffic": 300, "gross_transactions": 60, "gross_quantity": 120, "net_sales": 1200.0},
        ]
    )

    ref = compute_network_reference(frame)
    ranked = percentile_rank_in_network(frame, ref)

    percentiles = ranked.set_index("Store Name")["traffic_percentile"].to_dict()
    assert percentiles == {"Store_A": 1 / 3, "Store_B": 2 / 3, "Store_C": 1.0}
