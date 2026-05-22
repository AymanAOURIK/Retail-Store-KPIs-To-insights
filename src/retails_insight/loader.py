from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "Store Name",
    "Year",
    "Week",
    "traffic",
    "gross_transactions",
    "gross_quantity",
    "net_sales",
]

KEY_COLUMNS = ["Store Name", "Year", "Week"]


@dataclass(frozen=True)
class DQIssue:
    store: str | None
    year: int | None
    week: int | None
    kind: str
    message: str


def load_weekly_kpi(path: Path | str) -> pd.DataFrame:
    dataset_path = Path(path)
    df = pd.read_excel(dataset_path)
    _require_expected_columns(df)
    return df.loc[:, EXPECTED_COLUMNS].copy()


def validate(df: pd.DataFrame) -> list[DQIssue]:
    _require_expected_columns(df)

    issues: list[DQIssue] = []
    issues.extend(_duplicate_key_issues(df))
    issues.extend(_missing_value_issues(df))
    issues.extend(_gross_transactions_exceed_traffic_issues(df))
    return issues


def _require_expected_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"missing required columns: {missing}")


def _duplicate_key_issues(df: pd.DataFrame) -> list[DQIssue]:
    duplicate_mask = df.duplicated(subset=KEY_COLUMNS, keep=False)
    duplicate_rows = df.loc[duplicate_mask, KEY_COLUMNS]

    issues: list[DQIssue] = []
    for row in duplicate_rows.itertuples(index=False):
        issues.append(
            DQIssue(
                store=str(row[0]),
                year=int(row[1]),
                week=int(row[2]),
                kind="duplicate_store_year_week",
                message="Duplicate (Store Name, Year, Week) key.",
            )
        )
    return issues


def _missing_value_issues(df: pd.DataFrame) -> list[DQIssue]:
    issues: list[DQIssue] = []
    for row in df.loc[:, EXPECTED_COLUMNS].itertuples(index=False, name=None):
        store, year, week, *values = row
        missing_columns = [
            column
            for column, value in zip(EXPECTED_COLUMNS[3:], values, strict=True)
            if pd.isna(value)
        ]
        if missing_columns:
            issues.append(
                DQIssue(
                    store=None if pd.isna(store) else str(store),
                    year=None if pd.isna(year) else int(year),
                    week=None if pd.isna(week) else int(week),
                    kind="missing_value",
                    message=f"Missing values in columns: {', '.join(missing_columns)}.",
                )
            )
    return issues


def _gross_transactions_exceed_traffic_issues(df: pd.DataFrame) -> list[DQIssue]:
    invalid_rows = df.loc[df["gross_transactions"] > df["traffic"], KEY_COLUMNS + ["traffic", "gross_transactions"]]

    issues: list[DQIssue] = []
    for row in invalid_rows.itertuples(index=False):
        issues.append(
            DQIssue(
                store=str(row[0]),
                year=int(row[1]),
                week=int(row[2]),
                kind="gross_transactions_exceeds_traffic",
                message=(
                    f"gross_transactions ({int(row[4])}) exceeds traffic ({int(row[3])})."
                ),
            )
        )
    return issues
