# Eval Report v1

Deterministic pass rate: 100.0%
Threshold: 85%

| Scenario | Numeric grounding | Tag coverage | YoY caveat | Network gap | No hallucinated claims | LLM judge | Narrative excerpt |
|---|---|---|---|---|---|---|---|
| store_g_2025_w21_dq | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_07 — Week 21, 2025. Data quality caveat: gross_transactions_exceeds_traffic. Net sales fell sharply year over y... |
| ly_baseline_abnormal_case | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_03 — Week 18, 2025. Last year's conversion rate baseline may be abnormal. Year-over-year comparisons may be mis... |
| all_green_normal_case | PASS | PASS | PASS | PASS | PASS | SKIP | Week 20 of 2025 was a steady week for STORE_01. All tracked metrics came in within the expected range across the stor... |
| early_2024_no_ly_baseline | PASS | PASS | PASS | PASS | PASS | SKIP | Week 3 of 2024 was a steady week for STORE_05. All tracked metrics came in within the expected range across the store... |
| sales_decline_conversion_driver | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_04 — Week 16, 2025. Net sales fell sharply year over year. conversion rate was the dominant driver of the sales... |
| sales_decline_avg_price_driver | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_06 — Week 15, 2025. Net sales fell sharply year over year. avg selling price was the dominant driver of the sal... |
| dq_missing_value_case | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_08 — Week 12, 2025. Data quality caveat: missing_value. |
| ly_baseline_abnormal_traffic | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_09 — Week 19, 2025. Last year's traffic baseline may be abnormal. Year-over-year comparisons may be misleading ... |
| network_underperform_only | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_10 — Week 14, 2025. net sales was below the weekly network benchmark. traffic was below the weekly network benc... |
| early_2024_negative_gap_no_ly | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_02 — Week 7, 2024. net sales was below the weekly network benchmark. traffic was below the weekly network bench... |
| sales_decline_units_driver | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_07 — Week 11, 2025. Net sales fell sharply year over year. units per txn was the dominant driver of the sales d... |
| stable_case_with_minor_positive_yoy | PASS | PASS | PASS | PASS | PASS | SKIP | Week 10 of 2025 was a steady week for STORE_08. All tracked metrics came in within the expected range across the stor... |
| strong_week_positive_yoy | PASS | PASS | PASS | PASS | PASS | SKIP | Week 48 of 2025 was a steady week for STORE_01. All tracked metrics came in within the expected range across the stor... |
| ly_caveat_no_other_flags | PASS | PASS | PASS | PASS | PASS | SKIP | Week 12 of 2025 was a steady week for STORE_05. All tracked metrics came in within the expected range across the stor... |
| ly_abnormal_traffic_below_network | PASS | PASS | PASS | PASS | PASS | SKIP | STORE_06 — Week 19, 2025. Last year's traffic baseline may be abnormal. net sales was below the weekly network benchm... |

## Notes

- `store_g_2025_w21_dq`: Store_G 2025 W21 data-quality scenario with a sales decline and a traffic-driven narrative.
  - llm_judge: Connection error.
- `ly_baseline_abnormal_case`: Current week is stable, but last year's conversion-rate baseline was abnormal.
  - llm_judge: Connection error.
- `all_green_normal_case`: Healthy case with no anomalies, no DQ caveats, and no high-severity tags.
  - llm_judge: Connection error.
- `early_2024_no_ly_baseline`: Early 2024 scenario with no LY baseline available.
  - llm_judge: Connection error.
- `sales_decline_conversion_driver`: Sales declined sharply and conversion rate was the dominant driver.
  - llm_judge: Connection error.
- `sales_decline_avg_price_driver`: Sales declined sharply and average selling price was the dominant driver.
  - llm_judge: Connection error.
- `dq_missing_value_case`: Data-quality caveat only, without a sales decline narrative.
  - llm_judge: Connection error.
- `ly_baseline_abnormal_traffic`: Last year's traffic baseline was abnormal, but current performance is otherwise steady.
  - llm_judge: Connection error.
- `network_underperform_only`: Only low-severity network underperformance tags should appear.
  - llm_judge: Connection error.
- `early_2024_negative_gap_no_ly`: Early 2024 case with no LY baseline and low-severity network underperformance only.
  - llm_judge: Connection error.
- `sales_decline_units_driver`: Sales declined sharply with units per transaction as the dominant driver.
  - llm_judge: Connection error.
- `stable_case_with_minor_positive_yoy`: Stable case with minor positive YoY and no headline tags.
  - llm_judge: Connection error.
- `strong_week_positive_yoy`: Strong week with positive YoY, no anomaly flags, and no LY-baseline concern.
  - llm_judge: Connection error.
- `ly_caveat_no_other_flags`: LY baseline was abnormal with no other flags — YoY caveat must be present in narrative.
  - llm_judge: Connection error.
- `ly_abnormal_traffic_below_network`: LY traffic baseline was abnormal and current traffic is materially below the network — tests flag coverage + YoY caveat + network gap.
  - llm_judge: Connection error.
