from __future__ import annotations

import math

import pandas as pd

from retails_insight.decomposition import decompose_yoy_log_additive


def test_decompose_yoy_log_additive_attributes_single_driver_to_one_hundred_percent() -> None:
    previous = pd.DataFrame(
        [
            {
                "traffic": 100.0,
                "conversion_rate": 0.2,
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            }
        ]
    )
    current = pd.DataFrame(
        [
            {
                "traffic": 200.0,
                "conversion_rate": 0.2,
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            }
        ]
    )

    result = decompose_yoy_log_additive(current, previous)

    assert result.loc[0, "traffic_share_pct"] == 100.0
    assert result.loc[0, "conversion_rate_share_pct"] == 0.0
    assert result.loc[0, "units_per_txn_share_pct"] == 0.0
    assert result.loc[0, "avg_selling_price_share_pct"] == 0.0


def test_decompose_yoy_log_additive_returns_zero_shares_when_total_log_change_is_zero() -> None:
    previous = pd.Series(
        {
            "traffic": 100.0,
            "conversion_rate": 0.2,
            "units_per_txn": 2.0,
            "avg_selling_price": 10.0,
        }
    )
    current = previous.copy()

    result = decompose_yoy_log_additive(current, previous)

    assert result.loc[0, "net_sales_log_change"] == 0.0
    assert result.loc[0, "traffic_share_pct"] == 0.0
    assert result.loc[0, "conversion_rate_share_pct"] == 0.0


def test_decompose_yoy_log_additive_returns_nan_for_zero_or_missing_inputs() -> None:
    previous = pd.DataFrame(
        [
            {
                "traffic": 0.0,
                "conversion_rate": 0.2,
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            },
            {
                "traffic": 100.0,
                "conversion_rate": float("nan"),
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            },
        ]
    )
    current = pd.DataFrame(
        [
            {
                "traffic": 200.0,
                "conversion_rate": 0.2,
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            },
            {
                "traffic": 120.0,
                "conversion_rate": 0.25,
                "units_per_txn": 2.0,
                "avg_selling_price": 10.0,
            },
        ]
    )

    result = decompose_yoy_log_additive(current, previous)

    assert math.isnan(result.loc[0, "traffic_log_contribution"])
    assert math.isnan(result.loc[0, "net_sales_log_change"])
    assert math.isnan(result.loc[1, "conversion_rate_log_contribution"])
    assert math.isnan(result.loc[1, "conversion_rate_share_pct"])
