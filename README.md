# Yoobic Store Insight

A feasibility prototype that turns weekly store KPI data into a transparent, store-manager-ready narrative. Built as an AI Technical PM assignment.

---

## What it does

A store manager selects their store and week. The app shows KPI cards (net sales, traffic, CR, UPT, avg unit price) with YoY deltas and a gap-to-network-median indicator, a 12-week trend chart vs the network, and a 3–5 line LLM-generated narrative that calls out unusual values, flags suspect YoY baselines, and suggests likely root causes from the store-vs-network signals.

---

## Why a store manager would care

A manager does not need another dashboard full of raw numbers. They need a fast weekly readout of **what moved**, **what likely drove it**, and **whether the baseline itself looks suspicious**. This prototype delivers:

- material week-level issues surfaced in seconds
- YoY driver attribution split across traffic, conversion, UPT, and price
- visible data-quality caveats when a number is physically impossible (e.g. CR > 100%)
- an audit trail — the exact payload and tags sent to the LLM are always one click away

---

## Screenshots

### Main view — store KPIs, trend chart, and narrative

![Main view](screenshots/main_view.png)

### Data-quality caveat — Store_G 2025 W21

Store_G week 21 has `gross_transactions > traffic` (CR ≈ 134%). The app surfaces this as an explicit caveat in the narrative rather than silently narrating an impossible number.

![DQ caveat](screenshots/dq_caveat_store_g_w21.png)

### LY-baseline anomaly case

When last year's same-week value was itself abnormal, the narrative flags it so the YoY comparison is not taken at face value.

![LY baseline anomaly](screenshots/ly_baseline_anomaly.png)

### Transparency panel — what was sent to the LLM

The panel shows the full structured payload, deterministic tags, and any caveats the pipeline raised. Nothing reaches the LLM that did not first go through the deterministic layer.

![Transparency panel](screenshots/transparency_panel.png)

---

## Deterministic-first architecture

All KPI derivation, anomaly detection, YoY logic, network-gap computation, and feature selection happen before the LLM step in a pure-Python deterministic pipeline. The LLM only receives a structured payload and narrates it. This means:

- every number in the narrative is traceable to a specific formula run on the source data
- anomaly flags and DQ caveats are rule-based — the LLM does not decide what is unusual
- the app has a full rule-based fallback narrative if no API key is present
- numeric-grounding checks in the eval harness verify factual accuracy independently of prompt quality

---

## Local run

The app runs locally against `data/raw/practical-test-dataset-weekly-kpi.xlsx` (not committed — add your own copy).

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Minimum `.env` values:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o
YOOBIC_DATA_PATH=data/raw/practical-test-dataset-weekly-kpi.xlsx
```

If `OPENAI_API_KEY` is blank the app falls back to the deterministic narrative automatically.

### 4. Run the app

```bash
streamlit run app/streamlit_app.py
```

The LLM is called only when the user clicks **Generate narrative** — selecting a store-week alone triggers no API call.

---

## Evaluation

```bash
python -m pytest -q                          # deterministic pipeline tests
python -m yoobic_insight.eval                # eval harness (fallback path, no API key needed)
python -m yoobic_insight.eval --require-llm  # force LLM path
```

Current deterministic pass rate: **100%** (see [eval/reports/eval_v1.md](eval/reports/eval_v1.md)).

---

## V1 vs roadmap

| Area | V1 | Roadmap |
|---|---|---|
| Data source | Single local xlsx | Controlled ingestion from approved sources |
| Narrative | Deterministic fallback + optional LLM | Prompt versioning, broader scenario coverage |
| Privacy | Aliases sent to LLM; raw file stays local | Formal privacy review, stricter data contracts |
| UI | Streamlit demo | Production UX, role-based views, export flows |
| Evaluation | Deterministic golden scenarios | Larger suite, human review loop, regression dashboard |
| Operations | Manual local run | ML Engineering ownership, managed deployment |

---

## Privacy

Raw KPI files under `data/raw/` are gitignored and must stay local. Store names are aliased at the LLM boundary (`STORE_01`, `STORE_02`, …) — raw names never cross the API call. See [docs/privacy_note.md](docs/privacy_note.md).

---

## Supporting docs

- [docs/eda_summary.md](docs/eda_summary.md) — findings from exploratory analysis
- [docs/prd.md](docs/prd.md) — product requirements and scope decisions
- [docs/handoff_brief.md](docs/handoff_brief.md) — ML Engineering handoff notes
- [docs/privacy_note.md](docs/privacy_note.md) — privacy handling details
- [eval/reports/eval_v1.md](eval/reports/eval_v1.md) — evaluation report
