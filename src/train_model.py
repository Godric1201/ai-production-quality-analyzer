from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
METRICS_PATH = OUTPUT_DIR / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = OUTPUT_DIR / "feature_importance.csv"
MODEL_PATH = OUTPUT_DIR / "scrap_prediction_model.joblib"


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


def load_data(path: Path) -> pd.DataFrame:
    """Load the production quality dataset."""
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run src/generate_data.py first."
        )

    return pd.read_csv(path)


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split dataframe into feature matrix X and target vector y."""
    feature_columns = CATEGORICAL_FEATURES + NUMERIC_FEATURES

    X = df[feature_columns]
    y = df[TARGET_COLUMN]

    return X, y


def build_model() -> Pipeline:
    """Build preprocessing and Random Forest classification pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def evaluate_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """Evaluate the model and return metrics."""
    y_pred = model.predict(X_test)

    cm = confusion_matrix(y_test, y_pred)

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "confusion_matrix": {
            "true_negative": int(cm[0][0]),
            "false_positive": int(cm[0][1]),
            "false_negative": int(cm[1][0]),
            "true_positive": int(cm[1][1]),
        },
    }

    return metrics


def get_feature_importance(model: Pipeline) -> pd.DataFrame:
    """Extract feature importances from the fitted Random Forest model."""
    preprocessor = model.named_steps["preprocessor"]
    classifier = model.named_steps["model"]

    categorical_names = (
        preprocessor.named_transformers_["categorical"]
        .get_feature_names_out(CATEGORICAL_FEATURES)
        .tolist()
    )

    feature_names = categorical_names + NUMERIC_FEATURES

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": classifier.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    importance_df["importance"] = importance_df["importance"].round(6)

    return importance_df


def save_outputs(model: Pipeline, metrics: dict, feature_importance: pd.DataFrame) -> None:
    """Save model, metrics, and feature importance outputs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(METRICS_PATH, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    feature_importance.to_csv(FEATURE_IMPORTANCE_PATH, index=False)

    joblib.dump(model, MODEL_PATH)


def print_summary(metrics: dict, feature_importance: pd.DataFrame) -> None:
    """Print model training summary."""
    print("Model training completed.")
    print("\nModel metrics:")
    for key in ["accuracy", "precision", "recall", "f1_score"]:
        print(f"  {key}: {metrics[key]}")

    print("\nConfusion matrix:")
    for key, value in metrics["confusion_matrix"].items():
        print(f"  {key}: {value}")

    print("\nTop 10 feature importances:")
    print(feature_importance.head(10).to_string(index=False))

    print(f"\nSaved metrics to: {METRICS_PATH}")
    print(f"Saved feature importances to: {FEATURE_IMPORTANCE_PATH}")
    print(f"Saved model to: {MODEL_PATH}")


def main() -> None:
    df = load_data(DATA_PATH)
    X, y = split_features_target(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = build_model()
    model.fit(X_train, y_train)

    metrics = evaluate_model(model, X_test, y_test)
    feature_importance = get_feature_importance(model)

    save_outputs(model, metrics, feature_importance)
    print_summary(metrics, feature_importance)


if __name__ == "__main__":
    main()