from __future__ import annotations

from typing import Any

import pandas as pd


DEFAULT_BIAS_THRESHOLD = 0.1


def calculate_bias(
    data: pd.DataFrame,
    sensitive_column: str,
    target_column: str,
    bias_threshold: float = DEFAULT_BIAS_THRESHOLD,
) -> dict[str, Any]:
    if sensitive_column not in data.columns:
        raise ValueError(f"Sensitive column '{sensitive_column}' not found.")
    if target_column not in data.columns:
        raise ValueError(f"Target column '{target_column}' not found.")

    frame = data[[sensitive_column, target_column]].dropna()
    if frame.empty:
        return {"group_rates": {}, "disparity": 0.0, "is_biased": False}

    # Selection rate per group is a simple, transparent fairness proxy:
    # for each sensitive group we measure how often the positive outcome occurs.
    group_rates_series = frame.groupby(sensitive_column)[target_column].mean().sort_index()
    group_rates = {str(group): float(rate) for group, rate in group_rates_series.items()}

    max_rate = max(group_rates.values()) if group_rates else 0.0
    min_rate = min(group_rates.values()) if group_rates else 0.0
    disparity = float(max_rate - min_rate)

    return {
        "group_rates": group_rates,
        "disparity": disparity,
        "is_biased": disparity > bias_threshold,
    }


def calculate_prediction_bias(
    data: pd.DataFrame,
    sensitive_column: str,
    prediction_column: str = "predicted_label",
    bias_threshold: float = DEFAULT_BIAS_THRESHOLD,
) -> dict[str, Any]:
    return calculate_bias(
        data=data,
        sensitive_column=sensitive_column,
        target_column=prediction_column,
        bias_threshold=bias_threshold,
    )


def fairlearn_metrics_or_none(
    y_true: pd.Series,
    y_pred: pd.Series,
    sensitive_features: pd.Series,
) -> dict[str, float] | None:
    try:
        from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference
    except Exception:
        return None

    return {
        "demographic_parity_difference": float(
            demographic_parity_difference(y_true=y_true, y_pred=y_pred, sensitive_features=sensitive_features)
        ),
        "equalized_odds_difference": float(
            equalized_odds_difference(y_true=y_true, y_pred=y_pred, sensitive_features=sensitive_features)
        ),
    }
