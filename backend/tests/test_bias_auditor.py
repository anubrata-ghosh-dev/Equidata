from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.model import (
    SENSITIVE_COLUMNS,
    combine_mitigation_probabilities,
    counterfactual_average_probability,
    counterfactual_bias_scores,
    predict_single,
    train_biased_and_fair_models,
)
from app.core.training_data import generate_biased_dataset
from app.main import app


def _default_profile() -> dict[str, object]:
    return {
        "gender": "male",
        "race": "group_a",
        "religion": "hindu",
        "caste": "general",
        "education": "masters",
        "profession": "tech",
        "income": 85000,
        "experience_years": 6,
    }


def test_probability_changes_with_core_features() -> None:
    df = generate_biased_dataset(n_samples=3200, seed=42)
    biased_model, _ = train_biased_and_fair_models(df=df, target_column="target", sensitive_column="gender")

    base = _default_profile()

    low_income = dict(base)
    low_income["income"] = 30000
    mid_income = dict(base)
    mid_income["income"] = 70000
    high_income = dict(base)
    high_income["income"] = 120000

    _, p_low_income = predict_single(biased_model, low_income)
    _, p_mid_income = predict_single(biased_model, mid_income)
    _, p_high_income = predict_single(biased_model, high_income)

    assert p_mid_income > p_low_income
    assert p_high_income > p_mid_income

    low_exp = dict(base)
    low_exp["experience_years"] = 1
    high_exp = dict(base)
    high_exp["experience_years"] = 10

    _, p_low_exp = predict_single(biased_model, low_exp)
    _, p_high_exp = predict_single(biased_model, high_exp)

    assert p_high_exp > p_low_exp

    bachelors = dict(base)
    bachelors["education"] = "bachelors"
    masters = dict(base)
    masters["education"] = "masters"
    phd = dict(base)
    phd["education"] = "phd"

    _, p_bachelors = predict_single(biased_model, bachelors)
    _, p_masters = predict_single(biased_model, masters)
    _, p_phd = predict_single(biased_model, phd)

    assert p_masters > p_bachelors
    assert p_phd > p_masters

    tech = dict(base)
    tech["profession"] = "tech"
    unemployed = dict(base)
    unemployed["profession"] = "unemployed"

    _, p_tech = predict_single(biased_model, tech)
    _, p_unemployed = predict_single(biased_model, unemployed)

    assert abs(p_tech - p_unemployed) > 0.05


def test_counterfactual_bias_detected_and_mitigation_equalizes_gender() -> None:
    df = generate_biased_dataset(n_samples=3200, seed=42)
    biased_model, fair_model = train_biased_and_fair_models(df=df, target_column="target", sensitive_column="gender")

    base = _default_profile()
    male = dict(base)
    male["gender"] = "male"
    female = dict(base)
    female["gender"] = "female"

    _, p_male = predict_single(biased_model, male)
    _, p_female = predict_single(biased_model, female)
    assert abs(p_male - p_female) > 0.02

    bias = counterfactual_bias_scores(biased_model, base, SENSITIVE_COLUMNS)
    assert bias["bias_score"] > 0.05

    _, fair_male = predict_single(fair_model, male)
    cf_male = counterfactual_average_probability(biased_model, male, SENSITIVE_COLUMNS)
    mitigated_male = combine_mitigation_probabilities(fair_male, cf_male)

    _, fair_female = predict_single(fair_model, female)
    cf_female = counterfactual_average_probability(biased_model, female, SENSITIVE_COLUMNS)
    mitigated_female = combine_mitigation_probabilities(fair_female, cf_female)

    assert abs(mitigated_male - mitigated_female) < 1e-9
    assert 0.01 < mitigated_male < 0.99


def test_bias_decomposition_endpoint_returns_attribute_breakdown() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/bias/decomposition",
            json={"features": _default_profile()},
        )

    assert response.status_code == 200
    data = response.json()

    assert "dataset_decomposition" in data
    assert "counterfactual_decomposition" in data
    assert "overall_before_disparity" in data
    assert "overall_after_disparity" in data

    for column in ["gender", "caste", "religion"]:
        assert column in data["dataset_decomposition"]
        entry = data["dataset_decomposition"][column]
        assert "before_group_rates" in entry
        assert "after_group_rates" in entry
        assert "before_disparity" in entry
        assert "after_disparity" in entry

    assert data["overall_after_disparity"] < data["overall_before_disparity"]

    gender_cf = data["counterfactual_decomposition"]["gender"]
    assert gender_cf["biased_bias_score"] > 0.0
    assert gender_cf["mitigated_bias_score"] <= gender_cf["biased_bias_score"]
