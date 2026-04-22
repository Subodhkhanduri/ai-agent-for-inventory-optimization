"""
Forecast Model Evaluation — MAE / RMSE / MAPE / MASE
=====================================================
This is the authoritative source for all forecasting error metrics
reported in the thesis. Run this script to regenerate the numbers.

Usage:
    # With your real data (must be in project root):
    python benchmarks/run_forecast_evaluation.py

    # Specify paths explicitly:
    python benchmarks/run_forecast_evaluation.py train.csv test.csv

    # Quick smoke-test on synthetic data (no real CSV required):
    python benchmarks/run_forecast_evaluation.py --synthetic

Output:
    docs/forecast_metrics_report.md   — full Markdown report (commit this)
    Console summary                    — key numbers for the thesis table

Evaluation protocol
-------------------
For each item-store pair:
  1. Fit / calibrate each model using the TRAINING split (train_df).
  2. Predict forward for len(test_subset) steps.
  3. Compare predictions against actuals in the TEST split (test_df).
  4. Aggregate MAE, RMSE, MAPE, MASE across all pairs.

MASE denominator: mean absolute error of the naive in-sample
one-step-ahead forecast on the training series (Hyndman & Koehler, 2006).
  MAE_naive = mean(|y_t - y_{t-1}|) for t=2..T_train

Reference: Hyndman, R.J. & Koehler, A.B. (2006). Another look at
measures of forecast accuracy. International Journal of Forecasting,
22(4), 679–688. https://doi.org/10.1016/j.ijforecast.2006.03.001
"""

import sys
import os
import math
import time
import logging
import warnings
import argparse
import pickle
import numpy as np
import pandas as pd
from datetime import timedelta
from itertools import product as iter_product

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Fix Windows WinError 2 (wmic not found) for joblib/loky
if os.name == 'nt' and "LOKY_MAX_CPU_COUNT" not in os.environ:
    os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count())

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "global_lgbm_model.pkl")
REPORT_PATH = os.path.join(PROJECT_ROOT, "docs", "forecast_metrics_report.md")


# ══════════════════════════════════════════════════════════════════════════════
# Data helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_data(train_path: str, test_path: str):
    print(f"Loading training data: {train_path}")
    train_df = pd.read_csv(train_path)
    print(f"  → {len(train_df):,} rows")

    print(f"Loading test data:     {test_path}")
    test_df = pd.read_csv(test_path)
    print(f"  → {len(test_df):,} rows")

    for df in [train_df, test_df]:
        df["Date"] = pd.to_datetime(df["Date"])

    return train_df, test_df


def synthetic_data():
    """
    Reproduce the same synthetic dataset used in run_benchmarks.py
    so the evaluation is comparable to the robustness benchmark.
    Uses a 80/20 chronological split.
    """
    print("Generating synthetic dataset (no real CSVs provided) …")
    np.random.seed(42)
    items = list(range(1, 6))   # 5 items
    stores = list(range(1, 4))  # 3 stores — keeps runtime short
    dates = pd.date_range("2013-01-01", periods=365 * 4, freq="D")  # 4 years

    rows = []
    for date, item, store in iter_product(dates, items, stores):
        base = 15 + item + store
        trend = (date - dates[0]).days * 0.002
        seasonal = 2 * np.sin(2 * np.pi * date.dayofyear / 365)
        noise = np.random.normal(0, 2)
        demand = max(0, base + trend + seasonal + noise)
        rows.append({"Date": date, "Item": item, "Store": store,
                     "Demand": round(demand, 2),
                     "Daily_Sales": int(max(0, demand))})

    df = pd.DataFrame(rows)
    cutoff = df["Date"].quantile(0.8)
    train_df = df[df["Date"] <= cutoff].copy()
    test_df  = df[df["Date"] >  cutoff].copy()
    print(f"  Synthetic: {len(train_df):,} train rows, {len(test_df):,} test rows")
    return train_df, test_df


# ══════════════════════════════════════════════════════════════════════════════
# Error metrics
# ══════════════════════════════════════════════════════════════════════════════

def mae(actual, predicted):
    a, p = np.array(actual), np.array(predicted)
    return float(np.mean(np.abs(a - p)))

def rmse(actual, predicted):
    a, p = np.array(actual), np.array(predicted)
    return float(np.sqrt(np.mean((a - p) ** 2)))

def mape(actual, predicted, eps=1e-8):
    a, p = np.array(actual, dtype=float), np.array(predicted, dtype=float)
    # Exclude zero-demand periods from MAPE (undefined when actual=0)
    mask = np.abs(a) > eps
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)

def naive_mae(train_series):
    """
    MAE of the naive in-sample one-step forecast: ŷ_t = y_{t-1}.
    This is the MASE denominator (Hyndman & Koehler 2006).
    Returns NaN for series with fewer than 2 observations.
    """
    s = np.array(train_series, dtype=float)
    if len(s) < 2:
        return float("nan")
    return float(np.mean(np.abs(np.diff(s))))

def mase(actual, predicted, train_series):
    """
    MASE = MAE(forecast) / MAE(naive, in-sample training).
    Values < 1 mean the model beats the naive benchmark.
    """
    denom = naive_mae(train_series)
    if denom == 0 or math.isnan(denom):
        return float("nan")
    return mae(actual, predicted) / denom


# ══════════════════════════════════════════════════════════════════════════════
# Model wrappers — each takes (train_series, n_periods) → np.array
# ══════════════════════════════════════════════════════════════════════════════

def model_ma7(train_series, n_periods):
    val = np.mean(train_series[-7:]) if len(train_series) >= 7 else np.mean(train_series)
    return np.full(n_periods, max(0, val))


def model_ets(train_series, n_periods):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    try:
        series = np.array(train_series, dtype=float)
        model = ExponentialSmoothing(series, seasonal=None, trend="add")
        fitted = model.fit(optimized=True)
        preds = fitted.forecast(n_periods)
        return np.maximum(preds, 0)
    except Exception:
        return np.full(n_periods, max(0, np.mean(train_series)))


def model_arima(train_series, n_periods):
    from statsmodels.tsa.arima.model import ARIMA
    try:
        series = np.array(train_series, dtype=float)
        fitted = ARIMA(series, order=(2, 1, 2)).fit()
        preds = fitted.forecast(n_periods)
        return np.maximum(preds, 0)
    except Exception:
        return np.full(n_periods, max(0, np.mean(train_series)))


def model_lgbm_fitted(train_df_subset, n_periods, item, store):
    """
    Train a fresh LightGBM on the training subset and forecast forward.
    Uses the same feature engineering as the production code.
    """
    try:
        import lightgbm as lgb
        df = train_df_subset.copy()
        df = df.sort_values("Date").reset_index(drop=True)

        df["year"]        = df["Date"].dt.year
        df["month"]       = df["Date"].dt.month
        df["dayofweek"]   = df["Date"].dt.dayofweek
        df["dayofyear"]   = df["Date"].dt.dayofyear
        df["weekofyear"]  = df["Date"].dt.isocalendar().week.astype(int)
        df["lag_7"]       = df["Demand"].shift(7)
        df["lag_14"]      = df["Demand"].shift(14)
        df["rolling_mean_7"]  = df["Demand"].shift(1).rolling(7).mean()
        df["rolling_mean_30"] = df["Demand"].shift(1).rolling(30).mean()
        df["_item"]  = int(item)
        df["_store"] = int(store)

        train_clean = df.dropna()
        if len(train_clean) < 10:
            return None

        features = ["year","month","weekofyear","dayofweek","dayofyear",
                    "lag_7","lag_14","rolling_mean_7","rolling_mean_30","_item","_store"]
        model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.1,
                                  num_leaves=31, verbose=-1)
        model.fit(train_clean[features], train_clean["Demand"])

        all_demand = df["Demand"].values.tolist()
        last_date  = df["Date"].max()
        preds = []
        for i in range(n_periods):
            nd = last_date + timedelta(days=i + 1)
            arr = np.array(all_demand)
            row = {
                "year": nd.year, "month": nd.month,
                "weekofyear": nd.isocalendar()[1], "dayofweek": nd.weekday(),
                "dayofyear": nd.timetuple().tm_yday,
                "lag_7":  arr[-7]  if len(arr) >= 7  else arr[-1],
                "lag_14": arr[-14] if len(arr) >= 14 else arr[-1],
                "rolling_mean_7":  np.mean(arr[-7:])  if len(arr) >= 7  else np.mean(arr),
                "rolling_mean_30": np.mean(arr[-30:]) if len(arr) >= 30 else np.mean(arr),
                "_item": int(item), "_store": int(store),
            }
            pred = float(model.predict(pd.DataFrame([row]))[0])
            pred = max(0, pred)
            preds.append(pred)
            all_demand.append(pred)
        return np.array(preds)
    except Exception as e:
        logger.debug(f"LightGBM-fitted failed for item={item} store={store}: {e}")
        return None


def model_lgbm_global(lgbm_model, train_df_subset, n_periods, item, store):
    """
    Use the pre-trained global LightGBM model.
    Feature schema: year, month, weekofyear, dayofweek, dayofyear,
                    sales_lag_7, sales_lag_14, sales_rolling_mean_7,
                    sales_rolling_mean_30, sales_rolling_mean_365, store, item
    """
    if lgbm_model is None:
        return None
    try:
        df = train_df_subset.sort_values("Date")
        all_sales = df["Demand"].values
        last_date = df["Date"].max()

        def get_rolling(arr, w):
            return np.mean(arr[-w:]) if len(arr) >= w else (np.mean(arr) if len(arr) > 0 else 0)
        def get_lag(arr, lag):
            return arr[-lag] if len(arr) >= lag else (arr[-1] if len(arr) > 0 else 0)

        lag_7  = get_lag(all_sales, 7)
        lag_14 = get_lag(all_sales, 14)
        r7   = get_rolling(all_sales, 7)
        r30  = get_rolling(all_sales, 30)
        r365 = get_rolling(all_sales, 365)

        future_dates = pd.date_range(last_date + timedelta(days=1), periods=n_periods)
        fdf = pd.DataFrame({"Date": future_dates})
        fdf["year"]      = fdf["Date"].dt.year
        fdf["month"]     = fdf["Date"].dt.month
        fdf["weekofyear"]= fdf["Date"].dt.isocalendar().week.astype(int)
        fdf["dayofweek"] = fdf["Date"].dt.dayofweek
        fdf["dayofyear"] = fdf["Date"].dt.dayofyear
        fdf["sales_lag_7"]           = lag_7
        fdf["sales_lag_14"]          = lag_14
        fdf["sales_rolling_mean_7"]  = r7
        fdf["sales_rolling_mean_30"] = r30
        fdf["sales_rolling_mean_365"]= r365
        fdf["store"] = int(store)
        fdf["item"]  = int(item)

        features = ['year','month','weekofyear','dayofweek','dayofyear',
                    'sales_lag_7','sales_lag_14','sales_rolling_mean_7',
                    'sales_rolling_mean_30','sales_rolling_mean_365','store','item']
        preds = lgbm_model.predict(fdf[features])

        # Sanity check (same as production code)
        hist_mean = float(np.mean(all_sales)) if len(all_sales) > 0 else 1.0
        pred_mean = float(np.mean(preds))
        ratio = pred_mean / hist_mean if hist_mean != 0 else float("inf")
        if ratio > 10 or ratio < 0.1:
            return None

        return np.maximum(preds, 0)
    except Exception as e:
        logger.debug(f"LightGBM-global failed for item={item} store={store}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Per-pair evaluation
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_pair(train_df, test_df, item, store, lgbm_model):
    train_sub = (train_df[(train_df["Item"] == item) & (train_df["Store"] == store)]
                 .sort_values("Date").copy())
    test_sub  = (test_df[(test_df["Item"] == item) & (test_df["Store"] == store)]
                 .sort_values("Date").copy())

    if len(train_sub) < 7 or len(test_sub) < 1:
        return None

    actual       = test_sub["Demand"].values.astype(float)
    train_series = train_sub["Demand"].values.astype(float)
    n            = len(actual)
    naive_denom  = naive_mae(train_series)

    result = {"item": item, "store": store, "n_train": len(train_sub), "n_test": n}

    # ── 1. Moving Average ────────────────────────────────────────────────────
    preds_ma = model_ma7(train_series, n)
    result["MA7"] = {
        "MAE":  mae(actual, preds_ma),
        "RMSE": rmse(actual, preds_ma),
        "MAPE": mape(actual, preds_ma),
        "MASE": mae(actual, preds_ma) / naive_denom if naive_denom > 0 else float("nan"),
    }

    # ── 2. ETS ───────────────────────────────────────────────────────────────
    preds_ets = model_ets(train_series, n)
    result["ETS"] = {
        "MAE":  mae(actual, preds_ets),
        "RMSE": rmse(actual, preds_ets),
        "MAPE": mape(actual, preds_ets),
        "MASE": mae(actual, preds_ets) / naive_denom if naive_denom > 0 else float("nan"),
    }

    # ── 3. ARIMA ─────────────────────────────────────────────────────────────
    if len(train_series) >= 20:
        preds_arima = model_arima(train_series, n)
        result["ARIMA"] = {
            "MAE":  mae(actual, preds_arima),
            "RMSE": rmse(actual, preds_arima),
            "MAPE": mape(actual, preds_arima),
            "MASE": mae(actual, preds_arima) / naive_denom if naive_denom > 0 else float("nan"),
        }

    # ── 4. LightGBM (fitted) ─────────────────────────────────────────────────
    if len(train_series) >= 30:
        preds_lgbm_fit = model_lgbm_fitted(train_sub, n, item, store)
        if preds_lgbm_fit is not None:
            result["LightGBM_fitted"] = {
                "MAE":  mae(actual, preds_lgbm_fit),
                "RMSE": rmse(actual, preds_lgbm_fit),
                "MAPE": mape(actual, preds_lgbm_fit),
                "MASE": mae(actual, preds_lgbm_fit) / naive_denom if naive_denom > 0 else float("nan"),
            }

    # ── 5. LightGBM (global pre-trained) ─────────────────────────────────────
    if lgbm_model is not None:
        preds_lgbm_g = model_lgbm_global(lgbm_model, train_sub, n, item, store)
        if preds_lgbm_g is not None:
            result["LightGBM_global"] = {
                "MAE":  mae(actual, preds_lgbm_g),
                "RMSE": rmse(actual, preds_lgbm_g),
                "MAPE": mape(actual, preds_lgbm_g),
                "MASE": mae(actual, preds_lgbm_g) / naive_denom if naive_denom > 0 else float("nan"),
            }

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Aggregation
# ══════════════════════════════════════════════════════════════════════════════

def aggregate_results(pair_results):
    model_names = ["MA7", "ETS", "ARIMA", "LightGBM_fitted", "LightGBM_global"]
    agg = {}
    for model in model_names:
        rows = [r[model] for r in pair_results if model in r]
        if not rows:
            continue
        for metric in ["MAE", "RMSE", "MAPE", "MASE"]:
            vals = [r[metric] for r in rows if not math.isnan(r[metric])]
            if not vals:
                continue
            n = len(vals)
            mean = np.mean(vals)
            std  = np.std(vals, ddof=1) if n > 1 else 0.0
            se   = std / math.sqrt(n)
            agg.setdefault(model, {})[metric] = {
                "mean":     round(float(mean), 4),
                "std":      round(float(std), 4),
                "n":        n,
                "ci_lower": round(float(mean - 1.96 * se), 4),
                "ci_upper": round(float(mean + 1.96 * se), 4),
            }
    return agg


# ══════════════════════════════════════════════════════════════════════════════
# Report generator
# ══════════════════════════════════════════════════════════════════════════════

MODEL_LABELS = {
    "LightGBM_global": "LightGBM (global, pre-trained)",
    "LightGBM_fitted": "LightGBM (fitted on training data)",
    "ARIMA":           "ARIMA(2,1,2)",
    "ETS":             "Exponential Smoothing (trend)",
    "MA7":             "Moving Average (7-day)",
}
METRIC_ORDER = ["MAE", "RMSE", "MAPE", "MASE"]


def generate_report(agg, n_pairs, n_train_rows, n_test_rows,
                    train_path, test_path, elapsed_s) -> str:
    lines = []
    lines.append("# Forecast Model Evaluation Report\n")
    lines.append("> **Authoritative source** for all forecasting error metrics in the thesis.")
    lines.append("> Do not edit manually — regenerate by running `python benchmarks/run_forecast_evaluation.py`\n")
    lines.append("## Evaluation Setup\n")
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    lines.append(f"| Training data | `{os.path.basename(train_path)}` |")
    lines.append(f"| Test data | `{os.path.basename(test_path)}` |")
    lines.append(f"| Training rows | {n_train_rows:,} |")
    lines.append(f"| Test rows | {n_test_rows:,} |")
    lines.append(f"| Item-store pairs evaluated | {n_pairs} |")
    lines.append(f"| Evaluation time | {elapsed_s:.1f} s |")
    lines.append(f"| MASE reference | Hyndman & Koehler (2006) naive in-sample forecast |")
    lines.append("")

    # ── Main comparison table ────────────────────────────────────────────────
    lines.append("## Model Comparison — Mean Across All Item-Store Pairs\n")
    lines.append("MASE < 1 means the model outperforms the naive (random-walk) benchmark.")
    lines.append("")

    header = "| Model | MAE | RMSE | MAPE (%) | MASE | n pairs |"
    lines.append(header)
    lines.append("|---|---|---|---|---|---|")

    for model in ["LightGBM_global", "LightGBM_fitted", "ARIMA", "ETS", "MA7"]:
        if model not in agg:
            continue
        m = agg[model]
        label = MODEL_LABELS.get(model, model)
        mae_v   = f"{m['MAE']['mean']:.2f}"   if "MAE"  in m else "—"
        rmse_v  = f"{m['RMSE']['mean']:.2f}"  if "RMSE" in m else "—"
        mape_v  = f"{m['MAPE']['mean']:.2f}"  if "MAPE" in m else "—"
        mase_v  = f"{m['MASE']['mean']:.3f}"  if "MASE" in m else "—"
        n_v     = m.get("MAE", m.get("RMSE", {})).get("n", "—")
        # Mark best in each column
        best = "**" if model == _best_model(agg, "MAE") else ""
        lines.append(f"| {best}{label}{best} | {mae_v} | {rmse_v} | {mape_v} | {mase_v} | {n_v} |")

    lines.append("")

    # ── 95% CI tables ────────────────────────────────────────────────────────
    lines.append("## 95% Confidence Intervals (across item-store pairs)\n")
    lines.append("$$CI = \\bar{x} \\pm 1.96 \\cdot \\frac{s}{\\sqrt{n}}$$\n")

    for metric in METRIC_ORDER:
        unit = " (%)" if metric == "MAPE" else ""
        lines.append(f"### {metric}{unit}\n")
        lines.append("| Model | Mean | Std | 95% CI Lower | 95% CI Upper | n |")
        lines.append("|---|---|---|---|---|---|")
        for model in ["LightGBM_global", "LightGBM_fitted", "ARIMA", "ETS", "MA7"]:
            if model not in agg or metric not in agg[model]:
                continue
            s = agg[model][metric]
            label = MODEL_LABELS.get(model, model)
            lines.append(
                f"| {label} | {s['mean']:.4f} | {s['std']:.4f} | "
                f"{s['ci_lower']:.4f} | {s['ci_upper']:.4f} | {s['n']} |"
            )
        lines.append("")

    # ── Methodology note ─────────────────────────────────────────────────────
    lines.append("## Methodology Notes\n")
    lines.append("**Train/test split**: 80/20 chronological date split. "
                 "All models are calibrated exclusively on training data; "
                 "no test-set information leaks into parameter estimation.\n")
    lines.append("**MASE denominator**: Mean absolute error of the naïve "
                 "one-step in-sample forecast (random walk: $\\hat{y}_t = y_{t-1}$) "
                 "computed on the training series for each item-store pair. "
                 "Pairs with zero denominator (constant demand) are excluded from MASE aggregation.\n")
    lines.append("**MAPE exclusion**: Periods with zero actual demand are excluded "
                 "from MAPE calculation (division by zero is undefined).\n")
    lines.append("**LightGBM (global)**: Pre-trained model in `models/global_lgbm_model.pkl`. "
                 "Only evaluated for pairs where the sanity check passes "
                 "(predicted mean within 0.1×–10× of historical mean).\n")
    lines.append("**LightGBM (fitted)**: Fresh model trained per evaluation run on the training subset. "
                 "Requires ≥ 30 training observations.\n")
    lines.append("**ARIMA(2,1,2)**: Requires ≥ 20 training observations. "
                 "Auto-recovers to historical mean fallback on fit failure.\n")
    lines.append("**Reference**: Hyndman, R.J. & Koehler, A.B. (2006). "
                 "Another look at measures of forecast accuracy. "
                 "*International Journal of Forecasting*, 22(4), 679–688.")

    return "\n".join(lines) + "\n"


def _best_model(agg, metric):
    """Return the model name with the lowest mean for the given metric."""
    best_model, best_val = None, float("inf")
    for model, metrics in agg.items():
        if metric in metrics:
            val = metrics[metric]["mean"]
            if val < best_val:
                best_val = val
                best_model = model
    return best_model


# ══════════════════════════════════════════════════════════════════════════════
# Console summary
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(agg, n_pairs):
    print(f"\n{'='*65}")
    print(f"  FORECAST MODEL EVALUATION — {n_pairs} item-store pairs")
    print(f"{'='*65}")
    header = f"  {'Model':<35} {'MAE':>6}  {'RMSE':>6}  {'MAPE%':>6}  {'MASE':>6}"
    print(header)
    print(f"  {'-'*60}")
    for model in ["LightGBM_global","LightGBM_fitted","ARIMA","ETS","MA7"]:
        if model not in agg:
            continue
        m = agg[model]
        label = MODEL_LABELS.get(model, model)[:34]
        mae_v  = f"{m['MAE']['mean']:.2f}"  if "MAE"  in m else "  —  "
        rmse_v = f"{m['RMSE']['mean']:.2f}" if "RMSE" in m else "  —  "
        mape_v = f"{m['MAPE']['mean']:.2f}" if "MAPE" in m else "  —  "
        mase_v = f"{m['MASE']['mean']:.3f}" if "MASE" in m else "  —  "
        print(f"  {label:<35} {mae_v:>6}  {rmse_v:>6}  {mape_v:>6}  {mase_v:>6}")
    print(f"{'='*65}")
    best_mae  = _best_model(agg, "MAE")
    best_mase = _best_model(agg, "MASE")
    if best_mae:
        print(f"\n  Best MAE:  {MODEL_LABELS.get(best_mae,best_mae)}")
    if best_mase:
        print(f"  Best MASE: {MODEL_LABELS.get(best_mase,best_mase)}")
    print(f"\n  → Full report: docs/forecast_metrics_report.md\n")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Forecast model evaluation with MAE/RMSE/MAPE/MASE")
    parser.add_argument("train", nargs="?", default=os.path.join("data", "train_80_date_split.csv"))
    parser.add_argument("test",  nargs="?", default=os.path.join("data", "test_20_date_split.csv"))
    parser.add_argument("--synthetic", action="store_true",
                        help="Use synthetic data instead of real CSVs")
    parser.add_argument("--max-pairs", type=int, default=None,
                        help="Evaluate only the first N pairs (quick test)")
    args = parser.parse_args()

    # ── Load data ─────────────────────────────────────────────────────────────
    if args.synthetic:
        train_df, test_df = synthetic_data()
        train_path = "synthetic"
        test_path  = "synthetic"
    else:
        train_path = os.path.join(PROJECT_ROOT, args.train)
        test_path  = os.path.join(PROJECT_ROOT, args.test)
        if not os.path.exists(train_path) or not os.path.exists(test_path):
            print(f"\n⚠  Could not find CSVs at:")
            print(f"     {train_path}")
            print(f"     {test_path}")
            print(f"   Run with --synthetic to use generated data, or supply paths as arguments.")
            sys.exit(1)
        train_df, test_df = load_data(train_path, test_path)

    # ── Load pre-trained LightGBM ─────────────────────────────────────────────
    lgbm_model = None
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                lgbm_model = pickle.load(f)
            print(f"Loaded pre-trained LightGBM from {MODEL_PATH}")
        except Exception as e:
            print(f"⚠  Could not load LightGBM model: {e}")
    else:
        print(f"⚠  Pre-trained model not found at {MODEL_PATH} — skipping LightGBM-global")

    # ── Get item-store pairs ──────────────────────────────────────────────────
    train_pairs = set(zip(train_df["Item"], train_df["Store"]))
    test_pairs  = set(zip(test_df["Item"],  test_df["Store"]))
    pairs = sorted(train_pairs & test_pairs)

    if args.max_pairs:
        pairs = pairs[:args.max_pairs]

    print(f"\nEvaluating {len(pairs)} item-store pairs …\n")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    start = time.time()
    pair_results = []
    failed = 0

    for i, (item, store) in enumerate(pairs):
        try:
            result = evaluate_pair(train_df, test_df, item, store, lgbm_model)
            if result:
                pair_results.append(result)
        except Exception as e:
            logger.warning(f"Pair ({item},{store}) failed: {e}")
            failed += 1

        if (i + 1) % 50 == 0 or (i + 1) == len(pairs):
            print(f"  {i+1}/{len(pairs)} pairs … ({failed} failed)")

    elapsed = time.time() - start

    if not pair_results:
        print("❌  No pairs evaluated successfully. Check your data.")
        sys.exit(1)

    # ── Aggregate ─────────────────────────────────────────────────────────────
    agg = aggregate_results(pair_results)

    # ── Console output ────────────────────────────────────────────────────────
    print_summary(agg, len(pair_results))

    # ── Write report ──────────────────────────────────────────────────────────
    report = generate_report(
        agg, n_pairs=len(pair_results),
        n_train_rows=len(train_df), n_test_rows=len(test_df),
        train_path=train_path, test_path=test_path,
        elapsed_s=elapsed,
    )

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅  Report saved to: {REPORT_PATH}")

    if failed:
        print(f"⚠   {failed} pairs could not be evaluated (see logs with --debug).")


if __name__ == "__main__":
    main()