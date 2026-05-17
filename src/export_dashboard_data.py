from pathlib import Path
import json

import joblib
import pandas as pd

from root_cause_analysis import analyze_root_causes
from train_model import CATEGORICAL_FEATURES, MODEL_PATH, NUMERIC_FEATURES


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "outputs" / "feature_importance.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"
THRESHOLD_METRICS_PATH = PROJECT_ROOT / "outputs" / "threshold_metrics.csv"
COST_OPTIMIZATION_PATH = PROJECT_ROOT / "outputs" / "cost_optimized_threshold.json"
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
PREDICTION_RESULTS_PATH = PROJECT_ROOT / "outputs" / "prediction_results.csv"
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
MAX_PREDICTION_EXPORT_ROWS = 25

def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_inputs() -> tuple[pd.DataFrame, dict, pd.DataFrame, dict, pd.DataFrame, dict, object]:
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
    if not COST_OPTIMIZATION_PATH.exists():
        raise FileNotFoundError(
            "Cost optimization output not found. Run src/optimize_threshold_cost.py first."
        )
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run src/train_model.py first."
        )

    df = pd.read_csv(DATA_PATH)
    metrics = load_json(METRICS_PATH)
    feature_importance = pd.read_csv(FEATURE_IMPORTANCE_PATH)
    selected_threshold = load_json(SELECTED_THRESHOLD_PATH)
    threshold_metrics = pd.read_csv(THRESHOLD_METRICS_PATH)
    cost_optimization = load_json(COST_OPTIMIZATION_PATH)
    model = joblib.load(MODEL_PATH)

    return df, metrics, feature_importance, selected_threshold, threshold_metrics, cost_optimization, model


def format_percent(value: float) -> float:
    """Convert a fraction into a rounded percentage."""
    return round(float(value) * 100, 2)


def classify_predicted_risk(probability: float, threshold: float) -> str:
    """Classify a prediction as elevated or low risk using the selected threshold."""
    if probability >= threshold:
        return "High"
    return "Low"


def format_recommendations(recommendations: list[str]) -> str:
    """Format recommendation text for compact dataframe and JSON export."""
    return "; ".join(recommendations)


def analyze_prediction_row(row: pd.Series) -> pd.Series:
    """Run root cause analysis for one elevated-risk prediction row."""
    analysis = analyze_root_causes(row)

    return pd.Series(
        {
            "root_cause_summary": analysis["summary"],
            "engineering_recommendations": format_recommendations(
                analysis["recommendations"]
            ),
        }
    )


def build_prediction_results(
    df: pd.DataFrame,
    model: object,
    selected_threshold: dict,
) -> pd.DataFrame:
    """Add model predictions and root cause analysis to production rows."""
    results_df = df.copy()
    threshold = float(selected_threshold["selected_threshold"])

    probabilities = model.predict_proba(results_df[FEATURE_COLUMNS])[:, 1]
    results_df["scrap_probability"] = probabilities.round(4)
    results_df["predicted_scrap_risk"] = results_df["scrap_probability"].apply(
        lambda probability: classify_predicted_risk(probability, threshold)
    )
    results_df["root_cause_summary"] = ""
    results_df["engineering_recommendations"] = ""

    elevated_risk_mask = results_df["scrap_probability"] >= threshold
    if elevated_risk_mask.any():
        root_cause_columns = results_df.loc[elevated_risk_mask].apply(
            analyze_prediction_row,
            axis=1,
        )
        results_df.loc[
            elevated_risk_mask,
            ["root_cause_summary", "engineering_recommendations"],
        ] = root_cause_columns

    return results_df


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

def build_cost_optimization_summary(cost_optimization: dict) -> dict:
    """Build cost-based threshold optimization summary for dashboard visualization."""
    assumptions = cost_optimization["cost_assumptions"]
    optimized = cost_optimization["cost_optimized_threshold"]
    comparison = cost_optimization["comparison"]

    return {
        "missed_scrap_cost": assumptions["missed_scrap_cost"],
        "false_alarm_cost": assumptions["false_alarm_cost"],
        "currency": assumptions["currency"],
        "cost_optimized_threshold": optimized["threshold"],
        "optimized_total_cost": optimized["total_cost"],
        "optimized_recall": optimized["recall"],
        "optimized_false_negative": optimized["false_negative"],
        "optimized_false_positive": optimized["false_positive"],
        "default_total_cost": comparison["default_threshold_0_50"]["total_cost"],
        "recall_tuned_total_cost": comparison["recall_tuned_threshold_0_30"]["total_cost"],
        "cost_savings_vs_default": comparison["cost_savings_vs_default"],
        "selection_reason": cost_optimization["selection_reason"],
    }


def get_prediction_results_export(prediction_results: pd.DataFrame) -> list[dict]:
    """Return a compact high-risk prediction sample for JSON export."""
    export_columns = [
        "part_id",
        "machine_id",
        "shift",
        "material_batch",
        "temperature_c",
        "pressure_bar",
        "cycle_time_s",
        "operator_experience_years",
        "vibration_mm_s",
        "humidity_percent",
        "scrap",
        "scrap_probability",
        "predicted_scrap_risk",
        "root_cause_summary",
        "engineering_recommendations",
    ]
    available_columns = [
        column for column in export_columns if column in prediction_results.columns
    ]

    high_risk_results = prediction_results[
        prediction_results["predicted_scrap_risk"] == "High"
    ].copy()
    if high_risk_results.empty:
        high_risk_results = prediction_results.copy()

    export_df = (
        high_risk_results.sort_values("scrap_probability", ascending=False)
        .head(MAX_PREDICTION_EXPORT_ROWS)
        .loc[:, available_columns]
    )

    return json.loads(export_df.to_json(orient="records"))


def build_sample_prediction(prediction_results: pd.DataFrame) -> dict:
    """Build the dashboard sample prediction from the highest-risk row."""
    sample = prediction_results.sort_values(
        "scrap_probability",
        ascending=False,
    ).iloc[0]

    recommendation_text = sample["engineering_recommendations"]
    recommendations = [
        recommendation.strip()
        for recommendation in recommendation_text.split(";")
        if recommendation.strip()
    ]
    if not recommendations:
        recommendations = [
            "No immediate action required. Continue standard process monitoring."
        ]

    return {
        "title": "New Part Risk Prediction",
        "scrap_probability": format_percent(sample["scrap_probability"]),
        "risk_level": sample["predicted_scrap_risk"],
        "input_conditions": {
            column: sample[column]
            for column in FEATURE_COLUMNS
            if column in prediction_results.columns
        },
        "root_cause_summary": sample["root_cause_summary"],
        "engineering_recommendations": recommendation_text,
        "recommendations": recommendations,
    }


def build_dashboard_data(
    df: pd.DataFrame,
    metrics: dict,
    feature_importance: pd.DataFrame,
    selected_threshold: dict,
    threshold_metrics: pd.DataFrame,
    cost_optimization: dict,
    prediction_results: pd.DataFrame,
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
            "cost_optimization": build_cost_optimization_summary(cost_optimization),
        },
        "recommendations": build_recommendations(
            df=df,
            highest_risk_machine=highest_risk_machine,
            top_features=top_features,
        ),
        "prediction_results": get_prediction_results_export(prediction_results),
        "sample_prediction": build_sample_prediction(prediction_results),
    }

    return dashboard_data


def save_dashboard_data(data: dict) -> None:
    """Save dashboard data to JSON."""
    DASHBOARD_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(DASHBOARD_DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def save_prediction_results(prediction_results: pd.DataFrame) -> None:
    """Save row-level prediction results with root cause analysis columns."""
    PREDICTION_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    prediction_results.to_csv(PREDICTION_RESULTS_PATH, index=False)


def print_summary(data: dict) -> None:
    """Print a compact summary after export."""
    print("Dashboard data export completed.")
    print(f"Total parts: {data['kpis']['total_parts']}")
    print(f"Overall scrap rate: {data['kpis']['overall_scrap_rate']}%")
    print(f"Highest risk machine: {data['kpis']['highest_risk_machine']}")
    print(f"Model F1 score: {data['kpis']['model_f1_score']}")
    print(f"Saved to: {DASHBOARD_DATA_PATH}")
    print(f"Saved prediction results to: {PREDICTION_RESULTS_PATH}")


def print_root_cause_summary(prediction_results: pd.DataFrame) -> None:
    """Print a compact root cause analysis completion message."""
    analyzed_rows = int((prediction_results["root_cause_summary"] != "").sum())
    print(f"Root cause analysis completed for {analyzed_rows} elevated-risk rows.")


def main() -> None:
    (
        df,
        metrics,
        feature_importance,
        selected_threshold,
        threshold_metrics,
        cost_optimization,
        model,
    ) = load_inputs()

    prediction_results = build_prediction_results(
        df=df,
        model=model,
        selected_threshold=selected_threshold,
    )

    dashboard_data = build_dashboard_data(
        df,
        metrics,
        feature_importance,
        selected_threshold,
        threshold_metrics,
        cost_optimization,
        prediction_results,
    )

    save_prediction_results(prediction_results)
    save_dashboard_data(dashboard_data)
    print_root_cause_summary(prediction_results)
    print_summary(dashboard_data)


if __name__ == "__main__":
    main()
