from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "outputs" / "feature_importance.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"
THRESHOLD_METRICS_PATH = PROJECT_ROOT / "outputs" / "threshold_metrics.csv"
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"

def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_inputs() -> tuple[pd.DataFrame, dict, pd.DataFrame, dict, pd.DataFrame]:
    """Load all inputs required for dashboard export."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run src/generate_data.py first."
        )

    if not FEATURE_IMPORTANCE_PATH.exists():
        raise FileNotFoundError(
            f"Feature importance file not found at {FEATURE_IMPORTANCE_PATH}. "
            "Run src/train_model.py first."
        )

    if not SELECTED_THRESHOLD_PATH.exists() or not THRESHOLD_METRICS_PATH.exists():
        raise FileNotFoundError(
            "Threshold tuning outputs not found. Run src/tune_threshold.py first."
        )

    df = pd.read_csv(DATA_PATH)
    metrics = load_json(METRICS_PATH)
    feature_importance = pd.read_csv(FEATURE_IMPORTANCE_PATH)
    selected_threshold = load_json(SELECTED_THRESHOLD_PATH)
    threshold_metrics = pd.read_csv(THRESHOLD_METRICS_PATH)

    return df, metrics, feature_importance, selected_threshold, threshold_metrics


def format_percent(value: float) -> float:
    """Convert a fraction into a rounded percentage."""
    return round(float(value) * 100, 2)


def get_scrap_rate_by_category(df: pd.DataFrame, column: str) -> list[dict]:
    """Calculate scrap rate by a categorical column."""
    grouped = (
        df.groupby(column)["scrap"]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )

    return [
        {
            "label": str(row[column]),
            "scrap_rate": format_percent(row["scrap"]),
        }
        for _, row in grouped.iterrows()
    ]


def get_temperature_bin_analysis(df: pd.DataFrame) -> list[dict]:
    """Calculate scrap rate by process temperature range."""
    temp_bins = [0, 180, 185, 190, 195, 1000]
    temp_labels = ["<180°C", "180–185°C", "185–190°C", "190–195°C", ">195°C"]

    temp_df = df.copy()
    temp_df["temperature_range"] = pd.cut(
        temp_df["temperature_c"],
        bins=temp_bins,
        labels=temp_labels,
        right=False,
    )

    grouped = (
        temp_df.groupby("temperature_range", observed=False)["scrap"]
        .mean()
        .reset_index()
    )

    return [
        {
            "label": str(row["temperature_range"]),
            "scrap_rate": format_percent(row["scrap"]),
        }
        for _, row in grouped.iterrows()
    ]


def get_risk_distribution(df: pd.DataFrame) -> list[dict]:
    """Estimate risk distribution based on engineering rules."""
    risk_df = df.copy()

    conditions = [
        risk_df["temperature_c"] > 190,
        risk_df["cycle_time_s"] > 50,
        risk_df["vibration_mm_s"] > 2.7,
        risk_df["machine_id"] == "M2",
        risk_df["shift"] == "night",
    ]

    risk_df["risk_factor_count"] = sum(condition.astype(int) for condition in conditions)

    def classify_risk(count: int) -> str:
        if count >= 3:
            return "High risk"
        if count == 2:
            return "Medium risk"
        return "Low risk"

    risk_df["risk_level"] = risk_df["risk_factor_count"].apply(classify_risk)

    grouped = (
        risk_df["risk_level"]
        .value_counts()
        .reindex(["Low risk", "Medium risk", "High risk"], fill_value=0)
        .reset_index()
    )
    grouped.columns = ["risk_level", "count"]

    return [
        {
            "label": row["risk_level"],
            "count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]


def get_top_feature_importances(feature_importance: pd.DataFrame, top_n: int = 8) -> list[dict]:
    """Return top feature importances for dashboard charts."""
    top_features = feature_importance.head(top_n).copy()

    return [
        {
            "feature": str(row["feature"]),
            "importance": round(float(row["importance"]), 4),
        }
        for _, row in top_features.iterrows()
    ]


def build_recommendations(
    df: pd.DataFrame,
    highest_risk_machine: str,
    top_features: list[dict],
) -> list[str]:
    """Generate simple engineering recommendations based on analysis results."""
    recommendations = []

    machine_scrap_rates = df.groupby("machine_id")["scrap"].mean()
    highest_machine_scrap_rate = machine_scrap_rates[highest_risk_machine] * 100
    overall_scrap_rate = df["scrap"].mean() * 100

    recommendations.append(
        f"Prioritize inspection and calibration of {highest_risk_machine}, "
        f"which shows a scrap rate of {highest_machine_scrap_rate:.2f}% compared with "
        f"the overall average of {overall_scrap_rate:.2f}%."
    )

    top_feature_names = [item["feature"] for item in top_features]

    if "vibration_mm_s" in top_feature_names:
        recommendations.append(
            "Monitor machine vibration more closely, as vibration is one of the strongest "
            "drivers of predicted scrap risk and may indicate tool wear or unstable machine condition."
        )

    if "cycle_time_s" in top_feature_names:
        recommendations.append(
            "Investigate cycle time deviations above 50 seconds, as longer cycle times may indicate "
            "process instability or machine-related delays."
        )

    if "temperature_c" in top_feature_names:
        recommendations.append(
            "Review process temperature control, especially for runs above 190°C, where scrap risk increases."
        )

    if "operator_experience_years" in top_feature_names:
        recommendations.append(
            "Use additional process guidance or checklists for less experienced operators to reduce quality variation."
        )

    recommendations.append(
        "Use this dashboard as an early warning tool, but validate all findings with real production data "
        "before making operational changes."
    )

    return recommendations

def build_threshold_summary(
    metrics: dict,
    selected_threshold: dict,
    threshold_metrics: pd.DataFrame,
) -> dict:
    """Build threshold tuning summary for dashboard visualization."""
    default_threshold_row = threshold_metrics[
        threshold_metrics["threshold"] == 0.50
    ].iloc[0]

    selected_recall = float(selected_threshold["recall"])
    default_recall = float(default_threshold_row["recall"])

    selected_false_negative = int(selected_threshold["false_negative"])
    default_false_negative = int(default_threshold_row["false_negative"])

    selected_false_positive = int(selected_threshold["false_positive"])
    default_false_positive = int(default_threshold_row["false_positive"])

    return {
        "default_threshold": 0.50,
        "selected_threshold": selected_threshold["selected_threshold"],
        "default_recall": default_recall,
        "selected_recall": selected_recall,
        "recall_improvement_percentage_points": round(
            (selected_recall - default_recall) * 100,
            2,
        ),
        "default_false_negative": default_false_negative,
        "selected_false_negative": selected_false_negative,
        "missed_scrap_reduction": default_false_negative - selected_false_negative,
        "default_false_positive": default_false_positive,
        "selected_false_positive": selected_false_positive,
        "additional_false_alarms": selected_false_positive - default_false_positive,
        "selection_reason": selected_threshold["selection_reason"],
        "metrics_by_threshold": [
            {
                "threshold": float(row["threshold"]),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1_score": float(row["f1_score"]),
                "false_positive": int(row["false_positive"]),
                "false_negative": int(row["false_negative"]),
            }
            for _, row in threshold_metrics.iterrows()
        ],
    }

def build_dashboard_data(
    df: pd.DataFrame,
    metrics: dict,
    feature_importance: pd.DataFrame,
    selected_threshold: dict,
    threshold_metrics: pd.DataFrame,
) -> dict:
    """Build the complete dashboard data payload."""
    total_parts = len(df)
    overall_scrap_rate = format_percent(df["scrap"].mean())

    scrap_by_machine = get_scrap_rate_by_category(df, "machine_id")
    highest_risk_machine = scrap_by_machine[0]["label"]

    top_features = get_top_feature_importances(feature_importance)

    dashboard_data = {
        "project": {
            "title": "AI Production Quality Analyzer",
            "subtitle": "Machine Learning Dashboard for Scrap Prediction and Process Improvement",
            "dataset_type": "Synthetic manufacturing process dataset",
        },
        "kpis": {
            "total_parts": total_parts,
            "overall_scrap_rate": overall_scrap_rate,
            "highest_risk_machine": highest_risk_machine,
            "model_f1_score": metrics["f1_score"],
            "model_accuracy": metrics["accuracy"],
            "model_precision": metrics["precision"],
            "model_recall": metrics["recall"],
        },
        "charts": {
            "scrap_rate_by_machine": scrap_by_machine,
            "scrap_rate_by_shift": get_scrap_rate_by_category(df, "shift"),
            "scrap_rate_by_temperature_range": get_temperature_bin_analysis(df),
            "risk_distribution": get_risk_distribution(df),
            "top_feature_importances": top_features,
        },
                "model": {
            "metrics": metrics,
            "confusion_matrix": metrics["confusion_matrix"],
            "threshold_tuning": build_threshold_summary(
                metrics=metrics,
                selected_threshold=selected_threshold,
                threshold_metrics=threshold_metrics,
            ),
        },
        "recommendations": build_recommendations(
            df=df,
            highest_risk_machine=highest_risk_machine,
            top_features=top_features,
        ),
         "sample_prediction": {
            "title": "New Part Risk Prediction",
            "scrap_probability": 75.85,
            "risk_level": "High",
            "input_conditions": {
                "machine_id": "M2",
                "temperature_c": 194.0,
                "pressure_bar": 6.1,
                "cycle_time_s": 52.0,
                "shift": "night",
                "material_batch": "B4",
                "operator_experience_years": 1.5,
                "vibration_mm_s": 3.2,
                "humidity_percent": 55.0,
            },
            "recommendations": [
                "Inspect M2 calibration and machine condition.",
                "Review process temperature control above 190°C.",
                "Investigate cycle time deviation above 50 seconds.",
                "Check vibration level for possible tool wear or mechanical instability.",
            ],
        },
    }

    return dashboard_data


def save_dashboard_data(data: dict) -> None:
    """Save dashboard data to JSON."""
    DASHBOARD_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(DASHBOARD_DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def print_summary(data: dict) -> None:
    """Print a compact summary after export."""
    print("Dashboard data export completed.")
    print(f"Total parts: {data['kpis']['total_parts']}")
    print(f"Overall scrap rate: {data['kpis']['overall_scrap_rate']}%")
    print(f"Highest risk machine: {data['kpis']['highest_risk_machine']}")
    print(f"Model F1 score: {data['kpis']['model_f1_score']}")
    print(f"Saved to: {DASHBOARD_DATA_PATH}")


def main() -> None:
    df, metrics, feature_importance, selected_threshold, threshold_metrics = load_inputs()
    dashboard_data = build_dashboard_data(
        df,
        metrics,
        feature_importance,
        selected_threshold,
        threshold_metrics,
    )
    save_dashboard_data(dashboard_data)
    print_summary(dashboard_data)


if __name__ == "__main__":
    main()