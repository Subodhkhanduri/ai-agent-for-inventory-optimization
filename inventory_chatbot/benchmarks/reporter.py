# inventory_chatbot/benchmarks/reporter.py

from typing import Dict, Any, List

def generate_benchmarking_report(consistency_results: List[Dict[str, Any]], 
                                 noise_results: List[Dict[str, Any]]) -> str:
    """
    Generates a Markdown report of the robustness benchmarks.
    """
    report = "# 📊 LLM Robustness Benchmarking Report\n\n"
    
    report += "## 1. Consistency Evaluation\n"
    report += "| Query | Trials | Uniq Responses | Consistency Score |\n"
    report += "| :--- | :--- | :--- | :--- |\n"
    
    for res in consistency_results:
        report += f"| {res['query']} | {res['trials']} | {res['unique_responses']} | {res['consistency_score'] * 100}% |\n"
    
    report += "\n---\n\n"
    
    report += "## 2. Noise & Typo Sensitivity\n"
    for res in noise_results:
        report += f"### Base Query: *{res['base_query']}*\n"
        report += "| Noisy Query | Success | Response Preview |\n"
        report += "| :--- | :--- | :--- |\n"
        for nr in res['noisy_results']:
            preview = nr['response'][:100].replace('\n', ' ') + "..."
            status = "✅" if nr['is_successful'] else "❌"
            report += f"| {nr['noisy_query']} | {status} | {preview} |\n"
        report += "\n"
        
    report += "\n---\n"
    report += "## Summary Findings\n"
    report += "- **Consistency**: Measures how stable the LLM is across identical inputs.\n"
    report += "- **Sensitivity**: Measures how well the NLP/SQL logic handles human spelling errors.\n"
    
    return report
