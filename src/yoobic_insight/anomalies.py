from __future__ import annotations

import numpy as np
import pandas as pd

from yoobic_insight.features import ALL_METRICS, compute_kpi_tree

CURRENT_WEEK_THRESHOLD = 3.5
LY_BASELINE_THRESHOLD = 2.5


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
        if np.isfinite(score) and abs(score) > threshold:
            flags.append(f"current_week_anomalous_{metric}")

    return flags


def flag_ly_baseline(
    df: pd.DataFrame,
    store: str,
    year: int,
    week: int,
    threshold: float = LY_BASELINE_THRESHOLD,
) -> list[str]:
    frame = compute_kpi_tree(df)
    current = frame.loc[
        (frame["Store Name"] == store) & (frame["Year"] == year) & (frame["Week"] == week)
    ]
    if current.empty:
        return []

    ly_year = year - 1
    ly_row = frame.loc[
        (frame["Store Name"] == store) & (frame["Year"] == ly_year) & (frame["Week"] == week)
    ]
    if ly_row.empty:
        return []

    ly_network = frame.loc[(frame["Year"] == ly_year) & (frame["Week"] == week)]
    if ly_network.empty:
        return []

    flags: list[str] = []
    ly_index = ly_row.index[0]
    for metric in ALL_METRICS:
        metric_values = ly_network[metric].to_numpy(dtype=float)
        metric_index = ly_network.index.get_indexer([ly_index])[0]
        if metric_index < 0:
            continue

        scores = modified_zscore(metric_values)
        score = scores[metric_index]
        if np.isfinite(score) and abs(score) > threshold:
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
    absolute_deviation = abs(float(value) - median)
    mad = float(np.median(np.abs(reference - median)))

    if np.isclose(mad, 0.0):
        if np.isclose(absolute_deviation, 0.0):
            return 0.0
        return absolute_deviation

    return 0.6745 * (float(value) - median) / mad
