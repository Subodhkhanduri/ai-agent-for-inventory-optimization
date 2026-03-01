# inventory_chatbot/benchmarks/evaluator.py

import time
import logging
import pandas as pd
from typing import List, Dict, Any
from inventory_chatbot.crew.simple_orchestrator import SimpleInventoryOrchestrator

logger = logging.getLogger(__name__)

class RobustnessEvaluator:
    """
    Benchmarks LLM performance on consistency and noise sensitivity.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Note: We create a new orchestrator for each evaluation to ensure a fresh session context
        # but sharing the same DF.
        
    def run_consistency_test(self, query: str, trials: int = 5) -> Dict[str, Any]:
        """
        Runs the same query multiple times and checks for stability.
        """
        results = []
        sql_queries = []
        
        for i in range(trials):
            orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")
            start_time = time.time()
            res = orchestrator.execute(query)
            end_time = time.time()
            
            # Check if SQL was used and extract it
            # Note: sql_used is typically returned by the orchestrator in some way or we can check the context
            # In our current SimpleInventoryOrchestrator, it returns a dict with 'response'
            # We might need to expose the tool outputs for better evaluation.
            # For now, let's just track the final response and any metadata we can find.
            
            results.append({
                "trial": i + 1,
                "response": res.get("response", ""),
                "latency": round(end_time - start_time, 2)
            })
            
        # Analysis
        unique_responses = len(set([r["response"] for r in results]))
        consistency_score = (trials - (unique_responses - 1)) / trials
        
        return {
            "query": query,
            "trials": trials,
            "consistency_score": round(consistency_score, 2),
            "unique_responses": unique_responses,
            "details": results
        }

    def run_noise_test(self, base_query: str, noisy_queries: List[str]) -> Dict[str, Any]:
        """
        Tests how typos/noise in the query affects the output.
        """
        orchestrator = SimpleInventoryOrchestrator(dataframe=self.df, user_role="admin")
        
        # Base run
        base_res = orchestrator.execute(base_query)
        base_response = base_res.get("response", "")
        
        results = []
        for q in noisy_queries:
            res = orchestrator.execute(q)
            results.append({
                "noisy_query": q,
                "response": res.get("response", ""),
                "is_successful": "error" not in res.get("response", "").lower() # Basic check
            })
            
        return {
            "base_query": base_query,
            "noisy_results": results
        }

    def run_data_corruption_test(self, query: str, corrupt_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Tests how the LLM/Orchestrator handles corrupted data.
        """
        orchestrator = SimpleInventoryOrchestrator(dataframe=corrupt_df, user_role="admin")
        res = orchestrator.execute(query)
        
        return {
            "query": query,
            "response": res.get("response", ""),
            "status": "Handled" if "error" in res.get("response", "").lower() or "not find" in res.get("response", "").lower() else "Processed"
        }
