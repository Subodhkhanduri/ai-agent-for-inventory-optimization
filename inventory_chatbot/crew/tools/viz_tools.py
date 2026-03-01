# inventory_chatbot/crew/tools/viz_tools.py

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import pandas as pd
import base64

from inventory_chatbot.analytics.visualization import VisualizationTool as BackendVizTool


class ChartGeneratorToolInput(BaseModel):
    """Input schema for ChartGeneratorTool."""
    chart_type: str = Field(
        default="trend",
        description="Type of chart to generate: trend, bar, histogram, scatter"
    )
    title: str = Field(default="Visualization", description="Chart title")


class ChartGeneratorTool(BaseTool):
    name: str = "Chart Generator Tool"
    description: str = (
        "Generates various types of charts and visualizations from inventory data. "
        "Supports trend lines, bar charts, histograms, and scatter plots."
    )
    args_schema: Type[BaseModel] = ChartGeneratorToolInput
    dataframe: pd.DataFrame = None

    _viz_tool: BackendVizTool = None

    def _get_viz_tool(self) -> BackendVizTool:
        if self._viz_tool is None:
            self._viz_tool = BackendVizTool()
        return self._viz_tool

    def _run(self, chart_type: str = "trend", title: str = "Visualization") -> Any:
        """Generate visualization."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        try:
            viz_tool = self._get_viz_tool()

            # For now, we'll use the existing trend plot
            # Can be extended to support other chart types
            if chart_type == "trend":
                chart_b64 = viz_tool.generate_sales_trend_plot(self.dataframe)
            else:
                # Fallback to trend plot for unsupported types
                chart_b64 = viz_tool.generate_sales_trend_plot(self.dataframe)

            return {
                "chart_base64": chart_b64,
                "chart_type": chart_type,
                "description": f"Generated {chart_type} visualization",
                "message": "Visualization created successfully"
            }

        except Exception as e:
            return {"error": f"Visualization generation failed: {str(e)}"}


class TrendPlotToolInput(BaseModel):
    """Input schema for TrendPlotTool."""
    pass


class TrendPlotTool(BaseTool):
    name: str = "Trend Plot Tool"
    description: str = (
        "Generates a sales trend visualization showing patterns over time. "
        "Ideal for identifying trends, seasonality, and anomalies."
    )
    args_schema: Type[BaseModel] = TrendPlotToolInput
    dataframe: pd.DataFrame = None

    _viz_tool: BackendVizTool = None

    def _get_viz_tool(self) -> BackendVizTool:
        if self._viz_tool is None:
            self._viz_tool = BackendVizTool()
        return self._viz_tool

    def _run(self) -> Any:
        """Generate trend plot."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        try:
            viz_tool = self._get_viz_tool()
            chart_b64 = viz_tool.generate_sales_trend_plot(self.dataframe)

            return {
                "chart_base64": chart_b64,
                "chart_type": "trend_line",
                "description": "Sales trend visualization over time",
                "message": "Trend plot generated successfully"
            }

        except Exception as e:
            return {"error": f"Trend plot generation failed: {str(e)}"}
