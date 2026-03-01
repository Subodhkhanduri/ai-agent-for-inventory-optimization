# 📊 LLM Robustness Benchmarking Report

## 1. Consistency Evaluation
| Query | Trials | Uniq Responses | Consistency Score |
| :--- | :--- | :--- | :--- |
| what is the total sales for item 1 | 3 | 1 | 100.0% |
| forecast demand for item 1 in store 1 | 2 | 2 | 50.0% |

---

## 2. Noise & Typo Sensitivity
### Base Query: *what is the status of item 1 in store 1*
| Noisy Query | Success | Response Preview |
| :--- | :--- | :--- |
| wat is the statsu of itme 1 in stor 1 | ✅ | Based on the SQL query result, here's a clear and concise response:  The status of item 1 in store 1... |
| ITEM 1 STORE 1 STATUS PLS | ✅ | Based on the inventory status check for Item 1 at Store 1, the current quantity is 100, which is abo... |
| show inventory for product 1 at location 1 | ✅ | Based on the provided SQL query result, it appears that you are interested in viewing the inventory ... |


---
## Summary Findings
- **Consistency**: Measures how stable the LLM is across identical inputs.
- **Sensitivity**: Measures how well the NLP/SQL logic handles human spelling errors.
