from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    column_names: list[str]
    basic_stats: dict[str, Any]
    potential_sensitive_columns: list[str]


class TrainRequest(BaseModel):
    target_column: str = Field(..., description="Binary target column name")
    sensitive_column: str = Field(default="gender", description="Primary sensitive attribute column name")
    bias_threshold: float = Field(default=0.1, ge=0.0, le=1.0)


class TrainResponse(BaseModel):
    message: str
    target_column: str
    sensitive_column: str
    before_fairness: dict[str, Any]
    after_fairness: dict[str, Any]


class PredictionRequest(BaseModel):
    features: dict[str, Any]
    sensitive_column: str = Field(default="gender")


class GroupMetrics(BaseModel):
    male_rate: float
    female_rate: float
    caste_rates: dict[str, float]


class PredictionResponse(BaseModel):
    decision: str
    confidence: float
    bias_flag: bool
    bias_score: float
    fairness_score_before: float
    fairness_score_after: float
    mitigated_decision: str
    mitigated_confidence: float
    group_metrics: GroupMetrics


class MitigateRequest(BaseModel):
    features: dict[str, Any]
    sensitive_column: str = Field(default="gender")


class MitigateResponse(PredictionResponse):
    pass


class BiasDecompositionRequest(BaseModel):
    features: Optional[dict[str, Any]] = None


class AttributeBiasBreakdown(BaseModel):
    before_group_rates: dict[str, float]
    after_group_rates: dict[str, float]
    before_disparity: float
    after_disparity: float
    before_fairness_score: float
    after_fairness_score: float
    fairness_improvement: float


class CounterfactualAttributeBreakdown(BaseModel):
    biased_bias_score: float
    fair_model_bias_score: float
    mitigated_bias_score: float
    mitigated_probabilities: dict[str, float]


class BiasDecompositionResponse(BaseModel):
    dataset_decomposition: dict[str, AttributeBiasBreakdown]
    counterfactual_decomposition: dict[str, CounterfactualAttributeBreakdown]
    overall_before_disparity: float
    overall_after_disparity: float


class ErrorResponse(BaseModel):
    detail: str
