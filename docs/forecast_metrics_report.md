# Forecast Model Evaluation Report

> **Authoritative source** for all forecasting error metrics in the thesis.
> Do not edit manually — regenerate by running `python benchmarks/run_forecast_evaluation.py`

## Evaluation Setup

| Parameter | Value |
|---|---|
| Training data | `train_80_date_split.csv` |
| Test data | `test_20_date_split.csv` |
| Training rows | 730,500 |
| Test rows | 182,500 |
| Item-store pairs evaluated | 500 |
| Evaluation time | 1638.1 s |
| MASE reference | Hyndman & Koehler (2006) naive in-sample forecast |

## Model Comparison — Mean Across All Item-Store Pairs

MASE < 1 means the model outperforms the naive (random-walk) benchmark.

| Model | MAE | RMSE | MAPE (%) | MASE | n pairs |
|---|---|---|---|---|---|
| LightGBM (global, pre-trained) | 17.67 | 21.09 | 28.04 | 1.673 | 500 |
| **LightGBM (fitted on training data)** | 7.10 | 9.00 | 13.70 | 0.709 | 500 |
| ARIMA(2,1,2) | 17.43 | 21.43 | 27.56 | 1.649 | 500 |
| Exponential Smoothing (trend) | 44.17 | 49.15 | 67.08 | 3.981 | 500 |
| Moving Average (7-day) | 18.39 | 22.41 | 28.96 | 1.740 | 500 |

## 95% Confidence Intervals (across item-store pairs)

$$CI = \bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$$

### MAE

| Model | Mean | Std | 95% CI Lower | 95% CI Upper | n |
|---|---|---|---|---|---|
| LightGBM (global, pre-trained) | 17.6670 | 7.9111 | 16.9736 | 18.3605 | 500 |
| LightGBM (fitted on training data) | 7.0954 | 2.0722 | 6.9138 | 7.2770 | 500 |
| ARIMA(2,1,2) | 17.4330 | 7.7912 | 16.7501 | 18.1159 | 500 |
| Exponential Smoothing (trend) | 44.1667 | 27.2678 | 41.7765 | 46.5568 | 500 |
| Moving Average (7-day) | 18.3887 | 8.2729 | 17.6636 | 19.1139 | 500 |

### RMSE

| Model | Mean | Std | 95% CI Lower | 95% CI Upper | n |
|---|---|---|---|---|---|
| LightGBM (global, pre-trained) | 21.0877 | 9.1856 | 20.2826 | 21.8929 | 500 |
| LightGBM (fitted on training data) | 8.9978 | 2.6270 | 8.7676 | 9.2281 | 500 |
| ARIMA(2,1,2) | 21.4264 | 9.3837 | 20.6039 | 22.2489 | 500 |
| Exponential Smoothing (trend) | 49.1506 | 29.5298 | 46.5622 | 51.7390 | 500 |
| Moving Average (7-day) | 22.4114 | 9.8639 | 21.5468 | 23.2760 | 500 |

### MAPE (%)

| Model | Mean | Std | 95% CI Lower | 95% CI Upper | n |
|---|---|---|---|---|---|
| LightGBM (global, pre-trained) | 28.0414 | 3.0929 | 27.7703 | 28.3125 | 500 |
| LightGBM (fitted on training data) | 13.7007 | 3.5112 | 13.3929 | 14.0085 | 500 |
| ARIMA(2,1,2) | 27.5591 | 1.9670 | 27.3867 | 27.7315 | 500 |
| Exponential Smoothing (trend) | 67.0838 | 22.8537 | 65.0806 | 69.0870 | 500 |
| Moving Average (7-day) | 28.9555 | 2.8496 | 28.7058 | 29.2053 | 500 |

### MASE

| Model | Mean | Std | 95% CI Lower | 95% CI Upper | n |
|---|---|---|---|---|---|
| LightGBM (global, pre-trained) | 1.6733 | 0.2821 | 1.6486 | 1.6980 | 500 |
| LightGBM (fitted on training data) | 0.7089 | 0.0494 | 0.7046 | 0.7133 | 500 |
| ARIMA(2,1,2) | 1.6485 | 0.2462 | 1.6269 | 1.6701 | 500 |
| Exponential Smoothing (trend) | 3.9807 | 1.5986 | 3.8406 | 4.1208 | 500 |
| Moving Average (7-day) | 1.7397 | 0.2871 | 1.7146 | 1.7649 | 500 |

## Methodology Notes

**Train/test split**: 80/20 chronological date split. All models are calibrated exclusively on training data; no test-set information leaks into parameter estimation.

**MASE denominator**: Mean absolute error of the naïve one-step in-sample forecast (random walk: $\hat{y}_t = y_{t-1}$) computed on the training series for each item-store pair. Pairs with zero denominator (constant demand) are excluded from MASE aggregation.

**MAPE exclusion**: Periods with zero actual demand are excluded from MAPE calculation (division by zero is undefined).

**LightGBM (global)**: Pre-trained model in `models/global_lgbm_model.pkl`. Only evaluated for pairs where the sanity check passes (predicted mean within 0.1×–10× of historical mean).

**LightGBM (fitted)**: Fresh model trained per evaluation run on the training subset. Requires ≥ 30 training observations.

**ARIMA(2,1,2)**: Requires ≥ 20 training observations. Auto-recovers to historical mean fallback on fit failure.

**Reference**: Hyndman, R.J. & Koehler, A.B. (2006). Another look at measures of forecast accuracy. *International Journal of Forecasting*, 22(4), 679–688.
