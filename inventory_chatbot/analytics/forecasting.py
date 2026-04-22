import pandas as pd
import numpy as np
from datetime import timedelta
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class ForecastingTool:

    def __init__(self):
        self.lgbm_model = None

        # Load LightGBM model from project root/models directory
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.abspath(
            os.path.join(BASE_DIR, "..", "..", "models", "global_lgbm_model.pkl")
        )

        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.lgbm_model = pickle.load(f)

    # ------------------------------
    # Models (all use "Demand" column)
    # ------------------------------
    def simple_mean(self, df):
        return df["Demand"].mean()

    def moving_avg(self, df, window=7):
        return df["Demand"].tail(window).mean()

    def exp_smoothing(self, df, periods):
        try:
            series = df["Demand"].values.astype(float)
            model = ExponentialSmoothing(series, seasonal=None, trend=None)
            fitted = model.fit(optimized=True)
            return fitted.forecast(periods)
        except Exception as e:
            logger.error(f"Exponential Smoothing failed: {e}")
            return [df["Demand"].mean()] * periods

    def arima_forecast(self, df, periods):
        try:
            series = df["Demand"].values.astype(float)
            model = ARIMA(series, order=(2, 1, 2))
            fitted = model.fit()
            return fitted.forecast(periods)
        except Exception as e:
            logger.error(f"ARIMA forecast failed: {e}")
            return [df["Demand"].mean()] * periods

    def _train_lgbm_on_data(self, df, periods, item, store):
        """Train a fresh LightGBM on the uploaded data and forecast."""
        try:
            import lightgbm as lgb

            df = df.copy()
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date").reset_index(drop=True)

            # Feature engineering on the Demand column
            df["year"]       = df["Date"].dt.year
            df["month"]      = df["Date"].dt.month
            df["dayofweek"]  = df["Date"].dt.dayofweek
            df["dayofyear"]  = df["Date"].dt.dayofyear
            if hasattr(df["Date"].dt, "isocalendar"):
                df["weekofyear"] = df["Date"].dt.isocalendar().week.astype(int)
            else:
                df["weekofyear"] = df["Date"].dt.weekofyear

            df["lag_7"]          = df["Demand"].shift(7)
            df["lag_14"]         = df["Demand"].shift(14)
            df["rolling_mean_7"] = df["Demand"].shift(1).rolling(7).mean()
            df["rolling_mean_30"]= df["Demand"].shift(1).rolling(30).mean()
            df["_item"]  = int(item)
            df["_store"] = int(store)

            train = df.dropna()
            if len(train) < 10:
                return None

            features = ["year","month","weekofyear","dayofweek","dayofyear",
                        "lag_7","lag_14","rolling_mean_7","rolling_mean_30","_item","_store"]

            X_train = train[features]
            y_train = train["Demand"]

            model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1, num_leaves=31, verbose=-1)
            model.fit(X_train, y_train)

            # Iterative forecast
            all_demand = df["Demand"].values.tolist()
            last_date  = df["Date"].max()
            preds = []

            for i in range(periods):
                next_date = last_date + timedelta(days=i+1)
                arr = np.array(all_demand)

                row = {
                    "year":         next_date.year,
                    "month":        next_date.month,
                    "weekofyear":   next_date.isocalendar()[1],
                    "dayofweek":    next_date.weekday(),
                    "dayofyear":    next_date.timetuple().tm_yday,
                    "lag_7":        arr[-7]  if len(arr) >= 7  else arr[-1],
                    "lag_14":       arr[-14] if len(arr) >= 14 else arr[-1],
                    "rolling_mean_7":  np.mean(arr[-7:])  if len(arr) >= 7  else np.mean(arr),
                    "rolling_mean_30": np.mean(arr[-30:]) if len(arr) >= 30 else np.mean(arr),
                    "_item":  int(item),
                    "_store": int(store),
                }
                pred = model.predict(pd.DataFrame([row]))[0]
                pred = max(0, pred)
                preds.append(pred)
                all_demand.append(pred)

            return np.array(preds)

        except Exception as e:
            logger.error(f"In-memory LightGBM training failed: {e}")
            return None


    def lgbm_forecast(self, df, periods, item, store):
        """Use pre-trained global LightGBM model with sanity check."""
        if self.lgbm_model is None:
            return None

        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        last_date = df["Date"].max()
        all_sales = df["Demand"].values

        def get_rolling(arr, window):
            return np.mean(arr[-window:]) if len(arr) >= window else (np.mean(arr) if len(arr) > 0 else 0)

        def get_lag(arr, lag):
            return arr[-lag] if len(arr) >= lag else (arr[-1] if len(arr) > 0 else 0)

        lag_7  = get_lag(all_sales, 7)
        lag_14 = get_lag(all_sales, 14)
        rolling_7   = get_rolling(all_sales, 7)
        rolling_30  = get_rolling(all_sales, 30)
        rolling_365 = get_rolling(all_sales, 365)

        future_dates = pd.date_range(last_date + timedelta(days=1), periods=periods)
        future_df = pd.DataFrame({"Date": future_dates})

        future_df["year"]      = future_df["Date"].dt.year
        future_df["month"]     = future_df["Date"].dt.month
        if hasattr(future_df["Date"].dt, "isocalendar"):
            future_df["weekofyear"] = future_df["Date"].dt.isocalendar().week.astype(int)
        else:
            future_df["weekofyear"] = future_df["Date"].dt.weekofyear
        future_df["dayofweek"] = future_df["Date"].dt.dayofweek
        future_df["dayofyear"] = future_df["Date"].dt.dayofyear

        future_df["sales_lag_7"]            = lag_7
        future_df["sales_lag_14"]           = lag_14
        future_df["sales_rolling_mean_7"]   = rolling_7
        future_df["sales_rolling_mean_30"]  = rolling_30
        future_df["sales_rolling_mean_365"] = rolling_365

        try:
            future_df["store"] = int(store)
            future_df["item"]  = int(item)
        except (ValueError, TypeError):
            future_df["store"] = 0
            future_df["item"]  = 0

        features = [
            'year', 'month', 'weekofyear', 'dayofweek', 'dayofyear',
            'sales_lag_7', 'sales_lag_14', 'sales_rolling_mean_7',
            'sales_rolling_mean_30', 'sales_rolling_mean_365', 'store', 'item'
        ]

        preds = self.lgbm_model.predict(future_df[features])

        # ── Sanity check: reject if predictions are wildly off scale ──
        hist_mean = np.mean(all_sales) if len(all_sales) > 0 else 1
        pred_mean = np.mean(preds)
        ratio = pred_mean / hist_mean if hist_mean != 0 else float('inf')

        if ratio > 10 or ratio < 0.1:
            logger.warning(
                f"Pre-trained LightGBM predictions (mean={pred_mean:.1f}) are out of scale "
                f"vs historical mean ({hist_mean:.1f}, ratio={ratio:.1f}x). Discarding."
            )
            return None  # caller will fall back to statistical model

        return preds

    # ------------------------------
    # Main Forecast Method
    # ------------------------------
    def generate_forecast(self, df, item=None, store=None, periods=10):

        # Filter by Item/Store (title-case column names)
        if store is not None:
            df = df[df["Store"].astype(str) == str(store)]
        if item is not None:
            df = df[df["Item"].astype(str) == str(item)]

        if df.empty:
            raise ValueError("No data for the selected item/store.")

        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        n = len(df)

        # ── Model selection ── (UPDATED: fitted-first, global as fallback)
        forecast = None
        method   = None

        # 1. Train a fresh LightGBM on uploaded data (best accuracy — MASE=0.71)
        if n >= 30:
            forecast = self._train_lgbm_on_data(df, periods, item, store)
            if forecast is not None:
                method = "LightGBM (fitted)"

        # 2. Pre-trained global LightGBM (fallback when insufficient data for fitting)
        if forecast is None and self.lgbm_model and n >= 1:
            forecast = self.lgbm_forecast(df, periods, item, store)
            if forecast is not None:
                method = "LightGBM (global)"

        # 3. ARIMA fallback (requires >=20 rows)
        if forecast is None and n >= 20:
            method   = "ARIMA"
            forecast = self.arima_forecast(df, periods)

        # 4. Simple Exponential Smoothing (no trend — fixes ETS explosion)
        if forecast is None and n >= 7:
            method   = "Exponential Smoothing"
            forecast = self.exp_smoothing(df, periods)

        # 5. Moving average
        if forecast is None and n >= 2:
            method   = "Moving Average (7-day)"
            val      = self.moving_avg(df)
            forecast = [val] * periods

        # Ensure no negatives
        forecast = np.maximum(np.array(forecast, dtype=float), 0)

        # Build result DataFrame
        last_date = df["Date"].max()
        dates = [last_date + timedelta(days=i+1) for i in range(periods)]

        forecast_df = pd.DataFrame({
            "Date": dates,
            "Forecasted_Demand": np.round(forecast, 2)
        })

        # Plot
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df["Date"], df["Demand"], label="Historical Demand", color="steelblue")
        ax.plot(
            forecast_df["Date"],
            forecast_df["Forecasted_Demand"],
            label=f"Forecast ({method})",
            linestyle="--",
            marker="o",
            color="tomato"
        )
        ax.legend()
        ax.set_title(f"Demand Forecast — Item {item}, Store {store} ({method})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Demand")
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        import base64
        chart_b64 = base64.b64encode(buf.read()).decode("utf-8")

        return chart_b64, forecast_df.to_dict(orient="records"), method
