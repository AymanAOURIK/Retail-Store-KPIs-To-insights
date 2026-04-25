"""yoobic_insight: deterministic feature pipeline + LLM narrativisation
for weekly store performance briefings.

Subpackages built per phase (see TECHNICAL_PLAN.md):
    loader        - I/O + schema validation + DQ assertions
    features      - KPI tree, YoY, network references, rolling stats
    decomposition - log-additive driver attribution
    anomalies     - robust anomaly + abnormal-LY-baseline flags
    payload       - pydantic schema, privacy filter, audit log
    tags          - deterministic headline-tag generator (stage 1)
    narrative     - LLM narrativisation (stage 2) + rule fallback
    judge         - eval: deterministic checks + LLM-as-judge
"""
