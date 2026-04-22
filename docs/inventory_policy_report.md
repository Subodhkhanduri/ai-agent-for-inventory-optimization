# Inventory Policy Evaluation Report

## Evaluation Setup

| Parameter | Value |
|---|---|
| Training Rows | 730,500 |
| Test Rows | 182,500 |
| Item-Store Pairs Evaluated | 5 |
| Lead Time (L) | 7 days |
| Service Level (Z) | 1.65 (~95%) |
| Review Period (P) | 7 days |

---

## Summary of Evaluation Metrics

### 1. Fill Rate

$$\text{Fill Rate} = 1 - \frac{\sum \text{Unmet Demand}}{\sum \text{Total Demand}}$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Weighted Fill Rate** | **95.81%** | 92.93% |
| Mean Fill Rate (per pair) | 95.88% | 92.93% |
| Median Fill Rate | 95.59% | — |
| Min Fill Rate | 95.53% | — |
| Total Unmet Demand | 1,946 | — |
| Total Demand | 46,395 | — |

> ✅ **Excellent**: Fill rate ≥ 95% — strongly supports the Z=1.65 service level assumption.

### 2. Stockout Days Percentage

$$\text{Stockout Days \%} = \frac{\text{Days with demand > inventory}}{\text{Total days}} \times 100$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Mean Stockout Days %** | **5.54%** | 10.19% |
| Median Stockout Days % | 5.48% | — |

### 3. Average Inventory Level

$$\text{Average Inventory} = \frac{1}{T} \sum_{t=1}^{T} I_t$$

| Metric | ROP/Periodic Policy | Actual Baseline |
|---|---|---|
| **Mean Avg Inventory** | **109.54** | 97.51 |


---

## Interpretation

- **Fill Rate**: The ROP/Periodic policy achieves ≥95% fill rate, confirming the Z=1.65 service level is effective.
- **Stockout Days**: The ROP policy (5.5%) reduces stockouts vs. actual baseline (10.2%).
- **Avg Inventory**: Policy carries higher average inventory (109.5 vs. 97.5 actual). This is the trade-off for improved service level.

## Statistical Stability Analysis

$$CI = \bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$$

Computed across **n = 5** item-store pairs (95% confidence level).

| Metric | Mean | Std Dev (s) | 95% CI Lower | 95% CI Upper | Margin (±) |
|---|---|---|---|---|---|
| **Fill Rate** | 95.88% | 0.48% | 95.46% | 96.29% | ±0.42% |
| **Stockout Days %** | 5.54 | 0.36 | 5.22 | 5.85 | ±0.31 |
| **Avg Inventory** | 109.54 | 19.79 | 92.20 | 126.88 | ±17.34 |

> The narrow confidence intervals confirm that the evaluation results are statistically stable and not driven by outlier item-store pairs.

---

## Per-Pair Analysis (Selected)

### Top Performers (Highest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |
|---|---|---|---|---|---|---|
| 1 | 5 | 96.7% | 5.5% | 80.6 | 261 | 138 |
| 1 | 1 | 96.0% | 5.2% | 103.2 | 312 | 165 |
| 1 | 4 | 95.6% | 5.2% | 113.2 | 355 | 187 |
| 1 | 3 | 95.6% | 6.0% | 115.9 | 386 | 203 |
| 1 | 2 | 95.5% | 5.8% | 134.8 | 433 | 227 |

### Pairs Needing Attention (Lowest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |
|---|---|---|---|---|---|---|
| 1 | 2 | 95.5% | 5.8% | 134.8 | 433 | 227 |
| 1 | 3 | 95.6% | 6.0% | 115.9 | 386 | 203 |
| 1 | 4 | 95.6% | 5.2% | 113.2 | 355 | 187 |
| 1 | 1 | 96.0% | 5.2% | 103.2 | 312 | 165 |
| 1 | 5 | 96.7% | 5.5% | 80.6 | 261 | 138 |
