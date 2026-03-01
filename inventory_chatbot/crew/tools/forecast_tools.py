# inventory_chatbot/crew/tools/forecast_tools.py

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import pandas as pd
import base64

from inventory_chatbot.analytics.forecasting import ForecastingTool as BackendForecastTool


class ForecastToolInput(BaseModel):
    """Input schema for ForecastTool."""
    item: int = Field(..., description="Item number to forecast")
    store: int = Field(..., description="Store ID to forecast")
    periods: int = Field(default=10, description="Number of periods to forecast (default: 10)")


class ForecastTool(BaseTool):
    name: str = "Forecast Tool"
    description: str = (
        "Generates demand forecasts for specific item-store combinations using "
        "advanced time-series models (ARIMA, Prophet, LightGBM). Returns forecast values, "
        "visualizations, and model metadata."
    )
    args_schema: Type[BaseModel] = ForecastToolInput
    dataframe: pd.DataFrame = None
    user_role: str = "viewer"

    _backend_tool: BackendForecastTool = None

    def _get_backend(self) -> BackendForecastTool:
        if self._backend_tool is None:
            self._backend_tool = BackendForecastTool()
        return self._backend_tool

    def _run(self, item: int, store: int, periods: int = 10) -> Any:
        """Generate forecast."""
        
        # RBAC enforcement
        if self.user_role not in ["manager", "admin"]:
            return {
                "error": "Access denied. Forecasting requires manager or admin role.",
                "status": "forbidden"
            }

        if self.dataframe is None:
            return {"error": "No dataset available"}

        try:
            forecast_tool = self._get_backend()
            
            chart_b64, forecast_values, model_used = forecast_tool.generate_forecast(
                self.dataframe,
                item=item,
                store=store,
                periods=periods
            )

            return {
                "model_used": model_used,
                "forecast_values": forecast_values,
                "chart_base64": chart_b64,
                "message": f"Forecast generated using {model_used} model for {periods} periods"
            }

        except Exception as e:
            return {"error": f"Forecasting failed: {str(e)}"}
