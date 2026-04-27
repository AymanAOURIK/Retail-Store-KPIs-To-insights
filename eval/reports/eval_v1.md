# Eval Report v1

Deterministic pass rate: 100.0%
Threshold: 85%

| Scenario | Numeric grounding | Tag coverage | No hallucinated claims | LLM judge | Narrative excerpt |
|---|---|---|---|---|---|
| store_g_2025_w21_dq | PASS | PASS | PASS | SKIP | STORE_07 week 21 of 2025 summary. Data quality caveat: gross_transactions_exceeds_traffic. Net sales fell sharply yea... |
| ly_baseline_abnormal_case | PASS | PASS | PASS | SKIP | STORE_03 week 18 of 2025 summary. Last year's conversion rate baseline may be abnormal. |
| all_green_normal_case | PASS | PASS | PASS | SKIP | STORE_01 week 20 of 2025 summary. No headline tags were triggered for this store-week. |
| early_2024_no_ly_baseline | PASS | PASS | PASS | SKIP | STORE_05 week 3 of 2024 summary. No headline tags were triggered for this store-week. |
| sales_decline_conversion_driver | PASS | PASS | PASS | SKIP | STORE_04 week 16 of 2025 summary. Net sales fell sharply year over year. conversion rate was the dominant driver of t... |
| sales_decline_avg_price_driver | PASS | PASS | PASS | SKIP | STORE_06 week 15 of 2025 summary. Net sales fell sharply year over year. avg selling price was the dominant driver of... |
| dq_missing_value_case | PASS | PASS | PASS | SKIP | STORE_08 week 12 of 2025 summary. Data quality caveat: missing_value. |
| ly_baseline_abnormal_traffic | PASS | PASS | PASS | SKIP | STORE_09 week 19 of 2025 summary. Last year's traffic baseline may be abnormal. |
| network_underperform_only | PASS | PASS | PASS | SKIP | STORE_10 week 14 of 2025 summary. net sales was below the weekly network benchmark. traffic was below the weekly netw... |
| early_2024_negative_gap_no_ly | PASS | PASS | PASS | SKIP | STORE_02 week 7 of 2024 summary. net sales was below the weekly network benchmark. traffic was below the weekly netwo... |
| sales_decline_units_driver | PASS | PASS | PASS | SKIP | STORE_07 week 11 of 2025 summary. Net sales fell sharply year over year. units per txn was the dominant driver of the... |
| stable_case_with_minor_positive_yoy | PASS | PASS | PASS | SKIP | STORE_08 week 10 of 2025 summary. No headline tags were triggered for this store-week. |

## Notes

- `store_g_2025_w21_dq`: Store_G 2025 W21 data-quality scenario with a sales decline and a traffic-driven narrative.
  - llm_judge: Judge client unavailable.
- `ly_baseline_abnormal_case`: Current week is stable, but last year's conversion-rate baseline was abnormal.
  - llm_judge: Judge client unavailable.
- `all_green_normal_case`: Healthy case with no anomalies, no DQ caveats, and no high-severity tags.
  - llm_judge: Judge client unavailable.
- `early_2024_no_ly_baseline`: Early 2024 scenario with no LY baseline available.
  - llm_judge: Judge client unavailable.
- `sales_decline_conversion_driver`: Sales declined sharply and conversion rate was the dominant driver.
  - llm_judge: Judge client unavailable.
- `sales_decline_avg_price_driver`: Sales declined sharply and average selling price was the dominant driver.
  - llm_judge: Judge client unavailable.
- `dq_missing_value_case`: Data-quality caveat only, without a sales decline narrative.
  - llm_judge: Judge client unavailable.
- `ly_baseline_abnormal_traffic`: Last year's traffic baseline was abnormal, but current performance is otherwise steady.
  - llm_judge: Judge client unavailable.
- `network_underperform_only`: Only low-severity network underperformance tags should appear.
  - llm_judge: Judge client unavailable.
- `early_2024_negative_gap_no_ly`: Early 2024 case with no LY baseline and low-severity network underperformance only.
  - llm_judge: Judge client unavailable.
- `sales_decline_units_driver`: Sales declined sharply with units per transaction as the dominant driver.
  - llm_judge: Judge client unavailable.
- `stable_case_with_minor_positive_yoy`: Stable case with minor positive YoY and no headline tags.
  - llm_judge: Judge client unavailable.
