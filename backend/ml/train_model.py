"""Train a supervised baseline classifier for coding-error categories.

Dataset rows are curated synthetic examples for a reproducible prototype.
They are not real student submissions and must not be presented as such.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "weak_concept_training.csv"
MODEL_PATH = BASE_DIR / "weak_concept_model.joblib"
METRICS_PATH = BASE_DIR / "training_metrics.json"

REQUIRED_COLUMNS = {
    "language", "topic", "diagnostic_message", "code_snippet", "weak_concept"
}

def build_text(row: pd.Series) -> str:
    return "\n".join([
        f"language: {row['language']}",
        f"topic: {row['topic']}",
        f"diagnostic: {row['diagnostic_message']}",
        f"code: {row['code_snippet']}",
    ])

def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found: {DATA_PATH}")

    frame = pd.read_csv(DATA_PATH).fillna("")
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    frame = frame.drop_duplicates(subset=["language", "topic", "diagnostic_message", "code_snippet", "weak_concept"])
    frame["text"] = frame.apply(build_text, axis=1)

    counts = frame["weak_concept"].value_counts()
    if len(counts) < 2 or counts.min() < 4:
        raise ValueError("At least 4 examples per class and 2 classes are required.")

    X_train, X_test, y_train, y_test = train_test_split(
        frame["text"], frame["weak_concept"],
        test_size=0.25, random_state=42, stratify=frame["weak_concept"]
    )

    features = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_features=20000)),
        ("char_tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=1, max_features=40000)),
    ])
    pipeline = Pipeline([
        ("features", features),
        ("classifier", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42)),
    ])
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    labels = sorted(frame["weak_concept"].unique().tolist())
    report = classification_report(y_test, predictions, labels=labels, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_test, predictions, labels=labels).tolist()

    bundle = {
        "pipeline": pipeline,
        "labels": labels,
        "model_name": "tfidf_logistic_regression",
        "dataset_kind": "curated_synthetic_starter_examples",
        "dataset_rows": int(len(frame)),
    }
    joblib.dump(bundle, MODEL_PATH)

    metrics = {
        "model_name": bundle["model_name"],
        "dataset_kind": bundle["dataset_kind"],
        "dataset_rows": int(len(frame)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "class_distribution": {k: int(v) for k, v in counts.items()},
        "accuracy_on_held_out_synthetic_examples": round(float(accuracy), 4),
        "classification_report": report,
        "confusion_matrix_labels": labels,
        "confusion_matrix": matrix,
        "random_state": 42,
        "warning": "This is a small synthetic starter dataset. Metrics are for pipeline smoke-testing only; do not claim real-world accuracy or production readiness.",
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\nTraining completed.")
    print(f"Dataset rows: {len(frame)}")
    print(f"Training rows: {len(X_train)} | Test rows: {len(X_test)}")
    print(f"Held-out synthetic accuracy: {accuracy:.3f}")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")
    print("\nClassification report:")
    print(classification_report(y_test, predictions, zero_division=0))
    print("\nIMPORTANT: dataset is curated synthetic starter data, not real student data.")

if __name__ == "__main__":
    main()
