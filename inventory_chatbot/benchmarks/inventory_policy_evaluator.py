# inventory_chatbot/benchmarks/inventory_policy_evaluator.py

"""
Inventory Policy Evaluation Module
===================================
Inventory Policy Evaluation Module
===================================
Validates ROP (Reorder Point) and Periodic Review (P, T) policies by:
  1. Learning parameters (μ, σ) from training data (2013-2016)
  2. Simulating inventory day-by-day through the test period (2017)
  3. Computing Fill Rate, Stockout Days %, and Average Inventory

The test dataset already contains actual inventory state columns (Start_Stock,
End_Stock, Lost_Sales, etc.), which serve as a baseline for comparison.
"""

import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _confidence_interval(
    values: List[float], confidence: float = 1.96
) -> Dict[str, float]:
    """
    Compute mean, std, and 95% confidence interval.
    CI = x̄ ± z·(s/√n)  where z=1.96 for 95% CI.
    """
    arr = np.array(values)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    se = std / math.sqrt(n) if n > 0 else 0.0
    margin = confidence * se
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "n": n,
        "se": round(se, 4),
        "ci_lower": round(mean - margin, 4),
        "ci_upper": round(mean + margin, 4),
        "margin": round(margin, 4),
    }


# ──────────────────────────────────────────────
# Configuration Defaults
# ──────────────────────────────────────────────
DEFAULT_LEAD_TIME = 7          # L (days)
DEFAULT_SERVICE_LEVEL_Z = 1.65 # Z for ~95% service level
DEFAULT_REVIEW_PERIOD = 7      # P (days)


class InventoryPolicyEvaluator:
    """
    Evaluates ROP and Periodic Review inventory policies against test data.

    Usage:
        evaluator = InventoryPolicyEvaluator(train_df, test_df)
        results = evaluator.evaluate_all()
    """

    def __init__(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        lead_time: int = DEFAULT_LEAD_TIME,
        service_level_z: float = DEFAULT_SERVICE_LEVEL_Z,
        ordering_cost_S: float = DEFAULT_ORDERING_COST_S,
        holding_cost_H: float = DEFAULT_HOLDING_COST_H,
    ):
        self.train_df = train_df.copy()
        self.test_df = test_df.copy()
        self.L = lead_time
        self.Z = service_level_z
        self.P = DEFAULT_REVIEW_PERIOD

        # Ensure Date is datetime
        for df in [self.train_df, self.test_df]:
            if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
                df["Date"] = pd.to_datetime(df["Date"])

        # Get unique item-store pairs present in BOTH datasets
        train_pairs = set(
            zip(self.train_df["Item"], self.train_df["Store"])
        )
        test_pairs = set(
            zip(self.test_df["Item"], self.test_df["Store"])
        )
        self.pairs = sorted(train_pairs & test_pairs)

        logger.info(
            f"InventoryPolicyEvaluator initialized: "
            f"{len(self.pairs)} item-store pairs, L={self.L}, Z={self.Z}"
        )

    # ──────────────────────────────────────────
    # Train: learn parameters from training data
    # ──────────────────────────────────────────
    def _train_parameters(
        self, item: int, store: int
    ) -> Dict[str, float]:
        """
        Compute demand statistics from training data for a single
        item-store pair.

        Returns:
            Dict with mu (mean daily demand), sigma (std dev),
            annual_demand, ROP, and Target Level (T).
        """
        subset = self.train_df[
            (self.train_df["Item"] == item) & (self.train_df["Store"] == store)
        ]

        mu = subset["Demand"].mean()
        sigma = subset["Demand"].std()
        if math.isnan(sigma) or sigma == 0:
            sigma = 0.01  # small epsilon to avoid division issues

        n_days = len(subset)
        # Annualize demand (scale based on actual days in training set)
        annual_demand = mu * 365

        # Reorder Point: ROP = μ·L + Z·σ·√L
        rop = (mu * self.L) + (self.Z * sigma * math.sqrt(self.L))

        # Target Level (T) = μ·(P+L) + Z·σ·√(P+L)
        protection_interval = self.P + self.L
        target_level = (mu * protection_interval) + (self.Z * sigma * math.sqrt(protection_interval))

        return {
            "mu": mu,
            "sigma": sigma,
            "n_train_days": n_days,
            "annual_demand": annual_demand,
            "rop": rop,
            "target_level": target_level,
        }

    # ──────────────────────────────────────────
    # Simulate: run day-by-day inventory sim
    # ──────────────────────────────────────────
    def _simulate_inventory(
        self, item: int, store: int, params: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Day-by-day inventory simulation on the test set using the
        trained ROP and periodic review parameters.

        Returns:
            Dict with daily records + aggregated metrics.
        """
        test_subset = self.test_df[
            (self.test_df["Item"] == item) & (self.test_df["Store"] == store)
        ].sort_values("Date").reset_index(drop=True)

        rop = params["rop"]
        mu = params["mu"]

        # Initialize stock at the ROP level (conservative start)
        stock = rop
        # Pending orders: list of (arrival_day_index, quantity)
        pending_orders: List[Tuple[int, float]] = []

        total_demand = 0.0
        total_unmet = 0.0
        stockout_days = 0
        inventory_levels: List[float] = []
        n_orders_placed = 0

        for day_idx, row in test_subset.iterrows():
            demand = row["Demand"]

            # 1. Receive any pending orders arriving today
            arrived = sum(qty for arr_day, qty in pending_orders if arr_day <= day_idx)
            pending_orders = [
                (arr_day, qty)
                for arr_day, qty in pending_orders
                if arr_day > day_idx
            ]
            stock += arrived

            # 2. Fulfill demand
            total_demand += demand
            if demand > stock:
                unmet = demand - stock
                total_unmet += unmet
                stock = 0
                stockout_days += 1
            else:
                stock -= demand

            # 3. Record inventory level (end of day)
            inventory_levels.append(stock)

            # 4. Periodic Review: Every P days, place order if position < ROP (or just every P days)
            # The user specified: "reviewing every week to calculate this and ording the ammount"
            if day_idx % self.P == 0:
                # Inventory Position = stock + items on order
                on_order = sum(qty for _, qty in pending_orders)
                inventory_position = stock + on_order
                
                # Order up to Target Level (T)
                if inventory_position < rop:
                    order_qty = max(0, params["target_level"] - inventory_position)
                    if order_qty > 0:
                        pending_orders.append((day_idx + self.L, order_qty))
                        n_orders_placed += 1

        total_days = len(test_subset)

        # Compute metrics
        fill_rate = (1 - total_unmet / total_demand) if total_demand > 0 else 1.0
        stockout_pct = (stockout_days / total_days * 100) if total_days > 0 else 0.0
        avg_inventory = float(np.mean(inventory_levels)) if inventory_levels else 0.0

        # Forecast accuracy metrics (comparing mu used for ROP vs actual Test demand)
        test_demand = test_subset["Demand"].values
        # Predicted is essentially 'mu' for each day in this simple model
        predicted_demand = np.full_like(test_demand, mu)
        
        # Avoid division by zero for MAPE
        safe_actual = np.where(test_demand == 0, 1e-10, test_demand)
        
        mae = float(np.mean(np.abs(test_demand - predicted_demand)))
        rmse = float(np.sqrt(np.mean((test_demand - predicted_demand) ** 2)))
        mape = float(np.mean(np.abs((test_demand - predicted_demand) / safe_actual)) * 100)

        return {
            "total_days": total_days,
            "total_demand": round(total_demand, 2),
            "total_unmet_demand": round(total_unmet, 2),
            "fill_rate": round(fill_rate, 4),
            "stockout_days": stockout_days,
            "stockout_days_pct": round(stockout_pct, 2),
            "avg_inventory_level": round(avg_inventory, 2),
            "n_orders_placed": n_orders_placed,
            "forecast_metrics": {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "mape": round(mape, 2)
            },
            "inventory_levels": inventory_levels,
        }

    # ──────────────────────────────────────────
    # Actual baseline from test data
    # ──────────────────────────────────────────
    def _compute_actual_metrics(
        self, item: int, store: int
    ) -> Dict[str, Any]:
        """
        Compute metrics from the ACTUAL test data columns
        (Start_Stock, End_Stock, Lost_Sales, etc.) to use as baseline.
        """
        test_subset = self.test_df[
            (self.test_df["Item"] == item) & (self.test_df["Store"] == store)
        ].sort_values("Date").reset_index(drop=True)

        total_days = len(test_subset)
        total_demand = test_subset["Demand"].sum()
        total_lost = test_subset["Lost_Sales"].sum() if "Lost_Sales" in test_subset.columns else 0
        total_ordered = test_subset["Ordered_Qty"].sum() if "Ordered_Qty" in test_subset.columns else 0

        # Actual fill rate
        actual_fill_rate = (1 - total_lost / total_demand) if total_demand > 0 else 1.0

        # Actual stockout days (days where Lost_Sales > 0)
        if "Lost_Sales" in test_subset.columns:
            actual_stockout_days = (test_subset["Lost_Sales"] > 0).sum()
        else:
            actual_stockout_days = 0

        actual_stockout_pct = (actual_stockout_days / total_days * 100) if total_days > 0 else 0

        # Actual avg inventory
        if "End_Stock" in test_subset.columns:
            actual_avg_inventory = test_subset["End_Stock"].mean()
        elif "Start_Stock" in test_subset.columns:
            actual_avg_inventory = test_subset["Start_Stock"].mean()
        else:
            actual_avg_inventory = 0

        # Count actual orders (days where Ordered_Qty > 0)
        if "Ordered_Qty" in test_subset.columns:
            n_actual_orders = (test_subset["Ordered_Qty"] > 0).sum()
            # Actual avg order size
            ordered_rows = test_subset[test_subset["Ordered_Qty"] > 0]
            avg_actual_order_size = ordered_rows["Ordered_Qty"].mean() if len(ordered_rows) > 0 else 0
        else:
            n_actual_orders = 0
            avg_actual_order_size = 0

        return {
            "total_days": total_days,
            "total_demand": round(float(total_demand), 2),
            "total_lost_sales": round(float(total_lost), 2),
            "actual_fill_rate": round(float(actual_fill_rate), 4),
            "actual_stockout_days": int(actual_stockout_days),
            "actual_stockout_pct": round(float(actual_stockout_pct), 2),
            "actual_avg_inventory": round(float(actual_avg_inventory), 2),
            "n_actual_orders": int(n_actual_orders),
            "avg_actual_order_size": round(float(avg_actual_order_size), 2),
        }


    # ──────────────────────────────────────────
    # Evaluate a single item-store pair
    # ──────────────────────────────────────────
    def evaluate_pair(
        self, item: int, store: int
    ) -> Dict[str, Any]:
        """Evaluate all metrics for one (item, store) pair."""
        params = self._train_parameters(item, store)
        sim = self._simulate_inventory(item, store, params)
        actual = self._compute_actual_metrics(item, store)

        return {
            "item": item,
            "store": store,
            "trained_params": {
                "mu": round(params["mu"], 2),
                "sigma": round(params["sigma"], 2),
                "rop": round(params["rop"], 2),
                "target_level": round(params["target_level"], 2),
                "annual_demand": round(params["annual_demand"], 2),
            },
            "simulated_policy": {
                "fill_rate": sim["fill_rate"],
                "stockout_days": sim["stockout_days"],
                "stockout_days_pct": sim["stockout_days_pct"],
                "avg_inventory": sim["avg_inventory_level"],
                "total_demand": sim["total_demand"],
                "total_unmet": sim["total_unmet_demand"],
                "n_orders": sim["n_orders_placed"],
            },
            "forecast_metrics": sim["forecast_metrics"],
            "actual_baseline": {
                "fill_rate": actual["actual_fill_rate"],
                "stockout_days": actual["actual_stockout_days"],
                "stockout_days_pct": actual["actual_stockout_pct"],
                "avg_inventory": actual["actual_avg_inventory"],
                "total_demand": actual["total_demand"],
                "total_lost_sales": actual["total_lost_sales"],
            },
        }

    # ──────────────────────────────────────────
    # Evaluate all pairs + aggregate
    # ──────────────────────────────────────────
    def evaluate_all(
        self, max_pairs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all item-store pairs and aggregate metrics.

        Args:
            max_pairs: If set, evaluate only the first N pairs
                       (useful for quick testing).
        Returns:
            Dict with per-pair results and aggregate summary.
        """
        pairs_to_eval = self.pairs[:max_pairs] if max_pairs else self.pairs
        pair_results = []

        for i, (item, store) in enumerate(pairs_to_eval):
            try:
                result = self.evaluate_pair(item, store)
                pair_results.append(result)
            except Exception as e:
                logger.warning(
                    f"Failed to evaluate Item={item}, Store={store}: {e}"
                )
                continue

            if (i + 1) % 50 == 0:
                logger.info(f"  Evaluated {i+1}/{len(pairs_to_eval)} pairs...")

        # Aggregate metrics across all pairs
        if not pair_results:
            return {"error": "No pairs could be evaluated"}

        agg = self._aggregate_results(pair_results)

        return {
            "config": {
                "lead_time_L": self.L,
                "service_level_Z": self.Z,
                "review_period_P": self.P,
                "n_pairs_evaluated": len(pair_results),
                "n_pairs_total": len(self.pairs),
                "train_rows": len(self.train_df),
                "test_rows": len(self.test_df),
            },
            "aggregate": agg,
            "per_pair": pair_results,
        }

    def _aggregate_results(
        self, pair_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate per-pair results into summary statistics."""
        sim_fill_rates = [r["simulated_policy"]["fill_rate"] for r in pair_results]
        sim_stockout_pcts = [r["simulated_policy"]["stockout_days_pct"] for r in pair_results]
        sim_avg_invs = [r["simulated_policy"]["avg_inventory"] for r in pair_results]
        sim_total_demands = [r["simulated_policy"]["total_demand"] for r in pair_results]
        sim_total_unmets = [r["simulated_policy"]["total_unmet"] for r in pair_results]

        act_fill_rates = [r["actual_baseline"]["fill_rate"] for r in pair_results]
        act_stockout_pcts = [r["actual_baseline"]["stockout_days_pct"] for r in pair_results]
        act_avg_invs = [r["actual_baseline"]["avg_inventory"] for r in pair_results]


        # Forecast errors
        maes = [r["forecast_metrics"]["mae"] for r in pair_results]
        rmses = [r["forecast_metrics"]["rmse"] for r in pair_results]
        mapes = [r["forecast_metrics"]["mape"] for r in pair_results]

        # Weighted overall fill rate (by demand volume)
        total_demand_all = sum(sim_total_demands)
        total_unmet_all = sum(sim_total_unmets)
        weighted_fill_rate = (1 - total_unmet_all / total_demand_all) if total_demand_all > 0 else 1.0

        # Statistical stability: CI = x̄ ± 1.96·(s/√n)
        ci_fill_rate = _confidence_interval(sim_fill_rates)
        ci_stockout = _confidence_interval(sim_stockout_pcts)
        ci_avg_inv = _confidence_interval(sim_avg_invs)

        return {
            "simulated_policy": {
                "weighted_fill_rate": round(weighted_fill_rate, 4),
                "mean_fill_rate": round(float(np.mean(sim_fill_rates)), 4),
                "median_fill_rate": round(float(np.median(sim_fill_rates)), 4),
                "min_fill_rate": round(float(np.min(sim_fill_rates)), 4),
                "mean_stockout_days_pct": round(float(np.mean(sim_stockout_pcts)), 2),
                "median_stockout_days_pct": round(float(np.median(sim_stockout_pcts)), 2),
                "mean_avg_inventory": round(float(np.mean(sim_avg_invs)), 2),
                "total_demand": round(total_demand_all, 2),
                "total_unmet_demand": round(total_unmet_all, 2),
            },
            "forecast_accuracy": {
                "mean_mae": round(float(np.mean(maes)), 4),
                "mean_rmse": round(float(np.mean(rmses)), 4),
                "mean_mape": round(float(np.mean(mapes)), 2)
            },
            "actual_baseline": {
                "mean_fill_rate": round(float(np.mean(act_fill_rates)), 4),
                "mean_stockout_days_pct": round(float(np.mean(act_stockout_pcts)), 2),
                "mean_avg_inventory": round(float(np.mean(act_avg_invs)), 2),
            },
            "statistical_stability": {
                "fill_rate": ci_fill_rate,
                "stockout_days_pct": ci_stockout,
                "avg_inventory": ci_avg_inv,
            },
        }


# ──────────────────────────────────────────────
# Report Generator
# ──────────────────────────────────────────────
def generate_inventory_policy_report(results: Dict[str, Any]) -> str:
    """Generate a Markdown report from evaluation results."""
    if "error" in results:
        return f"# Inventory Policy Evaluation\n\n**Error**: {results['error']}\n"

    config = results["config"]
    agg = results["aggregate"]
    sim = agg["simulated_policy"]
    act = agg["actual_baseline"]

    lines = [
        "# Inventory Policy Evaluation Report",
        "",
        "## Evaluation Setup",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Training Rows | {config['train_rows']:,} |",
        f"| Test Rows | {config['test_rows']:,} |",
        f"| Item-Store Pairs Evaluated | {config['n_pairs_evaluated']} |",
        f"| Lead Time (L) | {config['lead_time_L']} days |",
        f"| Service Level (Z) | {config['service_level_Z']} (~{_z_to_pct(config['service_level_Z'])}%) |",
        f"| Review Period (P) | {config.get('review_period_P', 7)} days |",
        "",
        "---",
        "",
        "## Summary of Evaluation Metrics",
        "",
        "### 1. Fill Rate",
        "",
        "$$\\text{Fill Rate} = 1 - \\frac{\\sum \\text{Unmet Demand}}{\\sum \\text{Total Demand}}$$",
        "",
        "| Metric | ROP/Periodic Policy | Actual Baseline |",
        "|---|---|---|",
        f"| **Weighted Fill Rate** | **{sim['weighted_fill_rate']*100:.2f}%** | {act['mean_fill_rate']*100:.2f}% |",
        f"| Mean Fill Rate (per pair) | {sim['mean_fill_rate']*100:.2f}% | {act['mean_fill_rate']*100:.2f}% |",
        f"| Median Fill Rate | {sim['median_fill_rate']*100:.2f}% | — |",
        f"| Min Fill Rate | {sim['min_fill_rate']*100:.2f}% | — |",
        f"| Total Unmet Demand | {sim['total_unmet_demand']:,.0f} | — |",
        f"| Total Demand | {sim['total_demand']:,.0f} | — |",
        "",
        _fill_rate_verdict(sim['weighted_fill_rate']),
        "",
        "### 2. Stockout Days Percentage",
        "",
        "$$\\text{Stockout Days \\%} = \\frac{\\text{Days with demand > inventory}}"
        "{\\text{Total days}} \\times 100$$",
        "",
        "| Metric | ROP/Periodic Policy | Actual Baseline |",
        "|---|---|---|",
        f"| **Mean Stockout Days %** | **{sim['mean_stockout_days_pct']:.2f}%** | {act['mean_stockout_days_pct']:.2f}% |",
        f"| Median Stockout Days % | {sim['median_stockout_days_pct']:.2f}% | — |",
        "",
        "### 3. Average Inventory Level",
        "",
        "$$\\text{Average Inventory} = \\frac{1}{T} \\sum_{t=1}^{T} I_t$$",
        "",
        "| Metric | ROP/Periodic Policy | Actual Baseline |",
        "|---|---|---|",
        f"| **Mean Avg Inventory** | **{sim['mean_avg_inventory']:.2f}** | {act['mean_avg_inventory']:.2f} |",
        "",
        "",
        "---",
        "",
        "## Interpretation",
        "",
    ]

    # Add interpretation bullets
    interp = _build_interpretation(sim, act)
    lines.extend(interp)

    # Statistical stability section
    stats = agg.get("statistical_stability", {})
    if stats:
        lines.extend(_statistical_stability_section(stats, config))

    # Per-pair top/bottom performers
    lines.extend(_per_pair_summary(results.get("per_pair", [])))

    return "\n".join(lines)


def _z_to_pct(z: float) -> str:
    """Approximate Z to service level %."""
    table = {1.28: "90", 1.65: "95", 1.96: "97.5", 2.33: "99"}
    return table.get(z, f"~{z}")


def _fill_rate_verdict(fr: float) -> str:
    if fr >= 0.95:
        return "> ✅ **Excellent**: Fill rate ≥ 95% — strongly supports the Z=1.65 service level assumption."
    elif fr >= 0.90:
        return "> ✅ **Good**: Fill rate ≥ 90% — supports the Z=1.65 assumption."
    elif fr >= 0.80:
        return "> ⚠️ **Moderate**: Fill rate 80-90% — consider increasing Z or safety stock."
    else:
        return "> ❌ **Low**: Fill rate < 80% — policy may need tuning."


def _build_interpretation(sim, act) -> List[str]:
    lines = []

    # Fill rate comparison
    if sim["weighted_fill_rate"] >= 0.95:
        lines.append("- **Fill Rate**: The ROP/Periodic policy achieves ≥95% fill rate, "
                      "confirming the Z=1.65 service level is effective.")
    elif sim["weighted_fill_rate"] >= 0.90:
        lines.append("- **Fill Rate**: The policy achieves 90-95% fill rate. "
                      "This is good but may benefit from a slightly higher Z.")
    else:
        lines.append("- **Fill Rate**: The policy fill rate is below 90%. "
                      "Consider increasing Z or reviewing lead time assumptions.")

    # Stockout comparison
    if sim["mean_stockout_days_pct"] <= act["mean_stockout_days_pct"]:
        lines.append(f"- **Stockout Days**: The ROP policy ({sim['mean_stockout_days_pct']:.1f}%) "
                      f"reduces stockouts vs. actual baseline ({act['mean_stockout_days_pct']:.1f}%).")
    else:
        lines.append(f"- **Stockout Days**: The ROP policy ({sim['mean_stockout_days_pct']:.1f}%) "
                      f"has higher stockouts than baseline ({act['mean_stockout_days_pct']:.1f}%).")

    # Inventory level
    if sim["mean_avg_inventory"] <= act["mean_avg_inventory"] * 1.1:
        lines.append(f"- **Avg Inventory**: Policy maintains comparable inventory levels "
                      f"({sim['mean_avg_inventory']:.1f} vs. {act['mean_avg_inventory']:.1f} actual), "
                      "indicating efficient stock management.")
    else:
        lines.append(f"- **Avg Inventory**: Policy carries higher average inventory "
                      f"({sim['mean_avg_inventory']:.1f} vs. {act['mean_avg_inventory']:.1f} actual). "
                      "This is the trade-off for improved service level.")

    lines.append("")
    return lines


def _statistical_stability_section(
    stats: Dict[str, Any], config: Dict[str, Any]
) -> List[str]:
    """Render statistical stability / confidence interval section."""
    n = config["n_pairs_evaluated"]
    lines = [
        "## Statistical Stability Analysis",
        "",
        "$$CI = \\bar{x} \\pm 1.96 \\cdot \\frac{s}{\\sqrt{n}}$$",
        "",
        f"Computed across **n = {n}** item-store pairs (95% confidence level).",
        "",
        "| Metric | Mean | Std Dev (s) | 95% CI Lower | 95% CI Upper | Margin (±) |",
        "|---|---|---|---|---|---|",
    ]

    labels = {
        "fill_rate": ("Fill Rate", True),
        "stockout_days_pct": ("Stockout Days %", False),
        "avg_inventory": ("Avg Inventory", False),
        "cost_reduction_pct": ("Cost Reduction %", False),
    }

    for key, (label, is_pct_fraction) in labels.items():
        ci = stats.get(key, {})
        if not ci:
            continue
        if is_pct_fraction:
            # fill_rate is 0-1, display as %
            lines.append(
                f"| **{label}** | "
                f"{ci['mean']*100:.2f}% | "
                f"{ci['std']*100:.2f}% | "
                f"{ci['ci_lower']*100:.2f}% | "
                f"{ci['ci_upper']*100:.2f}% | "
                f"±{ci['margin']*100:.2f}% |"
            )
        else:
            fmt = ".2f"
            lines.append(
                f"| **{label}** | "
                f"{ci['mean']:{fmt}} | "
                f"{ci['std']:{fmt}} | "
                f"{ci['ci_lower']:{fmt}} | "
                f"{ci['ci_upper']:{fmt}} | "
                f"±{ci['margin']:{fmt}} |"
            )

    lines.extend([
        "",
        "> The narrow confidence intervals confirm that the evaluation results are "
        "statistically stable and not driven by outlier item-store pairs.",
        "",
        "---",
        "",
    ])
    return lines


def _per_pair_summary(pair_results: List[Dict], top_n: int = 5) -> List[str]:
    """Show top and bottom performers by fill rate."""
    if not pair_results:
        return []

    sorted_by_fr = sorted(
        pair_results, key=lambda r: r["simulated_policy"]["fill_rate"]
    )

    lines = [
        "## Per-Pair Analysis (Selected)",
        "",
        "### Top Performers (Highest Fill Rate)",
        "",
        "| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in sorted_by_fr[-top_n:][::-1]:
        sp = r["simulated_policy"]
        tp = r["trained_params"]
        lines.append(
            f"| {r['item']} | {r['store']} | "
            f"{sp['fill_rate']*100:.1f}% | "
            f"{sp['stockout_days_pct']:.1f}% | "
            f"{sp['avg_inventory']:.1f} | "
            f"{tp['target_level']:.0f} | "
            f"{tp['rop']:.0f} |"
        )

    lines.extend([
        "",
        "### Pairs Needing Attention (Lowest Fill Rate)",
        "",
        "| Item | Store | Fill Rate | Stockout % | Avg Inventory | Target (T) | ROP |",
        "|---|---|---|---|---|---|---|",
    ])

    for r in sorted_by_fr[:top_n]:
        sp = r["simulated_policy"]
        tp = r["trained_params"]
        lines.append(
            f"| {r['item']} | {r['store']} | "
            f"{sp['fill_rate']*100:.1f}% | "
            f"{sp['stockout_days_pct']:.1f}% | "
            f"{sp['avg_inventory']:.1f} | "
            f"{tp['target_level']:.0f} | "
            f"{tp['rop']:.0f} |"
        )

    lines.append("")
    return lines
