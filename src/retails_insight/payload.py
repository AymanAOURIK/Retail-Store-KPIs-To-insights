from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from retails_insight.decomposition import DRIVER_METRICS
from retails_insight.features import ALL_METRICS

ROUND_DIGITS = 4


class StoreWeekPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_alias: str
    year: int
    week: int
    kpis: dict[str, float | None]
    yoy: dict[str, float | None]
    network_median: dict[str, float | None]
    network_mad: dict[str, float | None]
    store_vs_network: dict[str, float | None]
    driver_attribution: dict[str, float | None]
    flags: list[str]
    dq_caveats: list[str]
    ly_baseline_abnormal: bool


class NarrativeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    flags_narrated: list[str]
    yoy_caveat_present: bool
    network_gap_mentioned: bool
    dominant_driver_cited: str | None
    source: Literal["llm", "fallback"]
    model: str | None
    tags_used: list[str]


class Anonymiser:
    def __init__(self, store_names: list[str] | tuple[str, ...] | set[str]) -> None:
        ordered_names = sorted({str(name) for name in store_names})
        self._store_to_alias = {
            store_name: f"STORE_{index:02d}" for index, store_name in enumerate(ordered_names, start=1)
        }
        self._alias_to_store = {alias: store for store, alias in self._store_to_alias.items()}

    def encode(self, store_name: str) -> str:
        try:
            return self._store_to_alias[store_name]
        except KeyError as exc:
            raise KeyError(f"unknown store name: {store_name}") from exc

    def decode(self, store_alias: str) -> str:
        try:
            return self._alias_to_store[store_alias]
        except KeyError as exc:
            raise KeyError(f"unknown store alias: {store_alias}") from exc


def build_payload(
    features_row: pd.Series | dict[str, object],
    ref_row: pd.Series | dict[str, object],
    anomalies: list[str],
    dq: list[object],
    anonymiser: Anonymiser,
) -> StoreWeekPayload:
    feature_values = _coerce_mapping(features_row)
    reference_values = _coerce_mapping(ref_row)

    flags = sorted(str(flag) for flag in anomalies)
    dq_caveats = sorted({_dq_caveat(issue) for issue in dq})
    ly_baseline_abnormal = any(flag.startswith("ly_baseline_abnormal_") for flag in flags)

    return StoreWeekPayload(
        store_alias=anonymiser.encode(str(feature_values["Store Name"])),
        year=int(feature_values["Year"]),
        week=int(feature_values["Week"]),
        kpis=_metric_dict(feature_values, ALL_METRICS),
        yoy=_metric_dict(feature_values, [f"{metric}_yoy" for metric in ALL_METRICS], strip_suffix="_yoy"),
        network_median=_metric_dict(
            reference_values,
            [f"{metric}_median" for metric in ALL_METRICS],
            strip_suffix="_median",
        ),
        network_mad=_metric_dict(
            reference_values,
            [f"{metric}_mad" for metric in ALL_METRICS],
            strip_suffix="_mad",
        ),
        store_vs_network=_store_vs_network(feature_values, reference_values),
        driver_attribution=_metric_dict(
            feature_values,
            [f"{metric}_share_pct" for metric in DRIVER_METRICS],
            strip_suffix="_share_pct",
        ),
        flags=flags,
        dq_caveats=dq_caveats,
        ly_baseline_abnormal=ly_baseline_abnormal,
    )


def _coerce_mapping(row: pd.Series | dict[str, object]) -> dict[str, object]:
    if isinstance(row, pd.Series):
        return row.to_dict()
    return dict(row)


def _metric_dict(
    values: dict[str, object],
    keys: list[str],
    *,
    strip_suffix: str | None = None,
) -> dict[str, float | None]:
    output: dict[str, float | None] = {}
    for key in keys:
        name = key.removesuffix(strip_suffix) if strip_suffix else key
        output[name] = _round_numeric(values.get(key))
    return output


def _store_vs_network(
    feature_values: dict[str, object],
    reference_values: dict[str, object],
) -> dict[str, float | None]:
    output: dict[str, float | None] = {}
    for metric in ALL_METRICS:
        key = f"{metric}_vs_network"
        if key in feature_values:
            output[metric] = _round_numeric(feature_values.get(key))
            continue

        metric_value = feature_values.get(metric)
        network_median = reference_values.get(f"{metric}_median")
        if _is_missing(metric_value) or _is_missing(network_median):
            output[metric] = None
        else:
            output[metric] = _round_numeric(float(metric_value) - float(network_median))
    return output


def _dq_caveat(issue: object) -> str:
    if isinstance(issue, str):
        return issue

    if is_dataclass(issue):
        issue_values = asdict(issue)
    elif hasattr(issue, "__dict__"):
        issue_values = dict(vars(issue))
    else:
        return str(issue)

    kind = issue_values.get("kind")
    message = issue_values.get("message")
    if kind and message:
        return f"{kind}: {message}"
    if kind:
        return str(kind)
    if message:
        return str(message)
    return str(issue)


def _round_numeric(value: object) -> float | None:
    if _is_missing(value):
        return None
    return round(float(value), ROUND_DIGITS)


def _is_missing(value: object) -> bool:
    return value is None or pd.isna(value)


def extract_flagged_kpis(flags: list[str]) -> list[str]:
    """Return KPI names extracted from anomaly flag strings."""
    kpis: list[str] = []
    for flag in flags:
        for prefix in ("ly_baseline_abnormal_", "current_week_anomalous_"):
            if flag.startswith(prefix):
                kpis.append(flag[len(prefix):])
                break
    return kpis
