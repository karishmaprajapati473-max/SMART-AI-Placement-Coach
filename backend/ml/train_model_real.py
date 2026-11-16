from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import pandas as pd

from ml.data_collection import load_approved_samples_for_training
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "weak_concept_model_real.joblib"
METRICS_PATH = BASE_DIR / "real_training_metrics.json"

WEAK_CONCEPTS = [
    "Syntax & Indentation",
    "Variables & Naming",
    "Data Types & Input Handling",
    "Arrays & Indexing",
    "Loops & Iteration",
    "Recursion",
    "Function Usage",
    "Algorithm Efficiency",
]

MIN_SAMPLES_PER_CLASS = 30
MIN_STUDENTS_PER_CLASS = 5


def build_text(row):
    return "\n".join([
        f"language: {row['language']}",
        f"topic: {row['topic']}",
        f"diagnostic: {row['diagnostic_message']}",
        f"code: {row['code_snippet']}",
    ])


def main():
    rows = load_approved_samples_for_training()

    if not rows:
        print("No human-approved real samples available.")
        print("No model trained. Existing synthetic model remains unchanged.")
        return

    frame = pd.DataFrame([dict(row) for row in rows]).fillna("")

    frame = frame[
        frame["weak_concept"].isin(WEAK_CONCEPTS)
    ].copy()

    frame["text"] = frame.apply(build_text, axis=1)
    frame = frame[frame["text"].str.strip() != ""]

    frame = frame.drop_duplicates(
        subset=[
            "language", "topic", "diagnostic_message",
            "code_snippet", "weak_concept"
        ]
    ).reset_index(drop=True)

    print("\n=== REAL DATASET READINESS ===")
    ready = True

    for concept in WEAK_CONCEPTS:
        subset = frame[frame["weak_concept"] == concept]
        samples = len(subset)
        students = subset["user_id"].nunique()

        print(f"{concept}: {samples} samples | {students} students")

        if samples < MIN_SAMPLES_PER_CLASS:
            ready = False
        if students < MIN_STUDENTS_PER_CLASS:
            ready = False

    if not ready:
        print("\nDataset is not ready for real-data validation.")
        print("Required: at least 30 samples and 5 students per category.")
        print("No model trained. Existing synthetic model remains unchanged.")
        return

    X = frame["text"]
    y = frame["weak_concept"]
    groups = frame["user_id"]

    splitter = GroupShuffleSplit(
        n_splits=500,
        test_size=0.30,
        random_state=42
    )

    selected_split = None

    for train_idx, test_idx in splitter.split(X, y, groups):
        train_labels = set(y.iloc[train_idx])
        test_labels = set(y.iloc[test_idx])

        if train_labels == set(WEAK_CONCEPTS) and test_labels == set(WEAK_CONCEPTS):
            selected_split = (train_idx, test_idx)
            break

    if selected_split is None:
        print("\nCould not create a student-separated split")
        print("containing all 8 categories in both train and test.")
        print("Collect more approved samples from more students.")
        return

    train_idx, test_idx = selected_split

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    features = FeatureUnion([
        (
            "word_tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
                max_features=20000
            )
        ),
        (
            "char_tfidf",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                sublinear_tf=True,
                min_df=1,
                max_features=40000
            )
        ),
    ])

    pipeline = Pipeline([
        ("features", features),
        (
            "classifier",
            LogisticRegression(
                max_iter=3000,
                class_weight="balanced",
                random_state=42
            )
        ),
    ])

    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    report = classification_report(
        y_test,
        predictions,
        labels=WEAK_CONCEPTS,
        output_dict=True,
        zero_division=0
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=WEAK_CONCEPTS
    ).tolist()

    metrics = {
        "dataset_kind": "human_reviewed_real_student_submissions",
        "total_approved_unique_samples": len(frame),
        "train_samples": len(train_idx),
        "test_samples": len(test_idx),
        "train_students": int(groups.iloc[train_idx].nunique()),
        "test_students": int(groups.iloc[test_idx].nunique()),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_precision": float(
            precision_score(y_test, predictions, labels=WEAK_CONCEPTS,
                            average="macro", zero_division=0)
        ),
        "macro_recall": float(
            recall_score(y_test, predictions, labels=WEAK_CONCEPTS,
                         average="macro", zero_division=0)
        ),
        "macro_f1": float(
            f1_score(y_test, predictions, labels=WEAK_CONCEPTS,
                     average="macro", zero_division=0)
        ),
        "classification_report": report,
        "confusion_matrix_labels": WEAK_CONCEPTS,
        "confusion_matrix": matrix,
        "split_method": "GroupShuffleSplit_by_student",
        "random_state": 42,
        "warning": "Pilot validation only. Results are not proof of production readiness."
    }

    joblib.dump({
        "pipeline": pipeline,
        "labels": WEAK_CONCEPTS,
        "model_name": "real_student_tfidf_logistic_regression",
        "dataset_kind": "human_reviewed_real_student_submissions",
        "dataset_rows": len(frame),
    }, MODEL_PATH)

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8"
    )

    print("\n=== REAL STUDENT VALIDATION RESULTS ===")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"Macro Recall: {metrics['macro_recall']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Training students: {metrics['train_students']}")
    print(f"Testing students: {metrics['test_students']}")
    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Metrics saved: {METRICS_PATH}")


if __name__ == "__main__":
    main()
