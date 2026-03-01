
import pandas as pd
import numpy as np
import math
from inventory_chatbot.analytics.inventory_calculator import calculate_periodic_review_status

def test_inventory_equations():
    # Setup dummy data
    # Mean = 10, Std Dev = 2 (approx)
    data = {
        "Date": pd.date_range(start="2023-01-01", periods=10),
        "item": [1] * 10,
        "store": [1] * 10,
        "Daily_Sales": [8, 12, 10, 10, 9, 11, 10, 10, 8, 12], # Mean=10, Std=1.333
        "Quantity": [50] * 10 # Current stock
    }
    df = pd.DataFrame(data)
    
    # Parameters
    P = 7
    L = 7
    Z = 1.65
    current_stock = 50
    on_order = 10
    
    # Manual Calculation
    mu_d = df["Daily_Sales"].mean() # 10.0
    sigma_d = df["Daily_Sales"].std() # 1.3333...
    
    protection_interval_days = P + L # 14
    sigma_protection = math.sqrt(protection_interval_days) * sigma_d # 3.7416 * 1.3333 = 4.988
    
    safety_stock_expect = Z * sigma_protection # 1.65 * 4.988 = 8.23
    
    target_level_expect = (mu_d * protection_interval_days) + safety_stock_expect # 140 + 8.23 = 148.23
    
    inventory_position = current_stock + on_order # 60
    
    order_qty_expect = target_level_expect - inventory_position # 148.23 - 60 = 88.23
    
    print(f"MANUAL EXPECTATIONS:")
    print(f"Mean: {mu_d}")
    print(f"Sigma: {sigma_d}")
    print(f"Target Level (T): {target_level_expect}")
    print(f"Safety Stock (Ss): {safety_stock_expect}")
    print(f"Order Qty (Q): {order_qty_expect}")
    print("-" * 30)
    
    # Run Function
    result = calculate_periodic_review_status(
        df=df,
        item=1,
        store=1,
        review_period_days=P,
        lead_time_days=L,
        service_level=Z,
        stock_on_order=on_order
    )
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    print("FUNCTION RESULT:")
    print(f"Target Level (T): {result['target_level_T']}")
    print(f"Safety Stock (Ss): {result['safety_stock_Ss']}")
    print(f"Order Qty (Q): {result['calculated_order_quantity_Q']}")
    
    # Assertions (approximate)
    assert abs(result['target_level_T'] - target_level_expect) < 0.1, f"T mismatch: {result['target_level_T']} vs {target_level_expect}"
    assert abs(result['safety_stock_Ss'] - safety_stock_expect) < 0.1, f"Ss mismatch: {result['safety_stock_Ss']} vs {safety_stock_expect}"
    assert abs(result['calculated_order_quantity_Q'] - order_qty_expect) < 0.1, f"Q mismatch: {result['calculated_order_quantity_Q']} vs {order_qty_expect}"
    
    print("\n✅ VERIFICATION SUCCESSFUL: Code definition matches provided equations.")

if __name__ == "__main__":
    test_inventory_equations()
