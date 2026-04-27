# Product Requirements Document

## Problem

Store managers and reviewers can inspect weekly KPI tables, but the interpretation step is slow and inconsistent. This prototype tests whether a deterministic feature pipeline can produce grounded, auditable narrative output for one store-week at a time.

## User

Primary user: a store manager or reviewer who wants a fast explanation of weekly performance without losing access to the supporting numbers.

## Product goal

Given a selected store, year, and week, the app should:

- summarize the store-week in plain language
- surface data-quality caveats explicitly
- show whether last year's baseline looks abnormal
- explain the main YoY driver when sales moved materially
- let the reviewer inspect the exact deterministic evidence behind the wording

## V1 scope

- local workbook input
- deterministic KPI engineering, YoY logic, network reference, anomaly flags, and tags
- optional LLM narration with deterministic fallback
- Streamlit demo with KPI cards, narrative, trend view, and transparency panel
- deterministic evaluation report stored in-repo

## Out of scope

- production deployment
- workflow automation
- databases, APIs, or background jobs
- privacy certification or enterprise access control
- cross-store action planning beyond the selected store-week summary

## Success criteria

- a teammate can run the app locally from README instructions in under 10 minutes
- the narrative remains traceable to deterministic tags and payload values
- known DQ cases such as `Store_G 2025 W21` are surfaced explicitly
- deterministic evaluation remains at or above the Phase target of `85%`

## Why this is credible

- deterministic flags constrain what the narrative is allowed to say
- the transparency panel exposes payload values, tags, and caveats for auditability
- store aliasing reduces privacy exposure at the LLM boundary
