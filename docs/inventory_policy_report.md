# Inventory Policy Evaluation Report

## Evaluation Setup

| Parameter | Value |
|---|---|
| Training Rows | 730,500 |
| Test Rows | 182,500 |
| Item-Store Pairs Evaluated | 500 |
| Lead Time (L) | 7 days |
| Service Level (Z) | 1.65 (~95%) |
| Ordering Cost (S) | $50 |
| Holding Cost (H) | $2/unit/year |

---

## Summary of Evaluation Metrics

### 1. Fill Rate

$$\text{Fill Rate} = 1 - \frac{\sum \text{Unmet Demand}}{\sum \text{Total Demand}}$$

| Metric | ROP/EOQ Policy | Actual Baseline |
|---|---|---|
| **Weighted Fill Rate** | **98.07%** | 92.35% |
| Mean Fill Rate (per pair) | 98.28% | 92.35% |
| Median Fill Rate | 98.25% | — |
| Min Fill Rate | 96.49% | — |
| Total Unmet Demand | 207,381 | — |
| Total Demand | 10,733,740 | — |

> ✅ **Excellent**: Fill rate ≥ 95% — strongly supports the Z=1.65 service level assumption.

### 2. Stockout Days Percentage

$$\text{Stockout Days \%} = \frac{\text{Days with demand > inventory}}{\text{Total days}} \times 100$$

| Metric | ROP/EOQ Policy | Actual Baseline |
|---|---|---|
| **Mean Stockout Days %** | **2.83%** | 11.45% |
| Median Stockout Days % | 2.74% | — |

### 3. Average Inventory Level

$$\text{Average Inventory} = \frac{1}{T} \sum_{t=1}^{T} I_t$$

| Metric | ROP/EOQ Policy | Actual Baseline |
|---|---|---|
| **Mean Avg Inventory** | **478.68** | 215.50 |

### 4. Total Cost (EOQ Analysis)

$$TC = \frac{D}{Q} \cdot S + \frac{Q}{2} \cdot H$$

| Metric | Value |
|---|---|
| Mean TC (EOQ Policy) | $1,868.85 |
| Mean TC (Actual Ordering) | $2,809.88 |
| **Mean Cost Reduction** | **34.24%** |
| Median Cost Reduction | 32.70% |
| Total TC (EOQ, all pairs) | $934,426.60 |
| Total TC (Actual, all pairs) | $1,404,939.63 |

---

## Interpretation

- **Fill Rate**: The ROP/EOQ policy achieves ≥95% fill rate, confirming the Z=1.65 service level is effective.
- **Stockout Days**: The ROP policy (2.8%) reduces stockouts vs. actual baseline (11.4%).
- **Avg Inventory**: Policy carries higher average inventory (478.7 vs. 215.5 actual). This is the trade-off for improved service level.
- **EOQ Cost**: The EOQ policy achieves a **34.2% cost reduction** over current ordering patterns.

## Statistical Stability Analysis

$$CI = \bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$$

Computed across **n = 500** item-store pairs (95% confidence level).

| Metric | Mean | Std Dev (s) | 95% CI Lower | 95% CI Upper | Margin (±) |
|---|---|---|---|---|---|
| **Fill Rate** | 98.28% | 0.59% | 98.23% | 98.33% | ±0.05% |
| **Stockout Days %** | 2.83 | 0.95 | 2.75 | 2.92 | ±0.08 |
| **Avg Inventory** | 478.68 | 114.60 | 468.64 | 488.73 | ±10.05 |
| **Cost Reduction %** | 34.24 | 11.80 | 33.20 | 35.27 | ±1.03 |

> The narrow confidence intervals confirm that the evaluation results are statistically stable and not driven by outlier item-store pairs.

---

## Per-Pair Analysis (Selected)

### Top Performers (Highest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | EOQ | ROP |
|---|---|---|---|---|---|---|
| 41 | 7 | 99.7% | 0.6% | 272.1 | 524 | 128 |
| 4 | 6 | 99.6% | 0.8% | 287.7 | 545 | 139 |
| 4 | 5 | 99.6% | 0.6% | 285.0 | 546 | 139 |
| 1 | 7 | 99.6% | 1.1% | 266.1 | 517 | 125 |
| 17 | 6 | 99.6% | 1.1% | 343.5 | 666 | 203 |

### Pairs Needing Attention (Lowest Fill Rate)

| Item | Store | Fill Rate | Stockout % | Avg Inventory | EOQ | ROP |
|---|---|---|---|---|---|---|
| 13 | 2 | 96.5% | 4.9% | 709.2 | 1381 | 850 |
| 36 | 8 | 96.6% | 4.7% | 653.6 | 1290 | 743 |
| 18 | 2 | 96.7% | 5.2% | 695.7 | 1381 | 849 |
| 10 | 2 | 96.9% | 4.1% | 657.3 | 1289 | 741 |
| 28 | 8 | 97.0% | 4.4% | 703.7 | 1380 | 848 |
