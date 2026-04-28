from __future__ import annotations

import pytest

from yoobic_insight.loader import DQIssue
from yoobic_insight.payload import Anonymiser, StoreWeekPayload, build_payload


def test_store_week_payload_rejects_extra_fields() -> None:
    with pytest.raises(Exception) as exc_info:
        StoreWeekPayload.model_validate(
            {
                "store_alias": "STORE_01",
                "year": 2025,
                "week": 21,
                "kpis": {},
                "yoy": {},
                "network_median": {},
                "network_mad": {},
                "store_vs_network": {},
                "driver_attribution": {},
                "flags": [],
                "dq_caveats": [],
                "ly_baseline_abnormal": False,
                "unexpected": "value",
            }
        )

    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_anonymiser_encodes_and_decodes_using_sorted_store_aliases() -> None:
    anonymiser = Anonymiser(["Store_C", "Store_A", "Store_B"])
    same_mapping = Anonymiser(["Store_B", "Store_C", "Store_A"])

    assert anonymiser.encode("Store_A") == "STORE_01"
    assert anonymiser.encode("Store_B") == "STORE_02"
    assert anonymiser.encode("Store_C") == "STORE_03"
    assert same_mapping.encode("Store_C") == "STORE_03"
    assert anonymiser.decode("STORE_02") == "Store_B"


def test_build_payload_returns_stable_nested_shape_from_synthetic_rows() -> None:
    features_row = {
        "Store Name": "Store_B",
        "Year": 2025,
        "Week": 21,
        "traffic": 123.456789,
        "gross_transactions": 45.678912,
        "gross_quantity": 89.123456,
        "net_sales": 987.654321,
        "conversion_rate": 0.3700004,
        "units_per_txn": 1.951234,
        "avg_selling_price": 11.081234,
        "avg_txn_value": 21.621234,
        "revenue_per_visitor": 8.000049,
        "traffic_yoy": 0.123456,
        "gross_transactions_yoy": -0.045678,
        "gross_quantity_yoy": 0.067891,
        "net_sales_yoy": 0.101112,
        "conversion_rate_yoy": -0.012345,
        "units_per_txn_yoy": 0.023456,
        "avg_selling_price_yoy": 0.034567,
        "avg_txn_value_yoy": 0.045678,
        "revenue_per_visitor_yoy": 0.056789,
        "traffic_vs_network": -10.111119,
        "gross_transactions_vs_network": -4.222229,
        "gross_quantity_vs_network": 5.333339,
        "net_sales_vs_network": 25.444449,
        "conversion_rate_vs_network": -0.010009,
        "units_per_txn_vs_network": 0.020009,
        "avg_selling_price_vs_network": 0.030009,
        "avg_txn_value_vs_network": 0.040009,
        "revenue_per_visitor_vs_network": 0.050009,
        "traffic_share_pct": 70.123456,
        "conversion_rate_share_pct": -10.234567,
        "units_per_txn_share_pct": 15.345678,
        "avg_selling_price_share_pct": 24.765433,
    }
    ref_row = {
        "Year": 2025,
        "Week": 21,
        "traffic_median": 133.567891,
        "traffic_mad": 12.345678,
        "gross_transactions_median": 49.901141,
        "gross_transactions_mad": 3.210987,
        "gross_quantity_median": 83.790117,
        "gross_quantity_mad": 4.321098,
        "net_sales_median": 962.209872,
        "net_sales_mad": 55.432198,
        "conversion_rate_median": 0.3800094,
        "conversion_rate_mad": 0.0123456,
        "units_per_txn_median": 1.931225,
        "units_per_txn_mad": 0.0456789,
        "avg_selling_price_median": 11.051225,
        "avg_selling_price_mad": 0.0567891,
        "avg_txn_value_median": 21.581225,
        "avg_txn_value_mad": 0.0678912,
        "revenue_per_visitor_median": 7.95004,
        "revenue_per_visitor_mad": 0.0789123,
    }

    payload = build_payload(
        features_row=features_row,
        ref_row=ref_row,
        anomalies=["ly_baseline_abnormal_traffic", "current_week_anomalous_net_sales"],
        dq=[
            DQIssue(
                store="Store_B",
                year=2025,
                week=21,
                kind="missing_value",
                message="Missing values in columns: gross_quantity.",
            ),
            DQIssue(
                store="Store_B",
                year=2025,
                week=21,
                kind="gross_transactions_exceeds_traffic",
                message="gross_transactions (87) exceeds traffic (65).",
            ),
        ],
        anonymiser=Anonymiser(["Store_C", "Store_A", "Store_B"]),
    )

    assert payload.model_dump() == {
        "store_alias": "STORE_02",
        "year": 2025,
        "week": 21,
        "kpis": {
            "traffic": 123.4568,
            "gross_transactions": 45.6789,
            "gross_quantity": 89.1235,
            "net_sales": 987.6543,
            "conversion_rate": 0.37,
            "units_per_txn": 1.9512,
            "avg_selling_price": 11.0812,
            "avg_txn_value": 21.6212,
            "revenue_per_visitor": 8.0,
        },
        "yoy": {
            "traffic": 0.1235,
            "gross_transactions": -0.0457,
            "gross_quantity": 0.0679,
            "net_sales": 0.1011,
            "conversion_rate": -0.0123,
            "units_per_txn": 0.0235,
            "avg_selling_price": 0.0346,
            "avg_txn_value": 0.0457,
            "revenue_per_visitor": 0.0568,
        },
        "network_median": {
            "traffic": 133.5679,
            "gross_transactions": 49.9011,
            "gross_quantity": 83.7901,
            "net_sales": 962.2099,
            "conversion_rate": 0.38,
            "units_per_txn": 1.9312,
            "avg_selling_price": 11.0512,
            "avg_txn_value": 21.5812,
            "revenue_per_visitor": 7.95,
        },
        "network_mad": {
            "traffic": 12.3457,
            "gross_transactions": 3.211,
            "gross_quantity": 4.3211,
            "net_sales": 55.4322,
            "conversion_rate": 0.0123,
            "units_per_txn": 0.0457,
            "avg_selling_price": 0.0568,
            "avg_txn_value": 0.0679,
            "revenue_per_visitor": 0.0789,
        },
        "store_vs_network": {
            "traffic": -10.1111,
            "gross_transactions": -4.2222,
            "gross_quantity": 5.3333,
            "net_sales": 25.4444,
            "conversion_rate": -0.01,
            "units_per_txn": 0.02,
            "avg_selling_price": 0.03,
            "avg_txn_value": 0.04,
            "revenue_per_visitor": 0.05,
        },
        "driver_attribution": {
            "traffic": 70.1235,
            "conversion_rate": -10.2346,
            "units_per_txn": 15.3457,
            "avg_selling_price": 24.7654,
        },
        "flags": [
            "current_week_anomalous_net_sales",
            "ly_baseline_abnormal_traffic",
        ],
        "dq_caveats": [
            "gross_transactions_exceeds_traffic: gross_transactions (87) exceeds traffic (65).",
            "missing_value: Missing values in columns: gross_quantity.",
        ],
        "ly_baseline_abnormal": True,
    }
