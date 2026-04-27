# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this is

A retail store weekly performance briefing pipeline: raw xlsx KPI data → deterministic feature engineering → LLM narrativisation → Streamlit demo. Built as an AI Technical PM feasibility prototype for Yoobic (B2B SaaS for frontline employee experience).

The pipeline is intentionally stateless. There is no database. The xlsx file is the only data source.

---

## Environment setup

```bash
# Activate the project venv (WSL)
source .venv/bin/activate        # or: source venv_wsl/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp CLAUDE.local.example.md CLAUDE.local.md
# Store local environment details outside git-tracked files
```

Set `OPENAI_API_KEY` only when testing an LLM path that exists in the checkout.

---

## Repo map

```
src/yoobic_insight/
  __init__.py           Only checked-in package file in the current checkout
app/                    Directory present, no tracked app files currently checked in
eval/
  prompts/              Directory present, no tracked prompt files currently checked in
  reports/              Directory present, no tracked report files currently checked in
notebooks/
  EDA.ipynb             Exploratory analysis — source of all EDA findings
tests/                  Directory present, no tracked test files currently checked in
docs/                   Repo docs and delivery notes
data/raw/               Gitignored — practical-test-dataset-weekly-kpi.xlsx lives here
_internal/              Gitignored planning docs — do not read or write
```

---

## Common commands

```bash
# Run all tests
pytest

# Execute EDA notebook end-to-end
jupyter nbconvert --to notebook --execute notebooks/EDA.ipynb --output notebooks/EDA.ipynb

# Inspect the currently tracked files under app/, eval/, and tests/
rg --files app eval tests
```

---

## Core pipeline — two stages

**Stage 1 (deterministic, pure Python):**
```
xlsx KPI data in `data/raw/` feeds a deterministic preprocessing layer in `src/yoobic_insight/`.
That layer is expected to prepare an anonymised payload before any LLM call is introduced.
```

**Stage 2 (LLM):**
```
An LLM boundary is expected to consume only the prepared payload and to retain a rule-based fallback.
```

Every number the LLM sees comes from the payload; it never reasons over raw rows. This is what makes numeric-grounding checks pass.

---

## Coding conventions

- **Pure functions only** in deterministic pipeline modules under `src/yoobic_insight/`. No I/O, no global state.
- **Pydantic v2 models only at the LLM boundary** when that boundary is added.
- **Portable paths:** all dataset access via `Path` resolved from project root. No hardcoded absolute paths.
- **No tests hit the API.** Stub `LLMClient` or pass `client=None`.
- **No tests read the xlsx.** Build in-memory frames from literals.
- **Anomaly detection is MAD-based** (modified z-score: `0.6745 × (x − median) / MAD`), not `zscore()` or `.std()`. If MAD = 0, fall back to absolute deviation or skip — never divide by zero.
- **Like-for-like YoY** uses the intersection of weeks present in both years for each store. Not `week <= 48`.

---

## Critical data caveats

- **Dataset:** `data/raw/practical-test-dataset-weekly-kpi.xlsx` — 10 stores, weekly KPIs for 2024 (W1–W52) and 2025 (W1–W48). Gitignored. Never commit.
- **Known DQ violation:** `Store_G 2025 W21` — `gross_transactions > traffic`. This is the one expected violation `loader.validate()` must surface. Any scenario touching this store-week must include a DQ caveat in the narrative.
- **2025 is truncated at W48.** All YoY comparisons must restrict to the like-for-like window.
- **Store names are sensitive.** They map to opaque aliases (`STORE_NN`) before anything crosses the LLM boundary.

---

## Eval pass-rate target

When the eval harness is checked in, Config C (structured payload + deterministic tags) must score ≥ 85% on deterministic checks. If a prompt change drops this, fix the prompt before merging.

---

## Local overrides

See `CLAUDE.local.example.md` for machine-specific settings (venv path, dataset path, API key location). Copy it to `CLAUDE.local.md` (gitignored) and edit locally.

---

## Council Review — when to stop and deliberate

Before implementing any major or unplanned change, invoke the council:

```
/council <one-sentence description of the proposed change>
```

**Mandatory triggers — do NOT proceed without a council verdict:**

| Trigger | Example |
|---|---|
| Adding a new module or file to `src/` | Creating `src/yoobic_insight/cache.py` |
| Deviating from a plan already discussed in the conversation | Switching from rule-based to ML-based anomaly detection mid-task |
| Touching 3 or more files for a single change | Refactoring that spans loader + features + payload |
| Moving logic across the deterministic/LLM boundary | Letting the LLM compute a metric that should stay in the deterministic layer |
| Adding a new dependency to `requirements.txt` | Adding `redis`, `httpx`, etc. |
| Changing eval scoring logic or the judge prompt | Any edit to tracked files under `eval/` once they exist |
| Proposing a new typed model outside the LLM boundary | Adding a new boundary model in a future LLM integration module |

**How to act on the verdict:**

- `APPROVE` → proceed as proposed
- `REVISE` → adjust the plan to satisfy the listed CONDITIONS, confirm with user, then code
- `REJECT` → stop, explain the rejection to the user, propose an alternative

---

## Karpathy Skills — coding principles

Four principles that govern how Claude approaches every coding task in this repo.

**1. Think Before Coding**
State assumptions explicitly before writing any code. If a requirement is ambiguous (e.g., which week window to use for YoY, whether a DQ edge case needs a narrative caveat), ask first rather than silently deciding. Surface tradeoffs.

**2. Simplicity First**
Minimum code that solves the problem — nothing speculative. No extra abstractions, no defensive error handling for scenarios that can't happen, no features beyond what was requested. Three similar lines beats a premature helper.

**3. Surgical Changes**
Touch only what you must. When fixing a bug in one module, don't refactor adjacent modules unnecessarily. Clean up only the mess directly caused by the current change. Leave unrelated code exactly as found.

**4. Goal-Driven Execution**
Transform every task into a measurable success criterion before starting. For this repo, the default bar is: `pytest` green and, once the eval harness exists in the checkout, Config C ≥ 85% deterministic pass-rate. Don't mark a task done until you can verify the applicable criteria are met.
