from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from retails_insight.loader import DQIssue, EXPECTED_COLUMNS, load_weekly_kpi, validate


def test_load_weekly_kpi_reads_expected_columns(tmp_path: Path, weekly_kpi_frame: pd.DataFrame) -> None:
    workbook_path = tmp_path / "weekly-kpi.xlsx"
    weekly_kpi_frame.to_excel(workbook_path, index=False)

    loaded = load_weekly_kpi(workbook_path)

    assert loaded.columns.tolist() == EXPECTED_COLUMNS
    pd.testing.assert_frame_equal(loaded, weekly_kpi_frame)


def test_load_weekly_kpi_rejects_missing_columns(tmp_path: Path, weekly_kpi_frame: pd.DataFrame) -> None:
    workbook_path = tmp_path / "weekly-kpi.xlsx"
    weekly_kpi_frame.drop(columns=["net_sales"]).to_excel(workbook_path, index=False)

    with pytest.raises(ValueError, match="missing required columns: net_sales"):
        load_weekly_kpi(workbook_path)


def test_validate_returns_no_issues_for_clean_frame(weekly_kpi_frame: pd.DataFrame) -> None:
    assert validate(weekly_kpi_frame) == []


def test_validate_flags_duplicate_store_year_week(weekly_kpi_frame: pd.DataFrame) -> None:
    duplicate = pd.concat([weekly_kpi_frame, weekly_kpi_frame.iloc[[0]]], ignore_index=True)

    issues = validate(duplicate)

    assert issues.count(
        DQIssue(
            store="Store_A",
            year=2025,
            week=20,
            kind="duplicate_store_year_week",
            message="Duplicate (Store Name, Year, Week) key.",
        )
    ) == 2


def test_validate_flags_missing_values(weekly_kpi_frame: pd.DataFrame) -> None:
    frame = weekly_kpi_frame.copy()
    frame.loc[1, "gross_quantity"] = None
    frame.loc[1, "net_sales"] = None

    assert validate(frame) == [
        DQIssue(
            store="Store_B",
            year=2025,
            week=21,
            kind="missing_value",
            message="Missing values in columns: gross_quantity, net_sales.",
        )
    ]


def test_validate_flags_gross_transactions_exceeds_traffic(weekly_kpi_frame: pd.DataFrame) -> None:
    frame = weekly_kpi_frame.copy()
    frame.loc[1, "traffic"] = 65
    frame.loc[1, "gross_transactions"] = 87

    issues = validate(frame)

    assert issues == [
        DQIssue(
            store="Store_B",
            year=2025,
            week=21,
            kind="gross_transactions_exceeds_traffic",
            message="gross_transactions (87) exceeds traffic (65).",
        )
    ]
