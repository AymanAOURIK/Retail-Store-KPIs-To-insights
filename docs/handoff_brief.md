# Handoff Brief

## What is in scope today

The repository contains a working local prototype for weekly retail KPI narrativisation. Phases 0 through 9 are implemented. The deterministic pipeline computes KPIs, like-for-like YoY metrics, network comparisons, anomaly flags, tags, and a typed payload. The UI is a Streamlit demo that can render either LLM-backed text or the rule-based fallback.

## How to run

Use the steps in [README.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/README.md):

1. create `.venv`
2. `pip install -r requirements.txt`
3. copy `.env.example` to `.env` and fill values
4. run `streamlit run app/streamlit_app.py`

The workbook is expected at `data/raw/practical-test-dataset-weekly-kpi.xlsx` unless `YOOBIC_DATA_PATH` overrides it.

## What to demo

- a normal store-week with no major headline tags
- `Store_G 2025 W21` to show the data-quality caveat
- a store-week with an LY-baseline abnormality tag
- the transparency panel to show exactly what supports the narrative

## Screenshots still needed

Capture real screenshots from the running app for:

- `Store_G 2025 W21`
- an LY-baseline anomaly case
- the transparency panel

## Evidence and evaluation

The checked-in deterministic evaluation report is [eval/reports/eval_v1.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/eval/reports/eval_v1.md). It reports a `100.0%` deterministic pass rate against the current golden scenarios, above the Phase target of `85%`.

## Known limits

- local prototype only; no deployment path is included here
- workbook remains the only data source
- privacy posture is improved but not final; see [docs/privacy_note.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/privacy_note.md)
- screenshots are documented as required but are not checked in yet

## Recommended next owner focus

If this prototype is handed to ML Engineering, the next work should center on larger eval coverage, prompt/version controls, and a reviewed privacy/data-contract design rather than UI expansion first.
