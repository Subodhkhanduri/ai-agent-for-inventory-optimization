import matplotlib.pyplot as plt
import base64
import io
import pandas as pd


class VisualizationTool:
    """
    Handles all chart creation + Base64 encoding for frontend display.
    """

    def __init__(self):
        pass

    # ----------------------------------------------------------
    # Convert Matplotlib figure → Base64 PNG
    # ----------------------------------------------------------
    def fig_to_base64(self, fig):
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)
        return encoded

    # ----------------------------------------------------------
    # Plot forecasted demand
    # ----------------------------------------------------------
    def plot_forecast(self, df: pd.DataFrame):
        """
        df should contain:
        - 'date'
        - 'forecast'
        """

        fig, ax = plt.subplots(figsize=(8, 4))

        ax.plot(df["date"], df["forecast"], marker="o")
        ax.set_title("Forecasted Demand")
        ax.set_xlabel("Date")
        ax.set_ylabel("Predicted Units")

        fig.tight_layout()

        return self.fig_to_base64(fig)

    # ----------------------------------------------------------
    # Plot historical + forecast together
    # ----------------------------------------------------------
    def plot_history_and_forecast(self, df_history, df_forecast):
        """
        df_history must have date + sales
        df_forecast must have date + forecast
        """

        fig, ax = plt.subplots(figsize=(9, 4))

        # Plot historical sales
        ax.plot(df_history["date"], df_history["sales"], label="Historical", marker=".")

        # Plot forecast
        ax.plot(df_forecast["date"], df_forecast["forecast"], label="Forecast", marker="o")

        ax.set_title("Historical vs Forecasted Demand")
        ax.set_xlabel("Date")
        ax.set_ylabel("Units")

        ax.legend()
        fig.tight_layout()

        return self.fig_to_base64(fig)
    
    def generate_sales_trend_plot(self, df):
        fig, ax = plt.subplots(figsize=(10, 5))

        # Example: item-level daily sales trend
        daily = df.groupby("Date")["Daily_Sales"].sum()

        ax.plot(daily.index, daily.values)
        ax.set_title("Daily Sales Trend")
        ax.set_xlabel("Date")
        ax.set_ylabel("Sales")

        fig.tight_layout()
        return self.fig_to_base64(fig)
