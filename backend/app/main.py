from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.bias import calculate_bias
from app.core.model import (
    HIRING_CATEGORICAL_COLUMNS,
    HIRING_FEATURE_COLUMNS,
    SENSITIVE_COLUMNS,
    TrainedModel,
    combine_mitigation_probabilities,
    compute_fairness_metrics,
    counterfactual_average_probability,
    counterfactual_bias_scores,
    predict_single,
    train_model,
    train_biased_and_fair_models,
)
from app.core.training_data import generate_biased_dataset, generate_scenario_dataset
from app.schemas.schemas import (
    AuditCurrentRequest,
    AuditCurrentResponse,
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


SCENARIO_ALIASES: dict[str, str] = {
    "hiring": "hiring",
    "loan": "loan_approval",
    "loanapproval": "loan_approval",
    "loan_approval": "loan_approval",
    "college": "college_admission",
    "collegeadmission": "college_admission",
    "college_admission": "college_admission",
}

SCENARIO_FEATURES: dict[str, list[str]] = {
    "hiring": ["experience", "education_level", "college_tier", "skills_score", "expected_salary"],
    "loan_approval": ["loan_amount", "interest_rate", "monthly_income", "profession", "emi"],
    "college_admission": ["entrance_score", "family_income", "parents_education", "previous_academic_score"],
}

SCENARIO_REQUIRED_INPUTS: dict[str, list[str]] = {
    "hiring": ["experience", "education_level", "college_tier", "skills_score", "expected_salary"],
    "loan_approval": ["loan_amount", "interest_rate", "monthly_income", "profession"],
    "college_admission": ["entrance_score", "family_income", "parents_education", "previous_academic_score"],
}

SCENARIO_CATEGORICAL: dict[str, list[str]] = {
    "hiring": ["education_level", "college_tier"],
    "loan_approval": ["profession"],
    "college_admission": ["parents_education"],
}

SCENARIO_DEFAULT_FEATURES: dict[str, dict[str, Any]] = {
    "hiring": {
        "experience": 4,
        "education_level": "bachelors",
        "college_tier": "other",
        "skills_score": 70,
        "expected_salary": 90000,
        "gender": "female",
        "caste": "general",
        "religion": "hindu",
    },
    "loan_approval": {
        "loan_amount": 800000,
        "interest_rate": 10.5,
        "monthly_income": 70000,
        "profession": "salaried",
        "gender": "female",
        "caste": "general",
        "religion": "hindu",
    },
    "college_admission": {
        "entrance_score": 78,
        "family_income": 550000,
        "parents_education": "graduate",
        "previous_academic_score": 82,
        "gender": "female",
        "caste": "general",
        "religion": "hindu",
    },
}


@dataclass
class ScenarioBundle:
    df: pd.DataFrame
    biased_model: TrainedModel
    fair_model: TrainedModel
    before_fairness: dict[str, Any]
    after_fairness: dict[str, Any]


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
    scenario_bundles: dict[str, ScenarioBundle] | None = None


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
    """Initialize scenario datasets and train biased/fair models for each."""
    target_column = "approved"
    sensitive_column = "gender"

    bundles: dict[str, ScenarioBundle] = {}
    for scenario in SCENARIO_FEATURES:
        raw_df = generate_scenario_dataset(scenario=scenario, n_samples=1800, seed=42)
        rename_map = {"target": target_column}
        if "experience_years" in raw_df.columns:
            rename_map["experience_years"] = "experience"
        df = raw_df.rename(columns=rename_map)

        feature_columns = SCENARIO_FEATURES[scenario]
        categorical_columns = SCENARIO_CATEGORICAL[scenario]

        baseline = calculate_bias(
            data=df,
            sensitive_column=sensitive_column,
            target_column=target_column,
        )
        logger.info("Bootstrap %s baseline disparity=%.4f", scenario, baseline.get("disparity", 0.0))

        biased_model = train_model(
            df=df,
            target_column=target_column,
            sensitive_column=sensitive_column,
            forced_feature_columns=feature_columns + SENSITIVE_COLUMNS,
            label_encode_columns=categorical_columns,
        )
        fair_model_local = train_model(
            df=df,
            target_column=target_column,
            sensitive_column=sensitive_column,
            forced_feature_columns=feature_columns,
            label_encode_columns=categorical_columns,
        )

        before_fairness = compute_fairness_metrics(
            df=df,
            model_bundle=biased_model,
            sensitive_column=sensitive_column,
        )
        after_fairness = compute_fairness_metrics(
            df=df,
            model_bundle=fair_model_local,
            sensitive_column=sensitive_column,
        )

        bundles[scenario] = ScenarioBundle(
            df=df,
            biased_model=biased_model,
            fair_model=fair_model_local,
            before_fairness=before_fairness,
            after_fairness=after_fairness,
        )

    hiring_bundle = bundles["hiring"]
    state.df = hiring_bundle.df
    state.target_column = target_column
    state.sensitive_column = sensitive_column
    state.bias_threshold = 0.1
    state.biased_model = hiring_bundle.biased_model
    state.fair_model = hiring_bundle.fair_model
    state.before_fairness = hiring_bundle.before_fairness
    state.after_fairness = hiring_bundle.after_fairness
    state.scenario_bundles = bundles


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


def _normalize_scenario(scenario: str | None) -> str:
    normalized = (scenario or "hiring").strip().lower().replace(" ", "_")
    return SCENARIO_ALIASES.get(normalized, "hiring")


def _normalize_features(features: dict[str, Any], scenario: str) -> dict[str, Any]:
    normalized = dict(features)

    if scenario == "hiring":
        if "experience_years" in normalized and "experience" not in normalized:
            normalized["experience"] = normalized.pop("experience_years")
        if "education" in normalized and "education_level" not in normalized:
            normalized["education_level"] = normalized.pop("education")

        normalized["education_level"] = str(normalized.get("education_level", "")).strip().lower()

        college_raw = str(normalized.get("college_tier", "")).strip().lower()
        if college_raw == "iit":
            normalized["college_tier"] = "iit"
        elif college_raw == "nit":
            normalized["college_tier"] = "nit"
        else:
            normalized["college_tier"] = "other"

    if scenario == "college_admission":
        normalized["parents_education"] = str(normalized.get("parents_education", "")).strip().lower()

    if scenario == "loan_approval":
        normalized["profession"] = str(normalized.get("profession", "")).strip().lower()

    if "skills_score" in normalized:
        normalized["skills_score"] = float(normalized["skills_score"])
    if "expected_salary" in normalized:
        normalized["expected_salary"] = float(normalized["expected_salary"])
    if "experience" in normalized:
        normalized["experience"] = float(normalized["experience"])
    if "loan_amount" in normalized:
        normalized["loan_amount"] = float(normalized["loan_amount"])
    if "interest_rate" in normalized:
        normalized["interest_rate"] = float(normalized["interest_rate"])
    if "monthly_income" in normalized:
        normalized["monthly_income"] = float(normalized["monthly_income"])
    if "entrance_score" in normalized:
        normalized["entrance_score"] = float(normalized["entrance_score"])
    if "family_income" in normalized:
        normalized["family_income"] = float(normalized["family_income"])
    if "previous_academic_score" in normalized:
        normalized["previous_academic_score"] = float(normalized["previous_academic_score"])

    if scenario == "loan_approval":
        if "loan_amount" in normalized and "interest_rate" in normalized:
            principal = float(normalized["loan_amount"])
            rate = float(normalized["interest_rate"])
            monthly_rate = max(rate / (12.0 * 100.0), 1e-6)
            factor = (1.0 + monthly_rate) ** 60
            emi = (principal * monthly_rate * factor) / (factor - 1.0)
            normalized["emi"] = float(emi)

    return normalized


def _validate_required_prediction_fields(features: dict[str, Any], scenario: str) -> None:
    required_columns = SCENARIO_REQUIRED_INPUTS[scenario]
    missing = [col for col in required_columns if col not in features]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required prediction fields: {missing}")


def _build_response_payload(
    original_prob: float,
    mitigated_prob: float,
    bias_score: float,
    before_fairness: dict[str, Any],
    after_fairness: dict[str, Any],
    caste_rates: dict[str, float],
) -> dict[str, Any]:
    return {
        "prediction": _decision_from_prob(mitigated_prob),
        "confidence": round(mitigated_prob * 100.0, 2),
        "bias_flag": bool(bias_score > 0.1),
    }


def _ensure_models_ready() -> None:
    if state.scenario_bundles is None:
        logger.warning("Models missing in state. Bootstrapping models lazily.")
        _bootstrap_models()


def _scenario_bundle(scenario: str) -> ScenarioBundle:
    _ensure_models_ready()
    assert state.scenario_bundles is not None
    if scenario not in state.scenario_bundles:
        raise HTTPException(status_code=400, detail=f"Unsupported scenario '{scenario}'.")
    return state.scenario_bundles[scenario]


def _counterfactual_values(column: str) -> list[str]:
    if column == "gender":
        return ["male", "female"]
    if column == "caste":
        return ["general", "obc", "sc", "st"]
    if column == "religion":
        return ["hindu", "muslim", "christian", "other"]
    return []


def _mitigated_probability(features: dict[str, Any], bundle: ScenarioBundle) -> float:
    _, removed_sensitive_prob = predict_single(bundle.fair_model, features)
    counterfactual_avg = counterfactual_average_probability(bundle.biased_model, features, SENSITIVE_COLUMNS)
    return combine_mitigation_probabilities(removed_sensitive_prob, counterfactual_avg)


def _feature_contributions(bundle: ScenarioBundle, scenario: str, features: dict[str, Any]) -> dict[str, float]:
    fair_features = {k: v for k, v in features.items() if k not in SENSITIVE_COLUMNS}
    _, baseline_prob = predict_single(bundle.fair_model, fair_features)

    contributions: dict[str, float] = {}
    for feature in SCENARIO_FEATURES[scenario]:
        if feature not in fair_features:
            continue

        col = bundle.df[feature] if feature in bundle.df.columns else None
        if col is None:
            continue

        variant = dict(fair_features)
        if pd.api.types.is_numeric_dtype(col):
            baseline_value: Any = float(col.median())
        else:
            mode = col.mode(dropna=True)
            baseline_value = str(mode.iloc[0]) if not mode.empty else str(variant[feature])
        variant[feature] = baseline_value

        _, variant_prob = predict_single(bundle.fair_model, variant)
        contributions[feature] = round(float(baseline_prob - variant_prob), 4)

    ranked = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
    return {k: v for k, v in ranked}


def _is_legacy_profile(features: dict[str, Any]) -> bool:
    legacy_keys = {"education", "profession", "income", "experience_years", "race"}
    return any(key in features for key in legacy_keys)


def _legacy_bias_decomposition(features: dict[str, Any]) -> BiasDecompositionResponse:
    legacy_df = generate_biased_dataset(n_samples=3200, seed=42)
    legacy_biased, legacy_fair = train_biased_and_fair_models(
        df=legacy_df,
        target_column="target",
        sensitive_column="gender",
    )

    dataset_decomposition: dict[str, dict[str, Any]] = {}
    before_disparities: list[float] = []
    after_disparities: list[float] = []
    for column in [col for col in SENSITIVE_COLUMNS if col in legacy_df.columns]:
        before = compute_fairness_metrics(legacy_df, legacy_biased, column)
        after = compute_fairness_metrics(legacy_df, legacy_fair, column)

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
    for column in [col for col in SENSITIVE_COLUMNS if col in legacy_df.columns]:
        values = _counterfactual_values(column)
        biased_info = counterfactual_bias_scores(legacy_biased, features, [column])
        fair_info = counterfactual_bias_scores(legacy_fair, features, [column])

        mitigated_probs: dict[str, float] = {}
        for value in values:
            variant = dict(features)
            variant[column] = value
            _, fair_prob = predict_single(legacy_fair, variant)
            cf_prob = counterfactual_average_probability(legacy_biased, variant, SENSITIVE_COLUMNS)
            mitigated_probs[value] = float(combine_mitigation_probabilities(fair_prob, cf_prob))

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

    try:
        np.random.seed(42)
        random.seed(42)

        scenario = _normalize_scenario(payload.scenario)
        bundle = _scenario_bundle(scenario)

        logger.info("=== PREDICT ENDPOINT ===")
        logger.info("Scenario: %s", scenario)
        logger.info("Incoming raw payload: %s", payload.features)
        
        _validate_required_prediction_fields(payload.features, scenario)

        features = _normalize_features(payload.features, scenario)
        # Sensitive attributes are dropped from fair decision features.
        features_for_fair_model = {k: v for k, v in features.items() if k not in SENSITIVE_COLUMNS}

        logger.info("Processed features: %s", features)
        logger.info("Fair model features (sensitive removed): %s", features_for_fair_model)
        logger.info("Model expected feature count: %s", len(bundle.fair_model.feature_columns))

        _, biased_prob = predict_single(bundle.biased_model, features)
        _, fair_prob = predict_single(bundle.fair_model, features_for_fair_model)
        bias_gap = abs(biased_prob - fair_prob)

        print("INPUT:", features)
        print("OUTPUT:", {"biased_probability": biased_prob, "fair_probability": fair_prob, "bias_gap": bias_gap})

        logger.info("Biased probability: %.6f", biased_prob)
        logger.info("Fair probability: %.6f", fair_prob)
        logger.info("Bias gap: %.6f", bias_gap)
        logger.info("=== PREDICT ENDPOINT END ===")

        biased_label = _decision_from_prob(biased_prob)
        fair_label = _decision_from_prob(fair_prob)
        return PredictionResponse(
            input_features=features,
            biased_prediction=biased_label,
            fair_prediction=fair_label,
            biased_probability=round(biased_prob, 4),
            fair_probability=round(fair_prob, 4),
            bias_gap=round(bias_gap, 4),
            prediction=fair_label,
            confidence=round(fair_prob * 100.0, 2),
            bias_flag=bool(bias_gap > 0.1),
        )
    except HTTPException:
        return JSONResponse(status_code=400, content={"error": "Invalid input. Check required feature fields and categories."})
    except Exception as exc:
        logger.exception("Prediction failure")
        return JSONResponse(status_code=400, content={"error": f"Prediction failed: {str(exc)}"})


@app.post("/mitigate", response_model=MitigateResponse, responses={400: {"model": ErrorResponse}}, tags=["Mitigation"])
def mitigate(payload: MitigateRequest) -> MitigateResponse:
    _ensure_models_ready()

    scenario = _normalize_scenario(payload.scenario)
    bundle = _scenario_bundle(scenario)

    _validate_required_prediction_fields(payload.features, scenario)
    features = _normalize_features(payload.features, scenario)

    _, original_prob = predict_single(bundle.biased_model, features)
    _, removed_sensitive_prob = predict_single(bundle.fair_model, features)
    counterfactual_avg = counterfactual_average_probability(bundle.biased_model, features, SENSITIVE_COLUMNS)
    mitigated_prob = combine_mitigation_probabilities(removed_sensitive_prob, counterfactual_avg)
    bias_gap = abs(original_prob - removed_sensitive_prob)

    bias_info = counterfactual_bias_scores(bundle.biased_model, features, SENSITIVE_COLUMNS)
    bias_score = float(bias_info["bias_score"])

    before = compute_fairness_metrics(bundle.df, bundle.biased_model, state.sensitive_column or "gender")
    after = compute_fairness_metrics(bundle.df, bundle.fair_model, state.sensitive_column or "gender")
    caste_before = compute_fairness_metrics(bundle.df, bundle.biased_model, "caste") if "caste" in bundle.df.columns else {"group_rates": {}}
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
    return MitigateResponse(
        input_features=features,
        biased_prediction=_decision_from_prob(original_prob),
        fair_prediction=_decision_from_prob(removed_sensitive_prob),
        biased_probability=round(original_prob, 4),
        fair_probability=round(removed_sensitive_prob, 4),
        bias_gap=round(bias_gap, 4),
        **payload_data,
    )


@app.post("/audit/current", response_model=AuditCurrentResponse, responses={400: {"model": ErrorResponse}}, tags=["Bias"])
def audit_current(payload: AuditCurrentRequest) -> AuditCurrentResponse:
    scenario = _normalize_scenario(payload.scenario)
    bundle = _scenario_bundle(scenario)

    logger.info("=== AUDIT/CURRENT ENDPOINT ===")
    logger.info("Scenario: %s", scenario)
    logger.info("Incoming raw payload: %s", payload.features)

    _validate_required_prediction_fields(payload.features, scenario)
    features = _normalize_features(payload.features, scenario)
    fair_features = {k: v for k, v in features.items() if k not in SENSITIVE_COLUMNS}

    logger.info("Processed features: %s", features)
    logger.info("Fair model features (sensitive removed): %s", fair_features)

    _, biased_prob = predict_single(bundle.biased_model, features)
    _, fair_prob = predict_single(bundle.fair_model, fair_features)
    bias_gap = abs(biased_prob - fair_prob)

    logger.info("Biased probability: %.6f", biased_prob)
    logger.info("Fair probability: %.6f", fair_prob)
    logger.info("Bias gap: %.6f", bias_gap)
    logger.info("=== AUDIT/CURRENT ENDPOINT END ===")

    return AuditCurrentResponse(
        input_features=features,
        biased_prediction=_decision_from_prob(biased_prob),
        fair_prediction=_decision_from_prob(fair_prob),
        biased_probability=round(biased_prob, 4),
        fair_probability=round(fair_prob, 4),
        bias_gap=round(bias_gap, 4),
        bias_flag=bool(bias_gap > 0.1),
        confidence=round(fair_prob * 100.0, 2),
        contributions=_feature_contributions(bundle, scenario, features),
    )


@app.post("/bias/decomposition", response_model=BiasDecompositionResponse, tags=["Bias"])
def bias_decomposition(payload: BiasDecompositionRequest) -> BiasDecompositionResponse:
    scenario = _normalize_scenario(payload.scenario)

    if payload.features is not None and _is_legacy_profile(payload.features):
        return _legacy_bias_decomposition(payload.features)

    bundle = _scenario_bundle(scenario)

    available_sensitive_columns = [col for col in SENSITIVE_COLUMNS if col in bundle.df.columns]
    if not available_sensitive_columns:
        raise HTTPException(status_code=400, detail="No supported sensitive columns available in the dataset.")

    dataset_decomposition: dict[str, dict[str, Any]] = {}
    before_disparities: list[float] = []
    after_disparities: list[float] = []
    for column in available_sensitive_columns:
        before = compute_fairness_metrics(bundle.df, bundle.biased_model, column)
        after = compute_fairness_metrics(bundle.df, bundle.fair_model, column)

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
        default_features = dict(SCENARIO_DEFAULT_FEATURES[scenario])
        default_features.update(payload.features)
        normalized = _normalize_features(default_features, scenario)
        for column in available_sensitive_columns:
            values = _counterfactual_values(column)
            biased_info = counterfactual_bias_scores(bundle.biased_model, normalized, [column])
            fair_info = counterfactual_bias_scores(bundle.fair_model, normalized, [column])

            mitigated_probs: dict[str, float] = {}
            for value in values:
                variant = dict(normalized)
                variant[column] = value
                mitigated_probs[value] = float(_mitigated_probability(variant, bundle))

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
