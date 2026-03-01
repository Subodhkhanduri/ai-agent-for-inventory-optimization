# inventory_chatbot/crew/tools/data_tools.py

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import pandas as pd


class DataQueryToolInput(BaseModel):
    """Input schema for DataQueryTool."""
    intent: str = Field(..., description="Query intent: COUNT_ROWS, TOTAL_SALES, STOCK_ALERTS, FILTER, etc.")
    column: str = Field(default=None, description="Column name to query (optional)")
    filter_condition: dict = Field(default=None, description="Filter conditions as dict (optional)")


class DataQueryTool(BaseTool):
    name: str = "Data Query Tool"
    description: str = (
        "Executes structured queries on the inventory dataset. "
        "Supports: COUNT_ROWS (count total rows), TOTAL_SALES (sum Daily_Sales), "
        "STOCK_ALERTS (count alert records), and custom filters."
    )
    args_schema: Type[BaseModel] = DataQueryToolInput
    dataframe: pd.DataFrame = None

    def _run(self, intent: str, column: str = None, filter_condition: dict = None) -> Any:
        """Execute the data query."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        df = self.dataframe

        try:
            if intent == "COUNT_ROWS":
                return {"count": len(df), "message": f"Dataset contains {len(df)} rows"}

            elif intent == "TOTAL_SALES":
                if "Daily_Sales" not in df.columns:
                    return {"error": "Daily_Sales column not found"}
                total = float(df["Daily_Sales"].sum())
                return {"total_sales": total, "message": f"Total Daily_Sales: {total:.2f} units"}

            elif intent == "STOCK_ALERTS":
                if "Alert_Status" not in df.columns:
                    return {"error": "Alert_Status column not found"}
                alerts = df[df["Alert_Status"] == 1].shape[0]
                return {"alert_count": alerts, "message": f"Found {alerts} stock alert records"}

            elif intent == "FILTER" and filter_condition:
                # Apply filters
                filtered_df = df.copy()
                for col, value in filter_condition.items():
                    if col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[col] == value]
                
                return {
                    "matching_rows": len(filtered_df),
                    "sample": filtered_df.head(5).to_dict(orient="records")
                }

            elif intent == "COLUMN_SUM" and column:
                if column not in df.columns:
                    return {"error": f"Column {column} not found"}
                total = float(df[column].sum())
                return {"column": column, "sum": total}

            else:
                return {"error": f"Unsupported intent: {intent}"}

        except Exception as e:
            return {"error": f"Query execution failed: {str(e)}"}


class StatisticsToolInput(BaseModel):
    """Input schema for StatisticsTool."""
    column: str = Field(..., description="Column name to calculate statistics for")
    stat_type: str = Field(..., description="Statistic type: mean, median, std, min, max, describe")


class StatisticsTool(BaseTool):
    name: str = "Statistics Tool"
    description: str = (
        "Calculates statistical measures (mean, median, std, min, max) for specified columns "
        "in the inventory dataset."
    )
    args_schema: Type[BaseModel] = StatisticsToolInput
    dataframe: pd.DataFrame = None

    def _run(self, column: str, stat_type: str) -> Any:
        """Calculate statistics."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        df = self.dataframe

        if column not in df.columns:
            return {"error": f"Column '{column}' not found in dataset"}

        try:
            col_data = df[column]

            if stat_type == "mean":
                result = float(col_data.mean())
                return {"column": column, "mean": result}
            elif stat_type == "median":
                result = float(col_data.median())
                return {"column": column, "median": result}
            elif stat_type == "std":
                result = float(col_data.std())
                return {"column": column, "std": result}
            elif stat_type == "min":
                result = float(col_data.min())
                return {"column": column, "min": result}
            elif stat_type == "max":
                result = float(col_data.max())
                return {"column": column, "max": result}
            elif stat_type == "describe":
                stats = col_data.describe().to_dict()
                return {"column": column, "statistics": stats}
            else:
                return {"error": f"Unsupported stat_type: {stat_type}"}

        except Exception as e:
            return {"error": f"Statistics calculation failed: {str(e)}"}


class ColumnInfoToolInput(BaseModel):
    """Input schema for ColumnInfoTool."""
    pass


class ColumnInfoTool(BaseTool):
    name: str = "Column Info Tool"
    description: str = (
        "Retrieves metadata about the dataset columns including column names, "
        "data types, and sample values."
    )
    args_schema: Type[BaseModel] = ColumnInfoToolInput
    dataframe: pd.DataFrame = None

    def _run(self) -> Any:
        """Get column information."""
        if self.dataframe is None:
            return {"error": "No dataset available"}

        df = self.dataframe

        try:
            info = {
                "columns": list(df.columns),
                "row_count": len(df),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_row": df.head(1).to_dict(orient="records")[0] if len(df) > 0 else {}
            }
            return info

        except Exception as e:
            return {"error": f"Failed to retrieve column info: {str(e)}"}
