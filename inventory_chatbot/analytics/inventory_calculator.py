# inventory_chatbot/analytics/inventory_calculator.py

import logging
import math
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

def calculate_rop_status(df: pd.DataFrame, item: int, store: int, 
                         lead_time: int = 7, service_level: float = 1.65) -> Dict[str, Any]:
    """
    Calculate Reorder Point (ROP) and current inventory status.
    Formula: ROP = (μ * L) + (Z * σ * √L)
    
    Args:
        df: Inventory DataFrame
        item: Item ID
        store: Store ID
        lead_time: L (days)
        service_level: Z (safety factor)
        
    Returns:
        Dictionary with ROP details and reorder recommendation.
    """
    try:
        # 1. Filter data for specific item/store
        subset = df[(df["Item"] == item) & (df["Store"] == store)].copy()
        
        if subset.empty:
            return {"error": f"No data found for item {item} in store {store}"}

        # Ensure Date is datetime
        if not pd.api.types.is_datetime64_any_dtype(subset["Date"]):
            subset["Date"] = pd.to_datetime(subset["Date"])
        
        subset = subset.sort_values("Date")

        # 2. Calculate μ (mean) and σ (std dev) of Demand
        mu = subset["Demand"].mean()
        sigma = subset["Demand"].std()
        
        if math.isnan(sigma): # If only 1 row
            sigma = 0

        # 3. Compute ROP
        # ROP = (μ * L) + (Z * σ * sqrt(L))
        lead_time_sqrt = math.sqrt(lead_time)
        rop = (mu * lead_time) + (service_level * sigma * lead_time_sqrt)
        
        # 4. Get Current Quantity
        # We look for "Quantity" or "Stock" columns. 
        # If missing, we use the most recent "Daily_Sales" as a placeholder (though ideally the data has stock levels)
        current_quantity = None
        for col in ["Quantity", "Stock", "Inventory_Level"]:
            if col in subset.columns:
                current_quantity = subset[col].iloc[-1]
                break
        
        if current_quantity is None:
            # Fallback: use End_Stock if available, otherwise last Demand
            if "End_Stock" in subset.columns:
                current_quantity = subset["End_Stock"].iloc[-1]
                quantity_source = "End_Stock (Data Column)"
            else:
                current_quantity = subset["Demand"].iloc[-1] * 1
                quantity_source = "Last Demand (Estimated)"
        else:
            quantity_source = "Data Column"

        needs_reorder = current_quantity < rop

        return {
            "item": item,
            "store": store,
            "mean_daily_sales": round(mu, 2),
            "std_dev_sales": round(sigma, 2),
            "lead_time": lead_time,
            "service_level": service_level,
            "calculated_rop": round(rop, 2),
            "current_quantity": round(current_quantity, 2),
            "needs_reorder": needs_reorder,
            "quantity_source": quantity_source
        }

    except Exception as e:
        logger.error(f"Error calculating ROP for item {item} store {store}: {e}")
        return {"error": str(e)}

def calculate_periodic_review_status(df: pd.DataFrame, item: int, store: int,
                                     review_period_days: int = 7,
                                     lead_time_days: int = 7,
                                     service_level: float = 1.65,
                                     stock_on_order: float = 0.0,
                                     forecasted_daily_demand: float = None) -> Dict[str, Any]:
    r"""
    Calculate Order Quantity (Q) using the Periodic Review System (P, T).
    Based on the standard equations:
    
    1. Inventory Position ($I_P$)
       $I_P = \text{On-hand Inventory} + \text{On-order Quantities}$
       
    2. Target Level ($T$)
       $T = \text{Forecast of Demand over } (P + L) + \text{Safety Stock}$
       
    3. Safety Stock ($Ss$)
       $Ss = Z \times \sigma_{P+L}$
       $\sigma_{P+L} = \sqrt{P + L} \times \sigma_d$
       
    4. Amount to Order ($Q$)
       $Q = T - I_P$

    Args:
        df: Inventory DataFrame containing historical Demand
        item: Item ID
        store: Store ID
        review_period_days: Length of review period ($P$)
        lead_time_days: Supply lead time ($L$)
        service_level: Service factor ($Z$). Default 1.65 (approx 95% service level)
        stock_on_order: Quantity already ordered but not received
        forecasted_daily_demand: Optional manually provided daily demand forecast. 
                               If None, calculates historical mean ($\mu_d$).
        
    Returns:
        Dictionary with detailed calculation breakdown.
    """
    try:
        # 1. Filter data for specific item/store
        subset = df[(df["Item"] == item) & (df["Store"] == store)].copy()
        
        if subset.empty:
            return {"error": f"No data found for item {item} in store {store}"}

        # Ensure Date is datetime
        if not pd.api.types.is_datetime64_any_dtype(subset["Date"]):
            subset["Date"] = pd.to_datetime(subset["Date"])
        
        subset = subset.sort_values("Date")

        # 2. Demand Parameters (Mean & Variability)
        # $\mu_d$ (Average Daily Demand)
        if forecasted_daily_demand is not None:
             mu_d = forecasted_daily_demand
             demand_source = "Forecast Model"
        else:
             mu_d = subset["Demand"].mean()
             demand_source = "Historical Mean"
             
        # $\sigma_d$ (Standard Deviation of Daily Demand)
        sigma_d = subset["Demand"].std()
        
        if math.isnan(sigma_d): # If only 1 row or constant demand
            sigma_d = 0

        # 3. Time Intervals
        P = review_period_days
        L = lead_time_days
        protection_interval = P + L  # (P + L)

        # 4. Calculate Safety Stock ($Ss$)
        # $\sigma_{P+L} = \sqrt{P + L} \times \sigma_d$
        sigma_protection_interval = math.sqrt(protection_interval) * sigma_d
        
        # $Ss = Z \times \sigma_{P+L}$
        safety_stock = service_level * sigma_protection_interval

        # 5. Calculate Target Level ($T$)
        # $T = \text{Average Demand over } (P + L) + Ss$
        # $T = (\mu_d \times (P + L)) + Ss$
        demand_during_protection = mu_d * protection_interval
        target_level = demand_during_protection + safety_stock

        # 6. Inventory Position ($I_P$)
        # Get On-hand Inventory
        current_on_hand = None
        for col in ["Quantity", "Stock", "Inventory_Level"]:
            if col in subset.columns:
                current_on_hand = subset[col].iloc[-1]
                break
        
        if current_on_hand is None:
            # Fallback: use End_Stock if available, otherwise last Demand
            if "End_Stock" in subset.columns:
                current_on_hand = subset["End_Stock"].iloc[-1]
                quantity_source = "End_Stock (Data Column)"
            else:
                current_on_hand = subset["Demand"].iloc[-1]
                quantity_source = "Last Demand (Estimated - Missing Col)"
        else:
            quantity_source = "Data Column"

        # $I_P = \text{On-hand} + \text{On-order}$
        inventory_position = current_on_hand + stock_on_order

        # 7. Amount to Order ($Q$)
        # $Q = T - I_P$
        order_quantity = target_level - inventory_position
        
        # Logic: If Q > 0, we order Q. If Q <= 0, we do not order.
        should_order = order_quantity > 0
        final_order_qty = max(0, order_quantity)

        return {
            "item": item,
            "store": store,
            "review_period_days_P": P,
            "lead_time_days_L": L,
            "protection_interval_days": protection_interval,
            
            "daily_demand_mean_mu": round(mu_d, 2),
            "daily_demand_std_sigma": round(sigma_d, 2),
            "demand_source": demand_source,
            
            "safety_stock_Ss": round(safety_stock, 2),
            "target_level_T": round(target_level, 2),
            
            "current_on_hand": round(current_on_hand, 2),
            "stock_on_order": round(stock_on_order, 2),
            "inventory_position_Ip": round(inventory_position, 2),
            
            "calculated_order_quantity_Q": round(final_order_qty, 2),
            "should_order": should_order,
            "quantity_source": quantity_source,
            
            # Helper for UI/Tool display
            "summary_code": "ORDER" if should_order else "OK"
        }

    except Exception as e:
        logger.error(f"Error calculating Periodic Review for item {item} store {store}: {e}")
        return {"error": str(e)}

def calculate_batch_periodic_review(df: pd.DataFrame, review_period_days: int = 7) -> pd.DataFrame:
    """
    Run Periodic Review System calculation for ALL items in the DataFrame.
    Returns a summary DataFrame with key metrics, sorted by urgency.
    """
    results = []
    
    # Get unique item-store pairs
    if "Item" not in df.columns or "Store" not in df.columns:
        return pd.DataFrame()

    pairs = df[["Item", "Store"]].drop_duplicates().to_dict('records')
    
    for pair in pairs:
        res = calculate_periodic_review_status(
            df=df,
            item=pair["Item"],
            store=pair["Store"],
            review_period_days=review_period_days
        )
        
        if "error" not in res:
            results.append({
                "Item": pair["Item"],
                "Store": pair["Store"],
                "Current Stock": res["current_on_hand"],
                "Target Level (T)": res["target_level_T"],
                "Order Qty (Q)": res["calculated_order_quantity_Q"],
                "Status": "🔴 ORDER" if res["should_order"] else "🟢 OK",
                "Urgency": res["calculated_order_quantity_Q"] if res["should_order"] else 0
            })
            
    if not results:
        return pd.DataFrame()
        
    results_df = pd.DataFrame(results)
    
    # Sort by Urgency (descending) so biggest orders are on top
    results_df = results_df.sort_values("Urgency", ascending=False)
    
    return results_df
def calculate_eoq(annual_demand: float, ordering_cost: float, holding_cost_per_unit: float) -> float: return math.sqrt((2 * annual_demand * ordering_cost) / holding_cost_per_unit)
