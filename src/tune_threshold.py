from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
MODEL_PATH = PROJECT_ROOT / "outputs" / "scrap_prediction_model.joblib"
THRESHOLD_METRICS_PATH = PROJECT_ROOT / "outputs" / "threshold_metrics.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"

TARGET_COLUMN = "scrap"

CATEGORICAL_FEATURES = [
    "machine_id",
    "shift",
    "material_batch",
]

NUMERIC_FEATURES = [
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "operator_experience_years",
    "vibration_mm_s",
    "humidity_percent",
]

FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES

THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run src/generate_data.py first."
        )

    return pd.read_csv(DATA_PATH)


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run src/train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def get_test_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Recreate the same test split used in train_model.py."""
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    return X_test, y_test


def evaluate_thresholds(y_true: pd.Series, y_probability: pd.Series) -> pd.DataFrame:
    rows = []

    for threshold in THRESHOLDS:
        y_pred = (y_probability >= threshold).astype(int)

        cm = confusion_matrix(y_true, y_pred)
        true_negative, false_positive, false_negative, true_positive = cm.ravel()

        rows.append(
            {
                "threshold": threshold,
                "accuracy": round(accuracy_score(y_true, y_pred), 4),
                "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
                "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
                "f1_score": round(f1_score(y_true, y_pred, zero_division=0), 4),
                "true_negative": int(true_negative),
                "false_positive": int(false_positive),
                "false_negative": int(false_negative),
                "true_positive": int(true_positive),
            }
        )

    return pd.DataFrame(rows)


def select_threshold(metrics_df: pd.DataFrame) -> dict:
    """
    Select a threshold for an early-warning quality use case.

    Selection logic:
    - Prefer recall >= 0.60 if possible.
    - Among those, choose the highest F1 score.
    - If no threshold reaches recall >= 0.60, choose the threshold with the highest F1 score.
    """
    recall_target = 0.60
    candidates = metrics_df[metrics_df["recall"] >= recall_target]

    if not candidates.empty:
        selected = candidates.sort_values(
            ["f1_score", "precision"],
            ascending=False,
        ).iloc[0]
        selection_reason = (
            "Selected because it reaches the recall target for an early-warning "
            "quality use case while maintaining the strongest F1 score among candidates."
        )
    else:
        selected = metrics_df.sort_values(
            ["f1_score", "recall"],
            ascending=False,
        ).iloc[0]
        selection_reason = (
            "Selected because no threshold reached the recall target; this threshold "
            "has the strongest F1 score among evaluated options."
        )

    selected_threshold = {
        "selected_threshold": float(selected["threshold"]),
        "accuracy": float(selected["accuracy"]),
        "precision": float(selected["precision"]),
        "recall": float(selected["recall"]),
        "f1_score": float(selected["f1_score"]),
        "true_negative": int(selected["true_negative"]),
        "false_positive": int(selected["false_positive"]),
        "false_negative": int(selected["false_negative"]),
        "true_positive": int(selected["true_positive"]),
        "selection_reason": selection_reason,
    }

    return selected_threshold


def save_outputs(metrics_df: pd.DataFrame, selected_threshold: dict) -> None:
    THRESHOLD_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    metrics_df.to_csv(THRESHOLD_METRICS_PATH, index=False)

    with open(SELECTED_THRESHOLD_PATH, "w", encoding="utf-8") as file:
        json.dump(selected_threshold, file, indent=2)


def print_summary(metrics_df: pd.DataFrame, selected_threshold: dict) -> None:
    print("Threshold tuning completed.")
    print("\nThreshold metrics:")
    print(metrics_df.to_string(index=False))

    print("\nSelected threshold:")
    print(f"  threshold: {selected_threshold['selected_threshold']}")
    print(f"  accuracy: {selected_threshold['accuracy']}")
    print(f"  precision: {selected_threshold['precision']}")
    print(f"  recall: {selected_threshold['recall']}")
    print(f"  f1_score: {selected_threshold['f1_score']}")
    print(f"  false_positive: {selected_threshold['false_positive']}")
    print(f"  false_negative: {selected_threshold['false_negative']}")
    print(f"\nReason: {selected_threshold['selection_reason']}")

    print(f"\nSaved threshold metrics to: {THRESHOLD_METRICS_PATH}")
    print(f"Saved selected threshold to: {SELECTED_THRESHOLD_PATH}")


def main() -> None:
    df = load_data()
    model = load_model()

    X_test, y_test = get_test_split(df)
    y_probability = model.predict_proba(X_test)[:, 1]

    metrics_df = evaluate_thresholds(y_true=y_test, y_probability=y_probability)
    selected_threshold = select_threshold(metrics_df)

    save_outputs(metrics_df, selected_threshold)
    print_summary(metrics_df, selected_threshold)


if __name__ == "__main__":
    main()