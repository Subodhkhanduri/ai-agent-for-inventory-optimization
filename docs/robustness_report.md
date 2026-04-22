# 📊 LLM Robustness & Pipeline Stability Evaluation Report

> **Model**: Meta LLaMA 3.1 8B Instruct | **Temperature**: 0.15 | **Inference**: Groq Cloud LPU

## 1. Consistency & Latency Evaluation

### Consistency Scores

Consistency measures stability of structured outputs across repeated identical queries.

$$\text{Consistency Score} = \frac{\text{Identical Structured Outputs}}{\text{Total Trials}}$$

| Query | Trials | Unique Resp | Consistency | P50 (s) | P95 (s) | P99 (s) | Mean (s) | Std (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| what is the total sales for item 1 in store 1… | 5 | 1 | 100% | 10.865 | 18.043 | 18.124 | 11.36 | 6.307 |
| how many rows are in the dataset… | 5 | 1 | 100% | 12.361 | 12.981 | 13.077 | 11.66 | 1.773 |
| forecast demand for item 1 in store 1… | 3 | 2 | 67% | 16.313 | 16.415 | 16.424 | 16.322 | 0.082 |
| check inventory status for item 3 store 2… | 3 | 3 | 33% | 15.657 | 16.393 | 16.459 | 15.9 | 0.408 |

> **Interpretation**: Consistency here measures exact textual equivalence of the full assistant response (e.g., 'The total is 100' vs 'Total: 100'). While textual responses vary due to LLM stochasticity, the **100% Numerical Precision** now achieved across all analytical queries proves that surface-level text variability DOES NOT impact the system's ability to extract and return correct data. The decoupling of textual style from numerical accuracy is a key design strength of the SQL pipeline.

---

## 2. Precision & Accuracy Evaluation

$$\text{Precision} = \frac{\text{Correct Structured Outputs}}{\text{Total Evaluated Queries}}$$

**Overall Precision**: **90.0%** across **39 queries**

**Latency**: P50=13.291s | P95=16.205s | **P99=19.994s** | Mean=12.762s | Std=3.28s

### 2a. Numerical Stability

Queries where the expected output is a **specific number** computed deterministically via Pandas.

**Numerical Precision**: **21/21** (100.0%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Count | 5 | 5 | 100% |
| Stats | 9 | 9 | 100% |
| Sum | 7 | 7 | 100% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| How many rows are in the dataset? | 10000 | ✅ | 12.581 |
| How many unique items are in the dataset? | 20 | ✅ | 12.918 |
| How many stores are in the dataset? | 5 | ✅ | 13.335 |
| How many records exist for item 1 in store 1? | 100 | ✅ | 13.291 |
| How many different items does store 1 carry? | 20 | ✅ | 13.954 |
| What is the average demand across all items? | 16.5 | ✅ | 12.361 |
| What is the maximum daily sales value in the dataset? | 30 | ✅ | 12.09 |
| What is the total sales across all stores? | 150073 | ✅ | 14.476 |
| Total sales for store 1 | 30098 | ✅ | 13.36 |
| What are total sales for store 2? | 29904 | ✅ | 14.039 |
| Total sales in store 3 | 29865 | ✅ | 12.088 |
| Total sales for item 1 across all stores | 7643 | ✅ | 12.247 |
| What are the total sales for item 5? | 7396 | ✅ | 13.232 |
| Sum of all sales of item 10 | 7435 | ✅ | 12.255 |
| What is the total sum of daily sales for item 1 in stor | 1565 | ✅ | 13.237 |
| What is the total daily sales for item 5 in store 3? | 1437 | ✅ | 14.285 |
| Total daily sales for item 2 in store 1 | 1616 | ✅ | 13.118 |
| What are total sales for item 3 in store 2? | 1494 | ✅ | 12.172 |
| Sum of daily sales for item 10 store 4 | 1516 | ✅ | 14.555 |
| Calculate total daily sales for item 1 at store 2 | 1510 | ✅ | 14.652 |
| Show total sales for item 7 in store 5 | 1444 | ✅ | 13.006 |

### 2b. Textual Stability

Queries where the expected output is a **keyword or concept** (intent classification, forecast trigger, general knowledge).

**Textual Precision**: **14/18** (77.8%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Forecast | 4 | 3 | 75% |
| General | 4 | 3 | 75% |
| Inventory | 6 | 4 | 67% |
| Knowledge | 4 | 4 | 100% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| Forecast demand for item 1 in store 1 | demand | ✅ | 17.533 |
| Predict sales for item 2 store 3 for next 10 days | demand | ❌ | 16.057 |
| What will be the demand for item 5 in store 2 next week | demand | ✅ | 15.275 |
| Project demand for item 10 store 4 | demand | ✅ | 14.859 |
| What columns are in the dataset? | Date | ✅ | 6.952 |
| Tell me about the dataset | columns | ✅ | 8.051 |
| Describe the structure of the uploaded data | columns | ❌ | 15.438 |
| How many columns are there? | 6 | ✅ | 5.663 |
| Check inventory status for item 3 at store 2 | no action | ✅ | 21.502 |
| Should I reorder item 3 for store 2? | no action | ✅ | 14.657 |
| Is item 3 at store 2 running low? | no action | ❌ | 14.885 |
| What is the inventory status of item 1 in store 1? | no action | ✅ | 15.113 |
| Do I need to order item 1 for store 1? | no action | ❌ | 14.308 |
| Check if item 5 at store 3 needs restocking | place order | ✅ | 13.35 |
| What is a reorder point? | reorder | ✅ | 5.949 |
| Explain safety stock | safety | ✅ | 5.773 |
| What is lead time in inventory management? | lead | ✅ | 8.169 |
| What is the periodic review system? | review | ✅ | 6.942 |

### 2c. Latency Distribution

| Query Type | n | Mean (s) | Std (s) | 95% CI |
| :--- | :---: | :---: | :---: | :--- |
| Numerical | 21 | 13.203 | 0.855 | [12.837, 13.568] |
| Textual | 18 | 12.249 | 4.827 | [10.019, 14.479] |
| **Overall** | **39** | **12.762** | **3.323** | **[11.720, 13.805]** |

---

## 3. Noise & Typo Robustness

Input queries were intentionally corrupted with misspellings, capitalization changes, and synonym substitutions.

### Base Query: *what is the total daily sales of item 1 in store 1*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| wat is the totl dales sal for itme 1 in stor 1 | ✅ | 13.875 |
| ITEM 1 STORE 1 TOTAL SALES PLS | ✅ | 5.987 |
| sum of sales for product 1 at location 1 | ✅ | 14.996 |
| item:1 store:1 sales?? | ✅ | 15.091 |
| howw much did item 1 sell in store 1 | ✅ | 13.638 |
| total daily sale item#1 store#1 | ✅ | 14.209 |

### Base Query: *how many items are in the dataset*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| how mny items r in the dataset | ✅ | 16.303 |
| HOW MANY ITEMS ARE THERE | ✅ | 12.559 |
| count of unique items in data | ✅ | 14.572 |
| number of products in the dataset | ✅ | 13.643 |

### Base Query: *check inventory status for item 3 at store 2*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| chck inventery status item 3 stor 2 | ✅ | 15.944 |
| is item 3 at store 2 low on stock?? | ✅ | 14.348 |
| item3 store2 stock level check | ✅ | 16.356 |

**Overall Noise Tolerance**: 13/13 (100%)

---

## 4. Tool-Use Classification Accuracy

**Classification Accuracy**: **100.0%** (18 tests)

**End-to-end Latency**: P50=11.578s | P95=17.777s | **P99=18.271s** | Std=4.421s

| Query | Expected | Actual | Correct | Classify (s) | Total (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| What is the total sales for item 1 in store 1? | SQL | SQL | ✅ | 0.434 | 15.114 |
| How many rows are in the dataset? | SQL | SQL | ✅ | 0.392 | 12.515 |
| Show me the top 5 items by sales | SQL | SQL | ✅ | 1.378 | 17.668 |
| Which store has the highest demand? | SQL | SQL | ✅ | 0.532 | 15.696 |
| What is the average daily sales across all stores? | SQL | SQL | ✅ | 0.254 | 12.147 |
| List all items in store 2 | SQL | SQL | ✅ | 0.792 | 18.395 |
| Total quantity for item 10 in store 4 | SQL | SQL | ✅ | 0.297 | 13.307 |
| How many records exist for store 3? | SQL | SQL | ✅ | 0.29 | 11.009 |
| What is the maximum demand value? | SQL | SQL | ✅ | 0.292 | 15.78 |
| Calculate total sales for item 5 | SQL | SQL | ✅ | 0.368 | 14.294 |
| What is a reorder point? | LLM | LLM | ✅ | 0.305 | 3.781 |
| How does safety stock work? | LLM | LLM | ✅ | 0.401 | 9.646 |
| What inventory management strategy should I use? | LLM | LLM | ✅ | 1.348 | 5.321 |
| Explain the periodic review system | LLM | LLM | ✅ | 4.468 | 5.898 |
| What are the best practices for demand forecasting | LLM | LLM | ✅ | 2.317 | 8.327 |
| How can I reduce stockouts? | LLM | LLM | ✅ | 5.468 | 6.123 |
| What is the difference between continuous and peri | LLM | LLM | ✅ | 1.47 | 7.441 |
| Tell me about ABC analysis | LLM | LLM | ✅ | 1.45 | 7.081 |

---

## 5. Ablation Study: NLP Pipeline vs Direct LLM (Two Baselines)

| Metric | NLP Pipeline | Direct LLM (20-row context) | Direct LLM (summary stats) |
| :--- | :---: | :---: | :---: |
| **Accuracy** | 90.0% | 38.0% | 74.0% |
| Mean Latency (s) | 12.812 | 6.908 | 16.529 |
| Std Latency (s) | 4.409 | 1.802 | 2.257 |
| P50 Latency (s) | 13.327 | 6.86 | 16.193 |
| P95 Latency (s) | 18.756 | 9.845 | 19.908 |
| **P99 Latency (s)** | **20.683** | **10.101** | **20.828** |

### Per-Query Comparison

| Query | Pipeline | Direct-20row | Direct-Summary | Pipeline (s) | Direct-20 (s) | Direct-Sum (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| What is the total sum of daily sales for item 1 in | ✅ | ❌ | ✅ | 14.289 | 8.485 | 15.814 |
| What is the total daily sales for item 5 in store  | ✅ | ❌ | ❌ | 13.447 | 6.896 | 13.568 |
| Total daily sales for item 2 in store 1 | ✅ | ❌ | ✅ | 15.569 | 3.869 | 17.796 |
| What are total sales for item 3 in store 2? | ✅ | ❌ | ✅ | 13.458 | 6.219 | 18.553 |
| Sum of daily sales for item 10 store 4 | ✅ | ❌ | ✅ | 13.327 | 6.945 | 16.542 |
| Calculate total daily sales for item 1 at store 2 | ✅ | ❌ | ✅ | 13.198 | 8.809 | 18.702 |
| Show total sales for item 7 in store 5 | ✅ | ❌ | ❌ | 16.657 | 5.041 | 17.556 |
| How many rows are in the dataset? | ✅ | ✅ | ✅ | 11.438 | 6.598 | 13.848 |
| How many unique items are in the dataset? | ✅ | ❌ | ✅ | 12.269 | 7.446 | 13.573 |
| How many stores are in the dataset? | ✅ | ✅ | ✅ | 14.302 | 5.085 | 18.551 |
| How many records exist for item 1 in store 1? | ✅ | ❌ | ❌ | 13.412 | 4.838 | 19.755 |
| How many different items does store 1 carry? | ✅ | ✅ | ✅ | 9.177 | 6.026 | 16.886 |
| What is the average demand across all items? | ✅ | ✅ | ✅ | 11.813 | 9.844 | 15.523 |
| What is the maximum daily sales value in the datas | ✅ | ❌ | ✅ | 13.095 | 6.838 | 13.715 |
| What is the total sales across all stores? | ✅ | ❌ | ✅ | 12.908 | 4.428 | 14.89 |
| Total sales for store 1 | ✅ | ❌ | ✅ | 11.092 | 6.374 | 15.518 |
| What are total sales for store 2? | ✅ | ❌ | ✅ | 14.329 | 4.843 | 21.22 |
| Total sales in store 3 | ✅ | ❌ | ✅ | 12.681 | 5.085 | 18.664 |
| Total sales for item 1 across all stores | ✅ | ❌ | ✅ | 12.275 | 9.619 | 13.787 |
| What are the total sales for item 5? | ✅ | ❌ | ✅ | 17.378 | 3.857 | 19.573 |
| Sum of all sales of item 10 | ✅ | ❌ | ✅ | 10.768 | 8.16 | 17.978 |
| Check inventory status for item 3 at store 2 | ✅ | ❌ | ❌ | 20.524 | 6.962 | 15.578 |
| Should I reorder item 3 for store 2? | ✅ | ❌ | ❌ | 13.457 | 7.654 | 15.309 |
| Is item 3 at store 2 running low? | ❌ | ❌ | ❌ | 16.846 | 9.854 | 16.107 |
| What is the inventory status of item 1 in store 1? | ✅ | ❌ | ❌ | 4.903 | 8.12 | 18.619 |
| Do I need to order item 1 for store 1? | ❌ | ❌ | ❌ | 20.781 | 5.668 | 13.673 |
| Check if item 5 at store 3 needs restocking | ✅ | ❌ | ❌ | 18.56 | 7.134 | 19.023 |
| Forecast demand for item 1 in store 1 | ✅ | ✅ | ✅ | 18.274 | 9.35 | 16.193 |
| Predict sales for item 2 store 3 for next 10 days | ❌ | ❌ | ❌ | 18.514 | 10.252 | 19.877 |
| What will be the demand for item 5 in store 2 next | ✅ | ✅ | ✅ | 14.84 | 4.348 | 20.189 |
| Project demand for item 10 store 4 | ✅ | ✅ | ✅ | 17.538 | 4.911 | 18.469 |
| What columns are in the dataset? | ✅ | ✅ | ✅ | 3.689 | 8.607 | 13.623 |
| Tell me about the dataset | ✅ | ✅ | ✅ | 9.545 | 5.476 | 18.211 |
| Describe the structure of the uploaded data | ❌ | ✅ | ✅ | 15.312 | 6.848 | 13.925 |
| How many columns are there? | ✅ | ✅ | ✅ | 9.792 | 5.871 | 13.512 |
| What is a reorder point? | ✅ | ✅ | ✅ | 2.896 | 8.634 | 13.836 |
| Explain safety stock | ✅ | ✅ | ✅ | 5.036 | 9.701 | 16.58 |
| What is lead time in inventory management? | ✅ | ✅ | ✅ | 6.955 | 7.87 | 15.093 |
| What is the periodic review system? | ✅ | ✅ | ✅ | 5.306 | 6.86 | 14.79 |

---

## 6. Ablation Study: Forecasting Models

**Item**: 1 | **Store**: 1 | **Data Points**: 100

| Model | Status | Latency (s) | Predictions (first 5) |
| :--- | :---: | :---: | :--- |
| LightGBM (global) | success | 0.016 | [16.6, 16.6, 17.59, 18.83, 20.13] |
| LightGBM (fitted) | success | 0.256 | [19.59, 19.3, 19.59, 19.59, 17.16] |
| ARIMA | success | 0.491 | [18.55, 18.79, 18.02, 18.6, 18.33] |
| Exponential Smoothing | success | 0.06 | [19.06, 19.15, 19.24, 19.33, 19.42] |
| Moving Average (7-day) | success | 0.001 | [18.07, 18.07, 18.07, 18.07, 18.07] |

---

## Statistical Summary

| Dimension | Metric | Value | n |
| :--- | :--- | :---: | :---: |
| Consistency | Mean Score | 75.0% | 4 |
| | Std Dev | 32.0% | |
| Precision | Overall | 90.0% | 39 |
| | Numerical Stability | 100.0% | 21 |
| | Textual Stability | 77.8% | 18 |
| Noise Tolerance | Success Rate | 100% | 13 |
| Tool Classification | Accuracy | 100.0% | 18 |
| Pipeline vs Direct | Pipeline Accuracy | 90.0% | 39 |
| | Direct LLM Accuracy | 38.0% | 39 |

> **Note**: GPU metrics are not applicable. LLM inference is offloaded to Groq's cloud-hosted LPU hardware. All local compute is CPU-only.
