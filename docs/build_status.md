# Build Status

| Phase | Status |
|---|---|
| 0 — Hygiene & truth-up | done |
| 1 — Environment & EDA notebook | done |
| 2 — `loader.py` + DQ validation | done |
| 3 — `features.py` + `decomposition.py` | done |
| 4 — `anomalies.py` | done |
| 5 — `payload.py` (Pydantic boundary) | done |
| 6 — `tags.py` | done |
| 7 — `llm.py` + `narrative.py` | done |
| 8 — `judge.py` + golden set + eval report | done |
| 9 — Streamlit UI (button-gated LLM call) | done |
| 10 — README + writeup | done |
| 11 — Final verification | pending — see notes |

## Verification status

- `pytest -q` — green (39 passed).
- `python -m yoobic_insight.eval` — exits 0; deterministic pass rate 100% on the 12-scenario golden set. Mode is reported in stdout (`Narrative sources: …`).
- LLM-mode validation — requires running locally with `OPENAI_API_KEY` set; deterministic gate is independent and runs in fallback mode by default.
- App boots locally via `streamlit run app/streamlit_app.py`; LLM narration only fires when **Generate narrative** is clicked.
- Dataset is gitignored. A historical commit still contains the workbook; this is documented in `docs/privacy_note.md`.

## Open items before declaring complete

- Capture three Phase-9 screenshots (Store_G W21 caveat, LY-baseline anomaly, transparency panel) into `screenshots/` and link them in `README.md`.
- Run `python -m yoobic_insight.eval --require-llm` with a live `OPENAI_API_KEY` and confirm the report shows `source="llm"` rows.
- Decide whether to rewrite git history to purge the historical workbook commit (destructive — coordinate before doing).
