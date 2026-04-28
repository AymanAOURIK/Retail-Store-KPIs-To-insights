# Screenshot Capture Guide

Run `streamlit run app/streamlit_app.py` and capture these four screens.
Save each as a PNG in this directory with the exact filename shown.

## 1. `main_view.png`
Select any store + week with a generated narrative visible.
Shows: KPI cards, trend chart, and the 3–5 line narrative in the box below.

## 2. `dq_caveat_store_g_w21.png`
Select **Store_G**, year **2025**, week **21**, then click Generate narrative.
Shows: the DQ caveat warning that gross_transactions > traffic (CR > 100%).

## 3. `ly_baseline_anomaly.png`
Select any store-week where the "LY baseline abnormal" tag fires.
(Try Store_G 2024 weeks or any store with a large modified z-score in LY.)
Shows: narrative text that mentions the prior-year value was itself unusual.

## 4. `transparency_panel.png`
Expand the "What was sent to the LLM" panel for any store-week.
Shows: the structured JSON payload, tags, and caveats.
