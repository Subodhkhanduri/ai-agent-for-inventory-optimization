# Inventory Policy Evaluation Report

## Evaluation Setup

| Parameter | Value |
|---|---|
| Training Rows | 730,500 |
| Test Rows | 182,500 |
| Item-Store Pairs Evaluated | 500 |
| Lead Time (L) | 7 days |
| Service Level (Z) | 1.65 (~95%) |
| Review Period (P) | 7 days |

---

## Summary of Evaluation Metrics

### 1. Fill Rate

$$\text{Fill Rate} = 1 - \frac{\sum \text{Unmet Demand}}{\sum \text{Total Demand}}$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Weighted Fill Rate** | **95.53%** | 92.35% |
| Mean Fill Rate (per pair) | 95.61% | 92.35% |
| Median Fill Rate | 95.60% | — |
| Min Fill Rate | 94.30% | — |
| Total Unmet Demand | 479,490 | — |
| Total Demand | 10,733,740 | — |

> ✅ **Excellent**: Fill rate ≥ 95% — strongly supports the Z=1.65 service level assumption.

### 2. Stockout Days Percentage

$$\text{Stockout Days \%} = \frac{\text{Days with demand > inventory}}{\text{Total days}} \times 100$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Mean Stockout Days %** | **6.32%** | 11.45% |
| Median Stockout Days % | 6.30% | — |

### 3. Average Inventory Level

$$\text{Average Inventory} = \frac{1}{T} \sum_{t=1}^{T} I_t$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Mean Avg Inventory** | **241.53** | 215.50 |


---

## Interpretation

- **Fill Rate**: The ROP/Periodic policy achieves ≥95% fill rate, confirming the Z=1.65 service level is effective.
- **Stockout Days**: The ROP policy (6.3%) reduces stockouts vs. actual baseline (11.4%).
- **Avg Inventory**: Policy carries higher average inventory (241.5 vs. 215.5 actual). This is the trade-off for improved service level.

## Statistical Stability Analysis

$$CI = \bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$$

Computed across **n = 500** item-store pairs (95% confidence level).

| Metric | Mean | Std Dev (s) | 95% CI Lower | 95% CI Upper | Margin (±) |
|---|---|---|---|---|---|
| **Fill Rate** | 95.61% | 0.51% | 95.56% | 95.65% | ±0.04% |
| **Stockout Days %** | 6.32 | 0.78 | 6.25 | 6.39 | ±0.07 |
| **Avg Inventory** | 241.53 | 106.97 | 232.16 | 250.91 | ±9.38 |

> The narrow confidence intervals confirm that the evaluation results are statistically stable and not driven by outlier item-store pairs.

---

## Per-Pair Analysis (Selected)

### Top Performers (Highest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |
|---|---|---|---|---|---|---|
| 4 | 5 | 97.8% | 3.8% | 84.5 | 263 | 139 |
| 37 | 6 | 97.1% | 4.4% | 110.8 | 349 | 183 |
| 23 | 9 | 97.0% | 5.5% | 148.0 | 476 | 250 |
| 14 | 7 | 97.0% | 6.0% | 190.4 | 628 | 328 |
| 14 | 5 | 97.0% | 6.6% | 211.1 | 688 | 360 |

### Pairs Needing Attention (Lowest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |
|---|---|---|---|---|---|---|
| 40 | 3 | 94.3% | 7.4% | 157.9 | 514 | 269 |
| 47 | 1 | 94.4% | 7.4% | 95.0 | 306 | 161 |
| 2 | 6 | 94.4% | 8.5% | 202.2 | 675 | 352 |
| 47 | 10 | 94.4% | 7.1% | 118.5 | 381 | 200 |
| 44 | 1 | 94.5% | 6.8% | 121.6 | 408 | 214 |
