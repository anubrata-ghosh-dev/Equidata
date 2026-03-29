from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler

from app.core.bias import fairlearn_metrics_or_none
from app.utils.utils import normalize_binary_target


SENSITIVE_COLUMNS = ["gender", "caste", "religion"]


@dataclass
class TrainedModel:
    pipeline: Pipeline
    feature_columns: list[str]
    target_column: str
    sensitive_column: str
    dropped_sensitive: bool


def _make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _feature_columns(df: pd.DataFrame, target_column: str, sensitive_column: str | None = None) -> list[str]:
    columns = [col for col in df.columns if col != target_column]
    if sensitive_column is not None:
        columns = [col for col in columns if col != sensitive_column]
    if not columns:
        raise HTTPException(status_code=400, detail="No usable feature columns remain for training.")
    return columns


def train_model(
    df: pd.DataFrame,
    target_column: str,
    sensitive_column: str,
    dropped_sensitive_columns: list[str] | None = None,
) -> TrainedModel:
    if sensitive_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Sensitive column '{sensitive_column}' not found.")

    dropped_sensitive_columns = dropped_sensitive_columns or []

    y = normalize_binary_target(df, target_column)
    features = [col for col in df.columns if col != target_column and col not in dropped_sensitive_columns]
    if not features:
        raise HTTPException(status_code=400, detail="No usable feature columns remain for training.")
    X = df[features].copy()

    categorical_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    numeric_cols = [col for col in X.columns if col not in categorical_cols]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", _make_one_hot_encoder(), categorical_cols),
            ("num", StandardScaler(), numeric_cols),
        ],
        remainder="drop",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    random_state=42,
                    solver="lbfgs",
                    C=2.5,
                    max_iter=1200,
                ),
            ),
        ]
    )

    pipeline.fit(X, y)
    return TrainedModel(
        pipeline=pipeline,
        feature_columns=features,
        target_column=target_column,
        sensitive_column=sensitive_column,
        dropped_sensitive=bool(dropped_sensitive_columns),
    )


def train_biased_and_fair_models(
    df: pd.DataFrame,
    target_column: str,
    sensitive_column: str,
) -> tuple[TrainedModel, TrainedModel]:
    biased = train_model(df=df, target_column=target_column, sensitive_column=sensitive_column)
    fair = train_model(
        df=df,
        target_column=target_column,
        sensitive_column=sensitive_column,
        dropped_sensitive_columns=[col for col in SENSITIVE_COLUMNS if col in df.columns],
    )
    return biased, fair


def _build_feature_row(features: dict[str, Any], required_columns: list[str]) -> pd.DataFrame:
    row: dict[str, Any] = {}
    for col in required_columns:
        val = features.get(col)
        if val is None:
            val = 0 if any(x in col.lower() for x in ['income', 'experience', 'years', 'age', 'salary']) else ""
        row[col] = val
    return pd.DataFrame([row])


def predict_single(model_bundle: TrainedModel, features: dict[str, Any]) -> tuple[int, float]:
    X = _build_feature_row(features, model_bundle.feature_columns)
    prob = float(model_bundle.pipeline.predict_proba(X)[0][1])
    decision = 1 if prob >= 0.5 else 0
    return decision, prob


def predict_batch_probabilities(model_bundle: TrainedModel, df: pd.DataFrame) -> pd.Series:
    X = df[model_bundle.feature_columns].copy()
    probs = model_bundle.pipeline.predict_proba(X)[:, 1]
    return pd.Series(probs, index=df.index, name="probability")


def selection_rate_by_group(df: pd.DataFrame, group_column: str, prediction_column: str = "pred") -> dict[str, float]:
    rates = df.groupby(group_column)[prediction_column].mean().sort_index()
    return {str(k): float(v) for k, v in rates.items()}


def disparity_from_group_rates(group_rates: dict[str, float]) -> float:
    if not group_rates:
        return 0.0
    values = list(group_rates.values())
    return float(max(values) - min(values))


def fairness_score(group_rates: dict[str, float]) -> float:
    return float(max(0.0, 1.0 - disparity_from_group_rates(group_rates)))


def compute_fairness_metrics(
    df: pd.DataFrame,
    model_bundle: TrainedModel,
    sensitive_column: str,
    threshold: float = 0.5,
) -> dict[str, Any]:
    probs = predict_batch_probabilities(model_bundle, df)
    preds = (probs >= threshold).astype(int)
    audit_df = pd.DataFrame({sensitive_column: df[sensitive_column], "pred": preds})
    group_rates = selection_rate_by_group(audit_df, sensitive_column, "pred")
    disparity = disparity_from_group_rates(group_rates)

    metrics: dict[str, Any] = {
        "group_rates": group_rates,
        "disparity": disparity,
        "fairness_score": max(0.0, 1.0 - disparity),
    }

    y_true = normalize_binary_target(df, model_bundle.target_column)
    optional = fairlearn_metrics_or_none(
        y_true=y_true,
        y_pred=preds.astype(int),
        sensitive_features=df[sensitive_column],
    )
    if optional is not None:
        metrics["fairlearn"] = optional
    return metrics


def _counterfactual_values_for(column: str) -> list[str]:
    if column == "gender":
        return ["male", "female"]
    if column == "caste":
        return ["general", "obc", "sc", "st"]
    if column == "religion":
        return ["hindu", "muslim", "christian", "other"]
    return []


def counterfactual_bias_scores(
    model_bundle: TrainedModel,
    features: dict[str, Any],
    sensitive_columns: list[str],
) -> dict[str, Any]:
    per_attribute: dict[str, dict[str, float]] = {}
    deltas: list[float] = []

    for column in sensitive_columns:
        if column not in features:
            continue
        probs: list[float] = []
        for value in _counterfactual_values_for(column):
            variant = dict(features)
            variant[column] = value
            _, prob = predict_single(model_bundle, variant)
            probs.append(prob)
        if probs:
            score = float(max(probs) - min(probs))
            deltas.append(score)
            per_attribute[column] = {
                "max_prob": float(max(probs)),
                "min_prob": float(min(probs)),
                "bias_score": score,
            }

    overall = float(max(deltas)) if deltas else 0.0
    return {
        "bias_score": overall,
        "per_attribute": per_attribute,
    }


def counterfactual_average_probability(
    model_bundle: TrainedModel,
    features: dict[str, Any],
    sensitive_columns: list[str],
) -> float:
    probs: list[float] = []

    gender_values = _counterfactual_values_for("gender") if "gender" in sensitive_columns else [features.get("gender")]
    caste_values = _counterfactual_values_for("caste") if "caste" in sensitive_columns else [features.get("caste")]
    religion_values = _counterfactual_values_for("religion") if "religion" in sensitive_columns else [features.get("religion")]

    for g in gender_values:
        for c in caste_values:
            for r in religion_values:
                variant = dict(features)
                if g is not None:
                    variant["gender"] = g
                if c is not None:
                    variant["caste"] = c
                if r is not None:
                    variant["religion"] = r
                _, p = predict_single(model_bundle, variant)
                probs.append(p)

    if not probs:
        _, p = predict_single(model_bundle, features)
        return float(p)
    return float(np.mean(probs))


def combine_mitigation_probabilities(removed_sensitive_prob: float, counterfactual_avg_prob: float) -> float:
    # Blend both methods to avoid extreme confidence swings while reducing sensitivity.
    return float((removed_sensitive_prob + counterfactual_avg_prob) / 2.0)


def fairness_on_training_predictions(
    df: pd.DataFrame,
    model_bundle: TrainedModel,
    bias_threshold: float,
) -> dict[str, Any]:
    X = df[model_bundle.feature_columns].copy()
    preds = pd.Series(model_bundle.pipeline.predict(X), index=df.index, name="predicted_label")
    audit_df = pd.DataFrame(
        {
            model_bundle.sensitive_column: df[model_bundle.sensitive_column],
            "predicted_label": preds.astype(int),
        }
    )
    metrics = calculate_prediction_bias(
        data=audit_df,
        sensitive_column=model_bundle.sensitive_column,
        prediction_column="predicted_label",
        bias_threshold=bias_threshold,
    )

    y_true = normalize_binary_target(df, model_bundle.target_column)
    optional = fairlearn_metrics_or_none(
        y_true=y_true,
        y_pred=preds.astype(int),
        sensitive_features=df[model_bundle.sensitive_column],
    )
    if optional is not None:
        metrics["fairlearn"] = optional
    return metrics
