# inventory_chatbot/crew/tools/inventory_tools.py

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import pandas as pd
from inventory_chatbot.analytics.inventory_calculator import calculate_rop_status, calculate_periodic_review_status

class InventoryStatusInput(BaseModel):
    """Input schema for InventoryStatusTool."""
    item: int = Field(..., description="Item number to check")
    store: int = Field(..., description="Store ID to check")
    review_period: int = Field(default=7, description="Review Period (P) in days")
    order_process_time: int = Field(default=1, description="Order Processing Time in days")
    transit_time: int = Field(default=6, description="Transit Time in days")
    lead_time_std: float = Field(default=0.0, description="Standard Deviation of Lead Time in days")
    stock_on_order: float = Field(default=0.0, description="Stock currently on order")
    forecasted_daily_demand: float = Field(default=None, description="Optional: Manually provide daily demand forecast")

class InventoryStatusTool(BaseTool):
    name: str = "Inventory Status Tool"
    description: str = (
        "Calculates the Order Quantity (Q) using a Periodic Review System (P, T). "
        "Returns the Target Level (T), Safety Stock (Ss), and recommended Order Quantity (Q)."
    )
    args_schema: Type[BaseModel] = InventoryStatusInput
    dataframe: pd.DataFrame = None

    def _run(self, item: int, store: int, 
             review_period: int = 7,
             order_process_time: int = 1,
             transit_time: int = 6,
             lead_time_std: float = 0.0,
             stock_on_order: float = 0.0,
             forecasted_daily_demand: float = None) -> Any:
        """Calculate inventory status."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        # Calculate Lead Time (L)
        lead_time_days = order_process_time + transit_time

        result = calculate_periodic_review_status(
            df=self.dataframe,
            item=item,
            store=store,
            review_period_days=review_period,
            lead_time_days=lead_time_days,
            stock_on_order=stock_on_order,
            forecasted_daily_demand=forecasted_daily_demand,
            lead_time_std=lead_time_std
        )
        
        if "error" in result:
            return result
            
        # Format the output for the LLM
        # Using new keys from calculator
        qty_q = result['calculated_order_quantity_Q']
        
        if result["should_order"]:
            status_msg = f"ORDER REQUIRED (Qty: {qty_q})"
            rec_msg = f"Place order for {qty_q} units immediately."
        else:
            status_msg = "STOCK HEALTHY"
            rec_msg = "No order needed at this time."
        
        return {
            "summary": f"Status for Item {item} at Store {store}: {status_msg}",
            "details": {
                "Current On-Hand": result["current_on_hand"],
                "Inventory Position (Ip)": result["inventory_position_Ip"],
                "Target Level (T)": result["target_level_T"],
                "Safety Stock (Ss)": result["safety_stock_Ss"],
                "Order Quantity (Q)": qty_q,
                "Status": status_msg,
                "Recommendation": rec_msg
            },
            "raw_data": result
        }
