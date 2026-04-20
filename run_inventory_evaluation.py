# run_inventory_evaluation.py

"""
Standalone script to evaluate ROP, Order Quantity, and EOQ inventory policies.

Usage:
    python run_inventory_evaluation.py                          # uses pre-split CSVs
    python run_inventory_evaluation.py train.csv test.csv       # custom datasets
    python run_inventory_evaluation.py --max-pairs 10           # quick test with 10 pairs
"""

import sys
import time
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from inventory_chatbot.benchmarks.inventory_policy_evaluator import (
    InventoryPolicyEvaluator,
    generate_inventory_policy_report,
)


def main():
    # ── Parse arguments ──
    train_path = "train_80_date_split.csv"
    test_path = "test_20_date_split.csv"
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
        ordering_cost_S=50,
        holding_cost_H=2,
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
    cost = agg["eoq_cost"]

    print(f"\n{'='*60}")
    print(f"  INVENTORY POLICY EVALUATION RESULTS")
    print(f"  ({results['config']['n_pairs_evaluated']} pairs evaluated in {elapsed:.1f}s)")
    print(f"{'='*60}")

    print(f"\n  [SECTION] FILL RATE")
    print(f"     ROP/EOQ Policy (weighted):  {sim['weighted_fill_rate']*100:.2f}%")
    print(f"     Actual Baseline (mean):     {act['mean_fill_rate']*100:.2f}%")

    print(f"\n  [SECTION] STOCKOUT DAYS")
    print(f"     ROP/EOQ Policy (mean):      {sim['mean_stockout_days_pct']:.2f}%")
    print(f"     Actual Baseline (mean):     {act['mean_stockout_days_pct']:.2f}%")

    print(f"\n  [SECTION] FORECAST ACCURACY (Demand Mean Prediction)")
    print(f"     Mean Absolute Error (MAE):  {agg['forecast_accuracy']['mean_mae']:.4f}")
    print(f"     Root Mean Square Error:     {agg['forecast_accuracy']['mean_rmse']:.4f}")
    print(f"     Mean Abs % Error (MAPE):    {agg['forecast_accuracy']['mean_mape']:.2f}%")

    print(f"\n  [SECTION] AVERAGE INVENTORY LEVEL")
    print(f"     ROP/EOQ Policy (mean):      {sim['mean_avg_inventory']:.2f}")
    print(f"     Actual Baseline (mean):     {act['mean_avg_inventory']:.2f}")

    print(f"\n  [SECTION] EOQ COST ANALYSIS")
    print(f"     Mean TC (EOQ Policy):       ${cost['mean_tc_eoq']:,.2f}")
    print(f"     Mean TC (Actual):           ${cost['mean_tc_actual']:,.2f}")
    print(f"     Mean Cost Reduction:        {cost['mean_cost_reduction_pct']:.2f}%")

    print(f"\n{'='*60}")

    # ── Generate Report ──
    report_md = generate_inventory_policy_report(results)
    report_path = "inventory_policy_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n[OK] Report saved to: {report_path}")


if __name__ == "__main__":
    main()
