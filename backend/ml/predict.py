"""Small inference helper for the trained weak-concept model."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

MODEL_PATH = Path(__file__).resolve().parent / "weak_concept_model.joblib"

@lru_cache(maxsize=1)
def load_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}. Run: python ml/train_model.py"
        )
    return joblib.load(MODEL_PATH)

def predict_weak_concept(
    diagnostic_message: str,
    language: str = "unknown",
    topic: str = "unknown",
    code_snippet: str = "",
) -> dict[str, Any]:
    bundle = load_bundle()
    model = bundle["pipeline"]
    text = "\n".join([
        f"language: {language}",
        f"topic: {topic}",
        f"diagnostic: {diagnostic_message}",
        f"code: {code_snippet}",
    ])
    probabilities = model.predict_proba([text])[0]
    best_index = int(probabilities.argmax())
    return {
        "weak_concept": str(model.classes_[best_index]),
        "confidence": round(float(probabilities[best_index]), 4),
        "method": "tfidf_logistic_regression",
        "dataset_kind": bundle.get("dataset_kind", "unknown"),
    }
