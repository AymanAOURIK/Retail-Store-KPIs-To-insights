from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def weekly_kpi_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Store Name": "Store_A",
                "Year": 2025,
                "Week": 20,
                "traffic": 100,
                "gross_transactions": 45,
                "gross_quantity": 80,
                "net_sales": 1000.25,
            },
            {
                "Store Name": "Store_B",
                "Year": 2025,
                "Week": 21,
                "traffic": 120,
                "gross_transactions": 50,
                "gross_quantity": 90,
                "net_sales": 1400.75,
            },
        ]
    )
