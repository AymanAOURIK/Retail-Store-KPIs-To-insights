# Privacy Note

## Current position

This repository improves privacy handling relative to the initial prototype state, but it should not be represented as fully hardened.

## Honest disclosures

- Raw KPI files under `data/raw/` are gitignored going forward and should stay local-only.
- A historical commit tracked the workbook before the repository hygiene fix. That history is acknowledged rather than ignored.
- The LLM boundary aliases store names deterministically, so serialized payloads use `STORE_01`, `STORE_02`, and so on instead of raw store names.

## What is and is not sent to the LLM

The intended boundary is a typed payload built from deterministic features, flags, caveats, and store aliases. Real store names should not appear in the serialized payload sent to the model. The narrative step is therefore constrained to transformed analytics rather than raw workbook identity fields.

## Residual risks

- The raw workbook still exists locally for app execution and analyst work.
- Alias maps remain sensitive because they can reconnect aliases to real store names.
- This repo does not yet include a formal retention, access-control, or key-management policy.

## Working guidance

- Keep `data/raw/` untracked.
- Do not commit `.env` or API keys.
- Treat any artifact that contains alias-to-store decoding as sensitive.
- If the payload schema changes in a way that could expose raw identifiers, require explicit privacy review before use.
