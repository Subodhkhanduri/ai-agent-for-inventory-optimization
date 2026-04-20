# inventory_chatbot/analytics/inventory_calculator.py



import logging

import math

import pandas as pd

from typing import Dict, Any



logger = logging.getLogger(__name__)



def calculate_rop_status(df: pd.DataFrame, item: int, store: int, 

                         lead_time: int = 7, service_level: float = 1.65, lead_time_std: float = 0.0) -> Dict[str, Any]:

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

        # ROP = (μ * L) + Z * sqrt(L * σ_d^2 + μ^2 * σ_L^2)

        variance_term = (lead_time * (sigma ** 2)) + ((mu ** 2) * (lead_time_std ** 2))

        std_dev_combined = math.sqrt(max(0, variance_term))

        rop = (mu * lead_time) + (service_level * std_dev_combined)

        

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

                                     forecasted_daily_demand: float = None,

                                     lead_time_std: float = 0.0) -> Dict[str, Any]:

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

        # $Ss = Z \times \sqrt{(P+L)\sigma_d^2 + \mu_d^2\sigma_L^2}$

        variance_protection = (protection_interval * (sigma_d ** 2)) + ((mu_d ** 2) * (lead_time_std ** 2))

        sigma_protection_interval = math.sqrt(max(0, variance_protection))

        

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

        

        # Calculate ROP

        variance_lead_time = (L * (sigma_d ** 2)) + ((mu_d ** 2) * (lead_time_std ** 2))

        sigma_lead_time = math.sqrt(max(0, variance_lead_time))

        rop = (mu_d * L) + (service_level * sigma_lead_time)
        needs_reorder_rop = inventory_position < rop

        # Logic: We only order if current inventory_position is below ROP
        should_order = (order_quantity > 0) and needs_reorder_rop
        final_order_qty = max(0, order_quantity) if should_order else 0



        return {

            "item": item,

            "store": store,

            "review_period_days_P": P,

            "lead_time_days_L": L,

            "protection_interval_days": protection_interval,
            "calculated_rop": round(rop, 2),
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

def estimate_historical_lead_time(df: pd.DataFrame) -> Dict[str, float]:
    """
    Estimate the mean and standard deviation of lead time from historical data.
    Assumes that Arrived_Qty corresponds to a previous Ordered_Qty.
    """
    if "Ordered_Qty" not in df.columns or "Arrived_Qty" not in df.columns or "Date" not in df.columns:
        return {"mean_lead_time": 7.0, "std_lead_time": 0.0}

    # Ensure Date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"])

    lead_times = []
    
    # Process each item-store pair
    for (item, store), group in df.groupby(["Item", "Store"]):
        group = group.sort_values("Date")
        
        # Get dates where orders were placed and arrived
        order_dates = group[group["Ordered_Qty"] > 0]["Date"].tolist()
        arrival_dates = group[group["Arrived_Qty"] > 0]["Date"].tolist()
        
        # Simple matching: n-th arrival matches n-th order
        # We need to find the subset that matches
        # If the first arrival happened before the first recorded order, skip it (it was from before the data starts)
        if not order_dates or not arrival_dates:
            continue
            
        # Strip arrival dates that are before the first order date
        arrival_dates = [d for d in arrival_dates if d > order_dates[0]]
        
        # Match FIFO
        for i in range(min(len(order_dates), len(arrival_dates))):
            diff = (arrival_dates[i] - order_dates[i]).days
            if diff > 0:
                lead_times.append(diff)

    if not lead_times:
        return {"mean_lead_time": 7.0, "std_lead_time": 0.0}

    arr = pd.Series(lead_times)
    return {
        "mean_lead_time": round(float(arr.mean()), 2),
        "std_lead_time": round(float(arr.std()), 2) if len(arr) > 1 else 0.0
    }

def compare_lead_time_scenarios(df: pd.DataFrame, lead_time_days: int = 7, service_level: float = 1.65, user_lead_time_std: float = None) -> Dict[str, Any]:
    """
    Compare Fixed Lead Time (std=0) vs Uncertain Lead Time.
    Returns comparison summary and item-level details.
    """
    # 1. Estimate from data
    historical_stats = estimate_historical_lead_time(df)
    
    # Use user input if provided, otherwise use historical
    comparison_std = user_lead_time_std if user_lead_time_std is not None else historical_stats["std_lead_time"]
    
    # 2. Run Batch Calculations
    # Fixed Scenario
    df_fixed = calculate_batch_periodic_review(df, lead_time_days=lead_time_days, service_level=service_level, lead_time_std=0.0)
    
    # Uncertain Scenario
    df_uncertain = calculate_batch_periodic_review(df, lead_time_days=lead_time_days, service_level=service_level, lead_time_std=comparison_std)
    
    if df_fixed.empty or df_uncertain.empty:
        return {"error": "Insufficient data for comparison"}

    # 3. Aggregate Summary Metrics
    # We need Safety Stock and Target Level which are NOT in the batch summary by default?
    # Let's re-calculate more details for the summary if needed, but let's check calculate_batch_periodic_review return
    
    # Wait, calculate_batch_periodic_review only returns Item, Store, Current Stock, ROP, Target Level, Order Qty, Status.
    # It doesn't return Safety Stock. I should probably update it or re-calculate summary here.
    
    # 4. Item-level comparison
    comparison_details = []
    total_ss_fixed = 0
    total_ss_uncertain = 0
    
    # Join the two dataframes to compare
    merge_df = pd.merge(df_fixed, df_uncertain, on=["Item", "Store"], suffixes=("_fixed", "_uncertain"))
    
    # We need Safety Stock specifically. I'll re-calculate it for each item to be precise.
    # Or I can update calculate_batch_periodic_review. Let's update calculate_batch_periodic_review to include SS.
    
    # For now, let's just use what we have and re-derive SS if needed, 
    # but the user wants "Fixed Safety Stock, Uncertain Safety Stock" in the table.
    # So I MUST update calculate_batch_periodic_review or calculate it here.
    
    return {
        "summary": {
            "fixed_std": 0.0,
            "uncertain_std": comparison_std,
            "historical_std": historical_stats["std_lead_time"],
            "total_items": len(merge_df),
            "recommendation": "Uncertain Lead Time (Stochastic)" if comparison_std > 0 else "Fixed Lead Time (Deterministic)",
            "justification": (
                f"With a lead time variability of {comparison_std} days, the Uncertain model is safer. "
                "It accounts for supply delays, reducing stockout risk at the cost of higher safety stock."
                if comparison_std > 0 else 
                "No lead time variability detected. The Fixed model is optimal as it avoids unnecessary holding costs."
            )
        },
        "item_comparison": merge_df.to_dict(orient="records")
    }



def calculate_batch_periodic_review(df: pd.DataFrame, review_period_days: int = 7, lead_time_days: int = 7, service_level: float = 1.65, lead_time_std: float = 0.0) -> pd.DataFrame:
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
            review_period_days=review_period_days,
            lead_time_days=lead_time_days,
            service_level=service_level,
            lead_time_std=lead_time_std
        )

        

        if "error" not in res:

            results.append({

                "Item": pair["Item"],

                "Store": pair["Store"],

                "Current Stock": res["current_on_hand"],
                "Safety Stock": res["safety_stock_Ss"],
                "ROP": round(res.get("calculated_rop", 0), 2),
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



