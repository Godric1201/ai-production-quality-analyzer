from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from train_model import (
    DATA_PATH,
    MODEL_PATH,
    TARGET_COLUMN,
    split_features_target,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SUMMARY_PATH = OUTPUT_DIR / "model_evaluation_summary.json"
RISK_BAND_PATH = OUTPUT_DIR / "risk_band_evaluation.csv"
REPORT_PATH = OUTPUT_DIR / "model_evaluation_report.md"
SELECTED_THRESHOLD_PATH = OUTPUT_DIR / "selected_threshold.json"
COST_OPTIMIZATION_PATH = OUTPUT_DIR / "cost_optimized_threshold.json"
THRESHOLD_COST_PATH = OUTPUT_DIR / "threshold_cost_analysis.csv"

RISK_BANDS = [
    {
        "label": "Low risk",
        "lower": 0.0,
        "upper": 0.30,
        "priority": "Standard monitoring",
    },
    {
        "label": "Medium risk",
        "lower": 0.30,
        "upper": 0.50,
        "priority": "Additional monitoring",
    },
    {
        "label": "High risk",
        "lower": 0.50,
        "upper": 1.0000001,
        "priority": "Engineering review priority",
    },
]


def load_json(path: Path, fallback: dict | None = None) -> dict:
    """Load a JSON file, returning fallback when an optional output is absent."""
    if not path.exists():
        return fallback or {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_model_inputs() -> tuple[pd.DataFrame, pd.Series, object]:
    """Load the trained model and recreate the model test split."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}.")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Trained model not found at {MODEL_PATH}.")

    df = pd.read_csv(DATA_PATH)
    X, y = split_features_target(df)
    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )
    model = joblib.load(MODEL_PATH)
    return X_test, y_test, model


def assign_risk_band(probability: float) -> dict:
    """Assign one predicted probability to a configured risk band."""
    for band in RISK_BANDS:
        if band["lower"] <= probability < band["upper"]:
            return band

    return RISK_BANDS[-1]


def build_risk_band_evaluation(
    y_test: pd.Series,
    probabilities: list[float],
) -> pd.DataFrame:
    """Aggregate actual scrap outcomes by predicted probability band."""
    evaluation_df = pd.DataFrame(
        {
            "actual_scrap": y_test.to_numpy(),
            "predicted_probability": probabilities,
        }
    )
    band_rows = []

    for band in RISK_BANDS:
        mask = evaluation_df["predicted_probability"].apply(
            lambda value: band["lower"] <= value < band["upper"]
        )
        band_df = evaluation_df[mask]
        row_count = len(band_df)
        actual_scrap_count = int(band_df["actual_scrap"].sum()) if row_count else 0
        actual_scrap_rate = (
            round(float(band_df["actual_scrap"].mean()), 4) if row_count else 0.0
        )
        average_predicted_risk = (
            round(float(band_df["predicted_probability"].mean()), 4)
            if row_count
            else 0.0
        )

        band_rows.append(
            {
                "risk_band": band["label"],
                "row_count": row_count,
                "actual_scrap_count": actual_scrap_count,
                "actual_scrap_rate": actual_scrap_rate,
                "average_predicted_risk": average_predicted_risk,
                "review_priority": band["priority"],
            }
        )

    return pd.DataFrame(band_rows)


def build_summary(y_test: pd.Series, probabilities: list[float]) -> dict:
    """Build compact model evaluation metrics and interpretation."""
    selected_threshold = load_json(SELECTED_THRESHOLD_PATH, {}).get("selected_threshold")
    cost_optimized = load_json(COST_OPTIMIZATION_PATH, {}).get(
        "cost_optimized_threshold",
        {},
    )

    summary = {
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(y_test, probabilities)), 4),
        "baseline_scrap_rate": round(float(y_test.mean()), 4),
        "selected_threshold": selected_threshold,
        "cost_optimized_threshold": cost_optimized.get("threshold"),
        "model_role": "early_warning_decision_support",
        "interpretation": (
            "The model is useful as an early-warning signal for engineering review, "
            "but its precision and recall trade-offs mean it should not be treated as "
            "an autonomous release or certification decision."
        ),
    }
    return summary


def build_threshold_tradeoff_rows(limit: int = 5) -> list[dict]:
    """Return compact threshold cost rows for report and dashboard use."""
    if not THRESHOLD_COST_PATH.exists():
        return []

    threshold_df = pd.read_csv(THRESHOLD_COST_PATH)
    threshold_df = threshold_df.sort_values("total_cost").head(limit)
    return [
        {
            "threshold": round(float(row["threshold"]), 2),
            "recall": round(float(row["recall"]), 4),
            "false_positive": int(row["false_positive"]),
            "false_negative": int(row["false_negative"]),
            "total_cost": round(float(row["total_cost"]), 2),
        }
        for _, row in threshold_df.iterrows()
    ]


def write_summary(summary: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)


def write_report(
    summary: dict,
    risk_band_df: pd.DataFrame,
    threshold_rows: list[dict],
) -> None:
    """Write a concise markdown evaluation report."""
    lines = [
        "# Model Evaluation & Risk Bands",
        "",
        "This report evaluates the scrap-risk model as an early-warning signal for engineering review.",
        "",
        "## Summary",
        "",
        f"- ROC-AUC: {summary['roc_auc']}",
        f"- PR-AUC: {summary['pr_auc']}",
        f"- Baseline scrap rate: {summary['baseline_scrap_rate']}",
        f"- Selected threshold: {summary.get('selected_threshold')}",
        f"- Cost-optimized threshold: {summary.get('cost_optimized_threshold')}",
        f"- Model role: {summary['model_role']}",
        "",
        "## Risk Bands",
        "",
        risk_band_df.to_markdown(index=False),
        "",
        "## Threshold Trade-off",
        "",
        (
            "Lower thresholds catch more scrap but create more false alarms. Higher thresholds "
            "reduce false alarms but miss more scrap. The cost-optimized threshold is used as a "
            "decision-support trade-off, not as a final acceptance rule."
        ),
        "",
        pd.DataFrame(threshold_rows).to_markdown(index=False) if threshold_rows else "No threshold cost rows available.",
        "",
        "## Interpretation",
        "",
        summary["interpretation"],
        "",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def print_summary(summary: dict, risk_band_df: pd.DataFrame) -> None:
    print("Model risk evaluation completed.")
    print(f"ROC-AUC: {summary['roc_auc']}")
    print(f"PR-AUC: {summary['pr_auc']}")
    print(f"Baseline scrap rate: {summary['baseline_scrap_rate']}")
    print("\nRisk band evaluation:")
    print(risk_band_df.to_string(index=False))
    print(f"\nSaved summary to: {SUMMARY_PATH}")
    print(f"Saved risk bands to: {RISK_BAND_PATH}")
    print(f"Saved report to: {REPORT_PATH}")


def main() -> None:
    X_test, y_test, model = load_model_inputs()
    probabilities = model.predict_proba(X_test)[:, 1].tolist()

    summary = build_summary(y_test, probabilities)
    risk_band_df = build_risk_band_evaluation(y_test, probabilities)
    threshold_rows = build_threshold_tradeoff_rows()

    write_summary(summary)
    risk_band_df.to_csv(RISK_BAND_PATH, index=False)
    write_report(summary, risk_band_df, threshold_rows)
    print_summary(summary, risk_band_df)


if __name__ == "__main__":
    main()
