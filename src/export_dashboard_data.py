from pathlib import Path
import json
import re

import joblib
import pandas as pd
import yaml

from root_cause_analysis import analyze_root_causes
from train_model import CATEGORICAL_FEATURES, MODEL_PATH, NUMERIC_FEATURES


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "outputs" / "feature_importance.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"
THRESHOLD_METRICS_PATH = PROJECT_ROOT / "outputs" / "threshold_metrics.csv"
THRESHOLD_COST_ANALYSIS_PATH = PROJECT_ROOT / "outputs" / "threshold_cost_analysis.csv"
COST_OPTIMIZATION_PATH = PROJECT_ROOT / "outputs" / "cost_optimized_threshold.json"
MODEL_EVALUATION_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "model_evaluation_summary.json"
RISK_BAND_EVALUATION_PATH = PROJECT_ROOT / "outputs" / "risk_band_evaluation.csv"
DATA_QUALITY_REPORT_PATH = PROJECT_ROOT / "outputs" / "data_quality_report.json"
BATCH_REVIEW_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "batch_review_summary.json"
SPEC_COMPLIANCE_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "spec_compliance_summary.json"
REVIEW_FEEDBACK_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "review_feedback_summary.json"
RCA_RULES_CONFIG_PATH = PROJECT_ROOT / "config" / "rca_rules.yaml"
SPEC_REQUIREMENTS_CONFIG_PATH = PROJECT_ROOT / "config" / "spec_requirements.yaml"
BATCH_REVIEW_RESULTS_PATH = PROJECT_ROOT / "outputs" / "batch_review_results.csv"
SPEC_COMPLIANCE_RESULTS_PATH = PROJECT_ROOT / "outputs" / "spec_compliance_results.csv"
REVIEW_FEEDBACK_CASES_PATH = PROJECT_ROOT / "outputs" / "review_feedback_cases.csv"
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
PREDICTION_RESULTS_PATH = PROJECT_ROOT / "outputs" / "prediction_results.csv"
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
MAX_PREDICTION_EXPORT_ROWS = 25

CASE_TRACE_INPUT_FIELDS = [
    "machine_id",
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "shift",
    "material_batch",
    "operator_experience_years",
    "vibration_mm_s",
    "humidity_percent",
]

CASE_TRACE_BATCH_COLUMNS = [
    "part_id",
    "scrap_probability",
    "risk_level",
    "review_threshold",
    "review_decision",
    "decision_reason",
    "root_cause_summary",
    "suspected_driver_count",
    "top_suspected_drivers",
    "engineering_recommendations",
]

CASE_TRACE_SPEC_COLUMNS = [
    "part_id",
    "spec_compliance_status",
    "violation_count",
    "critical_violation_count",
    "warning_violation_count",
    "violated_requirement_ids",
    "violation_summary",
    "recommended_actions",
]

CASE_TRACE_FEEDBACK_COLUMNS = [
    "part_id",
    "actual_scrap",
    "engineer_review_outcome",
    "feedback_classification",
    "feedback_priority",
    "feedback_interpretation",
    "review_notes",
]

def load_json(path: Path) -> dict:
    """Load a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_optional_json(path: Path) -> dict:
    """Load an optional JSON output for dashboard summary cards."""
    if not path.exists():
        return {
            "status": "missing",
            "message": "Output not generated yet.",
        }

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def trace_missing(message: str = "Case trace outputs not generated yet.") -> dict:
    """Return a safe placeholder for unavailable case trace data."""
    return {
        "status": "missing",
        "message": message,
    }


def load_trace_csv(path: Path, required_columns: list[str], label: str) -> pd.DataFrame | None:
    """Load a trace source CSV, returning None if it is not usable yet."""
    if not path.exists():
        return None

    df = pd.read_csv(path)
    missing_columns = [column for column in required_columns if column not in df.columns]
    if df.empty or missing_columns:
        return None

    df = df.copy()
    df["part_id"] = df["part_id"].astype(str)
    return df


def clean_value(value: object) -> object:
    """Convert pandas missing values to None for dashboard JSON."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


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


def load_yaml(path: Path) -> dict:
    """Load a YAML configuration file used as dashboard rulebook source."""
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def format_requirement_label(value: str) -> str:
    """Convert configured requirement identifiers into readable dashboard labels."""
    if not value:
        return "Not specified"

    labels = {
        "TEMP_MAX_WARNING": "Temperature warning",
        "TEMP_MAX_CRITICAL": "Temperature critical",
        "VIBRATION_MAX_WARNING": "Vibration warning",
        "VIBRATION_MAX_CRITICAL": "Vibration critical",
        "CYCLE_TIME_MAX_WARNING": "Cycle-time warning",
        "CYCLE_TIME_MAX_CRITICAL": "Cycle-time critical",
        "PRESSURE_MIN_WARNING": "Low pressure warning",
        "PRESSURE_MAX_WARNING": "High pressure warning",
        "HUMIDITY_MAX_WARNING": "Humidity warning",
        "LOW_OPERATOR_EXPERIENCE_WARNING": "Operator support warning",
    }
    if value in labels:
        return labels[value]

    words = str(value).replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\b\w", lambda match: match.group(0).upper(), words)


def format_signal_label(value: str) -> str:
    """Convert input signal columns into readable engineering labels."""
    if not value:
        return "Not specified"

    labels = {
        "temperature_c": "Temperature",
        "vibration_mm_s": "Vibration",
        "cycle_time_s": "Cycle time",
        "pressure_bar": "Pressure",
        "humidity_percent": "Humidity",
        "operator_experience_years": "Operator experience",
        "machine_id": "Machine",
        "shift": "Shift",
        "material_batch": "Material batch",
    }
    if value in labels:
        return labels[value]

    words = str(value).replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\b\w", lambda match: match.group(0).upper(), words)


def normalize_severity(value: str) -> str:
    """Normalize rule severity labels for dashboard badges."""
    if not value:
        return "Informational"

    severity = str(value).strip().lower()
    mapping = {
        "critical": "Critical",
        "high": "Critical",
        "warning": "Warning",
        "medium": "Warning",
        "monitoring": "Monitoring",
        "low": "Monitoring",
        "info": "Informational",
        "informational": "Informational",
    }
    return mapping.get(severity, format_signal_label(severity))


def format_signal_unit(value: str) -> str:
    """Return compact display units for configured sensor columns."""
    units = {
        "temperature_c": "C",
        "vibration_mm_s": "mm/s",
        "cycle_time_s": "s",
        "pressure_bar": "bar",
        "humidity_percent": "%",
        "operator_experience_years": "years",
    }
    return units.get(str(value), "")


def format_condition_text(rule: dict) -> str:
    """Build a compact readable trigger condition from a config rule."""
    operator_value = rule.get("operator")
    value = rule.get("value")
    values = rule.get("values")

    if operator_value and value is not None:
        unit = format_signal_unit(rule.get("parameter") or rule.get("column"))
        return f"{operator_value} {value}{f' {unit}' if unit else ''}"

    if values:
        if isinstance(values, list):
            return "matches " + ", ".join(str(item) for item in values)
        return f"matches {values}"

    return rule.get("condition") or rule.get("evidence") or "Not specified"


def build_engineering_rulebook() -> dict:
    """Export configured engineering checks into dashboard-readable rows."""
    spec_config = load_yaml(SPEC_REQUIREMENTS_CONFIG_PATH)
    rca_config = load_yaml(RCA_RULES_CONFIG_PATH)
    spec_requirements = spec_config.get("requirements", []) or []
    rca_rules = rca_config.get("rules", []) or []

    formatted_spec_requirements = []
    for requirement in spec_requirements:
        signal = requirement.get("parameter", "")
        formatted_spec_requirements.append(
            {
                "id": requirement.get("id", "Not specified"),
                "label": format_requirement_label(requirement.get("id", "")),
                "category": format_signal_label(signal),
                "signal": signal or "Not specified",
                "signal_label": format_signal_label(signal),
                "condition": format_condition_text(requirement),
                "severity": normalize_severity(requirement.get("severity", "")),
                "description": requirement.get("requirement_text", "Not specified"),
                "rationale": requirement.get("engineering_rationale", "Not specified"),
                "recommended_action": requirement.get(
                    "recommended_action",
                    "Not specified",
                ),
            }
        )

    formatted_rca_rules = []
    for rule in rca_rules:
        signal = rule.get("column", "")
        formatted_rca_rules.append(
            {
                "id": rule.get("id", "Not specified"),
                "label": rule.get("driver") or format_requirement_label(rule.get("id", "")),
                "category": format_signal_label(signal),
                "signal": signal or "Not specified",
                "condition": format_condition_text(rule),
                "severity": normalize_severity(rule.get("severity", "")),
                "possible_cause": rule.get(
                    "engineering_interpretation",
                    "Not specified",
                ),
                "evidence": rule.get("evidence", "Not specified"),
                "recommended_action": rule.get("recommendation", "Not specified"),
            }
        )

    return {
        "summary": {
            "spec_requirement_count": len(formatted_spec_requirements),
            "rca_rule_count": len(formatted_rca_rules),
            "source_files": [
                "config/spec_requirements.yaml",
                "config/rca_rules.yaml",
            ],
            "source_type": "YAML configuration",
            "note": (
                "Rules are loaded from configuration files and used for decision support."
            ),
        },
        "spec_requirements": formatted_spec_requirements,
        "rca_rules": formatted_rca_rules,
    }


def load_optional_csv(path: Path) -> pd.DataFrame:
    """Load an optional CSV output, returning an empty frame if unavailable."""
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def dataframe_records(df: pd.DataFrame) -> list[dict]:
    """Convert a dataframe to JSON-safe records."""
    return [
        {
            column: clean_value(row[column])
            for column in df.columns
        }
        for _, row in df.iterrows()
    ]


def build_threshold_tradeoff(limit: int = 5) -> list[dict]:
    """Export compact threshold trade-off rows sorted by total cost."""
    threshold_df = load_optional_csv(THRESHOLD_COST_ANALYSIS_PATH)
    required_columns = [
        "threshold",
        "recall",
        "false_positive",
        "false_negative",
        "total_cost",
    ]
    if threshold_df.empty or any(column not in threshold_df.columns for column in required_columns):
        return []

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


def build_model_evaluation() -> dict:
    """Build model evaluation and risk-band data for the dashboard."""
    summary = load_optional_json(MODEL_EVALUATION_SUMMARY_PATH)
    if summary.get("status") == "missing":
        summary = {}

    risk_band_df = load_optional_csv(RISK_BAND_EVALUATION_PATH)
    risk_bands = dataframe_records(risk_band_df) if not risk_band_df.empty else []

    return {
        "summary": summary,
        "risk_bands": risk_bands,
        "threshold_tradeoff": build_threshold_tradeoff(),
    }


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


def missing_workflow_card() -> dict:
    """Return a safe placeholder for workflow outputs not generated yet."""
    return {
        "status": "missing",
        "message": "Output not generated yet.",
    }


def build_data_quality_overview() -> dict:
    """Build a compact dashboard summary for the data quality layer."""
    report = load_optional_json(DATA_QUALITY_REPORT_PATH)
    if report.get("status") == "missing":
        return missing_workflow_card()

    target_summary = report.get("target_summary", {})
    return {
        "status": report.get("status", "unknown"),
        "row_count": report.get("row_count"),
        "column_count": report.get("column_count"),
        "warning_count": len(report.get("warnings", [])),
        "error_count": len(report.get("errors", [])),
        "scrap_rate": target_summary.get("scrap_rate"),
    }


def build_batch_review_overview() -> dict:
    """Build a compact dashboard summary for new-batch review routing."""
    summary = load_optional_json(BATCH_REVIEW_SUMMARY_PATH)
    if summary.get("status") == "missing":
        return missing_workflow_card()

    decision_counts = summary.get("decision_counts", {})
    return {
        "status": "available",
        "row_count": summary.get("row_count"),
        "review_threshold": summary.get("review_threshold"),
        "decision_counts": {
            "ENGINEERING_REVIEW_REQUIRED": decision_counts.get(
                "ENGINEERING_REVIEW_REQUIRED",
                0,
            ),
            "ADDITIONAL_MONITORING": decision_counts.get("ADDITIONAL_MONITORING", 0),
            "STANDARD_MONITORING": decision_counts.get("STANDARD_MONITORING", 0),
        },
        "risk_level_counts": summary.get("risk_level_counts", {}),
    }


def build_spec_compliance_overview() -> dict:
    """Build a compact dashboard summary for specification compliance checks."""
    summary = load_optional_json(SPEC_COMPLIANCE_SUMMARY_PATH)
    if summary.get("status") == "missing":
        return missing_workflow_card()

    status_counts = summary.get("status_counts", {})
    violated_requirements = summary.get("violation_counts_by_requirement", [])
    most_common = violated_requirements[0] if violated_requirements else None
    return {
        "status": "available",
        "row_count": summary.get("row_count"),
        "requirement_count": summary.get("requirement_count"),
        "status_counts": {
            "COMPLIANT": status_counts.get("COMPLIANT", 0),
            "WARNING_VIOLATION": status_counts.get("WARNING_VIOLATION", 0),
            "CRITICAL_VIOLATION": status_counts.get("CRITICAL_VIOLATION", 0),
        },
        "most_common_violated_requirement": most_common,
    }


def build_feedback_loop_overview() -> dict:
    """Build a compact dashboard summary for review feedback evaluation."""
    summary = load_optional_json(REVIEW_FEEDBACK_SUMMARY_PATH)
    if summary.get("status") == "missing":
        return missing_workflow_card()

    effectiveness = summary.get("review_effectiveness", {})
    return {
        "status": "available",
        "row_count": summary.get("row_count"),
        "issue_capture_rate": effectiveness.get("issue_capture_rate"),
        "false_alarm_rate_among_reviews": effectiveness.get(
            "false_alarm_rate_among_reviews"
        ),
        "missed_issue_count": effectiveness.get("missed_issue_count"),
        "false_alarm_count": effectiveness.get("false_alarm_count"),
        "classification_counts": summary.get("classification_counts", {}),
    }


def build_workflow_overview() -> dict:
    """Build all workflow maturity summary cards for the static dashboard."""
    return {
        "data_quality": build_data_quality_overview(),
        "batch_review": build_batch_review_overview(),
        "spec_compliance": build_spec_compliance_overview(),
        "feedback_loop": build_feedback_loop_overview(),
    }


def select_trace_row(trace_df: pd.DataFrame) -> pd.Series:
    """Select one representative part for the engineering review trace."""
    sortable = trace_df.copy()
    sortable["scrap_probability"] = pd.to_numeric(
        sortable["scrap_probability"],
        errors="coerce",
    ).fillna(-1)

    true_positive_critical = sortable[
        (sortable["feedback_classification"] == "TRUE_POSITIVE_REVIEW")
        & (sortable["spec_compliance_status"] == "CRITICAL_VIOLATION")
    ]
    if not true_positive_critical.empty:
        return true_positive_critical.sort_values(
            ["scrap_probability", "part_id"],
            ascending=[False, True],
        ).iloc[0]

    engineering_review = sortable[
        sortable["review_decision"] == "ENGINEERING_REVIEW_REQUIRED"
    ]
    if not engineering_review.empty:
        return engineering_review.sort_values(
            ["scrap_probability", "part_id"],
            ascending=[False, True],
        ).iloc[0]

    if not sortable.empty:
        return sortable.sort_values(
            ["scrap_probability", "part_id"],
            ascending=[False, True],
        ).iloc[0]

    return trace_df.iloc[0]


def row_object(row: pd.Series, columns: list[str]) -> dict:
    """Extract a JSON-safe object from a row."""
    return {
        column: clean_value(row[column])
        for column in columns
        if column in row.index
    }


def build_trace_summary(row: pd.Series) -> str:
    """Build a concise readable trace summary for the selected record."""
    review_decision = clean_value(row.get("review_decision"))
    risk_level = clean_value(row.get("risk_level"))
    rca_drivers = clean_value(row.get("top_suspected_drivers"))
    spec_status = clean_value(row.get("spec_compliance_status"))
    feedback_classification = clean_value(row.get("feedback_classification"))

    summary_parts = []
    if review_decision == "ENGINEERING_REVIEW_REQUIRED":
        summary_parts.append(
            f"the model routed it for engineering review with {risk_level} predicted risk"
        )
    else:
        summary_parts.append(
            f"the model routed it to {str(review_decision).lower().replace('_', ' ')} with {risk_level} predicted risk"
        )

    if rca_drivers:
        summary_parts.append(f"RCA highlighted {rca_drivers}")
    else:
        summary_parts.append("RCA did not identify configured suspected drivers")

    if spec_status:
        summary_parts.append(
            f"specification checks reported {str(spec_status).lower().replace('_', ' ')}"
        )
    else:
        summary_parts.append("specification compliance data is not available")

    if feedback_classification:
        summary_parts.append(
            f"later feedback classified the case as {str(feedback_classification).lower().replace('_', ' ')}"
        )
    else:
        summary_parts.append("later feedback is not available")

    return "This record was selected as a traceable engineering review example because " + ", ".join(summary_parts) + "."


def build_case_trace() -> dict:
    """Build a representative part-level trace across review workflow outputs."""
    batch_df = load_trace_csv(
        BATCH_REVIEW_RESULTS_PATH,
        CASE_TRACE_BATCH_COLUMNS,
        "batch review results",
    )
    spec_df = load_trace_csv(
        SPEC_COMPLIANCE_RESULTS_PATH,
        CASE_TRACE_SPEC_COLUMNS,
        "spec compliance results",
    )
    feedback_df = load_trace_csv(
        REVIEW_FEEDBACK_CASES_PATH,
        CASE_TRACE_FEEDBACK_COLUMNS,
        "review feedback cases",
    )

    if batch_df is None or spec_df is None or feedback_df is None:
        return trace_missing()

    trace_df = batch_df.merge(
        spec_df[CASE_TRACE_SPEC_COLUMNS],
        on="part_id",
        how="left",
        validate="one_to_one",
    ).merge(
        feedback_df[CASE_TRACE_FEEDBACK_COLUMNS],
        on="part_id",
        how="left",
        validate="one_to_one",
    )

    if trace_df.empty:
        return trace_missing()

    row = select_trace_row(trace_df)
    return {
        "part_id": clean_value(row.get("part_id")),
        "input_conditions": row_object(row, CASE_TRACE_INPUT_FIELDS),
        "model_review": row_object(
            row,
            [
                "scrap_probability",
                "risk_level",
                "review_threshold",
                "review_decision",
                "decision_reason",
            ],
        ),
        "rca": row_object(
            row,
            [
                "root_cause_summary",
                "suspected_driver_count",
                "top_suspected_drivers",
                "engineering_recommendations",
            ],
        ),
        "spec_compliance": row_object(
            row,
            [
                "spec_compliance_status",
                "violation_count",
                "critical_violation_count",
                "warning_violation_count",
                "violated_requirement_ids",
                "violation_summary",
                "recommended_actions",
            ],
        ),
        "feedback": row_object(
            row,
            [
                "actual_scrap",
                "engineer_review_outcome",
                "feedback_classification",
                "feedback_priority",
                "feedback_interpretation",
                "review_notes",
            ],
        ),
        "trace_summary": build_trace_summary(row),
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
        "workflow_overview": build_workflow_overview(),
        "engineering_rulebook": build_engineering_rulebook(),
        "model_evaluation": build_model_evaluation(),
        "case_trace": build_case_trace(),
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
