from __future__ import annotations

import numpy as np
import pandas as pd

KEY_COLUMNS = ["Store Name", "Year", "Week"]
BASE_METRICS = ["traffic", "gross_transactions", "gross_quantity", "net_sales"]
DERIVED_METRICS = [
    "conversion_rate",
    "units_per_txn",
    "avg_selling_price",
    "avg_txn_value",
    "revenue_per_visitor",
]
ALL_METRICS = BASE_METRICS + DERIVED_METRICS


def compute_kpi_tree(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["conversion_rate"] = _safe_divide(frame["gross_transactions"], frame["traffic"])
    frame["units_per_txn"] = _safe_divide(frame["gross_quantity"], frame["gross_transactions"])
    frame["avg_selling_price"] = _safe_divide(frame["net_sales"], frame["gross_quantity"])
    frame["avg_txn_value"] = _safe_divide(frame["net_sales"], frame["gross_transactions"])
    frame["revenue_per_visitor"] = _safe_divide(frame["net_sales"], frame["traffic"])
    return frame


def compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    frame = compute_kpi_tree(df)
    previous = frame.loc[:, KEY_COLUMNS + ALL_METRICS].copy()
    previous["Year"] = previous["Year"] + 1

    merged = frame.merge(
        previous,
        on=KEY_COLUMNS,
        how="inner",
        suffixes=("_curr", "_prev"),
    )

    yoy_columns: dict[str, pd.Series] = {}
    for metric in ALL_METRICS:
        yoy_columns[f"{metric}_yoy"] = _safe_divide(
            merged[f"{metric}_curr"] - merged[f"{metric}_prev"],
            merged[f"{metric}_prev"],
        )

    return merged.assign(**yoy_columns).sort_values(KEY_COLUMNS).reset_index(drop=True)


def compute_network_reference(df: pd.DataFrame) -> pd.DataFrame:
    frame = compute_kpi_tree(df)
    grouped = frame.groupby(["Year", "Week"], sort=True, dropna=False)

    aggregations: dict[str, tuple[str, str]] = {}
    for metric in ALL_METRICS:
        aggregations[f"{metric}_median"] = (metric, "median")
        aggregations[f"{metric}_mad"] = (metric, _median_absolute_deviation)

    return grouped.agg(**aggregations).reset_index()


def compute_store_vs_network(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    frame = compute_kpi_tree(df)
    merged = frame.merge(ref, on=["Year", "Week"], how="left")

    gap_columns: dict[str, pd.Series] = {}
    for metric in ALL_METRICS:
        gap_columns[f"{metric}_vs_network"] = merged[metric] - merged[f"{metric}_median"]

    return merged.assign(**gap_columns).sort_values(KEY_COLUMNS).reset_index(drop=True)


def percentile_rank_in_network(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    frame = compute_kpi_tree(df)
    if not ref.empty:
        frame = frame.merge(ref.loc[:, ["Year", "Week"]].drop_duplicates(), on=["Year", "Week"], how="inner")

    rank_columns: dict[str, pd.Series] = {}
    grouped = frame.groupby(["Year", "Week"], sort=False, dropna=False)
    for metric in ALL_METRICS:
        rank_columns[f"{metric}_percentile"] = grouped[metric].rank(method="average", pct=True)

    return frame.assign(**rank_columns).sort_values(KEY_COLUMNS).reset_index(drop=True)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float).div(denominator.astype(float))
    invalid = denominator.isna() | numerator.isna() | (denominator == 0)
    return result.mask(invalid, np.nan)


def _median_absolute_deviation(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    if clean.empty:
        return float("nan")

    median = float(clean.median())
    return float((clean - median).abs().median())
