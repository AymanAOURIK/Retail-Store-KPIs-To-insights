# Yoobic Store Insight

Yoobic Store Insight is a feasibility prototype that turns weekly store KPI data into a transparent narrative a store manager can scan quickly. The product hypothesis is narrow: deterministic preprocessing can make LLM-generated commentary reliable enough to review, audit, and hand off to ML Engineering.

## Why a store manager would care

A store manager does not need another dashboard tab full of raw numbers. They need a fast weekly readout of what moved, what likely drove it, and whether the baseline itself looks suspicious. This prototype focuses on that operating need:

- call out material week-level issues quickly
- explain whether traffic, conversion, UPT, or price drove the YoY move
- show the supporting numbers and flags beside the narrative
- keep data-quality caveats visible instead of hiding them in the background

## Reason to believe

- `Deterministic flags`: anomaly checks, DQ checks, YoY calculations, and driver attribution happen before any LLM step.
- `Transparency panel`: the UI exposes payload values, tags, flags, and caveats so a reviewer can inspect the basis for the wording.
- `Anonymisation`: the LLM boundary receives deterministic store aliases such as `STORE_01`, not raw store names.

## Local run

The app is intended to run locally against the workbook at `data/raw/practical-test-dataset-weekly-kpi.xlsx`.

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

The editable install registers `yoobic_insight` as a package so `python -m yoobic_insight.eval` and `streamlit run app/streamlit_app.py` both work without setting `PYTHONPATH`.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with at least:

- `OPENAI_API_KEY=` if you want live LLM narration
- `OPENAI_MODEL=gpt-4o-mini`
- `JUDGE_MODEL=gpt-4o`
- `YOOBIC_DATA_PATH=data/raw/practical-test-dataset-weekly-kpi.xlsx`

If `OPENAI_API_KEY` is blank, the app falls back to the deterministic rule-based narrative when the user clicks **Generate narrative**.

### 4. Run the Streamlit demo

```bash
streamlit run app/streamlit_app.py
```

The narrative is only generated when the user clicks **Generate narrative** in the UI; selecting a store-week does not trigger an LLM call. This keeps cost predictable and makes it explicit when the LLM boundary is exercised.

## Demo screenshots still needed

Do not fabricate these. Capture them from a local run of the app.

- `Store_G 2025 W21`: show the data-quality caveat where `gross_transactions > traffic`.
- `LY baseline anomaly case`: show a case where last year's same-week baseline is flagged as abnormal.
- `Transparency panel`: show the supporting payload, tags, flags, and caveats visible in the UI.

## Evaluation plan

The current deterministic evaluation report is in [eval/reports/eval_v1.md](eval/reports/eval_v1.md). The working bar for the prototype is Config C deterministic pass rate `>= 85%`; the current checked-in report shows `100.0%` against the deterministic checks.

To exercise the LLM path end-to-end, run:

```bash
python -m yoobic_insight.eval --require-llm
```

The eval CLI prints `Narrative sources: llm=N, fallback=M` so the operator can see which path each scenario used. Without `--require-llm`, missing credentials fall back transparently.

Evaluation intent:

- keep deterministic checks as the primary gate for factual grounding
- add LLM judge review only when a separate judge model is available
- expand scenarios around DQ caveats, LY-baseline anomalies, and low-signal normal weeks

## V1 vs roadmap

| Area | V1 in repo | Roadmap |
|---|---|---|
| Data source | Single local xlsx workbook | Controlled ingestion from approved sources |
| Narrative generation | Local deterministic pipeline plus optional LLM narration | Hardened prompt/versioning, broader scenario coverage |
| Privacy handling | Raw workbook stays local; aliases sent to LLM boundary | Formal privacy review, stricter data contracts, alias-map handling policy |
| UI | Single Streamlit demo for store-week exploration | Production-grade UX, role-based views, better export/share flows |
| Evaluation | Deterministic golden scenarios in repo | Larger eval suite, human review loop, regression dashboard |
| Operations | Manual local run | ML Engineering ownership and managed deployment path |

## Privacy note

This prototype is not presented as privacy-complete. The current honest state is:

- raw KPI files under `data/raw/` are gitignored going forward and should remain local-only
- the repository acknowledges a historical commit where the workbook was tracked before the hygiene fix
- store names are aliased at the LLM boundary so serialized payloads use `STORE_XX` identifiers rather than raw names

More detail is in [docs/privacy_note.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/privacy_note.md).

## Supporting docs

- [docs/prd.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/prd.md)
- [docs/handoff_brief.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/handoff_brief.md)
- [docs/privacy_note.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/privacy_note.md)
- [docs/eda_summary.md](/mnt/c/Users/LENOVO/desktop/Yoobic_Assignment/docs/eda_summary.md)
