import os
import sys
import pandas as pd

# Ensure we can import from the parent and benchmarks directories
current_dir = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(current_dir, "..")))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..", "benchmarks")))

from inventory_chatbot.benchmarks.evaluator import SimpleInventoryOrchestrator
from run_benchmarks import generate_large_mock_data, build_precision_tests

df = generate_large_mock_data(1000)
tests = build_precision_tests(df)

orchestrator = SimpleInventoryOrchestrator(dataframe=df, user_role="admin")

with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write("Debugging failed queries...\n")
    for t in tests:
        query = t["query"]
        expected = t["expected"]
        
        # Run query
        res = orchestrator.execute(query)
        resp = res.get("response", "")
        sql_used = res.get("data", {}).get("sql", "NO SQL") if isinstance(res.get("data"), dict) else "NO SQL"
        
        is_match = str(expected).lower() in str(resp).lower()
        if not is_match:
            f.write(f"\n--- FAILED ---\n")
            f.write(f"Query: {query}\n")
            f.write(f"Expected: {expected}\n")
            f.write(f"SQL Generated: {sql_used}\n")
            f.write(f"Actual Response:\n{resp[:200]}\n")
