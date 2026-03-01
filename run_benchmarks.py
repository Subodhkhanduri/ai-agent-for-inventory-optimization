# run_benchmarks.py

import pandas as pd
import logging
from inventory_chatbot.benchmarks.evaluator import RobustnessEvaluator
from inventory_chatbot.benchmarks.reporter import generate_benchmarking_report

# Setup logging to be quiet
logging.basicConfig(level=logging.WARNING)

def main():
    # 1. Mock/Sample data
    data = {
        "Date": pd.date_range(start="2023-01-01", periods=20, freq="D"),
        "Daily_Sales": [10, 12, 11, 15, 14, 13, 16, 12, 11, 10, 11, 13, 12, 14, 15, 16, 10, 11, 12, 13],
        "item": [1] * 20,
        "store": [1] * 20,
        "Quantity": [100] * 20
    }
    df = pd.DataFrame(data)
    
    evaluator = RobustnessEvaluator(df)
    
    print("Starting Consistency Tests...")
    c_res1 = evaluator.run_consistency_test("what is the total sales for item 1", trials=3)
    c_res2 = evaluator.run_consistency_test("forecast demand for item 1 in store 1", trials=2)
    
    print("Starting Noise Tests...")
    n_res1 = evaluator.run_noise_test(
        base_query="what is the status of item 1 in store 1",
        noisy_queries=[
            "wat is the statsu of itme 1 in stor 1",
            "ITEM 1 STORE 1 STATUS PLS",
            "show inventory for product 1 at location 1"
        ]
    )
    
    # 2. Generate and save report
    report_md = generate_benchmarking_report([c_res1, c_res2], [n_res1])
    
    with open("robustness_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print("\n✅ Benchmarking Complete! Report saved to robustness_report.md")

if __name__ == "__main__":
    main()
