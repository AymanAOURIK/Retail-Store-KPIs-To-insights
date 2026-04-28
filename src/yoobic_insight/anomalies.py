from __future__ import annotations

import numpy as np
import pandas as pd

from yoobic_insight.features import ALL_METRICS, compute_kpi_tree

CURRENT_WEEK_THRESHOLD = 3.5
LY_BASELINE_THRESHOLD = 3.0
LY_BASELINE_MIN_HISTORY = 12


def modified_zscore(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    scores = np.full(array.shape, np.nan, dtype=float)
    finite_mask = np.isfinite(array)
    if not finite_mask.any():
        return scores

    clean = array[finite_mask]
    median = float(np.median(clean))
    absolute_deviation = np.abs(clean - median)
    mad = float(np.median(absolute_deviation))

    if np.isclose(mad, 0.0):
        clean_scores = absolute_deviation
        clean_scores[np.isclose(absolute_deviation, 0.0)] = 0.0
    else:
        clean_scores = 0.6745 * (clean - median) / mad

    scores[finite_mask] = clean_scores
    return scores


def flag_current_week(
    df: pd.DataFrame,
    store: str,
    year: int,
    week: int,
    threshold: float = CURRENT_WEEK_THRESHOLD,
) -> list[str]:
    frame = _store_frame_until_week(df, store, year, week)
    target = frame.loc[(frame["Year"] == year) & (frame["Week"] == week)]
    if target.empty:
        return []

    history = frame.loc[(frame["Year"] < year) | ((frame["Year"] == year) & (frame["Week"] < week))]
    if history.empty:
        return []

    target_row = target.iloc[0]
    flags: list[str] = []
    for metric in ALL_METRICS:
        value = target_row[metric]
        history_values = history[metric].dropna().to_numpy(dtype=float)
        score = _score_against_reference(value, history_values)
        if not np.isnan(score) and abs(score) > threshold:
            flags.append(f"current_week_anomalous_{metric}")

    return flags


def flag_ly_baseline(
    df: pd.DataFrame,
    store: str,
    year: int,
    week: int,
    threshold: float = LY_BASELINE_THRESHOLD,
    min_history: int = LY_BASELINE_MIN_HISTORY,
) -> list[str]:
    """Check whether the store's LY same-week value was abnormal relative to
    its own LY-year history (excluding that week). Requires at least
    min_history prior weeks in the LY year to produce a reliable MAD estimate.
    """
    frame = compute_kpi_tree(df)
    ly_year = year - 1

    ly_row = frame.loc[
        (frame["Store Name"] == store) & (frame["Year"] == ly_year) & (frame["Week"] == week)
    ]
    if ly_row.empty:
        return []

    # History = all LY weeks for this store, excluding the same week being tested
    ly_history = frame.loc[
        (frame["Store Name"] == store) & (frame["Year"] == ly_year) & (frame["Week"] != week)
    ]
    if len(ly_history) < min_history:
        return []

    flags: list[str] = []
    ly_values = ly_row.iloc[0]
    for metric in ALL_METRICS:
        value = ly_values[metric]
        history_values = ly_history[metric].dropna().to_numpy(dtype=float)
        score = _score_against_reference(value, history_values)
        if not np.isnan(score) and abs(score) > threshold:
            flags.append(f"ly_baseline_abnormal_{metric}")

    return flags


def _store_frame_until_week(df: pd.DataFrame, store: str, year: int, week: int) -> pd.DataFrame:
    frame = compute_kpi_tree(df)
    return (
        frame.loc[
            (frame["Store Name"] == store)
            & ((frame["Year"] < year) | ((frame["Year"] == year) & (frame["Week"] <= week)))
        ]
        .sort_values(["Year", "Week"])
        .reset_index(drop=True)
    )


def _score_against_reference(value: float, reference_values: np.ndarray) -> float:
    if pd.isna(value):
        return float("nan")

    reference = np.asarray(reference_values, dtype=float)
    reference = reference[np.isfinite(reference)]
    if reference.size == 0:
        return float("nan")

    median = float(np.median(reference))
    centered_value = float(value) - median
    absolute_deviation = abs(centered_value)
    mad = float(np.median(np.abs(reference - median)))

    if not np.isclose(mad, 0.0):
        return 0.6745 * centered_value / mad

    q1 = float(np.percentile(reference, 25))
    q3 = float(np.percentile(reference, 75))
    iqr = q3 - q1
    if not np.isclose(iqr, 0.0):
        return centered_value / (iqr / 1.349)

    std = float(np.std(reference))
    if not np.isclose(std, 0.0):
        return centered_value / std

    if np.isclose(absolute_deviation, 0.0):
        return 0.0
    return float("inf")
