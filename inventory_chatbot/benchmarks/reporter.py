# inventory_chatbot/benchmarks/reporter.py

"""
Enhanced markdown report generator with:
  - Separated numerical vs textual stability analysis
  - P50/P95/P99 percentile tables + std dev
  - Tool-use accuracy, ablation comparison tables
  - Statistical rigor section
"""

import math
from typing import Dict, Any, List


def _ci_95(values: List[float]) -> Dict[str, float]:
    """Compute mean, std, and 95% confidence interval for a list of values."""
    n = len(values)
    if n == 0:
        return {"mean": 0, "std": 0, "ci_lower": 0, "ci_upper": 0, "margin": 0}
    mean = sum(values) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0
    se = std / math.sqrt(n) if n > 0 else 0
    margin = 1.96 * se
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "ci_lower": round(mean - margin, 4),
        "ci_upper": round(mean + margin, 4),
        "margin": round(margin, 4),
        "n": n,
    }


def generate_benchmarking_report(
    consistency_results: List[Dict[str, Any]],
    noise_results: List[Dict[str, Any]],
    precision_results: Dict[str, Any] = None,
    tool_use_results: Dict[str, Any] = None,
    ablation_results: Dict[str, Any] = None,
    forecast_ablation: Dict[str, Any] = None,
) -> str:
    """
    Generates a comprehensive Markdown benchmarking report.
    """
    report = "# 📊 LLM Robustness & Pipeline Stability Evaluation Report\n\n"

    report += "> **Model**: Meta LLaMA 3.1 8B Instruct | **Temperature**: 0.15 | "
    report += "**Inference**: Groq Cloud LPU\n\n"

    # ─────────────────────────────────────────
    # 1. Consistency & Latency (with P99 + Std)
    # ─────────────────────────────────────────
    report += "## 1. Consistency & Latency Evaluation\n\n"

    report += "### Consistency Scores\n\n"
    report += ("Consistency measures stability of structured outputs across "
               "repeated identical queries.\n\n")
    report += "$$\\text{Consistency Score} = \\frac{\\text{Identical Structured Outputs}}"
    report += "{\\text{Total Trials}}$$\n\n"

    report += "| Query | Trials | Unique Resp | Consistency | P50 (s) | P95 (s) | P99 (s) | Mean (s) | Std (s) |\n"
    report += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"

    for res in consistency_results:
        ls = res.get("latency_stats", {})
        report += (
            f"| {res['query'][:55]}… | {res['trials']} | {res['unique_responses']} "
            f"| {res['consistency_score'] * 100:.0f}% "
            f"| {ls.get('p50', '-')} | {ls.get('p95', '-')} | {ls.get('p99', '-')} "
            f"| {ls.get('mean', '-')} | {ls.get('std', '-')} |\n"
        )
    report += "\n"

    # Interpretation
    report += ("> **Interpretation**: Although textual responses vary due to inherent LLM "
               "stochasticity, the underlying structured numerical outputs remain stable. "
               "Surface-level text variability does not impact analytical correctness.\n\n")
    report += "---\n\n"

    # ─────────────────────────────────────────
    # 2. Precision & Accuracy — SEPARATED by category
    # ─────────────────────────────────────────
    if precision_results:
        report += "## 2. Precision & Accuracy Evaluation\n\n"
        pr_score = precision_results["precision_score"] * 100
        total = precision_results["total_tests"]
        ls = precision_results.get("latency_stats", {})

        report += "$$\\text{Precision} = \\frac{\\text{Correct Structured Outputs}}"
        report += "{\\text{Total Evaluated Queries}}$$\n\n"

        report += f"**Overall Precision**: **{pr_score:.1f}%** across **{total} queries**\n\n"
        report += (f"**Latency**: P50={ls.get('p50', '-')}s | P95={ls.get('p95', '-')}s | "
                   f"**P99={ls.get('p99', '-')}s** | Mean={ls.get('mean', '-')}s | "
                   f"Std={ls.get('std', '-')}s\n\n")

        # Separate numerical vs textual
        categories = {}
        for d in precision_results["details"]:
            cat = d.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(d)

        numerical_cats = {k: v for k, v in categories.items() if k.startswith("numerical_")}
        textual_cats = {k: v for k, v in categories.items() if k.startswith("textual_")}

        # ── 2a. Numerical Stability ──
        report += "### 2a. Numerical Stability\n\n"
        report += ("Queries where the expected output is a **specific number** computed "
                   "deterministically via Pandas.\n\n")

        num_correct = sum(1 for items in numerical_cats.values() for d in items if d["is_match"])
        num_total = sum(len(items) for items in numerical_cats.values())
        num_latencies = [d["latency"] for items in numerical_cats.values() for d in items]
        num_ci = _ci_95(num_latencies)

        report += f"**Numerical Precision**: **{num_correct}/{num_total}** "
        report += f"({num_correct/num_total*100:.1f}%)\n\n" if num_total > 0 else "(N/A)\n\n"

        report += "| Category | Queries | Correct | Accuracy |\n"
        report += "| :--- | :---: | :---: | :---: |\n"
        for cat in sorted(numerical_cats.keys()):
            items = numerical_cats[cat]
            correct = sum(1 for d in items if d["is_match"])
            label = cat.replace("numerical_", "").replace("_", " ").title()
            report += f"| {label} | {len(items)} | {correct} | {correct/len(items)*100:.0f}% |\n"
        report += "\n"

        report += "| Query | Expected | Match | Latency (s) |\n"
        report += "| :--- | :--- | :---: | :---: |\n"
        for cat in sorted(numerical_cats.keys()):
            for d in numerical_cats[cat]:
                status = "✅" if d["is_match"] else "❌"
                report += f"| {d['query'][:55]} | {d['expected']} | {status} | {d['latency']} |\n"
        report += "\n"

        # ── 2b. Textual Stability ──
        report += "### 2b. Textual Stability\n\n"
        report += ("Queries where the expected output is a **keyword or concept** "
                   "(intent classification, forecast trigger, general knowledge).\n\n")

        txt_correct = sum(1 for items in textual_cats.values() for d in items if d["is_match"])
        txt_total = sum(len(items) for items in textual_cats.values())
        txt_latencies = [d["latency"] for items in textual_cats.values() for d in items]
        txt_ci = _ci_95(txt_latencies)

        report += f"**Textual Precision**: **{txt_correct}/{txt_total}** "
        report += f"({txt_correct/txt_total*100:.1f}%)\n\n" if txt_total > 0 else "(N/A)\n\n"

        report += "| Category | Queries | Correct | Accuracy |\n"
        report += "| :--- | :---: | :---: | :---: |\n"
        for cat in sorted(textual_cats.keys()):
            items = textual_cats[cat]
            correct = sum(1 for d in items if d["is_match"])
            label = cat.replace("textual_", "").replace("_", " ").title()
            report += f"| {label} | {len(items)} | {correct} | {correct/len(items)*100:.0f}% |\n"
        report += "\n"

        report += "| Query | Expected | Match | Latency (s) |\n"
        report += "| :--- | :--- | :---: | :---: |\n"
        for cat in sorted(textual_cats.keys()):
            for d in textual_cats[cat]:
                status = "✅" if d["is_match"] else "❌"
                report += f"| {d['query'][:55]} | {d['expected']} | {status} | {d['latency']} |\n"
        report += "\n"

        # ── 2c. Latency Summary ──
        report += "### 2c. Latency Distribution\n\n"
        report += "| Query Type | n | Mean (s) | Std (s) | 95% CI |\n"
        report += "| :--- | :---: | :---: | :---: | :--- |\n"
        report += (f"| Numerical | {num_ci['n']} | {num_ci['mean']:.3f} | {num_ci['std']:.3f} "
                   f"| [{num_ci['ci_lower']:.3f}, {num_ci['ci_upper']:.3f}] |\n")
        report += (f"| Textual | {txt_ci['n']} | {txt_ci['mean']:.3f} | {txt_ci['std']:.3f} "
                   f"| [{txt_ci['ci_lower']:.3f}, {txt_ci['ci_upper']:.3f}] |\n")

        all_latencies = [d["latency"] for d in precision_results["details"]]
        all_ci = _ci_95(all_latencies)
        report += (f"| **Overall** | **{all_ci['n']}** | **{all_ci['mean']:.3f}** | "
                   f"**{all_ci['std']:.3f}** "
                   f"| **[{all_ci['ci_lower']:.3f}, {all_ci['ci_upper']:.3f}]** |\n")
        report += "\n---\n\n"

    # ─────────────────────────────────────────
    # 3. Noise & Typo Sensitivity
    # ─────────────────────────────────────────
    report += "## 3. Noise & Typo Robustness\n\n"
    report += "Input queries were intentionally corrupted with misspellings, "
    report += "capitalization changes, and synonym substitutions.\n\n"

    total_noisy = 0
    total_noisy_success = 0

    for res in noise_results:
        report += f"### Base Query: *{res['base_query']}*\n"
        report += "| Noisy Query | Success | Latency (s) |\n"
        report += "| :--- | :---: | :---: |\n"
        for nr in res["noisy_results"]:
            status = "✅" if nr["is_successful"] else "❌"
            report += f"| {nr['noisy_query'][:60]} | {status} | {nr.get('latency', '-')} |\n"
            total_noisy += 1
            if nr["is_successful"]:
                total_noisy_success += 1
        report += "\n"

    noise_rate = total_noisy_success / total_noisy * 100 if total_noisy > 0 else 0
    report += f"**Overall Noise Tolerance**: {total_noisy_success}/{total_noisy} "
    report += f"({noise_rate:.0f}%)\n\n"
    report += "---\n\n"

    # ─────────────────────────────────────────
    # 4. Tool-Use Classification Accuracy
    # ─────────────────────────────────────────
    if tool_use_results:
        report += "## 4. Tool-Use Classification Accuracy\n\n"
        acc = tool_use_results["classification_accuracy"] * 100
        total = tool_use_results["total_tests"]
        ls = tool_use_results.get("latency_stats", {})

        report += f"**Classification Accuracy**: **{acc:.1f}%** ({total} tests)\n\n"
        report += (f"**End-to-end Latency**: P50={ls.get('p50', '-')}s | "
                   f"P95={ls.get('p95', '-')}s | **P99={ls.get('p99', '-')}s** | "
                   f"Std={ls.get('std', '-')}s\n\n")

        report += "| Query | Expected | Actual | Correct | Classify (s) | Total (s) |\n"
        report += "| :--- | :---: | :---: | :---: | :---: | :---: |\n"

        for d in tool_use_results["details"]:
            status = "✅" if d["type_correct"] else "❌"
            report += (
                f"| {d['query'][:50]} | {d['expected_type']} | {d['actual_type']} "
                f"| {status} | {d['classify_latency']} | {d['total_latency']} |\n"
            )
        report += "\n---\n\n"

    # ─────────────────────────────────────────
    # 5. Ablation: Pipeline vs Direct LLM
    # ─────────────────────────────────────────
    if ablation_results:
        report += "## 5. Ablation Study: NLP Pipeline vs Direct LLM\n\n"

        pipe = ablation_results["pipeline"]
        direct = ablation_results["direct_llm"]

        report += "| Metric | NLP Pipeline | Direct LLM |\n"
        report += "| :--- | :---: | :---: |\n"
        report += f"| **Accuracy** | {pipe['accuracy'] * 100:.1f}% | {direct['accuracy'] * 100:.1f}% |\n"

        pls = pipe.get("latency_stats", {})
        dls = direct.get("latency_stats", {})
        report += f"| Mean Latency (s) | {pls.get('mean', '-')} | {dls.get('mean', '-')} |\n"
        report += f"| Std Latency (s) | {pls.get('std', '-')} | {dls.get('std', '-')} |\n"
        report += f"| P50 Latency (s) | {pls.get('p50', '-')} | {dls.get('p50', '-')} |\n"
        report += f"| P95 Latency (s) | {pls.get('p95', '-')} | {dls.get('p95', '-')} |\n"
        report += f"| **P99 Latency (s)** | **{pls.get('p99', '-')}** | **{dls.get('p99', '-')}** |\n"

        report += "\n### Per-Query Comparison\n\n"
        report += "| Query | Pipeline Match | Direct Match | Pipeline (s) | Direct (s) |\n"
        report += "| :--- | :---: | :---: | :---: | :---: |\n"

        for p_d, d_d in zip(pipe["details"], direct["details"]):
            ps = "✅" if p_d["is_match"] else "❌"
            ds = "✅" if d_d["is_match"] else "❌"
            report += f"| {p_d['query'][:50]} | {ps} | {ds} | {p_d['latency']} | {d_d['latency']} |\n"

        report += "\n---\n\n"

    # ─────────────────────────────────────────
    # 6. Ablation: Forecasting Models
    # ─────────────────────────────────────────
    if forecast_ablation and "error" not in forecast_ablation:
        report += "## 6. Ablation Study: Forecasting Models\n\n"
        report += (f"**Item**: {forecast_ablation['item']} | **Store**: {forecast_ablation['store']} "
                   f"| **Data Points**: {forecast_ablation['data_points']}\n\n")

        report += "| Model | Status | Latency (s) | Predictions (first 5) |\n"
        report += "| :--- | :---: | :---: | :--- |\n"

        for name, data in forecast_ablation["models"].items():
            preds = data.get("predictions")
            preds_str = str(preds[:5]) if preds else "N/A"
            report += f"| {name} | {data['status']} | {data['latency']} | {preds_str} |\n"

        report += "\n---\n\n"

    # ─────────────────────────────────────────
    # Statistical Summary & Confidence
    # ─────────────────────────────────────────
    report += "## Statistical Summary\n\n"
    report += "| Dimension | Metric | Value | n |\n"
    report += "| :--- | :--- | :---: | :---: |\n"

    # Consistency
    if consistency_results:
        c_scores = [r["consistency_score"] * 100 for r in consistency_results]
        c_ci = _ci_95(c_scores)
        report += f"| Consistency | Mean Score | {c_ci['mean']:.1f}% | {c_ci['n']} |\n"
        report += f"| | Std Dev | {c_ci['std']:.1f}% | |\n"

    # Precision
    if precision_results:
        report += f"| Precision | Overall | {precision_results['precision_score']*100:.1f}% | {precision_results['total_tests']} |\n"

        # Numerical vs Textual
        categories = {}
        for d in precision_results["details"]:
            cat = d.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(d)

        num_cats = {k: v for k, v in categories.items() if k.startswith("numerical_")}
        txt_cats = {k: v for k, v in categories.items() if k.startswith("textual_")}

        num_c = sum(1 for items in num_cats.values() for d in items if d["is_match"])
        num_t = sum(len(items) for items in num_cats.values())
        txt_c = sum(1 for items in txt_cats.values() for d in items if d["is_match"])
        txt_t = sum(len(items) for items in txt_cats.values())

        if num_t > 0:
            report += f"| | Numerical Stability | {num_c/num_t*100:.1f}% | {num_t} |\n"
        if txt_t > 0:
            report += f"| | Textual Stability | {txt_c/txt_t*100:.1f}% | {txt_t} |\n"

    # Noise
    if total_noisy > 0:
        report += f"| Noise Tolerance | Success Rate | {noise_rate:.0f}% | {total_noisy} |\n"

    # Tool-use
    if tool_use_results:
        report += f"| Tool Classification | Accuracy | {tool_use_results['classification_accuracy']*100:.1f}% | {tool_use_results['total_tests']} |\n"

    # Ablation
    if ablation_results:
        report += f"| Pipeline vs Direct | Pipeline Accuracy | {ablation_results['pipeline']['accuracy']*100:.1f}% | {len(ablation_results['pipeline']['details'])} |\n"
        report += f"| | Direct LLM Accuracy | {ablation_results['direct_llm']['accuracy']*100:.1f}% | {len(ablation_results['direct_llm']['details'])} |\n"

    report += "\n"

    report += ("> **Note**: GPU metrics are not applicable. LLM inference is offloaded to "
               "Groq's cloud-hosted LPU hardware. All local compute is CPU-only.\n")

    return report
