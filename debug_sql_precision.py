
import pandas as pd
import numpy as np
import os
from inventory_chatbot.crew.simple_orchestrator import SimpleInventoryOrchestrator
from inventory_chatbot.config import settings

def generate_large_mock_data(num_rows=10000):
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

print("Generating data...")
df = generate_large_mock_data(10000)
orchestrator = SimpleInventoryOrchestrator(dataframe=df, user_role="admin")

queries = [
    "How many rows are in the dataset?",
    "Total sales for store 1",
    "Total sales for item 1 across all stores",
    "Total daily sales for item 2 in store 1"
]

for q in queries:
    print(f"\n" + "="*50)
    print(f"Query: {q}")
    
    # Let's try to run the tool directly to see the SQL
    tool = orchestrator.tools["sql_query_tool"]
    tool._initialize_database()
    sql = tool._generate_sql(q)
    print(f"Generated SQL: {sql}")
    
    result = tool._execute_sql(sql)
    print(f"SQL Result: {result}")
    
    # Run full orchestrator to see final response
    res = orchestrator.execute(q)
    print(f"Final Response: {res['response']}")
