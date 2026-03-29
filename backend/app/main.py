from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.bias import calculate_bias
from app.core.model import (
    SENSITIVE_COLUMNS,
    TrainedModel,
    combine_mitigation_probabilities,
    compute_fairness_metrics,
    counterfactual_average_probability,
    counterfactual_bias_scores,
    predict_single,
    train_biased_and_fair_models,
)
from app.core.training_data import generate_biased_dataset
from app.schemas.schemas import (
    BiasDecompositionRequest,
    BiasDecompositionResponse,
    ErrorResponse,
    MitigateRequest,
    MitigateResponse,
    PredictionRequest,
    PredictionResponse,
    TrainRequest,
    TrainResponse,
    UploadResponse,
)
from app.utils.utils import detect_sensitive_columns, load_sample_dataframe, read_csv_upload, summarize_dataframe

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    df: pd.DataFrame | None = None
    target_column: str | None = None
    sensitive_column: str | None = None
    bias_threshold: float = 0.1
    biased_model: TrainedModel | None = None
    fair_model: TrainedModel | None = None
    before_fairness: dict[str, Any] | None = None
    after_fairness: dict[str, Any] | None = None


state = AppState()

app = FastAPI(
    title="Equidata - AI Bias Auditor",
    description="Upload a dataset, audit bias, train a simple model, predict outcomes, and compare fairness before/after mitigation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bootstrap_models() -> None:
    """Initialize dataset and models when state is empty or stale."""
    df = generate_biased_dataset(n_samples=3200, seed=42)
    target_column = "target"
    sensitive_column = "gender"

    baseline = calculate_bias(
        data=df,
        sensitive_column=sensitive_column,
        target_column=target_column,
    )
    logger.info("Bootstrap baseline disparity=%.4f", baseline.get("disparity", 0.0))

    biased_model, fair_model = train_biased_and_fair_models(
        df=df,
        target_column=target_column,
        sensitive_column=sensitive_column,
    )
    before_fairness = compute_fairness_metrics(
        df=df,
        model_bundle=biased_model,
        sensitive_column=sensitive_column,
    )
    after_fairness = compute_fairness_metrics(
        df=df,
        model_bundle=fair_model,
        sensitive_column=sensitive_column,
    )

    state.df = df
    state.target_column = target_column
    state.sensitive_column = sensitive_column
    state.bias_threshold = 0.1
    state.biased_model = biased_model
    state.fair_model = fair_model
    state.before_fairness = before_fairness
    state.after_fairness = after_fairness


@app.on_event("startup")
async def startup_event():
    """Automatically create structured data and train baseline + mitigated models."""
    try:
        logger.info("Training started at startup...")
        _bootstrap_models()
        assert state.df is not None
        logger.info("Sample data loaded: %s rows, %s columns", state.df.shape[0], state.df.shape[1])
        logger.info(
            "Fairness metrics calculated: before_disparity=%.4f, after_disparity=%.4f",
            (state.before_fairness or {}).get("disparity", 0.0),
            (state.after_fairness or {}).get("disparity", 0.0),
        )

        logger.info("✓ Training completed successfully at startup")

    except Exception as exc:
        logger.error(f"Training failed at startup: {exc}", exc_info=True)


def _decision_from_prob(prob: float) -> str:
    return "Approved" if prob >= 0.5 else "Rejected"


def _normalize_features(features: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(features)
    if "experience" in normalized and "experience_years" not in normalized:
        normalized["experience_years"] = normalized.pop("experience")

    education_alias = {
        "high_school": "bachelors",
        "graduate": "bachelors",
        "postgraduate": "masters",
    }
    if "education" in normalized:
        education_raw = str(normalized["education"]).strip().lower()
        normalized["education"] = education_alias.get(education_raw, education_raw)

    defaults = {
        "gender": "female",
        "race": "group_a",
        "religion": "hindu",
        "caste": "general",
        "education": "bachelors",
        "profession": "non-tech",
        "income": 0,
        "experience_years": 0,
    }
    for key, value in defaults.items():
        normalized.setdefault(key, value)
    return normalized


def _build_response_payload(
    original_prob: float,
    mitigated_prob: float,
    bias_score: float,
    before_fairness: dict[str, Any],
    after_fairness: dict[str, Any],
    caste_rates: dict[str, float],
) -> dict[str, Any]:
    before_rates = before_fairness.get("group_rates", {})
    return {
        "decision": _decision_from_prob(original_prob),
        "confidence": round(original_prob * 100.0, 2),
        "bias_flag": bool(bias_score > 0.05),
        "bias_score": round(bias_score, 6),
        "fairness_score_before": round(float(before_fairness.get("fairness_score", 0.0)), 6),
        "fairness_score_after": round(float(after_fairness.get("fairness_score", 0.0)), 6),
        "mitigated_decision": _decision_from_prob(mitigated_prob),
        "mitigated_confidence": round(mitigated_prob * 100.0, 2),
        "group_metrics": {
            "male_rate": float(before_rates.get("male", 0.0)),
            "female_rate": float(before_rates.get("female", 0.0)),
            "caste_rates": caste_rates,
        },
    }


def _ensure_models_ready() -> None:
    if state.biased_model is None or state.fair_model is None or state.df is None:
        logger.warning("Models missing in state. Bootstrapping models lazily.")
        _bootstrap_models()


def _counterfactual_values(column: str) -> list[str]:
    if column == "gender":
        return ["male", "female"]
    if column == "caste":
        return ["general", "obc", "sc", "st"]
    if column == "religion":
        return ["hindu", "muslim", "christian", "other"]
    return []


def _mitigated_probability(features: dict[str, Any]) -> float:
    assert state.biased_model is not None
    assert state.fair_model is not None
    _, removed_sensitive_prob = predict_single(state.fair_model, features)
    counterfactual_avg = counterfactual_average_probability(state.biased_model, features, SENSITIVE_COLUMNS)
    return combine_mitigation_probabilities(removed_sensitive_prob, counterfactual_avg)


@app.get("/", tags=["Health"])
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Equidata backend is running. Use /docs for API testing.",
    }


@app.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}}, tags=["Dataset"])
async def upload_dataset(file: UploadFile = File(...)) -> UploadResponse:
    df = await read_csv_upload(file)
    state.df = df

    return UploadResponse(
        column_names=[str(c) for c in df.columns],
        basic_stats=summarize_dataframe(df),
        potential_sensitive_columns=detect_sensitive_columns(df),
    )


@app.get("/sample", response_model=UploadResponse, tags=["Dataset"])
def load_sample() -> UploadResponse:
    df = load_sample_dataframe()
    state.df = df
    return UploadResponse(
        column_names=[str(c) for c in df.columns],
        basic_stats=summarize_dataframe(df),
        potential_sensitive_columns=detect_sensitive_columns(df),
    )


@app.post("/train", response_model=TrainResponse, responses={400: {"model": ErrorResponse}}, tags=["Model"])
def train_models(payload: TrainRequest) -> TrainResponse:
    if state.df is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. Call /upload or /sample first.")

    df = state.df.copy()
    if payload.sensitive_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Sensitive column '{payload.sensitive_column}' not found.")
    if payload.target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Target column '{payload.target_column}' not found.")

    baseline = calculate_bias(
        data=df,
        sensitive_column=payload.sensitive_column,
        target_column=payload.target_column,
        bias_threshold=payload.bias_threshold,
    )

    biased_model, fair_model = train_biased_and_fair_models(
        df=df,
        target_column=payload.target_column,
        sensitive_column=payload.sensitive_column,
    )

    before_fairness = fairness_on_training_predictions(
        df=df,
        model_bundle=biased_model,
        sensitive_column=payload.sensitive_column,
    )
    after_fairness = fairness_on_training_predictions(
        df=df,
        model_bundle=fair_model,
        sensitive_column=payload.sensitive_column,
    )

    state.target_column = payload.target_column
    state.sensitive_column = payload.sensitive_column
    state.bias_threshold = payload.bias_threshold
    state.biased_model = biased_model
    state.fair_model = fair_model
    state.before_fairness = before_fairness
    state.after_fairness = after_fairness

    return TrainResponse(
        message="Biased and fair models trained successfully.",
        target_column=payload.target_column,
        sensitive_column=payload.sensitive_column,
        before_fairness={"dataset_bias": baseline, "prediction_bias": before_fairness},
        after_fairness={"prediction_bias": after_fairness},
    )


def fairness_on_training_predictions(
    df: pd.DataFrame,
    model_bundle: TrainedModel,
    sensitive_column: str,
) -> dict[str, Any]:
    return compute_fairness_metrics(
        df=df,
        model_bundle=model_bundle,
        sensitive_column=sensitive_column,
    )


@app.post("/predict", response_model=PredictionResponse, responses={400: {"model": ErrorResponse}}, tags=["Model"])
def predict(payload: PredictionRequest) -> PredictionResponse:
    _ensure_models_ready()
    if state.sensitive_column != payload.sensitive_column:
        logger.warning(
            "Sensitive column mismatch at /predict. trained=%s request=%s. Continuing with trained column.",
            state.sensitive_column,
            payload.sensitive_column,
        )

    assert state.biased_model is not None
    assert state.fair_model is not None
    assert state.df is not None

    features = _normalize_features(payload.features)

    _, original_prob = predict_single(state.biased_model, features)
    _, removed_sensitive_prob = predict_single(state.fair_model, features)
    counterfactual_avg = counterfactual_average_probability(state.biased_model, features, SENSITIVE_COLUMNS)
    mitigated_prob = combine_mitigation_probabilities(removed_sensitive_prob, counterfactual_avg)

    bias_info = counterfactual_bias_scores(state.biased_model, features, SENSITIVE_COLUMNS)
    bias_score = float(bias_info["bias_score"])

    before = compute_fairness_metrics(state.df, state.biased_model, state.sensitive_column or "gender")
    after = compute_fairness_metrics(state.df, state.fair_model, state.sensitive_column or "gender")

    caste_before = compute_fairness_metrics(state.df, state.biased_model, "caste") if "caste" in state.df.columns else {"group_rates": {}}
    caste_rates = caste_before.get("group_rates", {})

    state.before_fairness = before
    state.after_fairness = after

    payload_data = _build_response_payload(
        original_prob=original_prob,
        mitigated_prob=mitigated_prob,
        bias_score=bias_score,
        before_fairness=before,
        after_fairness=after,
        caste_rates={k: float(v) for k, v in caste_rates.items()},
    )
    return PredictionResponse(**payload_data)


@app.post("/mitigate", response_model=MitigateResponse, responses={400: {"model": ErrorResponse}}, tags=["Mitigation"])
def mitigate(payload: MitigateRequest) -> MitigateResponse:
    _ensure_models_ready()
    if state.sensitive_column != payload.sensitive_column:
        logger.warning(
            "Sensitive column mismatch at /mitigate. trained=%s request=%s. Continuing with trained column.",
            state.sensitive_column,
            payload.sensitive_column,
        )

    assert state.biased_model is not None
    assert state.fair_model is not None
    assert state.df is not None

    features = _normalize_features(payload.features)

    _, original_prob = predict_single(state.biased_model, features)
    _, removed_sensitive_prob = predict_single(state.fair_model, features)
    counterfactual_avg = counterfactual_average_probability(state.biased_model, features, SENSITIVE_COLUMNS)
    mitigated_prob = combine_mitigation_probabilities(removed_sensitive_prob, counterfactual_avg)

    bias_info = counterfactual_bias_scores(state.biased_model, features, SENSITIVE_COLUMNS)
    bias_score = float(bias_info["bias_score"])

    before = compute_fairness_metrics(state.df, state.biased_model, state.sensitive_column or "gender")
    after = compute_fairness_metrics(state.df, state.fair_model, state.sensitive_column or "gender")
    caste_before = compute_fairness_metrics(state.df, state.biased_model, "caste") if "caste" in state.df.columns else {"group_rates": {}}
    caste_rates = caste_before.get("group_rates", {})

    state.before_fairness = before
    state.after_fairness = after

    payload_data = _build_response_payload(
        original_prob=original_prob,
        mitigated_prob=mitigated_prob,
        bias_score=bias_score,
        before_fairness=before,
        after_fairness=after,
        caste_rates={k: float(v) for k, v in caste_rates.items()},
    )
    return MitigateResponse(**payload_data)


@app.post("/bias/decomposition", response_model=BiasDecompositionResponse, tags=["Bias"])
def bias_decomposition(payload: BiasDecompositionRequest) -> BiasDecompositionResponse:
    _ensure_models_ready()

    assert state.biased_model is not None
    assert state.fair_model is not None
    assert state.df is not None

    available_sensitive_columns = [col for col in SENSITIVE_COLUMNS if col in state.df.columns]
    if not available_sensitive_columns:
        raise HTTPException(status_code=400, detail="No supported sensitive columns available in the dataset.")

    dataset_decomposition: dict[str, dict[str, Any]] = {}
    before_disparities: list[float] = []
    after_disparities: list[float] = []
    for column in available_sensitive_columns:
        before = compute_fairness_metrics(state.df, state.biased_model, column)
        after = compute_fairness_metrics(state.df, state.fair_model, column)

        before_disparity = float(before.get("disparity", 0.0))
        after_disparity = float(after.get("disparity", 0.0))
        before_disparities.append(before_disparity)
        after_disparities.append(after_disparity)
        dataset_decomposition[column] = {
            "before_group_rates": {k: float(v) for k, v in before.get("group_rates", {}).items()},
            "after_group_rates": {k: float(v) for k, v in after.get("group_rates", {}).items()},
            "before_disparity": before_disparity,
            "after_disparity": after_disparity,
            "before_fairness_score": float(before.get("fairness_score", 0.0)),
            "after_fairness_score": float(after.get("fairness_score", 0.0)),
            "fairness_improvement": float(before_disparity - after_disparity),
        }

    counterfactual_decomposition: dict[str, dict[str, Any]] = {}
    if payload.features is not None:
        normalized = _normalize_features(payload.features)
        for column in available_sensitive_columns:
            values = _counterfactual_values(column)
            biased_info = counterfactual_bias_scores(state.biased_model, normalized, [column])
            fair_info = counterfactual_bias_scores(state.fair_model, normalized, [column])

            mitigated_probs: dict[str, float] = {}
            for value in values:
                variant = dict(normalized)
                variant[column] = value
                mitigated_probs[value] = float(_mitigated_probability(variant))

            mitigated_bias_score = float(max(mitigated_probs.values()) - min(mitigated_probs.values())) if mitigated_probs else 0.0
            counterfactual_decomposition[column] = {
                "biased_bias_score": float(biased_info.get("bias_score", 0.0)),
                "fair_model_bias_score": float(fair_info.get("bias_score", 0.0)),
                "mitigated_bias_score": mitigated_bias_score,
                "mitigated_probabilities": mitigated_probs,
            }

    overall_before = float(sum(before_disparities) / len(before_disparities)) if before_disparities else 0.0
    overall_after = float(sum(after_disparities) / len(after_disparities)) if after_disparities else 0.0

    return BiasDecompositionResponse(
        dataset_decomposition=dataset_decomposition,
        counterfactual_decomposition=counterfactual_decomposition,
        overall_before_disparity=overall_before,
        overall_after_disparity=overall_after,
    )
