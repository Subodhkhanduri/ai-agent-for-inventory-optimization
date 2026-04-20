# verify_lgbm_usage.py
import pandas as pd
import numpy as np
from inventory_chatbot.analytics.forecasting import ForecastingTool

# 1. Prepare minimal data (e.g., 5 rows - would normally trigger simple_mean)
data = {
    "Date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]),
    "Daily_Sales": [10.0, 12.0, 11.0, 15.0, 14.0],
    "item": [1, 1, 1, 1, 1],
    "store": [1, 1, 1, 1, 1]
}
df = pd.DataFrame(data)

# 2. Run forecast
tool = ForecastingTool()
print(f"Model loaded: {tool.lgbm_model is not None}")

try:
    image_bytes, forecast_list, method_used = tool.generate_forecast(df, item=1, store=1, periods=5)
    print(f"Method used: {method_used}")
    print(f"Forecast count: {len(forecast_list)}")
    
    if method_used == "lgbm":
        print("SUCCESS: LightGBM model prioritized correctly!")
    else:
        print(f"FAILURE: Expected 'lgbm', but got '{method_used}'")
        
except Exception as e:
    print(f"Error during forecast: {e}")
