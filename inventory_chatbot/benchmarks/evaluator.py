# inventory_chatbot/benchmarks/evaluator.py

"""
Enhanced benchmarking suite with:
  - P50/P95/P99 latency percentiles
  - CPU utilization monitoring
  - Tool-use accuracy evaluation
  - Ablation testing (pipeline vs direct LLM)
"""

import time
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from inventory_chatbot.crew.simple_orchestrator import SimpleInventoryOrchestrator
from inventory_chatbot.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _percentiles(values: List[float]) -> Dict[str, float]:
    """Compute P50, P95, P99, mean, std from a list of floats."""
    arr = np.array(values)
    return {
        "p50": round(float(np.percentile(arr, 50)), 3),
        "p95": round(float(np.percentile(arr, 95)), 3),
        "p99": round(float(np.percentile(arr, 99)), 3),
        "mean": round(float(np.mean(arr)), 3),
        "std": round(float(np.std(arr)), 3),
        "min": round(float(np.min(arr)), 3),
        "max": round(float(np.max(arr)), 3),
    }


def _cpu_snapshot() -> Optional[float]:
    """Return current process CPU % (None if psutil unavailable)."""
    if not PSUTIL_AVAILABLE:
        return None
    try:
        proc = psutil.Process()
        return proc.cpu_percent(interval=0.1)
    except Exception:
        return None


# ──────────────────────────────────────────────
# Main evaluator class
# ──────────────────────────────────────────────

class RobustnessEvaluator:
    """
    Benchmarks LLM performance on consistency, noise sensitivity,
    precision, tool-use accuracy, and ablations.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    # ============================================================
    # 1. CONSISTENCY TEST  (with P99 latency + CPU)
    # ============================================================
    def run_consistency_test(self, query: str, trials: int = 5) -> Dict[str, Any]:
        """
        Runs the same query multiple times; reports stability and
        P50/P95/P99 latency percentiles.
        """
        results = []

        for i in range(trials):
            orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")
            cpu_before = _cpu_snapshot()
            start_time = time.time()
            res = orchestrator.execute(query)
            end_time = time.time()
            cpu_after = _cpu_snapshot()

            results.append({
                "trial": i + 1,
                "response": res.get("response", ""),
                "latency": round(end_time - start_time, 3),
                "cpu_before": cpu_before,
                "cpu_after": cpu_after,
            })
            time.sleep(1.0) # Rate limit protection

        latencies = [r["latency"] for r in results]
        unique_responses = len(set(r["response"] for r in results))
        # Proportion of responses matching the modal (most frequent) response.
        # Range [1/trials, 1.0]. All-identical -> 1.0; all-unique -> 1/trials.
        from collections import Counter
        response_counts = Counter(r["response"] for r in results)
        most_common_count = response_counts.most_common(1)[0][1]
        consistency_score = most_common_count / trials

        return {
            "query": query,
            "trials": trials,
            "consistency_score": round(consistency_score, 2),
            "unique_responses": unique_responses,
            "latency_stats": _percentiles(latencies),
            "details": results,
        }

    # ============================================================
    # 2. NOISE / TYPO SENSITIVITY TEST
    # ============================================================
    def run_noise_test(self, base_query: str, noisy_queries: List[str]) -> Dict[str, Any]:
        """
        Tests how typos/noise in the query affects the output.
        """
        orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")

        base_res = orchestrator.execute(base_query)
        base_response = base_res.get("response", "")

        results = []
        for i, q in enumerate(noisy_queries, 1):
            print(f"    [{i}/{len(noisy_queries)}] Noisy query: {q[:50]}...")
            start = time.time()
            res = orchestrator.execute(q)
            elapsed = round(time.time() - start, 3)
            results.append({
                "noisy_query": q,
                "response": res.get("response", ""),
                "is_successful": "error" not in res.get("response", "").lower(),
                "latency": elapsed,
            })
            time.sleep(1.0) # Rate limit protection

        return {
            "base_query": base_query,
            "base_response_preview": base_response[:120],
            "noisy_results": results,
        }

    # ============================================================
    # 3. PRECISION / EXACT-MATCH TEST  (with P99)
    # ============================================================
    def run_precision_test(self, queries: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Tests if the LLM responses contain ground-truth expected
        keywords/numbers.  Reports per-query latency + overall P99.
        """
        results = []
        successful_matches = 0
        latencies = []

        for i, q_obj in enumerate(queries, 1):
            query = q_obj["query"]
            expected = q_obj["expected"]
            category = q_obj.get("category", "general")

            print(f"    [{i}/{len(queries)}] Processing: {query[:50]}...")
            orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")
            cpu_before = _cpu_snapshot()
            start_time = time.time()
            res = orchestrator.execute(query)
            end_time = time.time()
            cpu_after = _cpu_snapshot()

            elapsed = round(end_time - start_time, 3)
            latencies.append(elapsed)

            response_text = res.get("response", "")
            
            # Robust matching: strip commas and whitespace for numerical comparison
            # Robust matching: strip commas, whitespace, and convert to float strings for comparison
            clean_response = str(response_text).lower().replace(",", "").replace("$", "").strip()
            clean_expected = str(expected).lower().replace(",", "").replace("$", "").strip()
            
            is_match = clean_expected in clean_response
            if is_match:
                successful_matches += 1

            results.append({
                "query": query,
                "category": category,
                "expected": expected,
                "response_preview": response_text[:200],
                "is_match": is_match,
                "latency": elapsed,
                "cpu_before": cpu_before,
                "cpu_after": cpu_after,
            })
            time.sleep(1.0) # Rate limit protection

        precision_score = successful_matches / len(queries) if queries else 0.0

        return {
            "total_tests": len(queries),
            "precision_score": round(precision_score, 2),
            "latency_stats": _percentiles(latencies) if latencies else {},
            "details": results,
        }

    # ============================================================
    # 4. DATA CORRUPTION TEST
    # ============================================================
    def run_data_corruption_test(self, query: str, corrupt_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Tests how the LLM/Orchestrator handles corrupted data.
        """
        orchestrator = SimpleInventoryOrchestrator(dataframe=corrupt_df, user_role="admin")
        res = orchestrator.execute(query)
        resp = res.get("response", "")

        return {
            "query": query,
            "response_preview": resp[:200],
            "status": "Handled" if "error" in resp.lower() or "not find" in resp.lower() else "Processed",
        }

    # ============================================================
    # 5. TOOL-USE ACCURACY TEST
    # ============================================================
    def run_tool_use_test(
        self,
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates whether the orchestrator classifies queries to the
        correct tool/pipeline path.

        Each test case: {
            "query": str,
            "expected_type": "SQL" | "LLM",          # classification
            "expected_tool": str | None,              # e.g. "forecast_tool"
        }
        """
        results = []
        correct_classifications = 0
        latencies = []

        for tc in test_cases:
            q = tc["query"]
            expected_type = tc.get("expected_type")

            orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")

            # Measure classification only
            start = time.time()
            actual_type = orchestrator._classify_query_type(q)
            classify_time = round(time.time() - start, 3)

            type_correct = (actual_type == expected_type) if expected_type else None
            if type_correct:
                correct_classifications += 1

            # Run full pipeline for latency
            start2 = time.time()
            res = orchestrator.execute(q)
            total_time = round(time.time() - start2, 3)
            latencies.append(total_time)

            results.append({
                "query": q,
                "expected_type": expected_type,
                "actual_type": actual_type,
                "type_correct": type_correct,
                "classify_latency": classify_time,
                "total_latency": total_time,
            })
            time.sleep(1.0) # Rate limit protection

        accuracy = correct_classifications / len(test_cases) if test_cases else 0.0

        return {
            "total_tests": len(test_cases),
            "classification_accuracy": round(accuracy, 2),
            "latency_stats": _percentiles(latencies) if latencies else {},
            "details": results,
        }

    # ============================================================
    # 6. ABLATION: PIPELINE vs DIRECT LLM
    # ============================================================
    def run_ablation_pipeline_vs_direct(
        self,
        queries: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Compares the full NLP pipeline (classify → SQL/tools → LLM
        response) against sending the query directly to the LLM with
        raw data context.

        Each query: {"query": str, "expected": str}
        """
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.15,
            max_tokens=800,
        )

        pipeline_results = []
        direct_results = []
        summary_results = []

        for q_obj in queries:
            query = q_obj["query"]
            expected = q_obj["expected"]

            # ── A. Full pipeline ──
            orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")
            start = time.time()
            pipe_res = orchestrator.execute(query)
            pipe_time = round(time.time() - start, 3)
            pipe_text = pipe_res.get("response", "")
            pipe_match = str(expected).lower() in pipe_text.lower()

            pipeline_results.append({
                "query": query,
                "expected": expected,
                "response_preview": pipe_text[:150],
                "is_match": pipe_match,
                "latency": pipe_time,
            })

            # ── B. Direct LLM (no pipeline, no tools) ──
            # Give the LLM a sample of the data as context
            sample = self.df.head(20).to_string(index=False)
            cols = list(self.df.columns)
            shape = f"{self.df.shape[0]} rows × {self.df.shape[1]} columns"

            direct_prompt = f"""You have an inventory dataset ({shape}).
Columns: {cols}

Sample data:
{sample}

Answer this question accurately and concisely:
{query}"""

            start2 = time.time()
            try:
                direct_resp = llm.invoke([{"role": "user", "content": direct_prompt}])
                direct_text = direct_resp.content
            except Exception as e:
                direct_text = f"Error: {e}"
            direct_time = round(time.time() - start2, 3)

            direct_match = str(expected).lower() in direct_text.lower()

            direct_results.append({
                "query": query,
                "expected": expected,
                "response_preview": direct_text[:150],
                "is_match": direct_match,
                "latency": direct_time,
            })
            time.sleep(1.0) # Rate limit protection

            # ── C. Direct LLM + summary stats (fair baseline) ──
            # Same query, but the LLM receives the same aggregate information
            # a SQL tool would produce. Isolates the effect of delegation.
            cols = list(self.df.columns)
            shape = f"{self.df.shape[0]} rows × {self.df.shape[1]} columns"

            numeric_cols = self.df.select_dtypes(include=['number']).columns.tolist()
            summary_lines = [f"Dataset shape: {shape}", f"Columns: {cols}"]
            for col in numeric_cols:
                s = self.df[col]
                summary_lines.append(
                    f"{col}: sum={s.sum():.0f}, mean={s.mean():.2f}, "
                    f"min={s.min():.0f}, max={s.max():.0f}, "
                    f"unique={s.nunique()}"
                )
            if "Item" in self.df.columns and "Daily_Sales" in self.df.columns:
                per_item = self.df.groupby("Item")["Daily_Sales"].sum().to_dict()
                summary_lines.append(f"Total Daily_Sales per Item: {per_item}")
            if "Store" in self.df.columns and "Daily_Sales" in self.df.columns:
                per_store = self.df.groupby("Store")["Daily_Sales"].sum().to_dict()
                summary_lines.append(f"Total Daily_Sales per Store: {per_store}")
            if ("Item" in self.df.columns and "Store" in self.df.columns
                    and "Daily_Sales" in self.df.columns):
                per_pair = (
                    self.df.groupby(["Item", "Store"])["Daily_Sales"]
                    .sum()
                    .to_dict()
                )
                if len(per_pair) <= 200:
                    summary_lines.append(
                        f"Total Daily_Sales per (Item, Store): {per_pair}"
                    )
            summary_block = "\n".join(summary_lines)

            summary_prompt = f"""You have access to the following summary of an inventory dataset:

{summary_block}

Answer this question using the summary above. Be accurate and concise:
{query}"""

            start3 = time.time()
            try:
                summary_resp = llm.invoke([{"role": "user", "content": summary_prompt}])
                summary_text = summary_resp.content
            except Exception as e:
                summary_text = f"Error: {e}"
            summary_time = round(time.time() - start3, 3)

            clean_sum = str(summary_text).lower().replace(",", "").replace("$", "").strip()
            clean_exp_s = str(expected).lower().replace(",", "").replace("$", "").strip()
            summary_match = clean_exp_s in clean_sum

            summary_results.append({
                "query": query,
                "expected": expected,
                "response_preview": summary_text[:150],
                "is_match": summary_match,
                "latency": summary_time,
            })
            time.sleep(1.0)  # Rate-limit protection

        # Aggregate
        pipe_latencies = [r["latency"] for r in pipeline_results]
        direct_latencies = [r["latency"] for r in direct_results]
        summary_latencies = [r["latency"] for r in summary_results]
        pipe_accuracy = sum(1 for r in pipeline_results if r["is_match"]) / len(pipeline_results) if pipeline_results else 0
        direct_accuracy = sum(1 for r in direct_results if r["is_match"]) / len(direct_results) if direct_results else 0
        summary_accuracy = sum(1 for r in summary_results if r["is_match"]) / len(summary_results) if summary_results else 0

        return {
            "pipeline": {
                "accuracy": round(pipe_accuracy, 2),
                "latency_stats": _percentiles(pipe_latencies) if pipe_latencies else {},
                "details": pipeline_results,
            },
            "direct_llm": {
                "accuracy": round(direct_accuracy, 2),
                "latency_stats": _percentiles(direct_latencies) if direct_latencies else {},
                "details": direct_results,
            },
            "direct_llm_with_summary": {
                "accuracy": round(summary_accuracy, 2),
                "latency_stats": _percentiles(summary_latencies) if summary_latencies else {},
                "details": summary_results,
            },
        }

    # ============================================================
    # 7. ABLATION: FORECASTING MODEL COMPARISON
    # ============================================================
    def run_ablation_forecast_models(
        self,
        item: int,
        store: int,
        periods: int = 10,
    ) -> Dict[str, Any]:
        """
        Compares LightGBM vs ARIMA vs Exp.Smoothing on the same item/store.
        Reports forecasted values and latency for each.
        """
        from inventory_chatbot.analytics.forecasting import ForecastingTool

        tool = ForecastingTool()
        subset = self.df[
            (self.df["Item"].astype(str) == str(item))
            & (self.df["Store"].astype(str) == str(store))
        ].copy()

        if subset.empty:
            return {"error": f"No data for item {item} store {store}"}

        subset["Date"] = pd.to_datetime(subset["Date"])
        subset = subset.sort_values("Date")
        n = len(subset)

        results = {}

        # LightGBM (global pre-trained)
        if tool.lgbm_model and n >= 1:
            start = time.time()
            preds = tool.lgbm_forecast(subset, periods, item, store)
            elapsed = round(time.time() - start, 3)
            results["LightGBM (global)"] = {
                "predictions": [round(float(p), 2) for p in preds] if preds is not None else None,
                "latency": elapsed,
                "status": "success" if preds is not None else "discarded (out-of-scale)",
            }

        # LightGBM (fitted on uploaded data)
        if n >= 30:
            start = time.time()
            preds = tool._train_lgbm_on_data(subset, periods, item, store)
            elapsed = round(time.time() - start, 3)
            results["LightGBM (fitted)"] = {
                "predictions": [round(float(p), 2) for p in preds] if preds is not None else None,
                "latency": elapsed,
                "status": "success" if preds is not None else "failed",
            }

        # ARIMA
        if n >= 20:
            start = time.time()
            preds = tool.arima_forecast(subset, periods)
            elapsed = round(time.time() - start, 3)
            results["ARIMA"] = {
                "predictions": [round(float(p), 2) for p in preds],
                "latency": elapsed,
                "status": "success",
            }

        # Exponential Smoothing
        if n >= 7:
            start = time.time()
            preds = tool.exp_smoothing(subset, periods)
            elapsed = round(time.time() - start, 3)
            results["Exponential Smoothing"] = {
                "predictions": [round(float(p), 2) for p in preds],
                "latency": elapsed,
                "status": "success",
            }

        # Moving Average
        if n >= 2:
            start = time.time()
            val = tool.moving_avg(subset)
            elapsed = round(time.time() - start, 3)
            results["Moving Average (7-day)"] = {
                "predictions": [round(float(val), 2)] * periods,
                "latency": elapsed,
                "status": "success",
            }

        return {
            "item": item,
            "store": store,
            "data_points": n,
            "models": results,
        }
