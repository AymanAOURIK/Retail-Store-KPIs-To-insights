from __future__ import annotations

import json
import os
import re
import subprocess
import html
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from yoobic_insight.anomalies import flag_current_week, flag_ly_baseline
from yoobic_insight.decomposition import DRIVER_METRICS, decompose_yoy_log_additive
from yoobic_insight.features import compute_kpi_tree, compute_network_reference, compute_store_vs_network, compute_yoy
from yoobic_insight.llm import LLMClient, LLMUnavailableError
from yoobic_insight.loader import DQIssue, load_weekly_kpi, validate
from yoobic_insight.narrative import narrate
from yoobic_insight.payload import Anonymiser, StoreWeekPayload, build_payload
from yoobic_insight.tags import Tag, generate_tags

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "practical-test-dataset-weekly-kpi.xlsx"
EVAL_REPORT_PATH = PROJECT_ROOT / "eval" / "reports" / "eval_v1.md"
TREND_WINDOW_WEEKS = 12

KPI_CONFIG = [
    {
        "label": "Net Sales",
        "metric": "net_sales",
        "format": "currency0",
        "network_label": "vs median",
    },
    {
        "label": "Traffic",
        "metric": "traffic",
        "format": "int",
        "network_label": "vs median",
    },
    {
        "label": "CR",
        "metric": "conversion_rate",
        "format": "pct1",
        "network_label": "vs median",
    },
    {
        "label": "UPT",
        "metric": "units_per_txn",
        "format": "float2",
        "network_label": "vs median",
    },
    {
        "label": "AUP",
        "metric": "avg_selling_price",
        "format": "currency2",
        "network_label": "vs median",
    },
]

TREND_OPTIONS = {
    "Net Sales": "net_sales",
    "Traffic": "traffic",
    "CR": "conversion_rate",
    "UPT": "units_per_txn",
    "AUP": "avg_selling_price",
}

SEVERITY_STYLES = {
    1: ("High", "#9f1239", "#ffe4e6"),
    2: ("Medium", "#9a3412", "#ffedd5"),
    3: ("Low", "#1d4ed8", "#dbeafe"),
}


@st.cache_data(show_spinner=False)
def load_app_data(dataset_path: str) -> dict[str, object]:
    raw_df = load_weekly_kpi(dataset_path)
    dq_issues = validate(raw_df)
    kpi_df = compute_kpi_tree(raw_df)
    ref_df = compute_network_reference(raw_df)
    store_vs_network_df = compute_store_vs_network(raw_df, ref_df)
    yoy_df = compute_yoy(raw_df)
    return {
        "raw_df": raw_df,
        "dq_issues": dq_issues,
        "kpi_df": kpi_df,
        "ref_df": ref_df,
        "store_vs_network_df": store_vs_network_df,
        "yoy_df": yoy_df,
    }


@st.cache_resource(show_spinner=False)
def get_anonymiser(store_names: tuple[str, ...]) -> Anonymiser:
    return Anonymiser(store_names)


def main() -> None:
    st.set_page_config(page_title="Yoobic Store Insight", layout="wide")
    st.title("Yoobic Store Insight")
    st.caption("Local feasibility demo: deterministic KPI pipeline with transparent LLM narrativisation.")

    dataset_path = resolve_dataset_path()
    if not dataset_path.exists():
        st.error(f"Dataset not found at `{dataset_path}`.")
        return

    try:
        app_data = load_app_data(str(dataset_path))
    except Exception as exc:
        st.error(f"Failed to load weekly KPI data: {exc}")
        return

    raw_df = app_data["raw_df"]
    dq_issues = app_data["dq_issues"]
    store_vs_network_df = app_data["store_vs_network_df"]
    ref_df = app_data["ref_df"]
    yoy_df = app_data["yoy_df"]

    store, year, week = render_sidebar(raw_df)
    selected_row = get_selected_row(store_vs_network_df, store, year, week)
    if selected_row is None:
        st.error("The selected store-week is not present in the KPI table.")
        return

    ref_row = get_reference_row(ref_df, year, week)
    if ref_row is None:
        st.error("The network reference row for the selected week is not available.")
        return

    yoy_row = get_selected_row(yoy_df, store, year, week)
    anonymiser = get_anonymiser(tuple(sorted(raw_df["Store Name"].astype(str).unique())))

    payload = build_store_week_payload(
        raw_df=raw_df,
        dq_issues=dq_issues,
        selected_row=selected_row,
        ref_row=ref_row,
        yoy_row=yoy_row,
        anonymiser=anonymiser,
    )
    tags = generate_tags(payload)
    narrative_result, llm_status = build_narrative(payload, tags)

    render_status_banner(payload, narrative_result.source, llm_status)
    render_kpi_cards(payload)
    render_trend_chart(store_vs_network_df, year, week, store)
    render_narrative(payload, narrative_result, llm_status, ly_available=yoy_row is not None)
    render_transparency_panel(payload, tags)
    render_footer(narrative_result)


def resolve_dataset_path() -> Path:
    env_path = os.getenv("YOOBIC_DATA_PATH")
    if env_path:
        candidate = Path(env_path)
        return candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    return DEFAULT_DATA_PATH


def render_sidebar(raw_df: pd.DataFrame) -> tuple[str, int, int]:
    st.sidebar.header("Selection")

    store_options = sorted(raw_df["Store Name"].astype(str).unique())
    default_store = store_options[-1]
    store = st.sidebar.selectbox("Store", store_options, index=store_options.index(default_store))

    store_df = raw_df.loc[raw_df["Store Name"] == store]
    year_options = sorted(store_df["Year"].astype(int).unique(), reverse=True)
    default_year = year_options[0]
    year = st.sidebar.selectbox("Year", year_options, index=year_options.index(default_year))

    week_options = sorted(
        store_df.loc[store_df["Year"] == year, "Week"].astype(int).unique(),
    )
    default_week = week_options[-1]
    week = st.sidebar.selectbox("Week", week_options, index=week_options.index(default_week))

    st.sidebar.caption(f"Data source: `{resolve_dataset_path()}`")
    return store, int(year), int(week)


def get_selected_row(df: pd.DataFrame, store: str, year: int, week: int) -> pd.Series | None:
    match = df.loc[
        (df["Store Name"] == store) & (df["Year"] == year) & (df["Week"] == week)
    ]
    if match.empty:
        return None
    return match.iloc[0]


def get_reference_row(ref_df: pd.DataFrame, year: int, week: int) -> pd.Series | None:
    match = ref_df.loc[(ref_df["Year"] == year) & (ref_df["Week"] == week)]
    if match.empty:
        return None
    return match.iloc[0]


def build_store_week_payload(
    *,
    raw_df: pd.DataFrame,
    dq_issues: list[DQIssue],
    selected_row: pd.Series,
    ref_row: pd.Series,
    yoy_row: pd.Series | None,
    anonymiser: Anonymiser,
) -> StoreWeekPayload:
    combined_values = selected_row.to_dict()
    if yoy_row is not None:
        for key, value in yoy_row.items():
            if key.endswith("_yoy"):
                combined_values[key] = value
        combined_values.update(_driver_shares(yoy_row))
    else:
        for metric in (
            "traffic",
            "gross_transactions",
            "gross_quantity",
            "net_sales",
            "conversion_rate",
            "units_per_txn",
            "avg_selling_price",
            "avg_txn_value",
            "revenue_per_visitor",
        ):
            combined_values[f"{metric}_yoy"] = None
        for metric in DRIVER_METRICS:
            combined_values[f"{metric}_share_pct"] = None

    store = str(selected_row["Store Name"])
    year = int(selected_row["Year"])
    week = int(selected_row["Week"])
    flags = sorted(
        set(flag_current_week(raw_df, store, year, week) + flag_ly_baseline(raw_df, store, year, week))
    )
    selected_dq = [
        issue
        for issue in dq_issues
        if issue.store == store and issue.year == year and issue.week == week
    ]
    return build_payload(combined_values, ref_row, flags, selected_dq, anonymiser)


def _driver_shares(yoy_row: pd.Series) -> dict[str, float | None]:
    current = pd.Series({metric: yoy_row[f"{metric}_curr"] for metric in DRIVER_METRICS})
    previous = pd.Series({metric: yoy_row[f"{metric}_prev"] for metric in DRIVER_METRICS})
    contributions = decompose_yoy_log_additive(current, previous).iloc[0]
    return {
        f"{metric}_share_pct": contributions.get(f"{metric}_share_pct")
        for metric in DRIVER_METRICS
    }


def build_narrative(payload: StoreWeekPayload, tags: list[Tag]) -> tuple[object, str]:
    try:
        client = LLMClient()
    except LLMUnavailableError as exc:
        client = None
        result = narrate(payload, tags, client)
        return result, f"Fallback active: {exc}"

    result = narrate(payload, tags, client)
    if result.source == "llm":
        return result, f"LLM ready: {client.model}"
    return result, f"Fallback active: {client.model} request failed or was unavailable"


def render_status_banner(payload: StoreWeekPayload, narrative_source: str, llm_status: str) -> None:
    badge_label = "LLM" if narrative_source == "llm" else "Fallback"
    badge_color = "#14532d" if narrative_source == "llm" else "#9a3412"
    badge_bg = "#dcfce7" if narrative_source == "llm" else "#ffedd5"
    st.markdown(
        (
            "<div style='display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin:0.25rem 0 1rem;'>"
            f"<span style='font-weight:700;font-size:1.05rem;'>{payload.store_alias} · {payload.year} W{payload.week}</span>"
            f"<span style='background:{badge_bg};color:{badge_color};padding:0.2rem 0.6rem;border-radius:999px;"
            f"font-weight:700;'>{badge_label}</span>"
            f"<span style='color:#475569;'>{llm_status}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_kpi_cards(payload: StoreWeekPayload) -> None:
    columns = st.columns(len(KPI_CONFIG))
    for column, config in zip(columns, KPI_CONFIG, strict=True):
        metric = config["metric"]
        value = payload.kpis.get(metric)
        yoy = payload.yoy.get(metric)
        gap = payload.store_vs_network.get(metric)
        with column:
            st.markdown(
                f"""
                <div style="border:1px solid #e2e8f0;border-radius:16px;padding:1rem 1rem 0.9rem;background:#ffffff;min-height:160px;">
                  <div style="font-size:0.85rem;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#64748b;">{config["label"]}</div>
                  <div style="font-size:1.7rem;font-weight:800;color:#0f172a;margin:0.35rem 0 0.8rem;">{format_metric_value(value, config["format"])}</div>
                  <div style="margin-bottom:0.35rem;">{format_delta_html("YoY", yoy, percent=True)}</div>
                  <div>{format_delta_html(config["network_label"], gap, percent=False, fmt=config["format"])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_trend_chart(store_vs_network_df: pd.DataFrame, year: int, week: int, store: str) -> None:
    st.subheader("Trend vs Network Median")
    selected_label = st.selectbox("KPI", list(TREND_OPTIONS.keys()), index=0)
    metric = TREND_OPTIONS[selected_label]

    trend_df = build_trend_frame(store_vs_network_df, store, year, week, metric)
    chart = (
        alt.Chart(trend_df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("label:N", sort=alt.SortField(field="sort_key"), title="Year-Week"),
            y=alt.Y("value:Q", title=selected_label),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(
                    domain=["Store", "Network Median"],
                    range=["#0f766e", "#94a3b8"],
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Week"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("formatted_value:N", title=selected_label),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)


def build_trend_frame(
    store_vs_network_df: pd.DataFrame,
    store: str,
    year: int,
    week: int,
    metric: str,
) -> pd.DataFrame:
    store_history = store_vs_network_df.loc[store_vs_network_df["Store Name"] == store].copy()
    store_history["sort_key"] = store_history["Year"] * 100 + store_history["Week"]
    selected_sort_key = year * 100 + week
    window = (
        store_history.loc[store_history["sort_key"] <= selected_sort_key]
        .sort_values(["Year", "Week"])
        .tail(TREND_WINDOW_WEEKS)
        .copy()
    )
    window["label"] = window.apply(lambda row: f"{int(row['Year'])}-W{int(row['Week']):02d}", axis=1)
    long_df = pd.concat(
        [
            pd.DataFrame(
                {
                    "label": window["label"],
                    "sort_key": window["sort_key"],
                    "series": "Store",
                    "value": window[metric],
                }
            ),
            pd.DataFrame(
                {
                    "label": window["label"],
                    "sort_key": window["sort_key"],
                    "series": "Network Median",
                    "value": window[f"{metric}_median"],
                }
            ),
        ],
        ignore_index=True,
    )
    long_df["formatted_value"] = long_df["value"].apply(format_tooltip_value)
    return long_df


def render_narrative(
    payload: StoreWeekPayload,
    narrative_result: object,
    llm_status: str,
    *,
    ly_available: bool,
) -> None:
    source = getattr(narrative_result, "source")
    badge_label = "LLM" if source == "llm" else "Fallback"
    badge_color = "#14532d" if source == "llm" else "#9a3412"
    badge_bg = "#dcfce7" if source == "llm" else "#ffedd5"
    st.subheader("Narrative")
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0;border-radius:18px;padding:1.1rem 1.2rem;background:#f8fafc;">
          <div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.75rem;">
            <span style="background:{badge_bg};color:{badge_color};padding:0.2rem 0.6rem;border-radius:999px;font-weight:700;">{badge_label}</span>
            <span style="color:#475569;">{llm_status}</span>
          </div>
          <div style="font-size:1rem;line-height:1.65;color:#0f172a;">{format_narrative_text(getattr(narrative_result, 'text'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if source == "fallback" and not os.getenv("OPENAI_API_KEY"):
        st.info("`OPENAI_API_KEY` is not set, so the app is using the rule-based fallback narrative.")
    if not ly_available:
        st.caption("No last-year same-week baseline is available for this store-week.")


def render_transparency_panel(payload: StoreWeekPayload, tags: list[Tag]) -> None:
    with st.expander("What was sent to the LLM", expanded=False):
        st.code(json.dumps(payload.model_dump(), indent=2, sort_keys=True), language="json")

    with st.expander("Tags raised", expanded=False):
        if not tags:
            st.write("No deterministic tags were raised for this store-week.")
        for tag in tags:
            severity_label, color, background = SEVERITY_STYLES.get(tag.severity, ("Unknown", "#334155", "#e2e8f0"))
            st.markdown(
                (
                    f"<div style='border:1px solid {background};border-radius:14px;padding:0.8rem 0.9rem;"
                    "margin-bottom:0.7rem;background:#ffffff;'>"
                    f"<div style='display:flex;align-items:center;gap:0.55rem;flex-wrap:wrap;'>"
                    f"<span style='background:{background};color:{color};padding:0.15rem 0.55rem;border-radius:999px;font-weight:700;'>"
                    f"{severity_label}</span>"
                    f"<span style='font-weight:700;color:#0f172a;'>{tag.id}</span>"
                    "</div>"
                    f"<div style='margin-top:0.45rem;color:#334155;'>{tag.message_template}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    with st.expander("DQ caveats", expanded=False):
        if not payload.dq_caveats:
            st.write("No DQ caveats were raised for this store-week.")
        else:
            for caveat in payload.dq_caveats:
                st.warning(caveat)


def render_footer(narrative_result: object) -> None:
    eval_pass_rate = read_eval_pass_rate()
    commit_sha = read_commit_sha()
    model_name = getattr(narrative_result, "model", None) or "rule-based fallback"
    st.divider()
    st.caption(
        f"Eval pass-rate: {eval_pass_rate} | Commit: `{commit_sha}` | Model: `{model_name}`"
    )


def read_eval_pass_rate() -> str:
    if not EVAL_REPORT_PATH.exists():
        return "unavailable"
    match = re.search(
        r"Deterministic pass rate:\s*([0-9]+(?:\.[0-9]+)?%)",
        EVAL_REPORT_PATH.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else "unavailable"


def read_commit_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def format_metric_value(value: float | None, fmt: str) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    number = float(value)
    if fmt == "currency0":
        return f"${number:,.0f}"
    if fmt == "currency2":
        return f"${number:,.2f}"
    if fmt == "int":
        return f"{number:,.0f}"
    if fmt == "pct1":
        return f"{number * 100:.1f}%"
    if fmt == "float2":
        return f"{number:.2f}"
    return f"{number:,.2f}"


def format_tooltip_value(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.2f}"


def format_delta_html(
    label: str,
    value: float | None,
    *,
    percent: bool,
    fmt: str | None = None,
) -> str:
    if value is None or pd.isna(value):
        return f"<span style='color:#64748b;'>{label}: N/A</span>"
    number = float(value)
    arrow = "▲" if number > 0 else "▼" if number < 0 else "■"
    color = "#166534" if number > 0 else "#b91c1c" if number < 0 else "#475569"
    if percent:
        formatted = f"{number * 100:+.1f}%"
    elif fmt in {"currency0", "currency2"}:
        decimals = 0 if fmt == "currency0" else 2
        formatted = f"${number:+,.{decimals}f}"
    elif fmt == "int":
        formatted = f"{number:+,.0f}"
    else:
        formatted = f"{number:+,.2f}"
    return f"<span style='color:#64748b;'>{label}:</span> <span style='color:{color};font-weight:700;'>{arrow} {formatted}</span>"


def format_narrative_text(text: str) -> str:
    return "<br><br>".join(
        html.escape(sentence.strip())
        for sentence in re.split(r"(?<=\.)\s+", text.strip())
        if sentence.strip()
    )


if __name__ == "__main__":
    main()
