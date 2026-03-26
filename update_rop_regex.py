import re

path = r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\analytics\inventory_calculator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. replace logic
sub1 = re.sub(
    r"# Logic: If Q > 0, we order Q\. If Q <= 0, we do not order\.\s*should_order = order_quantity > 0\s*final_order_qty = max\(0, order_quantity\)",
    "# Calculate ROP\n        sigma_lead_time = math.sqrt(L) * sigma_d\n        rop = (mu_d * L) + (service_level * sigma_lead_time)\n        needs_reorder_rop = inventory_position < rop\n\n        # Logic: We only order if current inventory_position is below ROP\n        should_order = (order_quantity > 0) and needs_reorder_rop\n        final_order_qty = max(0, order_quantity) if should_order else 0",
    content
)

# 2. replace return dict properties
sub2 = re.sub(
    r'"protection_interval_days": protection_interval,\s*"daily_demand_mean_mu": round\(mu_d, 2\),',
    '"protection_interval_days": protection_interval,\n            "calculated_rop": round(rop, 2),\n            "daily_demand_mean_mu": round(mu_d, 2),',
    sub1
)

# 3. replace append result mapping
sub3 = re.sub(
    r'"Current Stock": res\["current_on_hand"\],\s*"Target Level \(T\)": res\["target_level_T"\],',
    '"Current Stock": res["current_on_hand"],\n                "ROP": round(res.get("calculated_rop", 0), 2),\n                "Target Level (T)": res["target_level_T"],',
    sub2
)

if sub3 != content:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(sub3)
    print("Replaced successfully")
else:
    print("No changes made. Match failed.")
