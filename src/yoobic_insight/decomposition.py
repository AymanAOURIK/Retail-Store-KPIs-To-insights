from __future__ import annotations

import numpy as np
import pandas as pd

DRIVER_METRICS = [
    "traffic",
    "conversion_rate",
    "units_per_txn",
    "avg_selling_price",
]


def decompose_yoy_log_additive(curr: pd.DataFrame | pd.Series, prev: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Log-additive YoY decomposition. Positive contribution = driver pushed net sales up; negative = pulled it down. Shares sum to ~100% by construction (log-additive identity)."""
    current = _coerce_frame(curr, suffix="_curr")
    previous = _coerce_frame(prev, suffix="_prev")

    merged = pd.concat([current.reset_index(drop=True), previous.reset_index(drop=True)], axis=1)
    contribution_logs: dict[str, pd.Series] = {}
    for metric in DRIVER_METRICS:
        contribution_logs[f"{metric}_log_contribution"] = _safe_log_ratio(
            merged[f"{metric}_curr"],
            merged[f"{metric}_prev"],
        )

    result = merged.assign(**contribution_logs)
    total_log_change = result[[f"{metric}_log_contribution" for metric in DRIVER_METRICS]].sum(axis=1, min_count=len(DRIVER_METRICS))
    result["net_sales_log_change"] = total_log_change

    share_columns: dict[str, pd.Series] = {}
    for metric in DRIVER_METRICS:
        share_columns[f"{metric}_share_pct"] = _share_of_total(
            result[f"{metric}_log_contribution"],
            total_log_change,
        )

    return result.assign(**share_columns)


def _coerce_frame(data: pd.DataFrame | pd.Series, suffix: str) -> pd.DataFrame:
    if isinstance(data, pd.Series):
        frame = data.to_frame().T
    else:
        frame = pd.DataFrame(data).copy()

    renamed = {}
    for metric in DRIVER_METRICS:
        if metric not in frame.columns:
            raise ValueError(f"missing required metric: {metric}")
        renamed[metric] = f"{metric}{suffix}"
    return frame.rename(columns=renamed)


def _safe_log_ratio(current: pd.Series, previous: pd.Series) -> pd.Series:
    curr = current.astype(float)
    prev = previous.astype(float)
    valid = curr.notna() & prev.notna() & (curr > 0) & (prev > 0)
    output = pd.Series(np.nan, index=curr.index, dtype=float)
    output.loc[valid] = np.log(curr.loc[valid] / prev.loc[valid])
    return output


def _share_of_total(component: pd.Series, total: pd.Series) -> pd.Series:
    valid = component.notna() & total.notna()
    nonzero_total = valid & ~np.isclose(total, 0.0)
    zero_total = valid & np.isclose(total, 0.0)

    output = pd.Series(np.nan, index=component.index, dtype=float)
    output.loc[nonzero_total] = (component.loc[nonzero_total] / total.loc[nonzero_total]) * 100.0
    output.loc[zero_total] = 0.0
    return output
