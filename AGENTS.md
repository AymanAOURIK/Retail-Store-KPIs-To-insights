# AGENTS.md — Operating model for Yoobic Store Insight

This file tells AI agents (Codex, Claude Code, etc.) how to work in this repository.
Read it before touching any file. When instructions here conflict with a general coding heuristic, these rules win.

---

## What this repo is

A feasibility prototype: raw retail KPI data → deterministic feature pipeline → LLM narrativisation → Streamlit demo.
The goal is to validate one question: *can deterministic ML pre-processing make LLM narrative generation reliable and auditable enough to hand off to ML Engineering?*

This is not a production service. Optimise for clarity and testability, not scalability.

---

## Useful changes vs not

**Do these:**
- Implement or fix modules within a phase's declared "files to touch" scope.
- Write or extend `pytest` tests for pure functions in `src/yoobic_insight/`.
- Improve deterministic logic (feature engineering, decomposition, anomaly detection).
- Improve tracked files under `eval/` when they exist in the checkout.
- Fix portable path issues — `Path` from project root, never absolute strings.

**Do not do these:**
- Add a database, caching layer, or background job queue. The app is intentionally stateless.
- Add FastAPI or any HTTP wrapper. Keep the prototype as a direct package-driven demo rather than an HTTP service.
- Refactor working phases to add abstraction. Three similar functions beats a premature helper.
- Touch files in `_internal/`. Those are planning docs, gitignored, and not deliverables.
- Commit the dataset (`data/raw/*.xlsx`) or any real `.env` file.
- Add Docker, CI workflows, or deployment config unless explicitly asked.

---

## Architectural boundaries — enforce these

### 1. Deterministic layer (never calls LLM)
The deterministic layer lives under `src/yoobic_insight/`. In the current checkout, only `src/yoobic_insight/__init__.py` is checked in; any future pipeline modules must stay pure and must not call the LLM.

All functions in this layer must be **pure**: same input → same output, no global state, no I/O.
Unit tests must cover them without any network access.

### 2. LLM boundary
When LLM integration files are added, the only code that calls the OpenAI API must live in a dedicated boundary module, and the orchestration layer must own the fallback.

**Privacy invariant:** A typed payload schema must be the single gateway. Real store names must never appear in a serialised payload sent to the LLM. Any change that could route raw data to the LLM boundary needs an explicit privacy review note in the PR.

### 3. Evaluation layer
The evaluation layer lives under `eval/`. In the current checkout, the directories exist but no tracked eval files are present. When the LLM-as-judge is added, `JUDGE_MODEL` must be a different model than `OPENAI_MODEL` to avoid self-bias.

### 4. UI layer
The UI layer belongs in `app/`. The directory exists in the current checkout, but no tracked app file is present yet. No business logic should live in the eventual app entrypoint.

---

## Source-of-truth rules

| Concern | Source of truth |
|---|---|
| Package entrypoint | `src/yoobic_insight/__init__.py` |
| Dataset location | `data/raw/practical-test-dataset-weekly-kpi.xlsx` |
| Notebook analysis | `notebooks/EDA.ipynb` |
| Repo documentation | `CLAUDE.md`, `AGENTS.md`, and files under `docs/` |

When there is a conflict between a doc and the code, fix the code and update the doc — not the reverse.

---

## Persistence model

The app is stateless. No database. The xlsx file is the data source. The audit log (`audit_logs/llm_calls.jsonl`) is append-only and gitignored. Do not introduce session state beyond what Streamlit requires for the current view.

---

## Critical invariants — do not break these

1. **Portable paths only:** Dataset access uses `Path` resolved from the project root. No hardcoded absolute paths.

2. **Dataset privacy:** `data/raw/` stays gitignored. Do not commit the KPI dataset.

3. **No `_internal/` access:** Do not read, reference, or write `_internal/`.

4. **Zero committed secrets:** Do not commit `.env` or API keys.

5. **Goal-driven verification:** Use `pytest` once tests exist in the checkout, and run the eval harness once its tracked files are present.

---

## Testing expectations

- **No test ever calls the OpenAI API.** Use stubs, fixtures, or `client=None`.
- **No test reads the xlsx file.** Use in-memory pandas frames constructed from literals.
- Add module-specific coverage only after the corresponding files are checked in.
- Eval pass-rate target for config C: ≥ 85% on deterministic checks once the eval harness is present.

---

## Quality guardrails

- Portable paths only: all dataset access uses `Path` resolved from the project root. No `C:\Users\...` strings anywhere.
- `_internal/` is gitignored. Agents must not read from, reference, or write to it.
- Zero secrets in committed files. Grep for `sk-` and `OPENAI_API_KEY=sk-` before any commit touching `.env`-adjacent files.
- `audit_logs/` is gitignored. Do not commit audit log files.
- `data/raw/` is gitignored. Do not commit the dataset.

---

## Do not bypass these modules

| Module | Why it is mandatory |
|---|---|
| `src/yoobic_insight/__init__.py` | Current package entrypoint; keep imports and packaging grounded there until more modules exist |
| `notebooks/EDA.ipynb` | Current checked-in analysis artifact; use it instead of inventing undocumented data claims |

---

## Karpathy Skills — agent execution principles

These four principles govern how any agent (Codex, Claude Code, etc.) must approach every task in this repo.

**1. Think Before Coding**
Before writing or editing any code, state which files you will touch and why. If the scope is ambiguous — e.g., a bug spans multiple modules — stop and ask rather than making a silent call. State the invariant you are preserving or the test you expect to pass.

**2. Simplicity First**
Implement the minimum change that satisfies the task. Do not add helper abstractions, do not generalise for hypothetical future stores or KPIs, do not introduce new dependencies. If you find yourself writing more than ~30 lines for a single function, question whether the scope is right.

**3. Surgical Changes**
Stay within the declared scope of the current phase. If one module needs a fix, do not opportunistically refactor neighboring modules. Do not touch tracked files under `eval/` unless the task is explicitly about evaluation. Unrelated improvements belong in a separate task.

**4. Goal-Driven Execution**
Before starting, name the success criterion. For this repo the default bar is: `pytest` exits 0 once tests exist **and** the eval entrypoint reports Config C ≥ 85% deterministic pass-rate once the eval harness is checked in. Do not mark a task complete until you have verified the applicable checks. If you cannot run one, state that explicitly rather than assuming success.
