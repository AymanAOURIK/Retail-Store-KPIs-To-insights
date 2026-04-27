from __future__ import annotations

from yoobic_insight.payload import StoreWeekPayload
from yoobic_insight.tags import Tag, generate_tags


def test_generate_tags_returns_exact_sorted_golden_tag_ids() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=21,
        kpis={
            "traffic": 80.0,
            "gross_transactions": 30.0,
            "gross_quantity": 60.0,
            "net_sales": 600.0,
            "conversion_rate": 0.375,
            "units_per_txn": 2.0,
            "avg_selling_price": 10.0,
            "avg_txn_value": 20.0,
            "revenue_per_visitor": 7.5,
        },
        yoy={
            "traffic": -0.2,
            "gross_transactions": -0.15,
            "gross_quantity": -0.1,
            "net_sales": -0.25,
            "conversion_rate": -0.05,
            "units_per_txn": 0.0,
            "avg_selling_price": 0.0,
            "avg_txn_value": -0.1,
            "revenue_per_visitor": -0.15,
        },
        network_median={
            "traffic": 100.0,
            "gross_transactions": 40.0,
            "gross_quantity": 70.0,
            "net_sales": 800.0,
            "conversion_rate": 0.4,
            "units_per_txn": 2.1,
            "avg_selling_price": 11.0,
            "avg_txn_value": 22.0,
            "revenue_per_visitor": 8.0,
        },
        network_mad={
            "traffic": 10.0,
            "gross_transactions": 5.0,
            "gross_quantity": 20.0,
            "net_sales": 50.0,
            "conversion_rate": 0.01,
            "units_per_txn": 0.2,
            "avg_selling_price": 0.5,
            "avg_txn_value": 1.0,
            "revenue_per_visitor": 0.4,
        },
        store_vs_network={
            "traffic": -20.0,
            "gross_transactions": -10.0,
            "gross_quantity": -10.0,
            "net_sales": -200.0,
            "conversion_rate": -0.025,
            "units_per_txn": -0.1,
            "avg_selling_price": -1.0,
            "avg_txn_value": -2.0,
            "revenue_per_visitor": -0.5,
        },
        driver_attribution={
            "traffic": 70.0,
            "conversion_rate": 20.0,
            "units_per_txn": 5.0,
            "avg_selling_price": 5.0,
        },
        flags=["current_week_anomalous_net_sales", "ly_baseline_abnormal_traffic"],
        dq_caveats=[
            "gross_transactions_exceeds_traffic: gross_transactions (87) exceeds traffic (65).",
            "missing_value: Missing values in columns: gross_quantity.",
        ],
        has_ly_baseline=True,
    )

    tags = generate_tags(payload)

    assert [tag.id for tag in tags] == [
        "dq_caveat_gross_transactions_exceeds_traffic",
        "dq_caveat_missing_value",
        "ly_baseline_suspect_traffic",
        "sales_yoy_strong_decline",
        "traffic_drove_decline",
        "network_underperform_avg_selling_price",
        "network_underperform_avg_txn_value",
        "network_underperform_conversion_rate",
        "network_underperform_gross_transactions",
        "network_underperform_net_sales",
        "network_underperform_revenue_per_visitor",
        "network_underperform_traffic",
    ]


def test_generate_tags_omits_decline_and_driver_tags_when_thresholds_are_not_met() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=21,
        kpis={},
        yoy={"net_sales": -0.05},
        network_median={},
        network_mad={"traffic": 10.0},
        store_vs_network={"traffic": -9.0},
        driver_attribution={"traffic": 90.0},
        flags=[],
        dq_caveats=[],
        has_ly_baseline=False,
    )

    assert generate_tags(payload) == []


def test_generate_tags_sorts_by_severity_then_id() -> None:
    payload = StoreWeekPayload(
        store_alias="STORE_01",
        year=2025,
        week=21,
        kpis={},
        yoy={"net_sales": -0.2},
        network_median={},
        network_mad={"traffic": 5.0, "net_sales": 5.0},
        store_vs_network={"traffic": -6.0, "net_sales": -10.0},
        driver_attribution={
            "traffic": 55.0,
            "conversion_rate": 10.0,
            "units_per_txn": 20.0,
            "avg_selling_price": 15.0,
        },
        flags=["ly_baseline_abnormal_net_sales"],
        dq_caveats=["z_issue: Late file arrival.", "a_issue: Missing baseline row."],
        has_ly_baseline=True,
    )

    tags = generate_tags(payload)

    assert tags == [
        Tag(
            id="dq_caveat_a_issue",
            severity=1,
            kpi=None,
            message_template="Data quality caveat: a_issue.",
        ),
        Tag(
            id="dq_caveat_z_issue",
            severity=1,
            kpi=None,
            message_template="Data quality caveat: z_issue.",
        ),
        Tag(
            id="ly_baseline_suspect_net_sales",
            severity=1,
            kpi="net_sales",
            message_template="Last year's net sales baseline may be abnormal.",
        ),
        Tag(
            id="sales_yoy_strong_decline",
            severity=1,
            kpi="net_sales",
            message_template="Net sales fell sharply year over year.",
        ),
        Tag(
            id="traffic_drove_decline",
            severity=2,
            kpi="traffic",
            message_template="traffic was the dominant driver of the sales decline.",
        ),
        Tag(
            id="network_underperform_net_sales",
            severity=3,
            kpi="net_sales",
            message_template="net sales was below the weekly network benchmark.",
        ),
        Tag(
            id="network_underperform_traffic",
            severity=3,
            kpi="traffic",
            message_template="traffic was below the weekly network benchmark.",
        ),
    ]
