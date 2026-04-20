import pandas as pd
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from inventory_chatbot.analytics.inventory_calculator import estimate_historical_lead_time, compare_lead_time_scenarios

try:
    # Load test data
    df = pd.read_csv("test_20_date_split.csv")
    df["Date"] = pd.to_datetime(df["Date"])

    # Test estimation
    stats = estimate_historical_lead_time(df)
    print(f"Historical Lead Time Stats: {stats}")

    # Test comparison
    comparison = compare_lead_time_scenarios(df, lead_time_days=7, service_level=1.65, user_lead_time_std=2.0)
    print(f"Comparison Recommendation: {comparison['summary']['recommendation']}")
    print(f"Number of items compared: {comparison['summary']['total_items']}")
    
    if len(comparison['item_comparison']) > 0:
        first_item = comparison['item_comparison'][0]
        print(f"First item comparison keys: {list(first_item.keys())}")
        print(f"First item: Item={first_item['Item']}, Store={first_item['Store']}")
        print(f"SS Fixed: {first_item['Safety Stock_fixed']}, SS Uncertain: {first_item['Safety Stock_uncertain']}")
    
    print("\nVerification Successful!")
except Exception as e:
    print(f"Verification Failed: {e}")
    import traceback
    traceback.print_exc()
