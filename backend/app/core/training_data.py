from __future__ import annotations

import numpy as np
import pandas as pd


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def calculate_emi(loan_amount: np.ndarray, annual_interest_rate: np.ndarray, tenure_months: int = 60) -> np.ndarray:
    monthly_rate = annual_interest_rate / (12.0 * 100.0)
    # Avoid division instability for near-zero rates.
    monthly_rate = np.clip(monthly_rate, 1e-6, None)
    numerator = loan_amount * monthly_rate * np.power(1 + monthly_rate, tenure_months)
    denominator = np.power(1 + monthly_rate, tenure_months) - 1
    return numerator / denominator


def generate_hiring_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    experience_years = np.clip(rng.normal(5.5, 3.2, size=n_samples), 0, 20)
    education_level = rng.choice(["high_school", "bachelors", "masters", "phd"], size=n_samples, p=[0.08, 0.56, 0.28, 0.08])
    college_tier = rng.choice(["IIT", "NIT", "Other"], size=n_samples, p=[0.12, 0.22, 0.66])
    skills_score = np.clip(rng.normal(68, 15, size=n_samples), 20, 100)

    edu_salary_bonus = np.array([{"high_school": -12000, "bachelors": 0, "masters": 18000, "phd": 30000}[e] for e in education_level])
    college_salary_bonus = np.array([{"IIT": 35000, "NIT": 20000, "Other": 0}[c] for c in college_tier])
    expected_salary = np.clip(25000 + 4500 * experience_years + 900 * skills_score + edu_salary_bonus + college_salary_bonus + rng.normal(0, 15000, size=n_samples), 25000, 320000)

    gender = rng.choice(["male", "female"], size=n_samples, p=[0.55, 0.45])
    caste = rng.choice(["general", "obc", "sc", "st"], size=n_samples, p=[0.34, 0.39, 0.17, 0.10])
    religion = rng.choice(["hindu", "muslim", "christian", "other"], size=n_samples, p=[0.58, 0.21, 0.15, 0.06])

    edu_score = np.array([{"high_school": -0.45, "bachelors": 0.0, "masters": 0.28, "phd": 0.42}[e] for e in education_level])
    college_score = np.array([{"IIT": 0.24, "NIT": 0.12, "Other": 0.0}[c] for c in college_tier])

    exp_norm = np.clip(experience_years / 20.0, 0.0, 1.0)
    skills_norm = np.clip(skills_score / 100.0, 0.0, 1.0)
    salary_norm = np.clip((expected_salary - 25000.0) / (320000.0 - 25000.0), 0.0, 1.0)

    gender_bias = np.array([{"male": 0.09, "female": -0.09}[g] for g in gender])
    caste_bias = np.array([{"general": 0.10, "obc": 0.02, "sc": -0.06, "st": -0.09}[c] for c in caste])
    religion_bias = np.array([{"hindu": 0.05, "muslim": -0.05, "christian": -0.01, "other": -0.03}[r] for r in religion])

    stochastic_noise = rng.normal(0.0, 0.12, size=n_samples)
    base_signal = (
        0.34 * exp_norm
        + 0.44 * skills_norm
        + 0.22 * edu_score
        + 0.20 * college_score
        - 0.28 * salary_norm
        + stochastic_noise
    )

    linear = (base_signal - np.median(base_signal)) + gender_bias + caste_bias + religion_bias
    prob = np.clip(_sigmoid(2.1 * linear), 0.01, 0.99)
    target = rng.binomial(1, prob, size=n_samples)

    return pd.DataFrame(
        {
            "experience_years": np.round(experience_years, 1),
            "education_level": education_level,
            "college_tier": college_tier,
            "skills_score": np.round(skills_score, 1),
            "expected_salary": expected_salary.round(0).astype(int),
            "gender": gender,
            "caste": caste,
            "religion": religion,
            "target": target.astype(int),
        }
    )


def generate_loan_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    loan_amount = np.clip(rng.normal(900000, 420000, size=n_samples), 100000, 3000000)
    interest_rate = np.clip(rng.normal(11.5, 2.8, size=n_samples), 6.0, 22.0)
    profession = rng.choice(["salaried", "self_employed", "business", "student"], size=n_samples, p=[0.52, 0.21, 0.17, 0.10])
    monthly_income = np.clip(rng.normal(65000, 26000, size=n_samples), 12000, 260000)
    emi = calculate_emi(loan_amount, interest_rate)

    gender = rng.choice(["male", "female"], size=n_samples, p=[0.56, 0.44])
    caste = rng.choice(["general", "obc", "sc", "st"], size=n_samples, p=[0.33, 0.40, 0.17, 0.10])
    religion = rng.choice(["hindu", "muslim", "christian", "other"], size=n_samples, p=[0.58, 0.22, 0.14, 0.06])

    dti = emi / np.clip(monthly_income, 1.0, None)
    profession_score = np.array([{"salaried": 0.22, "self_employed": 0.02, "business": 0.12, "student": -0.35}[p] for p in profession])

    income_norm = np.clip((monthly_income - 12000.0) / (260000.0 - 12000.0), 0.0, 1.0)
    dti_norm = np.clip((dti - 0.10) / (1.20 - 0.10), 0.0, 1.0)
    rate_norm = np.clip((interest_rate - 6.0) / (22.0 - 6.0), 0.0, 1.0)

    gender_bias = np.array([{"male": 0.08, "female": -0.08}[g] for g in gender])
    caste_bias = np.array([{"general": 0.11, "obc": 0.03, "sc": -0.07, "st": -0.10}[c] for c in caste])
    religion_bias = np.array([{"hindu": 0.05, "muslim": -0.05, "christian": -0.01, "other": -0.03}[r] for r in religion])

    stochastic_noise = rng.normal(0.0, 0.13, size=n_samples)
    base_signal = (
        0.52 * income_norm
        - 0.58 * dti_norm
        - 0.16 * rate_norm
        + 0.22 * profession_score
        + stochastic_noise
    )

    linear = (base_signal - np.median(base_signal)) + gender_bias + caste_bias + religion_bias
    prob = np.clip(_sigmoid(2.2 * linear), 0.01, 0.99)
    target = rng.binomial(1, prob, size=n_samples)

    return pd.DataFrame(
        {
            "loan_amount": loan_amount.round(0).astype(int),
            "interest_rate": np.round(interest_rate, 2),
            "monthly_income": monthly_income.round(0).astype(int),
            "profession": profession,
            "emi": np.round(emi, 2),
            "gender": gender,
            "caste": caste,
            "religion": religion,
            "target": target.astype(int),
        }
    )


def generate_college_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    entrance_score = np.clip(rng.normal(71, 14, size=n_samples), 0, 100)
    family_income = np.clip(rng.normal(520000, 250000, size=n_samples), 60000, 2200000)
    parents_education = rng.choice(["none", "school", "graduate", "postgraduate"], size=n_samples, p=[0.05, 0.39, 0.38, 0.18])
    previous_academic_score = np.clip(rng.normal(74, 12, size=n_samples), 35, 100)

    gender = rng.choice(["male", "female"], size=n_samples, p=[0.53, 0.47])
    caste = rng.choice(["general", "obc", "sc", "st"], size=n_samples, p=[0.35, 0.38, 0.17, 0.10])
    religion = rng.choice(["hindu", "muslim", "christian", "other"], size=n_samples, p=[0.58, 0.2, 0.16, 0.06])

    parent_score = np.array([{"none": -0.18, "school": 0.0, "graduate": 0.10, "postgraduate": 0.18}[p] for p in parents_education])
    income_norm = np.clip((family_income - 60000.0) / (2200000.0 - 60000.0), 0.0, 1.0)
    entrance_norm = np.clip(entrance_score / 100.0, 0.0, 1.0)
    prev_score_norm = np.clip(previous_academic_score / 100.0, 0.0, 1.0)

    gender_bias = np.array([{"male": 0.07, "female": -0.07}[g] for g in gender])
    caste_bias = np.array([{"general": 0.10, "obc": 0.02, "sc": -0.08, "st": -0.11}[c] for c in caste])
    religion_bias = np.array([{"hindu": 0.04, "muslim": -0.04, "christian": -0.01, "other": -0.02}[r] for r in religion])

    stochastic_noise = rng.normal(0.0, 0.12, size=n_samples)
    base_signal = (
        0.46 * entrance_norm
        + 0.40 * prev_score_norm
        + 0.12 * parent_score
        + 0.10 * income_norm
        + stochastic_noise
    )

    linear = (base_signal - np.median(base_signal)) + gender_bias + caste_bias + religion_bias
    prob = np.clip(_sigmoid(2.0 * linear), 0.01, 0.99)
    target = rng.binomial(1, prob, size=n_samples)

    return pd.DataFrame(
        {
            "entrance_score": np.round(entrance_score, 1),
            "family_income": family_income.round(0).astype(int),
            "parents_education": parents_education,
            "previous_academic_score": np.round(previous_academic_score, 1),
            "gender": gender,
            "caste": caste,
            "religion": religion,
            "target": target.astype(int),
        }
    )


def generate_scenario_dataset(scenario: str, n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    normalized = scenario.strip().lower()
    if normalized == "hiring":
        return generate_hiring_dataset(n_samples=n_samples, seed=seed)
    if normalized == "loan_approval":
        return generate_loan_dataset(n_samples=n_samples, seed=seed)
    if normalized == "college_admission":
        return generate_college_dataset(n_samples=n_samples, seed=seed)
    raise ValueError(f"Unsupported scenario '{scenario}'.")


def generate_biased_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Backward-compatible legacy dataset used by existing tests and utilities."""
    if n_samples < 2000 or n_samples > 5000:
        raise ValueError("n_samples must be between 2000 and 5000.")

    rng = np.random.default_rng(seed)

    gender = rng.choice(["male", "female"], size=n_samples, p=[0.52, 0.48])
    race = rng.choice(["group_a", "group_b"], size=n_samples, p=[0.55, 0.45])
    religion = rng.choice(["hindu", "muslim", "christian", "other"], size=n_samples, p=[0.58, 0.2, 0.16, 0.06])
    caste = rng.choice(["general", "obc", "sc", "st"], size=n_samples, p=[0.35, 0.38, 0.17, 0.1])
    education = rng.choice(["bachelors", "masters", "phd"], size=n_samples, p=[0.57, 0.31, 0.12])
    profession = rng.choice(
        ["tech", "non-tech", "business", "unemployed"],
        size=n_samples,
        p=[0.31, 0.39, 0.18, 0.12],
    )

    education_year_bonus = {"bachelors": 2.0, "masters": 4.5, "phd": 6.5}
    profession_year_bonus = {"tech": 2.0, "non-tech": 1.2, "business": 1.7, "unemployed": -1.8}
    exp_noise = rng.normal(0, 2.2, size=n_samples)
    experience_years = np.array(
        [
            4.0 + education_year_bonus[edu] + profession_year_bonus[prof] + noise
            for edu, prof, noise in zip(education, profession, exp_noise)
        ]
    )
    experience_years = np.clip(experience_years, 0, 25)

    education_income_bonus = {"bachelors": 12000, "masters": 30000, "phd": 52000}
    profession_income_bonus = {"tech": 26000, "non-tech": 10000, "business": 20000, "unemployed": -22000}
    base_income = 26000 + 2600 * experience_years
    income_noise = rng.normal(0, 8500, size=n_samples)
    income = np.array(
        [
            base + education_income_bonus[edu] + profession_income_bonus[prof] + noise
            for base, edu, prof, noise in zip(base_income, education, profession, income_noise)
        ]
    )
    income = np.clip(income, 12000, 220000).round(0)

    edu_score = np.array([{"bachelors": 0.0, "masters": 0.45, "phd": 0.85}[e] for e in education])
    prof_score = np.array([{"tech": 0.35, "non-tech": 0.05, "business": 0.2, "unemployed": -0.9}[p] for p in profession])
    exp_score = (experience_years - 5.0) / 6.0
    income_score = (income - 40000.0) / 32000.0
    race_score = np.array([{"group_a": 0.04, "group_b": 0.0}[r] for r in race])

    gender_bias = np.array([{"male": 0.11, "female": -0.11}[g] for g in gender])
    caste_bias = np.array([{"general": 0.12, "obc": 0.03, "sc": -0.07, "st": -0.1}[c] for c in caste])
    religion_bias = np.array([{"hindu": 0.06, "muslim": -0.05, "christian": -0.01, "other": -0.04}[r] for r in religion])

    linear = -0.6 + 0.55 * edu_score + 0.45 * exp_score + 0.55 * income_score + 0.25 * prof_score + race_score
    linear = linear + gender_bias + caste_bias + religion_bias
    prob = _sigmoid(linear)
    target = rng.binomial(1, prob, size=n_samples)

    df = pd.DataFrame(
        {
            "gender": gender,
            "race": race,
            "religion": religion,
            "caste": caste,
            "education": education,
            "profession": profession,
            "income": income.astype(int),
            "experience_years": np.round(experience_years, 1),
            "target": target.astype(int),
        }
    )
    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
