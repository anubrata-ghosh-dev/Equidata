from __future__ import annotations

from io import StringIO
from typing import Any

import pandas as pd
from fastapi import HTTPException, UploadFile

from app.core.training_data import generate_biased_dataset


SENSITIVE_KEYWORDS = {
    "gender",
    "sex",
    "race",
    "ethnicity",
    "religion",
    "nationality",
    "age",
    "caste",
    "disability",
}

def load_sample_dataframe() -> pd.DataFrame:
    try:
        return generate_biased_dataset(n_samples=3200, seed=42)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create sample dataset: {exc}") from exc


async def read_csv_upload(file: UploadFile) -> pd.DataFrame:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        decoded = content.decode("utf-8-sig")
        df = pd.read_csv(StringIO(decoded))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV has no rows.")

    return df


def detect_sensitive_columns(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for col in df.columns:
        normalized = col.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in SENSITIVE_KEYWORDS:
            candidates.append(col)
            continue
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in normalized:
                candidates.append(col)
                break
    return candidates


def normalize_binary_target(df: pd.DataFrame, target_column: str) -> pd.Series:
    if target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Target column '{target_column}' not found.")

    target = df[target_column]
    if target.dtype == bool:
        return target.astype(int)

    if target.dtype.kind in {"i", "u", "f"}:
        unique_values = sorted(v for v in target.dropna().unique().tolist())
        if len(unique_values) > 2:
            raise HTTPException(status_code=400, detail="Target must be binary (0/1).")
        return target.fillna(0).astype(int)

    normalized = target.astype(str).str.strip().str.lower()
    mapping = {
        "1": 1,
        "0": 0,
        "true": 1,
        "false": 0,
        "yes": 1,
        "no": 0,
        "y": 1,
        "n": 0,
        "approved": 1,
        "rejected": 0,
        "positive": 1,
        "negative": 0,
    }
    mapped = normalized.map(mapping)
    if mapped.isna().any():
        raise HTTPException(
            status_code=400,
            detail="Target contains non-binary values. Use values like 0/1, yes/no, true/false.",
        )
    return mapped.astype(int)


def summarize_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    numeric_summary = df.describe(include=["number"]).to_dict() if not df.select_dtypes(include=["number"]).empty else {}
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
        "numeric_summary": numeric_summary,
    }
