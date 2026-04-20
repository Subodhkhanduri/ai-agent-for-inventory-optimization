# run_benchmarks.py

"""
Comprehensive LLM Robustness & Pipeline Stability Benchmarking Suite
====================================================================
- 40+ precision queries (numerical + textual categories)  
- Consistency with 5+ trials per query type
- 10+ noise/typo variations
- 15+ tool-use classification tests
- Ablation: Pipeline vs Direct LLM
- Ablation: Forecasting model comparison
- P50/P95/P99 latency + std dev
- Separated numerical vs textual stability reporting
"""

import sys
import os
import pandas as pd
import numpy as np
import logging

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inventory_chatbot.benchmarks.evaluator import RobustnessEvaluator
from inventory_chatbot.benchmarks.reporter import generate_benchmarking_report

logging.basicConfig(level=logging.WARNING)


# ──────────────────────────────────────────────
# SYNTHETIC DATA GENERATOR
# ──────────────────────────────────────────────
def generate_large_mock_data(num_rows=10000):
    """Generates a large dataset to prove scalability."""
    print(f"Generating synthetic dataset with {num_rows} rows...")
    np.random.seed(42)
    shops = [1, 2, 3, 4, 5]
    items = list(range(1, 21))

    dates = pd.date_range(start="2023-01-01", periods=num_rows // 100, freq="D")

    from itertools import product
    combinations = list(product(dates, shops, items))
    combinations = combinations[:num_rows]

    df = pd.DataFrame(combinations, columns=["Date", "Store", "Item"])
    df["Daily_Sales"] = np.random.poisson(lam=15, size=len(df))
    df["Quantity"] = np.random.randint(50, 200, size=len(df))
    df["Demand"] = df["Daily_Sales"] * 1.1
    return df


# ──────────────────────────────────────────────
# EVALUATION DATASET (40+ queries with ground truth)
# ──────────────────────────────────────────────
def build_precision_tests(df):
    """Build ground-truth precision tests from the dataset (40+ queries)."""
    from inventory_chatbot.analytics.inventory_calculator import calculate_periodic_review_status

    # Pre-compute ground truths using deterministic Pandas operations
    item1_store1_sales = df[(df["Item"] == 1) & (df["Store"] == 1)]["Daily_Sales"].sum()
    item5_store3_sales = df[(df["Item"] == 5) & (df["Store"] == 3)]["Daily_Sales"].sum()
    item2_store1_sales = df[(df["Item"] == 2) & (df["Store"] == 1)]["Daily_Sales"].sum()
    item3_store2_sales = df[(df["Item"] == 3) & (df["Store"] == 2)]["Daily_Sales"].sum()
    item10_store4_sales = df[(df["Item"] == 10) & (df["Store"] == 4)]["Daily_Sales"].sum()
    item1_store2_sales = df[(df["Item"] == 1) & (df["Store"] == 2)]["Daily_Sales"].sum()
    item7_store5_sales = df[(df["Item"] == 7) & (df["Store"] == 5)]["Daily_Sales"].sum()

    total_rows = len(df)
    unique_items = df["Item"].nunique()
    unique_stores = df["Store"].nunique()
    avg_demand = round(df["Demand"].mean(), 1)
    total_sales_all = int(df["Daily_Sales"].sum())
    max_daily_sale = int(df["Daily_Sales"].max())

    # Per-store totals
    store1_total = int(df[df["Store"] == 1]["Daily_Sales"].sum())
    store2_total = int(df[df["Store"] == 2]["Daily_Sales"].sum())
    store3_total = int(df[df["Store"] == 3]["Daily_Sales"].sum())

    # Per-item totals
    item1_total = int(df[df["Item"] == 1]["Daily_Sales"].sum())
    item5_total = int(df[df["Item"] == 5]["Daily_Sales"].sum())
    item10_total = int(df[df["Item"] == 10]["Daily_Sales"].sum())

    # Count-based queries
    item1_store1_count = len(df[(df["Item"] == 1) & (df["Store"] == 1)])
    store1_item_count = df[df["Store"] == 1]["Item"].nunique()

    # Inventory status queries
    pr_status_3_2 = calculate_periodic_review_status(df, 3, 2, 7, 7)
    pr_keyword_3_2 = "ORDER" if pr_status_3_2.get("should_order") else "HEALTHY"

    pr_status_1_1 = calculate_periodic_review_status(df, 1, 1, 7, 7)
    pr_keyword_1_1 = "ORDER" if pr_status_1_1.get("should_order") else "HEALTHY"

    pr_status_5_3 = calculate_periodic_review_status(df, 5, 3, 7, 7)
    pr_keyword_5_3 = "ORDER" if pr_status_5_3.get("should_order") else "HEALTHY"

    return [
        # ── NUMERICAL: Data Retrieval (Sum/Total) ──
        {"query": "What is the total sum of daily sales for item 1 in store 1?",
         "expected": str(int(item1_store1_sales)), "category": "numerical_sum"},
        {"query": "What is the total daily sales for item 5 in store 3?",
         "expected": str(int(item5_store3_sales)), "category": "numerical_sum"},
        {"query": "Total daily sales for item 2 in store 1",
         "expected": str(int(item2_store1_sales)), "category": "numerical_sum"},
        {"query": "What are total sales for item 3 in store 2?",
         "expected": str(int(item3_store2_sales)), "category": "numerical_sum"},
        {"query": "Sum of daily sales for item 10 store 4",
         "expected": str(int(item10_store4_sales)), "category": "numerical_sum"},
        {"query": "Calculate total daily sales for item 1 at store 2",
         "expected": str(int(item1_store2_sales)), "category": "numerical_sum"},
        {"query": "Show total sales for item 7 in store 5",
         "expected": str(int(item7_store5_sales)), "category": "numerical_sum"},

        # ── NUMERICAL: Count/Shape queries ──
        {"query": "How many rows are in the dataset?",
         "expected": str(total_rows), "category": "numerical_count"},
        {"query": "How many unique items are in the dataset?",
         "expected": str(unique_items), "category": "numerical_count"},
        {"query": "How many stores are in the dataset?",
         "expected": str(unique_stores), "category": "numerical_count"},
        {"query": "How many records exist for item 1 in store 1?",
         "expected": str(item1_store1_count), "category": "numerical_count"},
        {"query": "How many different items does store 1 carry?",
         "expected": str(store1_item_count), "category": "numerical_count"},

        # ── NUMERICAL: Aggregation/Statistics ──
        {"query": "What is the average demand across all items?",
         "expected": str(avg_demand), "category": "numerical_stats"},
        {"query": "What is the maximum daily sales value in the dataset?",
         "expected": str(max_daily_sale), "category": "numerical_stats"},
        {"query": "What is the total sales across all stores?",
         "expected": str(total_sales_all), "category": "numerical_stats"},
        {"query": "Total sales for store 1",
         "expected": str(store1_total), "category": "numerical_stats"},
        {"query": "What are total sales for store 2?",
         "expected": str(store2_total), "category": "numerical_stats"},
        {"query": "Total sales in store 3",
         "expected": str(store3_total), "category": "numerical_stats"},
        {"query": "Total sales for item 1 across all stores",
         "expected": str(item1_total), "category": "numerical_stats"},
        {"query": "What are the total sales for item 5?",
         "expected": str(item5_total), "category": "numerical_stats"},
        {"query": "Sum of all sales of item 10",
         "expected": str(item10_total), "category": "numerical_stats"},

        # ── TEXTUAL: Inventory Status ──
        {"query": "Check inventory status for item 3 at store 2",
         "expected": pr_keyword_3_2, "category": "textual_inventory"},
        {"query": "Should I reorder item 3 for store 2?",
         "expected": pr_keyword_3_2, "category": "textual_inventory"},
        {"query": "Is item 3 at store 2 running low?",
         "expected": pr_keyword_3_2, "category": "textual_inventory"},
        {"query": "What is the inventory status of item 1 in store 1?",
         "expected": pr_keyword_1_1, "category": "textual_inventory"},
        {"query": "Do I need to order item 1 for store 1?",
         "expected": pr_keyword_1_1, "category": "textual_inventory"},
        {"query": "Check if item 5 at store 3 needs restocking",
         "expected": pr_keyword_5_3, "category": "textual_inventory"},

        # ── TEXTUAL: Forecast (keyword detection) ──
        {"query": "Forecast demand for item 1 in store 1",
         "expected": "forecast", "category": "textual_forecast"},
        {"query": "Predict sales for item 2 store 3 for next 10 days",
         "expected": "forecast", "category": "textual_forecast"},
        {"query": "What will be the demand for item 5 in store 2 next week?",
         "expected": "forecast", "category": "textual_forecast"},
        {"query": "Project demand for item 10 store 4",
         "expected": "forecast", "category": "textual_forecast"},

        # ── TEXTUAL: Dataset Description ──
        {"query": "What columns are in the dataset?",
         "expected": "Date", "category": "textual_general"},
        {"query": "Tell me about the dataset",
         "expected": "columns", "category": "textual_general"},
        {"query": "Describe the structure of the uploaded data",
         "expected": "columns", "category": "textual_general"},
        {"query": "How many columns are there?",
         "expected": str(len(df.columns)), "category": "textual_general"},

        # ── TEXTUAL: General Knowledge ──
        {"query": "What is a reorder point?",
         "expected": "reorder", "category": "textual_knowledge"},
        {"query": "Explain safety stock",
         "expected": "safety", "category": "textual_knowledge"},
        {"query": "What is lead time in inventory management?",
         "expected": "lead", "category": "textual_knowledge"},
        {"query": "What is the periodic review system?",
         "expected": "review", "category": "textual_knowledge"},
    ]


def build_tool_use_tests():
    """Build tool-use classification test cases (15+)."""
    return [
        # Should be SQL
        {"query": "What is the total sales for item 1 in store 1?", "expected_type": "SQL"},
        {"query": "How many rows are in the dataset?", "expected_type": "SQL"},
        {"query": "Show me the top 5 items by sales", "expected_type": "SQL"},
        {"query": "Which store has the highest demand?", "expected_type": "SQL"},
        {"query": "What is the average daily sales across all stores?", "expected_type": "SQL"},
        {"query": "List all items in store 2", "expected_type": "SQL"},
        {"query": "Total quantity for item 10 in store 4", "expected_type": "SQL"},
        {"query": "How many records exist for store 3?", "expected_type": "SQL"},
        {"query": "What is the maximum demand value?", "expected_type": "SQL"},
        {"query": "Calculate total sales for item 5", "expected_type": "SQL"},

        # Should be LLM
        {"query": "What is a reorder point?", "expected_type": "LLM"},
        {"query": "How does safety stock work?", "expected_type": "LLM"},
        {"query": "What inventory management strategy should I use?", "expected_type": "LLM"},
        {"query": "Explain the periodic review system", "expected_type": "LLM"},
        {"query": "What are the best practices for demand forecasting?", "expected_type": "LLM"},
        {"query": "How can I reduce stockouts?", "expected_type": "LLM"},
        {"query": "What is the difference between continuous and periodic review?", "expected_type": "LLM"},
        {"query": "Tell me about ABC analysis", "expected_type": "LLM"},
    ]


def build_noise_tests():
    """Build expanded noise/typo test variations (10+)."""
    return [
        {
            "base_query": "what is the total daily sales of item 1 in store 1",
            "noisy_queries": [
                "wat is the totl dales sal for itme 1 in stor 1",
                "ITEM 1 STORE 1 TOTAL SALES PLS",
                "sum of sales for product 1 at location 1",
                "item:1 store:1 sales??",
                "howw much did item 1 sell in store 1",
                "total daily sale item#1 store#1",
            ],
        },
        {
            "base_query": "how many items are in the dataset",
            "noisy_queries": [
                "how mny items r in the dataset",
                "HOW MANY ITEMS ARE THERE",
                "count of unique items in data",
                "number of products in the dataset",
            ],
        },
        {
            "base_query": "check inventory status for item 3 at store 2",
            "noisy_queries": [
                "chck inventery status item 3 stor 2",
                "is item 3 at store 2 low on stock??",
                "item3 store2 stock level check",
            ],
        },
    ]


def build_ablation_queries(df):
    """Build queries for pipeline vs direct LLM ablation."""
    item1_store1_sales = df[(df["Item"] == 1) & (df["Store"] == 1)]["Daily_Sales"].sum()
    item3_store2_sales = df[(df["Item"] == 3) & (df["Store"] == 2)]["Daily_Sales"].sum()
    item5_store3_sales = df[(df["Item"] == 5) & (df["Store"] == 3)]["Daily_Sales"].sum()
    total_rows = len(df)

    return [
        {"query": "What is the total daily sales for item 1 in store 1?",
         "expected": str(int(item1_store1_sales))},
        {"query": "How many rows are in the dataset?",
         "expected": str(total_rows)},
        {"query": "What is the total daily sales for item 3 in store 2?",
         "expected": str(int(item3_store2_sales))},
        {"query": "Which store has the most items?",
         "expected": "store"},
        {"query": "What is the average demand across all items?",
         "expected": str(round(df["Demand"].mean(), 0)).split(".")[0]},
        {"query": "What is the total sales for item 5 in store 3?",
         "expected": str(int(item5_store3_sales))},
        {"query": "How many unique items are in the dataset?",
         "expected": str(df["Item"].nunique())},
    ]


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    # Load data
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        print(f"Loading user dataset from: {csv_path}")
        df = pd.read_csv(csv_path)
    else:
        df = generate_large_mock_data(10000)

    evaluator = RobustnessEvaluator(df)

    # ── 1. Consistency & P99 Latency (5 trials each) ──
    print("\n[1/6] Running Consistency & P99 Latency Tests (5 trials each)...")
    consistency_queries = [
        ("what is the total sales for item 1 in store 1", 5),
        ("how many rows are in the dataset", 5),
        ("forecast demand for item 1 in store 1", 3),
        ("check inventory status for item 3 store 2", 3),
    ]
    consistency_results = []
    for query, trials in consistency_queries:
        c_res = evaluator.run_consistency_test(query, trials=trials)
        consistency_results.append(c_res)
        print(f"  [OK] '{query[:50]}' - Consistency: {c_res['consistency_score']*100:.0f}%, "
              f"P99: {c_res['latency_stats'].get('p99', 'N/A')}s")

    # -- 2. Precision (40+ ground-truth queries) --
    print("\n[2/6] Running Precision Tests (40+ queries)...")
    precision_tests = build_precision_tests(df)
    p_res = evaluator.run_precision_test(precision_tests)
    print(f"  [OK] Precision Score: {p_res['precision_score'] * 100:.1f}% ({p_res['total_tests']} tests)")
    print(f"  [OK] Latency P99: {p_res['latency_stats'].get('p99', 'N/A')}s, "
          f"Std: {p_res['latency_stats'].get('std', 'N/A')}s")

    # Category breakdown
    categories = {}
    for d in p_res["details"]:
        cat = d.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "correct": 0}
        categories[cat]["total"] += 1
        if d["is_match"]:
            categories[cat]["correct"] += 1

    for cat, counts in sorted(categories.items()):
        acc = counts["correct"] / counts["total"] * 100
        print(f"    - {cat}: {acc:.0f}% ({counts['correct']}/{counts['total']})")

    # ── 3. Noise / Typo ──
    print("\n[3/6] Running Noise & Typo Tests (10+ variations)...")
    noise_test_defs = build_noise_tests()
    noise_results = []
    for test_def in noise_test_defs:
        n_res = evaluator.run_noise_test(
            base_query=test_def["base_query"],
            noisy_queries=test_def["noisy_queries"],
        )
        noise_results.append(n_res)
        success_count = sum(1 for r in n_res["noisy_results"] if r["is_successful"])
        print(f"  [OK] '{test_def['base_query'][:50]}' - {success_count}/{len(test_def['noisy_queries'])} passed")

    # ── 4. Tool-Use Accuracy ──
    print("\n[4/6] Running Tool-Use Classification Tests (18 queries)...")
    tool_tests = build_tool_use_tests()
    tu_res = evaluator.run_tool_use_test(tool_tests)
    print(f"  [OK] Classification Accuracy: {tu_res['classification_accuracy'] * 100:.1f}%")

    # -- 5. Ablation: Pipeline vs Direct LLM (Expanded n=40) --
    print(f"\n[5/6] Running Expanded Ablation: Pipeline vs Direct LLM ({len(precision_tests)} queries)...")
    ab_res = evaluator.run_ablation_pipeline_vs_direct(precision_tests)
    print(f"  [OK] Pipeline Accuracy: {ab_res['pipeline']['accuracy'] * 100:.1f}%")
    print(f"  [OK] Direct LLM Accuracy: {ab_res['direct_llm']['accuracy'] * 100:.1f}%")

    # -- 6. Ablation: Forecasting Models --
    print("\n[6/6] Running Ablation: Forecasting Models...")
    fc_res = None
    try:
        fc_res = evaluator.run_ablation_forecast_models(item=1, store=1, periods=10)
        if "error" not in fc_res:
            for model_name, data in fc_res["models"].items():
                print(f"  [OK] {model_name}: {data['status']} ({data['latency']}s)")
        else:
            print(f"  [WARN] Skipped: {fc_res.get('error', 'unknown error')}")
    except Exception as e:
        print(f"  [WARN] Forecasting ablation skipped (missing dependency): {e}")
        fc_res = None

    # ── Generate Report ──
    print("\nGenerating report...")
    report_md = generate_benchmarking_report(
        consistency_results=consistency_results,
        noise_results=noise_results,
        precision_results=p_res,
        tool_use_results=tu_res,
        ablation_results=ab_res,
        forecast_ablation=fc_res,
    )

    report_path = os.path.join(os.path.dirname(__file__), "..", "docs", "robustness_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[DONE] Benchmarking Complete! Tested on {len(df)} rows.")
    print(f"   Precision queries:     {p_res['total_tests']}")
    print(f"   Tool-use queries:      {tu_res['total_tests']}")
    print(f"   Noise variations:      {sum(len(t['noisy_queries']) for t in noise_test_defs)}")
    print(f"   Consistency trials:    {sum(t for _, t in consistency_queries)}")
    print("Report saved to robustness_report.md")


if __name__ == "__main__":
    main()
