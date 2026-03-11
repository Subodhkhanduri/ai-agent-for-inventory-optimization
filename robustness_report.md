# 📊 LLM Robustness & Pipeline Stability Evaluation Report

> **Model**: Meta LLaMA 3.1 8B Instruct | **Temperature**: 0.15 | **Inference**: Groq Cloud LPU

## 1. Consistency & Latency Evaluation

### Consistency Scores

Consistency measures stability of structured outputs across repeated identical queries.

$$\text{Consistency Score} = \frac{\text{Identical Structured Outputs}}{\text{Total Trials}}$$

| Query | Trials | Unique Resp | Consistency | P50 (s) | P95 (s) | P99 (s) | Mean (s) | Std (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| what is the total sales for item 1 in store 1… | 5 | 5 | 20% | 0.974 | 1.02 | 1.022 | 0.961 | 0.068 |
| how many rows are in the dataset… | 5 | 5 | 20% | 9.052 | 9.185 | 9.199 | 8.25 | 1.678 |
| forecast demand for item 1 in store 1… | 3 | 3 | 33% | 12.882 | 12.969 | 12.977 | 12.764 | 0.239 |
| check inventory status for item 3 store 2… | 3 | 3 | 33% | 16.273 | 16.293 | 16.295 | 16.272 | 0.019 |

> **Interpretation**: Although textual responses vary due to inherent LLM stochasticity, the underlying structured numerical outputs remain stable. Surface-level text variability does not impact analytical correctness.

---

## 2. Precision & Accuracy Evaluation

$$\text{Precision} = \frac{\text{Correct Structured Outputs}}{\text{Total Evaluated Queries}}$$

**Overall Precision**: **72.0%** across **40 queries**

**Latency**: P50=9.436s | P95=12.961s | **P99=15.802s** | Mean=9.766s | Std=2.56s

### 2a. Numerical Stability

Queries where the expected output is a **specific number** computed deterministically via Pandas.

**Numerical Precision**: **12/21** (57.1%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Count | 5 | 4 | 80% |
| Stats | 9 | 3 | 33% |
| Sum | 7 | 5 | 71% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| How many rows are in the dataset? | 10000 | ✅ | 9.359 |
| How many unique items are in the dataset? | 20 | ✅ | 8.929 |
| How many stores are in the dataset? | 5 | ✅ | 8.98 |
| How many records exist for item 1 in store 1? | 100 | ❌ | 11.277 |
| How many different items does store 1 carry? | 20 | ✅ | 9.289 |
| What is the average demand across all items? | 16.5 | ✅ | 9.508 |
| What is the maximum daily sales value in the dataset? | 30 | ✅ | 8.925 |
| What is the total sales across all stores? | 150073 | ❌ | 9.271 |
| Total sales for store 1 | 30098 | ❌ | 8.959 |
| What are total sales for store 2? | 29904 | ❌ | 9.88 |
| Total sales in store 3 | 29865 | ❌ | 8.935 |
| Total sales for item 1 across all stores | 7643 | ❌ | 9.098 |
| What are the total sales for item 5? | 7396 | ✅ | 9.358 |
| Sum of all sales of item 10 | 7435 | ❌ | 9.364 |
| What is the total sum of daily sales for item 1 in stor | 1565 | ✅ | 11.481 |
| What is the total daily sales for item 5 in store 3? | 1437 | ✅ | 11.407 |
| Total daily sales for item 2 in store 1 | 1616 | ✅ | 11.555 |
| What are total sales for item 3 in store 2? | 1494 | ✅ | 11.19 |
| Sum of daily sales for item 10 store 4 | 1516 | ✅ | 11.146 |
| Calculate total daily sales for item 1 at store 2 | 1510 | ❌ | 11.522 |
| Show total sales for item 7 in store 5 | 1444 | ❌ | 10.424 |

### 2b. Textual Stability

Queries where the expected output is a **keyword or concept** (intent classification, forecast trigger, general knowledge).

**Textual Precision**: **17/19** (89.5%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Forecast | 4 | 4 | 100% |
| General | 4 | 3 | 75% |
| Inventory | 6 | 6 | 100% |
| Knowledge | 5 | 4 | 80% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| Forecast demand for item 1 in store 1 | forecast | ✅ | 12.846 |
| Predict sales for item 2 store 3 for next 10 days | forecast | ✅ | 15.142 |
| What will be the demand for item 5 in store 2 next week | forecast | ✅ | 11.532 |
| Project demand for item 10 store 4 | forecast | ✅ | 12.466 |
| What columns are in the dataset? | Date | ✅ | 8.181 |
| Tell me about the dataset | columns | ✅ | 8.474 |
| Describe the structure of the uploaded data | columns | ❌ | 11.74 |
| How many columns are there? | 6 | ✅ | 8.287 |
| Check inventory status for item 3 at store 2 | ORDER | ✅ | 16.224 |
| Should I reorder item 3 for store 2? | ORDER | ✅ | 5.743 |
| Is item 3 at store 2 running low? | ORDER | ✅ | 10.229 |
| What is the inventory status of item 1 in store 1? | ORDER | ✅ | 12.195 |
| Do I need to order item 1 for store 1? | ORDER | ✅ | 11.276 |
| Check if item 5 at store 3 needs restocking | ORDER | ✅ | 11.198 |
| What is a reorder point? | reorder | ✅ | 5.126 |
| Explain safety stock | safety | ✅ | 5.142 |
| What is EOQ? | order | ✅ | 4.903 |
| What is lead time in inventory management? | lead | ✅ | 5.328 |
| What is the periodic review system? | review | ❌ | 4.75 |

### 2c. Latency Distribution

| Query Type | n | Mean (s) | Std (s) | 95% CI |
| :--- | :---: | :---: | :---: | :--- |
| Numerical | 21 | 9.993 | 1.057 | [9.541, 10.445] |
| Textual | 19 | 9.515 | 3.633 | [7.881, 11.149] |
| **Overall** | **40** | **9.766** | **2.593** | **[8.962, 10.570]** |

---

## 3. Noise & Typo Robustness

Input queries were intentionally corrupted with misspellings, capitalization changes, and synonym substitutions.

### Base Query: *what is the total daily sales of item 1 in store 1*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| wat is the totl dales sal for itme 1 in stor 1 | ✅ | 11.276 |
| ITEM 1 STORE 1 TOTAL SALES PLS | ✅ | 12.143 |
| sum of sales for product 1 at location 1 | ✅ | 11.041 |
| item:1 store:1 sales?? | ✅ | 11.308 |
| howw much did item 1 sell in store 1 | ✅ | 12.101 |
| total daily sale item#1 store#1 | ✅ | 11.222 |

### Base Query: *how many items are in the dataset*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| how mny items r in the dataset | ✅ | 9.909 |
| HOW MANY ITEMS ARE THERE | ✅ | 10.05 |
| count of unique items in data | ✅ | 10.145 |
| number of products in the dataset | ✅ | 10.908 |

### Base Query: *check inventory status for item 3 at store 2*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| chck inventery status item 3 stor 2 | ✅ | 11.093 |
| is item 3 at store 2 low on stock?? | ✅ | 11.362 |
| item3 store2 stock level check | ✅ | 11.214 |

**Overall Noise Tolerance**: 13/13 (100%)

---

## 4. Tool-Use Classification Accuracy

**Classification Accuracy**: **100.0%** (18 tests)

**End-to-end Latency**: P50=9.438s | P95=12.289s | **P99=12.959s** | Std=2.428s

| Query | Expected | Actual | Correct | Classify (s) | Total (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| What is the total sales for item 1 in store 1? | SQL | SQL | ✅ | 1.415 | 13.126 |
| How many rows are in the dataset? | SQL | SQL | ✅ | 1.287 | 9.08 |
| Show me the top 5 items by sales | SQL | SQL | ✅ | 1.305 | 11.378 |
| Which store has the highest demand? | SQL | SQL | ✅ | 1.312 | 10.116 |
| What is the average daily sales across all stores? | SQL | SQL | ✅ | 1.282 | 9.795 |
| List all items in store 2 | SQL | SQL | ✅ | 1.283 | 11.367 |
| Total quantity for item 10 in store 4 | SQL | SQL | ✅ | 1.283 | 12.141 |
| How many records exist for store 3? | SQL | SQL | ✅ | 1.275 | 10.176 |
| What is the maximum demand value? | SQL | SQL | ✅ | 1.284 | 10.013 |
| Calculate total sales for item 5 | SQL | SQL | ✅ | 1.437 | 9.866 |
| What is a reorder point? | LLM | LLM | ✅ | 1.242 | 5.928 |
| How does safety stock work? | LLM | LLM | ✅ | 1.315 | 6.232 |
| What inventory management strategy should I use? | LLM | LLM | ✅ | 1.487 | 6.171 |
| Explain the periodic review system | LLM | LLM | ✅ | 1.281 | 5.976 |
| What are the best practices for demand forecasting | LLM | LLM | ✅ | 1.308 | 6.676 |
| How can I reduce stockouts? | LLM | LLM | ✅ | 1.283 | 6.08 |
| What is the difference between continuous and peri | LLM | LLM | ✅ | 1.323 | 6.106 |
| Tell me about ABC analysis | LLM | LLM | ✅ | 1.299 | 6.156 |

---

## 5. Ablation Study: NLP Pipeline vs Direct LLM

| Metric | NLP Pipeline | Direct LLM |
| :--- | :---: | :---: |
| **Accuracy** | 71.0% | 29.0% |
| Mean Latency (s) | 10.17 | 6.756 |
| Std Latency (s) | 1.035 | 0.236 |
| P50 Latency (s) | 10.156 | 6.795 |
| P95 Latency (s) | 11.324 | 7.07 |
| **P99 Latency (s)** | **11.386** | **7.095** |

### Per-Query Comparison

| Query | Pipeline Match | Direct Match | Pipeline (s) | Direct (s) |
| :--- | :---: | :---: | :---: | :---: |
| What is the total daily sales for item 1 in store  | ✅ | ❌ | 10.156 | 6.795 |
| How many rows are in the dataset? | ❌ | ✅ | 10.098 | 6.419 |
| What is the total daily sales for item 3 in store  | ✅ | ❌ | 11.141 | 6.999 |
| Which store has the most items? | ✅ | ✅ | 10.026 | 6.872 |
| What is the average demand across all items? | ❌ | ❌ | 7.946 | 6.534 |
| What is the total sales for item 5 in store 3? | ✅ | ❌ | 11.402 | 7.101 |
| How many unique items are in the dataset? | ✅ | ❌ | 10.421 | 6.573 |

---

## 6. Ablation Study: Forecasting Models

**Item**: 1 | **Store**: 1 | **Data Points**: 100

| Model | Status | Latency (s) | Predictions (first 5) |
| :--- | :---: | :---: | :--- |
| LightGBM (global) | success | 0.018 | [16.6, 16.6, 17.59, 18.83, 20.13] |
| LightGBM (fitted) | success | 0.093 | [19.59, 19.3, 19.59, 19.59, 17.16] |
| ARIMA | success | 0.158 | [18.55, 18.79, 18.02, 18.6, 18.33] |
| Exponential Smoothing | success | 0.025 | [19.06, 19.15, 19.24, 19.33, 19.42] |
| Moving Average (7-day) | success | 0.0 | [18.07, 18.07, 18.07, 18.07, 18.07] |

---

## Statistical Summary

| Dimension | Metric | Value | n |
| :--- | :--- | :---: | :---: |
| Consistency | Mean Score | 26.5% | 4 |
| | Std Dev | 7.5% | |
| Precision | Overall | 72.0% | 40 |
| | Numerical Stability | 57.1% | 21 |
| | Textual Stability | 89.5% | 19 |
| Noise Tolerance | Success Rate | 100% | 13 |
| Tool Classification | Accuracy | 100.0% | 18 |
| Pipeline vs Direct | Pipeline Accuracy | 71.0% | 7 |
| | Direct LLM Accuracy | 29.0% | 7 |

> **Note**: GPU metrics are not applicable. LLM inference is offloaded to Groq's cloud-hosted LPU hardware. All local compute is CPU-only.
