# Implementation plan — Yoobic Insight

End-to-end build plan agreed after the Council review (REVISE, 5 conditions) and the Codex adversarial review (3 high-severity findings). Phases are sequenced so every phase ends with a verifiable gate. Codex executes; the human reviews each commit before the next phase starts.

> Status legend: ✅ done · 🟡 in progress / awaiting commit · ⬜ not started

---

## Phase 0 — Hygiene & truth-up 🟡

**Status:** changes applied; KPI dataset untracked; `.gitignore` updated; instruction files corrected; awaiting the housekeeping commit.

**Goal:** stop the dataset privacy leak, make every instruction file match the actual repo state, and tighten permission allowlists so nothing risky is auto-approved.

**Files to create / modify:**
- `.gitignore` — append `data/raw/*.xlsx`, `data/raw/*.csv`, `data/raw/*.xls` block.
- `CLAUDE.md` — strip claims about non-existent modules; describe current skeleton + intended end-state with a banner; reference `docs/build_status.md`.
- `AGENTS.md` — replace the false "data/raw is gitignored" line with the truthful current state.
- `docs/agent_permissions.md` — remove `python -m yoobic_insight.eval` and `jupyter nbconvert --execute …` from the standing allowlist; move them to per-invocation approval.
- `docs/build_status.md` — new file, tracks per-phase status (this plan's status legend).
- `data/raw/practical-test-dataset-weekly-kpi.xlsx` — `git rm --cached` (keeps local copy).
- `.claude/settings.json` / `.claude/settings.local.json` — confirm no eval / notebook auto-approve rules remain.

**Exact scope:** documentation + git index hygiene only. **No source code, no logic.**

**Validation commands:**
```bash
git ls-files | grep -i 'practical-test-dataset' && echo "STILL TRACKED" || echo "untracked OK"
git check-ignore -v data/raw/practical-test-dataset-weekly-kpi.xlsx
git status --short
```

**Commit message suggestion:**
```
chore: phase 0 — untrack KPI dataset, gitignore data/raw, truth-up agent contracts
```

**Exit gate:**
- `git ls-files` does not include the xlsx.
- `.gitignore` actively masks `data/raw/*.xlsx`.
- No instruction file claims a module that doesn't exist.
- No standing allowlist auto-approves API-calling or notebook-executing commands.

---

## Phase 1 — Environment & EDA notebook ⬜

**Goal:** prove we can read the dataset, validate `Net Sales ≈ Traffic × CR × UPT × AUP`, surface the Store_G W21 violation by hand, and lock down constants (e.g., identity tolerance) for later phases.

**Files to create / modify:**
- `requirements.txt` — pinned: pandas, numpy, pydantic>=2, openai, streamlit, pyyaml, python-dotenv, pytest, jupyter, openpyxl.
- `.env.example` — `OPENAI_API_KEY=`, `OPENAI_MODEL=gpt-4o-mini`, `JUDGE_MODEL=gpt-4o`, `YOOBIC_DATA_PATH=data/raw/practical-test-dataset-weekly-kpi.xlsx`.
- `notebooks/EDA.ipynb` — 5 sections: schema, identity check, coverage, Store_G W21 violation, network distributions.
- `docs/eda_summary.md` — bullet findings, one paragraph per notebook section. **Source of truth** for any constant used later.

**Exact scope:** read-only exploration, summary doc, dependencies pinned. No `src/yoobic_insight/` changes.

**Validation commands:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute notebooks/EDA.ipynb --output notebooks/EDA.ipynb
```

**Commit message suggestion:**
```
chore(phase-1): pin deps, add .env.example, EDA notebook + summary
```

**Exit gate:**
- Notebook executes end-to-end without errors.
- `docs/eda_summary.md` documents row count, identity drift distribution, coverage gaps, Store_G W21 details, network medians/MADs.
- All numeric constants the code will rely on (identity tolerance, MAD threshold default) are written down in the summary.

---

## Phase 2 — `loader.py` + DQ validation ⬜

**Council condition:** #4 (surface Store_G 2025 W21).

**Goal:** load the xlsx into a tidy DataFrame and emit DQ issues — including the one expected violation.

**Files to create / modify:**
- `src/yoobic_insight/loader.py` — pure functions:
  - `load_weekly_kpi(path: Path) -> pd.DataFrame`
  - `validate(df: pd.DataFrame) -> list[DQIssue]`
  - `DQIssue` dataclass: `(store, year, week, kind, message)`. **Not Pydantic** (Council #1: Pydantic stays at the LLM boundary only).
- `tests/test_loader.py` — in-memory frames only, never reads the real xlsx.
- `tests/conftest.py` — shared fixtures (synthetic frames).

**Exact scope:** I/O + validation only. No feature engineering, no anomaly logic.

**Validation commands:**
```bash
pytest tests/test_loader.py -v
python -c "from yoobic_insight.loader import load_weekly_kpi, validate; \
  df = load_weekly_kpi('data/raw/practical-test-dataset-weekly-kpi.xlsx'); \
  issues = validate(df); \
  print([i for i in issues if i.kind == 'gross_transactions_exceeds_traffic'])"
```

**Commit message suggestion:**
```
feat(loader): xlsx loader + DQ validator surfacing Store_G 2025 W21
```

**Exit gate:**
- `pytest tests/test_loader.py` green.
- `validate()` returns at least one `gross_transactions_exceeds_traffic` for Store_G 2025 W21.
- No test reads the real xlsx; no test hits the API.

---

## Phase 3 — `features.py` + `decomposition.py` ⬜

**Council condition:** #3 (like-for-like YoY = intersection of weeks per store).

**Goal:** compute current KPIs, YoY deltas (intersection-window), network medians/MADs, store-vs-network gaps, and log-additive driver attribution. All pure functions.

**Files to create / modify:**
- `src/yoobic_insight/features.py`:
  - `compute_kpi_tree(df) -> pd.DataFrame`
  - `compute_yoy(df) -> pd.DataFrame`
  - `compute_network_reference(df) -> pd.DataFrame`
  - `compute_store_vs_network(df, ref) -> pd.DataFrame`
  - `percentile_rank_in_network(df, ref) -> pd.DataFrame`
- `src/yoobic_insight/decomposition.py`:
  - `decompose_yoy_log_additive(curr, prev) -> pd.DataFrame`
- `tests/test_features.py`, `tests/test_decomposition.py`.

**Exact scope:** numeric features only. **No anomaly flagging, no Pydantic, no I/O.** YoY uses **set-intersection per store**, not a global `week ≤ 48` mask.

**Validation commands:**
```bash
pytest tests/test_features.py tests/test_decomposition.py -v
```

**Commit message suggestion:**
```
feat(features): KPI tree, like-for-like YoY, network reference, log-additive decomposition
```

**Exit gate:**
- Algebraic tests pass: synthetic row where only traffic moves → 100% attribution to traffic.
- Intersection-window test passes: store with weeks {1,2,3} in 2024 and {1,3} in 2025 → only weeks 1 and 3 produce YoY rows.
- `pytest` green.

---

## Phase 4 — `anomalies.py` ⬜

**Council condition:** #3 (MAD=0 fallback). **Assignment hidden requirement:** LY-baseline abnormality flag.

**Goal:** flag (a) current-week anomalies vs the store's own pre-W history, and (b) cases where last year's same-week value was itself an outlier in *its* contemporaneous network.

**Files to create / modify:**
- `src/yoobic_insight/anomalies.py`:
  - `modified_zscore(values: np.ndarray) -> np.ndarray` — `0.6745*(x-median)/MAD`; MAD=0 falls back to abs deviation; 0/0 returns 0.
  - `flag_current_week(df, store, year, week) -> list[Tag]` — uses only data with `(year, week) <= (year, week)` for that store.
  - `flag_ly_baseline(df, store, year, week) -> list[Tag]` — scores LY same-week against the contemporaneous LY network.
- `tests/test_anomalies.py`.

**Exact scope:** anomaly detection only. **No tag templating** (that is Phase 6). No-leakage rule is enforced by signature + tests.

**Validation commands:**
```bash
pytest tests/test_anomalies.py -v
```

**Commit message suggestion:**
```
feat(anomalies): current-week + LY-baseline MAD flags with no-leakage guard
```

**Exit gate:**
- Synthetic outlier flagged; constant series not flagged; MAD=0 case doesn't crash.
- LY-only abnormality test passes (Store_G W in 2024 is the network outlier → 2025 Store_G W gets `ly_baseline_abnormal_<kpi>`).
- `pytest` green.

---

## Phase 5 — `payload.py` (Pydantic boundary) ⬜

**Council condition:** #1 (input AND output Pydantic models live in `payload.py` only).

**Goal:** the single Pydantic boundary between deterministic Python and the LLM. Anonymise stores deterministically.

**Files to create / modify:**
- `src/yoobic_insight/payload.py`:
  - `class StoreWeekPayload(BaseModel)` with `extra="forbid"` — fields: `store_alias, year, week, kpis, yoy, network_median, network_mad, store_vs_network, driver_attribution, flags, dq_caveats, has_ly_baseline`.
  - `class NarrativeResult(BaseModel)` — `text, source: Literal["llm","fallback"], model, tags_used`.
  - `class Anonymiser` — deterministic `encode/decode` (sorted store names → STORE_01…STORE_10).
  - `def build_payload(features_row, ref_row, anomalies, dq, anonymiser) -> StoreWeekPayload`.
- `tests/test_payload.py`.

**Exact scope:** schema + builder + anonymiser. **No prompt construction, no API calls.** Numbers rounded to 4 dp for stable eval comparisons.

**Validation commands:**
```bash
pytest tests/test_payload.py -v
```

**Commit message suggestion:**
```
feat(payload): Pydantic StoreWeekPayload + NarrativeResult + deterministic Anonymiser
```

**Exit gate:**
- Extra fields rejected by Pydantic.
- Anonymiser round-trips; same input → same alias across processes.
- `pytest` green.

---

## Phase 6 — `tags.py` (deterministic headlines) ⬜

**Council condition:** #2 (two-stage chain: features → tags → narrative).

**Goal:** turn a payload into a deterministic, sorted list of tags. The LLM will narrate these — never invent its own.

**Files to create / modify:**
- `src/yoobic_insight/tags.py`:
  - `Tag` dataclass: `(id, severity, kpi, message_template)`.
  - `generate_tags(payload: StoreWeekPayload) -> list[Tag]`.
  - Rule examples: `sales_yoy_strong_decline`, `traffic_drove_decline`, `ly_baseline_suspect_<kpi>`, `dq_caveat_<id>`, `network_underperform_<kpi>`.
- `tests/test_tags.py`.

**Exact scope:** pure if/else over the payload. **No LLM, no I/O.** Tags sorted by `(severity, id)` for determinism.

**Validation commands:**
```bash
pytest tests/test_tags.py -v
```

**Commit message suggestion:**
```
feat(tags): deterministic headline generator from StoreWeekPayload
```

**Exit gate:**
- Golden inputs → exact tag list.
- Toggling payload fields toggles the right tags.
- `pytest` green.

---

## Phase 7 — `llm.py` + `narrative.py` ⬜

**Council conditions:** #1, #2, #5 (simple narrative output: text + source).

**Goal:** the only place that calls OpenAI; always falls back to a rule-based narrative when no key / network failure.

**Files to create / modify:**
- `src/yoobic_insight/llm.py`:
  - `class LLMUnavailableError(Exception)`.
  - `class LLMClient` — `__init__(api_key, model)`; `chat(system, user, max_tokens) -> str`; raises `LLMUnavailableError` on missing key, network failure, rate-limit. No retries, no caching.
- `src/yoobic_insight/narrative.py`:
  - `narrate(payload, tags, client) -> NarrativeResult`.
  - `_rule_based_narrative(payload, tags) -> NarrativeResult` — stitches templated sentences from tags.
  - `_build_prompt(payload, tags) -> tuple[str, str]` — reads system prompt from `eval/prompts/v1_narrative.md`.
- `eval/prompts/v1_narrative.md` — versioned system prompt + 2 few-shot examples; rule "narrate the listed tags only — never invent numbers."
- `tests/test_narrative.py` — stubs `LLMClient`; never hits the API.

**Exact scope:** LLM wrapper + two-stage chain + fallback. **No eval logic.**

**Validation commands:**
```bash
pytest tests/test_narrative.py -v
```

**Commit message suggestion:**
```
feat(narrative): two-stage tag→LLM chain with deterministic fallback
```

**Exit gate:**
- Stubbed client → `source="llm"`.
- `client=None` → `source="fallback"`.
- Stub raising `LLMUnavailableError` → graceful fallback.
- `pytest` green.

---

## Phase 8 — `judge.py` + golden set + eval report ⬜

**Council condition:** #5 (concrete pass-rate target, defined deterministic checks).

**Goal:** automated quality bar. Config C ≥ 85% on deterministic checks must be enforced, otherwise the build fails.

**Files to create / modify:**
- `src/yoobic_insight/judge.py`:
  - `numeric_grounding(payload, narrative_text) -> CheckResult` — every `\d+(\.\d+)?%?` in text appears in payload within 1%.
  - `tag_coverage(tags, narrative_text) -> CheckResult` — each high-severity tag mentioned by keyword or KPI name.
  - `no_hallucinated_flags(tags, narrative_text) -> CheckResult` — claim words ("declined", "anomalous", "unusual") only when a backing tag exists.
  - `llm_judge(payload, narrative_text, judge_client) -> CheckResult` — optional, gpt-4o; quality grade only.
  - `evaluate_golden_set(path) -> EvalReport`.
- `src/yoobic_insight/eval.py` — `__main__` entry: `python -m yoobic_insight.eval`. Exits non-zero if Config C deterministic pass-rate < 85%.
- `eval/golden_set.yaml` — 12 scenarios. **Must include:**
  - Store_G 2025 W21 (DQ caveat scenario) — Council #4.
  - LY-baseline abnormal but current week normal.
  - All-green (sanity).
  - Early-2024 weeks (no LY baseline available, `has_ly_baseline=False`).
- `eval/reports/eval_v1.md` — generated artifact; columns: scenario id, pass/fail per check, narrative excerpt.
- `tests/test_judge.py`.

**Exact scope:** evaluation harness. **No UI.**

**Validation commands:**
```bash
pytest tests/test_judge.py -v
python -m yoobic_insight.eval     # writes eval/reports/eval_v1.md, exits 0 iff ≥ 85%
```

**Commit message suggestion:**
```
feat(eval): judge + 12-scenario golden set + Config C ≥ 85% gate
```

**Exit gate:**
- Smoke-test with `client=None` (fallback narratives) wires up cleanly.
- Real run with API key: pass-rate ≥ 85% deterministic.
- `eval/reports/eval_v1.md` contains the Store_G W21 scenario, passing its DQ-caveat check.

---

## Phase 9 — Streamlit UI ⬜

**Goal:** a local, single-page demo that proves the pipeline end-to-end and includes the transparency panel.

**Files to create / modify:**
- `app/streamlit_app.py`:
  - Sidebar selectors: store, year, week (defaults to last available week).
  - KPI cards row: Net Sales, Traffic, CR, UPT, AUP — current value, YoY %, network-median delta, coloured arrows.
  - One trend chart: store KPI vs network median over last N weeks.
  - Narrative card: 3–5 lines + badge (`LLM ✓` or `Fallback`).
  - Expandable: **"What was sent to the LLM"** — pretty-printed `StoreWeekPayload` JSON.
  - Expandable: tags raised with severity colours.
  - Footer: latest eval pass-rate, commit SHA, model name.
- `@st.cache_data` on the loader; `@st.cache_resource` on the anonymiser.

**Exact scope:** UI only — imports `src/yoobic_insight` directly. **No HTTP layer, no auth.**

**Validation commands (manual):**
```bash
streamlit run app/streamlit_app.py
# → http://localhost:8501
# Click Store_G W21 → DQ caveat in narrative
# Click an early-2024 week → no LY baseline indicator
# Unset OPENAI_API_KEY → fallback badge appears
```

**Commit message suggestion:**
```
feat(app): Streamlit demo with KPI cards, trend chart, narrative + transparency panel
```

**Exit gate:**
- All three manual scenarios reproduce.
- App renders with and without `OPENAI_API_KEY`.

---

## Phase 10 — README + writeup ⬜

**Goal:** a colleague can clone, follow README, and have the UI running in under 10 minutes.

**Files to create / modify:**
- `README.md` — run instructions, screenshots (Store_G W21, LY-baseline anomaly, transparency panel), value pitch, reason-to-believe (deterministic flags + transparency panel + anonymisation), v1 vs roadmap table, eval plan, **honest privacy note** (alias map, dataset gitignored going forward, historical commit acknowledged).
- `docs/prd.md` — 1 page.
- `docs/handoff_brief.md` — 1 page.
- `docs/privacy_note.md` — 1 page.
- `docs/eda_summary.md` — already created in Phase 1; reference from README.

**Exact scope:** documentation only.

**Validation commands:** manual review. Try the cold-clone test on a second machine if available.

**Commit message suggestion:**
```
docs: README, PRD, handoff brief, privacy note + screenshots
```

**Exit gate:** cold-clone test succeeds.

---

## Phase 11 — Final verification ⬜

**Goal:** the whole pipeline passes its own gates.

**Validation commands:**
```bash
pytest                                              # all green
python -m yoobic_insight.eval                       # exit 0, pass-rate ≥ 85%
streamlit run app/streamlit_app.py                  # UI loads, 3 screenshot scenarios reproduce
git status --short                                  # clean
git ls-files | grep -i 'practical-test-dataset'     # empty
```

**Manual checklist:**
- [ ] No tracked xlsx.
- [ ] Every section in CLAUDE.md is backed by code in the checkout (or marked roadmap).
- [ ] AGENTS.md privacy claim matches reality.
- [ ] `docs/agent_permissions.md` does not auto-approve API-calling or notebook-executing commands.
- [ ] `eval/reports/eval_v1.md` shows Store_G W21 scenario passing its DQ-caveat check.
- [ ] README screenshots match what the app actually renders.

**Exit gate:** all of the above.

---

## Sequencing summary

| Phase | Output | Estimated effort | Council conditions | Codex findings |
|---|---|---|---|---|
| 0 | Hygiene & truth-up | 30 min | — | all 3 |
| 1 | EDA notebook + env | 45 min | — | — |
| 2 | `loader.py` + DQ | 45 min | #4 | — |
| 3 | `features.py` + `decomposition.py` | 1.5 h | #3 | — |
| 4 | `anomalies.py` | 1 h | #3 | — |
| 5 | `payload.py` | 45 min | #1 | — |
| 6 | `tags.py` | 45 min | #2 | — |
| 7 | `llm.py` + `narrative.py` | 1 h | #1, #2, #5 | — |
| 8 | `judge.py` + golden set + eval | 1.5 h | #5 | — |
| 9 | Streamlit UI | 1.5 h | — | — |
| 10 | README + writeup | 1 h | — | — |
| 11 | Verification | 30 min | all | all |

Total: ~11 hours of focused work.

---

## Out of scope (deferred to roadmap)

- Agentic next-steps engine.
- DQ anomaly detection beyond the explicit hard checks.
- Cost-monitoring layer.
- Deployment to Railways / Streamlit Cloud — local only, screenshots in README.
- Notion. GitHub README is the single source.
- Retries / caching / structured outputs in the LLM client.
