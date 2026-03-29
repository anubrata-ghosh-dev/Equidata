# Equidata - AI Bias Auditor Backend

Production-ready, modular FastAPI backend for quick bias auditing and simple ML modeling.

## Features

- Upload dataset CSV via API
- Detect potential sensitive columns
- Compute dataset bias using group selection-rate disparity
- Train LogisticRegression models
  - biased model: all features
  - fair model: sensitive feature removed
- Predict with biased model
- Mitigate with fair model and return before/after fairness metrics
- Optional fairlearn metrics (if installed)
- No database; all state stored in memory

## Files

- `main.py`: FastAPI endpoints and in-memory state
- `schemas.py`: Pydantic request/response schemas
- `utils.py`: CSV parsing, profiling, sensitive-column detection
- `bias.py`: fairness calculations
- `model.py`: training and prediction utilities
- `mitigation.py`: mitigation summary logic
- `sample_data.csv`: quick local test dataset

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Run the API:

   uvicorn main:app --reload

4. Open docs:

   http://127.0.0.1:8000/docs

## Quick Test Flow

1. Call `GET /sample` to load built-in sample data.
2. Call `POST /train` with:

   {
     "target_column": "target",
     "sensitive_column": "gender",
     "bias_threshold": 0.1
   }

3. Call `POST /predict` with:

   {
     "features": {
       "gender": "female",
       "race": "group_a",
       "education": "bachelors",
       "experience_years": 3
     },
     "sensitive_column": "gender"
   }

4. Call `POST /mitigate` using the same feature payload.

## Optional fairlearn

If you want extra fairness metrics:

pip install fairlearn

If fairlearn is not installed, the app still works using fallback fairness logic.
