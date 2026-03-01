
import pandas as pd
from inventory_chatbot.analytics.inventory_calculator import calculate_batch_periodic_review

def test_batch_review():
    # Setup dummy data for multiple items
    data = {
        "Date": pd.date_range(start="2023-01-01", periods=10).tolist() * 2,
        "item": [1] * 10 + [2] * 10,
        "store": [1] * 10 + [1] * 10,
        "Daily_Sales": [10] * 10 + [5] * 10,
        "Quantity": [50] * 10 + [100] * 10 
    }
    df = pd.DataFrame(data)
    
    # Item 1: Mean=10, P+L=14, T~150, Stock=50 -> Q~100 (ORDER)
    # Item 2: Mean=5, P+L=14, T~75, Stock=100 -> Q=-25 (NO ORDER)
    
    results = calculate_batch_periodic_review(df)
    
    print("Batch Review Results:")
    print(results)
    
    # Assertions
    assert not results.empty, "Results should not be empty"
    assert len(results) == 2, f"Expected 2 items, got {len(results)}"
    
    # Check Item 1
    item1 = results[results["Item"] == 1].iloc[0]
    assert "ORDER" in item1["Status"], "Item 1 should need ordering"
    assert item1["Order Qty (Q)"] > 0, "Item 1 Qty should be positive"
    
    # Check Item 2
    item2 = results[results["Item"] == 2].iloc[0]
    assert "OK" in item2["Status"], "Item 2 should be OK"
    
    print("\n✅ Batch Review Logic Verified")

if __name__ == "__main__":
    test_batch_review()
