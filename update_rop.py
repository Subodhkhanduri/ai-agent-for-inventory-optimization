import sys
import math

path = r"d:\MTP2\conversational-inventory-ai-main\inventory_chatbot\analytics\inventory_calculator.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = '''        # Logic: If Q > 0, we order Q. If Q <= 0, we do not order.
        should_order = order_quantity > 0
        final_order_qty = max(0, order_quantity)

        return {'''
replacement1 = '''        # Calculate ROP
        sigma_lead_time = math.sqrt(L) * sigma_d
        rop = (mu_d * L) + (service_level * sigma_lead_time)
        needs_reorder_rop = inventory_position < rop
        
        # Logic: We only order if current inventory_position is below ROP
        should_order = (order_quantity > 0) and needs_reorder_rop
        final_order_qty = max(0, order_quantity) if should_order else 0

        return {'''

content = content.replace(target1, replacement1)

target2 = '''            "protection_interval_days": protection_interval,
            
            "daily_demand_mean_mu": round(mu_d, 2),'''
replacement2 = '''            "protection_interval_days": protection_interval,
            
            "calculated_rop": round(rop, 2),
            "daily_demand_mean_mu": round(mu_d, 2),'''
content = content.replace(target2, replacement2)

target3 = '''        if "error" not in res:
            results.append({
                "Item": pair["Item"],
                "Store": pair["Store"],
                "Current Stock": res["current_on_hand"],
                "Target Level (T)": res["target_level_T"],'''
replacement3 = '''        if "error" not in res:
            results.append({
                "Item": pair["Item"],
                "Store": pair["Store"],
                "Current Stock": res["current_on_hand"],
                "ROP": round(res.get("calculated_rop", 0), 2),
                "Target Level (T)": res["target_level_T"],'''
content = content.replace(target3, replacement3)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("done")
