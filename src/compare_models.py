from pathlib import Path
import json

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
MODEL_COMPARISON_PATH = PROJECT_ROOT / "outputs" / "model_comparison.csv"
BEST_MODEL_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "best_model_summary.json"

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


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run src/generate_data.py first."
        )

    return pd.read_csv(DATA_PATH)


def get_train_test_split(df: pd.DataFrame):
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    return train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )


def build_preprocessor(scale_numeric: bool = False) -> ColumnTransformer:
    numeric_transformer = StandardScaler() if scale_numeric else "passthrough"

    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                numeric_transformer,
                NUMERIC_FEATURES,
            ),
        ]
    )


def build_models() -> dict:
    return {
        "Logistic Regression": Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(scale_numeric=True)),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(scale_numeric=False)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=8,
                        min_samples_leaf=8,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "Gradient Boosting": Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(scale_numeric=False)),
                (
                    "model",
                    GradientBoostingClassifier(
                        n_estimators=150,
                        learning_rate=0.05,
                        max_depth=3,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def evaluate_model(model, X_train, X_test, y_train, y_test) -> dict:
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    true_negative, false_positive, false_negative, true_positive = cm.ravel()

    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "true_negative": int(true_negative),
        "false_positive": int(false_positive),
        "false_negative": int(false_negative),
        "true_positive": int(true_positive),
    }


def compare_models(df: pd.DataFrame) -> pd.DataFrame:
    X_train, X_test, y_train, y_test = get_train_test_split(df)
    models = build_models()

    rows = []

    for model_name, model in models.items():
        print(f"Training and evaluating: {model_name}")
        metrics = evaluate_model(model, X_train, X_test, y_train, y_test)

        rows.append(
            {
                "model": model_name,
                **metrics,
            }
        )

    comparison_df = pd.DataFrame(rows).sort_values(
        ["f1_score", "recall", "precision"],
        ascending=False,
    )

    return comparison_df


def build_best_model_summary(comparison_df: pd.DataFrame) -> dict:
    best_row = comparison_df.iloc[0].to_dict()

    production_model = "Random Forest"
    production_row = comparison_df[comparison_df["model"] == production_model].iloc[0].to_dict()

    return {
        "best_model_by_f1": {
            "model": best_row["model"],
            "accuracy": best_row["accuracy"],
            "precision": best_row["precision"],
            "recall": best_row["recall"],
            "f1_score": best_row["f1_score"],
        },
        "selected_production_model": {
            "model": production_model,
            "accuracy": production_row["accuracy"],
            "precision": production_row["precision"],
            "recall": production_row["recall"],
            "f1_score": production_row["f1_score"],
            "selection_reason": (
                "Random Forest is kept as the production model because it provides "
                "a strong balance of performance, robustness on tabular data, and "
                "interpretable feature importance values for engineering analysis."
            ),
        },
    }


def save_outputs(comparison_df: pd.DataFrame, best_model_summary: dict) -> None:
    MODEL_COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)

    comparison_df.to_csv(MODEL_COMPARISON_PATH, index=False)

    with open(BEST_MODEL_SUMMARY_PATH, "w", encoding="utf-8") as file:
        json.dump(best_model_summary, file, indent=2)


def print_summary(comparison_df: pd.DataFrame, best_model_summary: dict) -> None:
    print("\nModel comparison completed.")
    print("\nComparison table:")
    print(comparison_df.to_string(index=False))

    print("\nBest model by F1 score:")
    best = best_model_summary["best_model_by_f1"]
    print(f"  Model: {best['model']}")
    print(f"  F1 score: {best['f1_score']}")
    print(f"  Recall: {best['recall']}")
    print(f"  Precision: {best['precision']}")

    selected = best_model_summary["selected_production_model"]
    print("\nSelected production model:")
    print(f"  Model: {selected['model']}")
    print(f"  Reason: {selected['selection_reason']}")

    print(f"\nSaved comparison to: {MODEL_COMPARISON_PATH}")
    print(f"Saved best model summary to: {BEST_MODEL_SUMMARY_PATH}")


def main() -> None:
    df = load_data()
    comparison_df = compare_models(df)
    best_model_summary = build_best_model_summary(comparison_df)

    save_outputs(comparison_df, best_model_summary)
    print_summary(comparison_df, best_model_summary)


if __name__ == "__main__":
    main()