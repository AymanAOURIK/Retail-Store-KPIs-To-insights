# EDA Summary

## Locked Constants

- `IDENTITY_ABS_TOLERANCE = 1e-9`
- `MODIFIED_ZSCORE_THRESHOLD = 3.5`
- `YOY_WEEK_INTERSECTION = weeks present in both years for the same store`
- With the current dataset, the like-for-like year intersection is weeks `1..48` for every store.

## 1. Schema

The notebook loads `data/raw/practical-test-dataset-weekly-kpi.xlsx` from the repository root with `Path` resolution and confirms a clean base table of 1,000 rows and 7 columns: `Store Name`, `Year`, `Week`, `traffic`, `gross_transactions`, `gross_quantity`, and `net_sales`. There are 10 distinct stores across 2024 and 2025, no duplicate `(Store Name, Year, Week)` keys, and no missing values in any column. The data is at a single weekly store grain, which is the expected analytical input for later deterministic pipeline phases.

## 2. Identity Check

The decomposition identity `net_sales = traffic × conversion_rate × units_per_txn × avg_selling_price` holds to floating-point precision only. The maximum absolute reconstruction drift is `2.9103830456733704e-11`, the 99th percentile absolute drift is `1.4551915228366852e-11`, and no row exceeds `1e-9`. This supports locking `IDENTITY_ABS_TOLERANCE = 1e-9` as the later validation threshold: it is materially above observed floating-point noise while still tight enough to catch real feature-engineering errors.

## 3. Coverage

Coverage is complete within each store-year slice. Every store has all 52 weeks for 2024 and all 48 available weeks for 2025, with no internal holes. The only coverage asymmetry is cross-year: 2025 stops at week 48 while 2024 runs to week 52. Later year-over-year logic therefore must use the per-store week intersection rather than assuming full 52-week overlap; in the current dataset that resolves to weeks `1..48` for every store.

## 4. Store_G Week 21 Violation

`Store_G`, `2025`, week `21` is the expected data-quality exception. That row has `traffic = 65`, `gross_transactions = 87`, `gross_quantity = 238`, and `net_sales = 28851.64597840668`, which implies `gross_transactions - traffic = 22` and a conversion rate of `1.3384615384615384`. Because transactions exceed visits, this row should be surfaced explicitly in later validation as `gross_transactions_exceeds_traffic` rather than treated as normal business variation.

## 5. Network Distributions

The weekly network distributions are well behaved overall, with a single clear extreme in conversion-linked metrics driven by the `Store_G` week 21 anomaly. Robust central tendencies for the full weekly panel are: `traffic` median `935.0` / MAD `404.5`, `gross_transactions` `136.0` / `50.0`, `gross_quantity` `271.0` / `97.0`, `net_sales` `37202.6792` / `14427.5155`, `conversion_rate` `0.1464` / `0.0344`, `units_per_txn` `1.9742` / `0.2108`, `avg_selling_price` `139.4098` / `19.8059`, `avg_txn_value` `276.3491` / `52.0277`, and `revenue_per_visitor` `43.4183` / `13.0537`. For later anomaly scoring, the default modified z-score cut-off should be `3.5`, which is the standard robust threshold and already isolates a small minority of rows in this dataset rather than collapsing normal weekly variation into false positives.
