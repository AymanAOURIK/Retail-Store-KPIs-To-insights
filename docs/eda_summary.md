# EDA Summary

Full analysis is in `notebooks/EDA.ipynb` (outputs rendered, no execution needed).

---

## Locked constants

| Constant | Value | Source |
|---|---|---|
| `IDENTITY_ABS_TOLERANCE` | `1e-9` | Max observed reconstruction drift: `2.9e-11` |
| `MODIFIED_ZSCORE_THRESHOLD` | `3.5` | Iglewicz & Hoaglin 1993; isolates genuine extremes without false positives |
| `YOY_WEEK_INTERSECTION` | W1–W48 per store | 2025 truncated at W48; per-store intersection used, not `week <= 48` |

---

## 1. Schema

Clean base table: **1,000 rows, 7 columns**, one row per `(Store Name, Year, Week)`. Ten distinct stores across 2024 and 2025. No duplicate keys, no missing values in any column. The data is ready for deterministic feature engineering with no imputation or deduplication step.

---

## 2. Retail equation identity check

The standard decomposition `net_sales = traffic × conversion_rate × units_per_txn × avg_selling_price` holds to floating-point precision across all 1,000 rows. Maximum absolute reconstruction drift: `2.9e-11`; 99th-percentile drift: `1.5e-11`. No row exceeds `1e-9`. This confirms CR, UPT, and AUP can be derived deterministically from the four raw columns without any inconsistency risk.

---

## 3. Coverage & YoY window

2025 data stops at W48; 2024 runs to W52. A naïve YoY comparison over all available 2024 weeks would produce a biased denominator. The pipeline uses **the per-store intersection of weeks present in both years** — in this dataset that resolves to **W1–W48 for every store** (48 like-for-like weeks). `compute_yoy()` receives only this intersection frame.

---

## 4. Store_G 2025 W21 — data-quality violation

`Store_G`, year 2025, week 21: `gross_transactions = 87`, `traffic = 65`, implying `conversion_rate ≈ 1.34` — physically impossible because a conversion rate above 1.0 means transactions exceed visits. This is the one expected DQ violation `loader.validate()` must surface as `gross_transactions_exceeds_traffic`. Any narrative generated for this store-week must include an explicit data-quality caveat.

---

## 5. Network distributions & anomaly detection choice

Weekly network distributions are well-behaved except for the Store_G W21 conversion-rate outlier. Robust medians: traffic `935`, CR `0.146`, UPT `1.97`, avg_selling_price `$139.41`, net_sales `$37,203`.

**Why MAD-based, not z-score.** The Store_G W21 outlier lifts the mean and inflates σ for conversion_rate, causing the standard z-score to understate its severity and misclassify neighbouring genuine anomalies as normal. The modified z-score formula `0.6745 × (x − median) / MAD` is breakdown-resistant: at threshold 3.5 it flags a small minority of rows without collapsing normal weekly variation into false positives (see Section 5 in `notebooks/EDA.ipynb`).

---

## Summary: what EDA proved and how it informed the pipeline

| Finding | Design decision |
|---|---|
| No nulls, no duplicate keys | Loader raises hard errors on any violation — no silent coercion |
| Retail equation holds to 1e-9 | Derived KPIs are computed, not stored; `IDENTITY_ABS_TOLERANCE` is the validation gate |
| 2025 truncated at W48 | YoY uses per-store week intersection — prevents biased denominators |
| Store_G W21 CR > 1 | Loader validates and flags; narrative carries explicit DQ caveat |
| Skewed distributions with a clear outlier | MAD-based modified z-score at 3.5 is the anomaly method throughout |
