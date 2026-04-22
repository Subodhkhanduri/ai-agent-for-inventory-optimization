# run_inventory_evaluation.py

"""
Standalone script to evaluate ROP and Periodic Review inventory policies.

Usage:
    python run_inventory_evaluation.py                          # uses pre-split CSVs
    python run_inventory_evaluation.py train.csv test.csv       # custom datasets
    python run_inventory_evaluation.py --max-pairs 10           # quick test with 10 pairs
"""

import sys
import os
import time
import logging
import pandas as pd

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Fix Windows WinError 2 (wmic not found) for joblib/loky
if os.name == 'nt' and "LOKY_MAX_CPU_COUNT" not in os.environ:
    os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count())

from inventory_chatbot.benchmarks.inventory_policy_evaluator import (
    InventoryPolicyEvaluator,
    generate_inventory_policy_report,
)


def main():
    # ── Parse arguments ──
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    train_path = os.path.join(data_dir, "train_80_date_split.csv")
    test_path = os.path.join(data_dir, "test_20_date_split.csv")
    max_pairs = None

    args = sys.argv[1:]
    if "--max-pairs" in args:
        idx = args.index("--max-pairs")
        max_pairs = int(args[idx + 1])
        args = args[:idx] + args[idx+2:]

    if len(args) >= 2:
        train_path = args[0]
        test_path = args[1]

    # ── Load Data ──
    print(f"Loading training data from: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"  -> {len(train_df):,} rows")

    print(f"Loading test data from: {test_path}")
    test_df = pd.read_csv(test_path)
    print(f"  -> {len(test_df):,} rows")

    # ── Initialize Evaluator ──
    print("\nInitializing evaluator...")
    evaluator = InventoryPolicyEvaluator(
        train_df=train_df,
        test_df=test_df,
        lead_time=7,
        service_level_z=1.65,
    )

    print(f"Found {len(evaluator.pairs)} item-store pairs in both train & test sets.")

    # ── Run Evaluation ──
    start = time.time()
    if max_pairs:
        print(f"\nEvaluating first {max_pairs} pairs (use --max-pairs to change)...")
    else:
        print(f"\nEvaluating all {len(evaluator.pairs)} pairs...")

    results = evaluator.evaluate_all(max_pairs=max_pairs)
    elapsed = time.time() - start

    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return

    # ── Print Summary ──
    agg = results["aggregate"]
    sim = agg["simulated_policy"]
    act = agg["actual_baseline"]

    print(f"\n{'='*60}")
    print(f"  INVENTORY POLICY EVALUATION RESULTS")
    print(f"  ({results['config']['n_pairs_evaluated']} pairs evaluated in {elapsed:.1f}s)")
    print(f"{'='*60}")

    print(f"\n  [SECTION] FILL RATE")
    print(f"     ROP/Periodic Policy (weighted):  {sim['weighted_fill_rate']*100:.2f}%")
    print(f"     Actual Baseline (mean):          {act['mean_fill_rate']*100:.2f}%")

    print(f"\n  [SECTION] STOCKOUT DAYS")
    print(f"     ROP/Periodic Policy (mean):      {sim['mean_stockout_days_pct']:.2f}%")
    print(f"     Actual Baseline (mean):          {act['mean_stockout_days_pct']:.2f}%")

    print(f"\n  [SECTION] FORECAST ACCURACY (Demand Mean Prediction)")
    print(f"     Mean Absolute Error (MAE):  {agg['forecast_accuracy']['mean_mae']:.4f}")
    print(f"     Root Mean Square Error:     {agg['forecast_accuracy']['mean_rmse']:.4f}")
    print(f"     Mean Abs % Error (MAPE):    {agg['forecast_accuracy']['mean_mape']:.2f}%")

    print(f"\n  [SECTION] AVERAGE INVENTORY LEVEL")
    print(f"     ROP/Periodic Policy (mean):      {sim['mean_avg_inventory']:.2f}")
    print(f"     Actual Baseline (mean):          {act['mean_avg_inventory']:.2f}")


    print(f"\n{'='*60}")

    # ── Generate Report ──
    report_md = generate_inventory_policy_report(results)
    report_path = os.path.join(os.path.dirname(__file__), "..", "docs", "inventory_policy_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n[OK] Report saved to: {report_path}")


if __name__ == "__main__":
    main()
