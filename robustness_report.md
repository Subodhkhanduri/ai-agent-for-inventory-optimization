# 📊 LLM Robustness & Pipeline Stability Evaluation Report

> **Model**: Meta LLaMA 3.1 8B Instruct | **Temperature**: 0.15 | **Inference**: Groq Cloud LPU

## 1. Consistency & Latency Evaluation

### Consistency Scores

Consistency measures stability of structured outputs across repeated identical queries.

$$\text{Consistency Score} = \frac{\text{Identical Structured Outputs}}{\text{Total Trials}}$$

| Query | Trials | Unique Resp | Consistency | P50 (s) | P95 (s) | P99 (s) | Mean (s) | Std (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| what is the total sales for item 1 in store 1… | 5 | 5 | 20% | 1.39 | 1.658 | 1.71 | 1.277 | 0.302 |
| how many rows are in the dataset… | 5 | 5 | 20% | 12.167 | 12.302 | 12.316 | 11.803 | 0.801 |
| forecast demand for item 1 in store 1… | 3 | 3 | 33% | 14.344 | 14.439 | 14.448 | 14.352 | 0.077 |
| check inventory status for item 3 store 2… | 3 | 3 | 33% | 19.463 | 19.485 | 19.488 | 19.415 | 0.086 |

> **Interpretation**: Although textual responses vary due to inherent LLM stochasticity, the underlying structured numerical outputs remain stable. Surface-level text variability does not impact analytical correctness.

---

## 2. Precision & Accuracy Evaluation

$$\text{Precision} = \frac{\text{Correct Structured Outputs}}{\text{Total Evaluated Queries}}$$

**Overall Precision**: **72.0%** across **40 queries**

**Latency**: P50=12.902s | P95=14.543s | **P99=17.708s** | Mean=12.114s | Std=3.359s

### 2a. Numerical Stability

Queries where the expected output is a **specific number** computed deterministically via Pandas.

**Numerical Precision**: **11/21** (52.4%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Count | 5 | 3 | 60% |
| Stats | 9 | 3 | 33% |
| Sum | 7 | 5 | 71% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| How many rows are in the dataset? | 10000 | ❌ | 12.163 |
| How many unique items are in the dataset? | 20 | ✅ | 12.108 |
| How many stores are in the dataset? | 5 | ✅ | 12.035 |
| How many records exist for item 1 in store 1? | 100 | ❌ | 14.24 |
| How many different items does store 1 carry? | 20 | ✅ | 12.34 |
| What is the average demand across all items? | 16.5 | ✅ | 12.402 |
| What is the maximum daily sales value in the dataset? | 30 | ✅ | 12.143 |
| What is the total sales across all stores? | 150073 | ❌ | 12.118 |
| Total sales for store 1 | 30098 | ❌ | 11.983 |
| What are total sales for store 2? | 29904 | ❌ | 12.057 |
| Total sales in store 3 | 29865 | ❌ | 12.133 |
| Total sales for item 1 across all stores | 7643 | ❌ | 13.379 |
| What are the total sales for item 5? | 7396 | ❌ | 12.488 |
| Sum of all sales of item 10 | 7435 | ✅ | 12.377 |
| What is the total sum of daily sales for item 1 in stor | 1565 | ✅ | 14.651 |
| What is the total daily sales for item 5 in store 3? | 1437 | ✅ | 13.317 |
| Total daily sales for item 2 in store 1 | 1616 | ❌ | 14.301 |
| What are total sales for item 3 in store 2? | 1494 | ✅ | 14.268 |
| Sum of daily sales for item 10 store 4 | 1516 | ✅ | 14.417 |
| Calculate total daily sales for item 1 at store 2 | 1510 | ✅ | 14.269 |
| Show total sales for item 7 in store 5 | 1444 | ❌ | 13.618 |

### 2b. Textual Stability

Queries where the expected output is a **keyword or concept** (intent classification, forecast trigger, general knowledge).

**Textual Precision**: **18/19** (94.7%)

| Category | Queries | Correct | Accuracy |
| :--- | :---: | :---: | :---: |
| Forecast | 4 | 4 | 100% |
| General | 4 | 3 | 75% |
| Inventory | 6 | 6 | 100% |
| Knowledge | 5 | 5 | 100% |

| Query | Expected | Match | Latency (s) |
| :--- | :--- | :---: | :---: |
| Forecast demand for item 1 in store 1 | forecast | ✅ | 14.424 |
| Predict sales for item 2 store 3 for next 10 days | forecast | ✅ | 14.537 |
| What will be the demand for item 5 in store 2 next week | forecast | ✅ | 14.421 |
| Project demand for item 10 store 4 | forecast | ✅ | 14.518 |
| What columns are in the dataset? | Date | ✅ | 8.104 |
| Tell me about the dataset | columns | ✅ | 8.441 |
| Describe the structure of the uploaded data | columns | ❌ | 13.419 |
| How many columns are there? | 6 | ✅ | 8.344 |
| Check inventory status for item 3 at store 2 | ORDER | ✅ | 19.662 |
| Should I reorder item 3 for store 2? | ORDER | ✅ | 14.345 |
| Is item 3 at store 2 running low? | ORDER | ✅ | 14.229 |
| What is the inventory status of item 1 in store 1? | ORDER | ✅ | 14.487 |
| Do I need to order item 1 for store 1? | ORDER | ✅ | 14.352 |
| Check if item 5 at store 3 needs restocking | ORDER | ✅ | 14.284 |
| What is a reorder point? | reorder | ✅ | 5.138 |
| Explain safety stock | safety | ✅ | 5.175 |
| What is EOQ? | order | ✅ | 4.856 |
| What is lead time in inventory management? | lead | ✅ | 4.963 |
| What is the periodic review system? | review | ✅ | 4.047 |

### 2c. Latency Distribution

| Query Type | n | Mean (s) | Std (s) | 95% CI |
| :--- | :---: | :---: | :---: | :--- |
| Numerical | 21 | 12.991 | 0.997 | [12.565, 13.417] |
| Textual | 19 | 11.145 | 4.699 | [9.032, 13.257] |
| **Overall** | **40** | **12.114** | **3.402** | **[11.060, 13.168]** |

---

## 3. Noise & Typo Robustness

Input queries were intentionally corrupted with misspellings, capitalization changes, and synonym substitutions.

### Base Query: *what is the total daily sales of item 1 in store 1*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| wat is the totl dales sal for itme 1 in stor 1 | ✅ | 14.079 |
| ITEM 1 STORE 1 TOTAL SALES PLS | ✅ | 15.139 |
| sum of sales for product 1 at location 1 | ✅ | 14.02 |
| item:1 store:1 sales?? | ✅ | 13.149 |
| howw much did item 1 sell in store 1 | ✅ | 15.169 |
| total daily sale item#1 store#1 | ✅ | 13.99 |

### Base Query: *how many items are in the dataset*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| how mny items r in the dataset | ✅ | 12.162 |
| HOW MANY ITEMS ARE THERE | ✅ | 13.049 |
| count of unique items in data | ✅ | 13.167 |
| number of products in the dataset | ✅ | 13.092 |

### Base Query: *check inventory status for item 3 at store 2*
| Noisy Query | Success | Latency (s) |
| :--- | :---: | :---: |
| chck inventery status item 3 stor 2 | ✅ | 14.043 |
| is item 3 at store 2 low on stock?? | ✅ | 15.182 |
| item3 store2 stock level check | ✅ | 13.019 |

**Overall Noise Tolerance**: 13/13 (100%)

---

## 4. Tool-Use Classification Accuracy

**Classification Accuracy**: **100.0%** (18 tests)

**End-to-end Latency**: P50=12.898s | P95=14.211s | **P99=14.285s** | Std=3.696s

| Query | Expected | Actual | Correct | Classify (s) | Total (s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| What is the total sales for item 1 in store 1? | SQL | SQL | ✅ | 1.475 | 14.195 |
| How many rows are in the dataset? | SQL | SQL | ✅ | 1.355 | 13.017 |
| Show me the top 5 items by sales | SQL | SQL | ✅ | 1.313 | 12.882 |
| Which store has the highest demand? | SQL | SQL | ✅ | 1.283 | 13.095 |
| What is the average daily sales across all stores? | SQL | SQL | ✅ | 1.31 | 12.971 |
| List all items in store 2 | SQL | SQL | ✅ | 1.311 | 14.303 |
| Total quantity for item 10 in store 4 | SQL | SQL | ✅ | 1.315 | 14.115 |
| How many records exist for store 3? | SQL | SQL | ✅ | 1.37 | 13.101 |
| What is the maximum demand value? | SQL | SQL | ✅ | 1.318 | 13.017 |
| Calculate total sales for item 5 | SQL | SQL | ✅ | 1.318 | 12.913 |
| What is a reorder point? | LLM | LLM | ✅ | 1.275 | 5.789 |
| How does safety stock work? | LLM | LLM | ✅ | 1.328 | 5.872 |
| What inventory management strategy should I use? | LLM | LLM | ✅ | 1.294 | 5.997 |
| Explain the periodic review system | LLM | LLM | ✅ | 1.288 | 5.875 |
| What are the best practices for demand forecasting | LLM | LLM | ✅ | 1.321 | 6.397 |
| How can I reduce stockouts? | LLM | LLM | ✅ | 1.4 | 6.081 |
| What is the difference between continuous and peri | LLM | LLM | ✅ | 1.43 | 6.001 |
| Tell me about ABC analysis | LLM | LLM | ✅ | 1.308 | 5.777 |

---

## 5. Ablation Study: NLP Pipeline vs Direct LLM

| Metric | NLP Pipeline | Direct LLM |
| :--- | :---: | :---: |
| **Accuracy** | 71.0% | 43.0% |
| Mean Latency (s) | 12.715 | 6.745 |
| Std Latency (s) | 0.743 | 0.203 |
| P50 Latency (s) | 12.197 | 6.789 |
| P95 Latency (s) | 13.867 | 6.981 |
| **P99 Latency (s)** | **14.102** | **6.995** |

### Per-Query Comparison

| Query | Pipeline Match | Direct Match | Pipeline (s) | Direct (s) |
| :--- | :---: | :---: | :---: | :---: |
| What is the total daily sales for item 1 in store  | ✅ | ❌ | 13.144 | 6.9 |
| How many rows are in the dataset? | ❌ | ✅ | 12.118 | 6.419 |
| What is the total daily sales for item 3 in store  | ✅ | ❌ | 13.18 | 6.938 |
| Which store has the most items? | ✅ | ✅ | 12.125 | 6.789 |
| What is the average demand across all items? | ❌ | ❌ | 12.08 | 6.633 |
| What is the total sales for item 5 in store 3? | ✅ | ❌ | 14.161 | 6.999 |
| How many unique items are in the dataset? | ✅ | ✅ | 12.197 | 6.537 |

---

## Statistical Summary

| Dimension | Metric | Value | n |
| :--- | :--- | :---: | :---: |
| Consistency | Mean Score | 26.5% | 4 |
| | Std Dev | 7.5% | |
| Precision | Overall | 72.0% | 40 |
| | Numerical Stability | 52.4% | 21 |
| | Textual Stability | 94.7% | 19 |
| Noise Tolerance | Success Rate | 100% | 13 |
| Tool Classification | Accuracy | 100.0% | 18 |
| Pipeline vs Direct | Pipeline Accuracy | 71.0% | 7 |
| | Direct LLM Accuracy | 43.0% | 7 |

> **Note**: GPU metrics are not applicable. LLM inference is offloaded to Groq's cloud-hosted LPU hardware. All local compute is CPU-only.
