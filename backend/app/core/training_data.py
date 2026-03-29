from __future__ import annotations

import numpy as np
import pandas as pd


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_biased_dataset(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Generate a structured dataset with realistic signal and controlled detectable bias."""
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

    # Controlled bias terms: detectable but not extreme.
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
