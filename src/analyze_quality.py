from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "outputs" / "feature_importance.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"
MODEL_COMPARISON_PATH = PROJECT_ROOT / "outputs" / "model_comparison.csv"
BEST_MODEL_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "best_model_summary.json"
COST_OPTIMIZATION_PATH = PROJECT_ROOT / "outputs" / "cost_optimized_threshold.json"
PREDICTION_RESULTS_PATH = PROJECT_ROOT / "outputs" / "prediction_results.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "quality_report.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_inputs() -> tuple[pd.DataFrame, dict, pd.DataFrame, dict, pd.DataFrame, dict, dict, pd.DataFrame | None]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run src/generate_data.py first."
        )

    if not METRICS_PATH.exists() or not FEATURE_IMPORTANCE_PATH.exists():
        raise FileNotFoundError(
            "Model outputs not found. Run src/train_model.py before generating the report."
        )

    if not SELECTED_THRESHOLD_PATH.exists():
        raise FileNotFoundError(
            "Selected threshold output not found. Run src/tune_threshold.py before generating the report."
        )

    if not MODEL_COMPARISON_PATH.exists() or not BEST_MODEL_SUMMARY_PATH.exists():
        raise FileNotFoundError(
            "Model comparison outputs not found. Run src/compare_models.py before generating the report."
        )

    if not COST_OPTIMIZATION_PATH.exists():
        raise FileNotFoundError(
            "Cost optimization output not found. Run src/optimize_threshold_cost.py before generating the report."
        )

    df = pd.read_csv(DATA_PATH)
    metrics = load_json(METRICS_PATH)
    feature_importance = pd.read_csv(FEATURE_IMPORTANCE_PATH)
    selected_threshold = load_json(SELECTED_THRESHOLD_PATH)
    model_comparison = pd.read_csv(MODEL_COMPARISON_PATH)
    best_model_summary = load_json(BEST_MODEL_SUMMARY_PATH)
    cost_optimization = load_json(COST_OPTIMIZATION_PATH)
    prediction_results = (
        pd.read_csv(PREDICTION_RESULTS_PATH)
        if PREDICTION_RESULTS_PATH.exists()
        else None
    )

    return (
        df,
        metrics,
        feature_importance,
        selected_threshold,
        model_comparison,
        best_model_summary,
        cost_optimization,
        prediction_results,
    )


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def get_machine_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("machine_id")
        .agg(
            total_parts=("part_id", "count"),
            scrap_parts=("scrap", "sum"),
            scrap_rate=("scrap", "mean"),
            avg_temperature_c=("temperature_c", "mean"),
            avg_cycle_time_s=("cycle_time_s", "mean"),
            avg_vibration_mm_s=("vibration_mm_s", "mean"),
        )
        .reset_index()
        .sort_values("scrap_rate", ascending=False)
    )

    return summary


def dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def split_recommendations(value: object) -> list[str]:
    if pd.isna(value):
        return []

    return [
        recommendation.strip()
        for recommendation in str(value).split(";")
        if recommendation.strip()
    ]


def extract_root_cause_drivers(summary: object) -> list[str]:
    if pd.isna(summary):
        return []

    text = str(summary).strip()
    marker = "mainly due to "
    if marker not in text.lower():
        return [text] if text else []

    driver_text = text.lower().split(marker, 1)[1].rstrip(".")
    return [
        driver.strip()
        for driver in driver_text.replace(", and ", ", ").replace(" and ", ", ").split(",")
        if driver.strip()
    ]


def build_root_cause_section(prediction_results: pd.DataFrame | None) -> str:
    required_columns = {
        "part_id",
        "scrap_probability",
        "predicted_scrap_risk",
        "root_cause_summary",
        "engineering_recommendations",
    }

    fallback = """## Root Cause Analysis & Engineering Actions

Root cause analysis output is not available for this report run. Generate `outputs/prediction_results.csv` with `root_cause_summary` and `engineering_recommendations` columns to include high-risk engineering actions.

---"""

    if prediction_results is None or prediction_results.empty:
        return fallback

    if not required_columns.issubset(prediction_results.columns):
        return fallback

    results = prediction_results.copy()
    results["root_cause_summary"] = results["root_cause_summary"].fillna("").astype(str)
    results["engineering_recommendations"] = (
        results["engineering_recommendations"].fillna("").astype(str)
    )

    rca_rows = results[results["root_cause_summary"].str.strip() != ""].copy()
    if rca_rows.empty:
        return """## Root Cause Analysis & Engineering Actions

No elevated-risk rows with root cause analysis were available in `outputs/prediction_results.csv` for this report run.

---"""

    driver_counts = (
        pd.Series(
            driver
            for summary in rca_rows["root_cause_summary"]
            for driver in extract_root_cause_drivers(summary)
        )
        .value_counts()
        .head(5)
    )

    if driver_counts.empty:
        driver_summary = "- No recurring root cause drivers were available."
    else:
        driver_summary = "\n".join(
            f"- {driver.title()}: {count} elevated-risk rows"
            for driver, count in driver_counts.items()
        )

    representative = rca_rows.sort_values(
        "scrap_probability",
        ascending=False,
    ).head(5)
    representative_table = representative[
        [
            "part_id",
            "scrap_probability",
            "predicted_scrap_risk",
            "root_cause_summary",
        ]
    ].copy()
    representative_table["scrap_probability"] = representative_table[
        "scrap_probability"
    ].apply(lambda value: f"{float(value) * 100:.2f}%")

    recommendation_counts = (
        pd.Series(
            recommendation
            for value in rca_rows["engineering_recommendations"]
            for recommendation in split_recommendations(value)
        )
        .value_counts()
        .head(5)
    )

    if recommendation_counts.empty:
        recommendation_summary = "- No engineering recommendations were available."
    else:
        recommendation_summary = "\n".join(
            f"- {recommendation}" for recommendation in recommendation_counts.index
        )

    return f"""## Root Cause Analysis & Engineering Actions

The prediction export includes **{len(rca_rows):,} elevated-risk rows with root cause analysis**. The rule-based analysis converts high-risk model predictions into concise engineering context for report review and dashboard follow-up.

### Most Recurring Root Cause Drivers

{driver_summary}

### Representative High-Risk Parts / Batches

{dataframe_to_markdown_table(representative_table)}

### Concise Engineering Actions

{recommendation_summary}

---"""


def build_report(
    df: pd.DataFrame,
    metrics: dict,
    feature_importance: pd.DataFrame,
    selected_threshold: dict,
    model_comparison: pd.DataFrame,
    best_model_summary: dict,
    cost_optimization: dict,
    prediction_results: pd.DataFrame | None,
) -> str:
    total_parts = len(df)
    overall_scrap_rate = df["scrap"].mean()
    scrap_parts = int(df["scrap"].sum())

    machine_summary = get_machine_summary(df)
    highest_risk_machine = machine_summary.iloc[0]["machine_id"]
    highest_machine_scrap_rate = machine_summary.iloc[0]["scrap_rate"]

    top_features = feature_importance.head(8).copy()

    machine_table = machine_summary.copy()
    machine_table["scrap_rate"] = machine_table["scrap_rate"].apply(lambda x: f"{x * 100:.2f}%")
    machine_table["avg_temperature_c"] = machine_table["avg_temperature_c"].round(1)
    machine_table["avg_cycle_time_s"] = machine_table["avg_cycle_time_s"].round(1)
    machine_table["avg_vibration_mm_s"] = machine_table["avg_vibration_mm_s"].round(2)

    feature_table = top_features.copy()
    feature_table["importance"] = feature_table["importance"].round(4)

    comparison_table = model_comparison[
        ["model", "accuracy", "precision", "recall", "f1_score"]
    ].copy()
    comparison_table[["accuracy", "precision", "recall", "f1_score"]] = comparison_table[
        ["accuracy", "precision", "recall", "f1_score"]
    ].round(4)

    best_model = best_model_summary["best_model_by_f1"]
    selected_model = best_model_summary["selected_production_model"]

    cost_assumptions = cost_optimization["cost_assumptions"]
    cost_optimized = cost_optimization["cost_optimized_threshold"]
    cost_comparison = cost_optimization["comparison"]

    cm = metrics["confusion_matrix"]
    default_recall = metrics["recall"]
    tuned_recall = selected_threshold["recall"]
    recall_improvement_pp = (tuned_recall - default_recall) * 100
    root_cause_section = build_root_cause_section(prediction_results)

    report = f"""# AI Production Quality Analysis Report

## Executive Summary

This report analyzes a synthetic manufacturing quality dataset containing **{total_parts:,} production records**. The overall scrap rate is **{percent(overall_scrap_rate)}**, corresponding to **{scrap_parts} scrap parts**.

The analysis identifies **{highest_risk_machine}** as the highest-risk machine, with a scrap rate of **{percent(highest_machine_scrap_rate)}**. The machine learning model highlights vibration, cycle time, temperature, and machine-specific effects as relevant drivers of scrap risk.

The project demonstrates how machine learning can support production quality monitoring, early risk detection, threshold optimization, cost-aware decision-making, and structured process improvement in a manufacturing environment.

---

## Dataset Overview

The dataset simulates manufacturing process data for a production quality control scenario. Each row represents one produced part and contains process parameters, machine information, shift information, material batch information, and the final quality outcome.

### Dataset Size

| Metric | Value |
|---|---:|
| Total production records | {total_parts:,} |
| Scrap parts | {scrap_parts} |
| Overall scrap rate | {percent(overall_scrap_rate)} |
| Number of machines | {df["machine_id"].nunique()} |
| Number of shifts | {df["shift"].nunique()} |
| Number of material batches | {df["material_batch"].nunique()} |

### Input Features

The model uses the following feature groups:

- Machine information: `machine_id`
- Process parameters: `temperature_c`, `pressure_bar`, `cycle_time_s`
- Operating context: `shift`, `material_batch`
- Operator and machine condition: `operator_experience_years`, `vibration_mm_s`, `humidity_percent`

---

## Model Approach

A **Random Forest classifier** was trained to predict whether a produced part is likely to become scrap.

The pipeline includes:

1. Loading the production quality dataset
2. One-hot encoding categorical variables
3. Comparing multiple classification models
4. Training the selected Random Forest classifier
5. Evaluating classification performance
6. Tuning the classification threshold for early-warning quality monitoring
7. Optimizing the threshold using operational cost assumptions
8. Exporting model metrics and feature importance values
9. Preparing dashboard-ready JSON data for visualization

Random Forest was selected because it performs well on tabular data, handles nonlinear interactions, and provides interpretable feature importance values.

---

## Model Comparison

Three classification models were evaluated on the same train-test split.

{dataframe_to_markdown_table(comparison_table)}

### Model Selection

The best model by F1 score is **{best_model["model"]}** with an F1 score of **{best_model["f1_score"]:.3f}**.

The selected production model is **{selected_model["model"]}**. Random Forest is used as the main production model because it provides a practical balance between predictive performance, robustness on tabular production data, and interpretable feature importance values for engineering analysis.

Gradient Boosting achieved high accuracy but detected very few scrap cases, which makes it unsuitable for this imbalanced quality prediction scenario. Logistic Regression achieved higher recall but produced more false positives and a lower F1 score.

---

## Model Performance

| Metric | Value |
|---|---:|
| Accuracy | {metrics["accuracy"]:.3f} |
| Precision | {metrics["precision"]:.3f} |
| Recall | {metrics["recall"]:.3f} |
| F1 Score | {metrics["f1_score"]:.3f} |

### Confusion Matrix

| Prediction Result | Count |
|---|---:|
| True Negative | {cm["true_negative"]} |
| False Positive | {cm["false_positive"]} |
| False Negative | {cm["false_negative"]} |
| True Positive | {cm["true_positive"]} |

### Interpretation

The model achieves high overall accuracy, but the F1 score is lower because scrap cases are relatively rare compared with good parts. This is typical for quality prediction problems with imbalanced production data.

For a real production deployment, recall would likely be prioritized over raw accuracy because missing defective parts can be more costly than generating false alarms.

---

## Threshold Tuning for Early-Warning Quality Monitoring

The default classification threshold is **0.50**. For a manufacturing quality early-warning use case, the decision threshold was tuned to **{selected_threshold["selected_threshold"]:.2f}** to prioritize recall and reduce missed scrap cases.

| Metric | Default Threshold 0.50 | Tuned Threshold {selected_threshold["selected_threshold"]:.2f} |
|---|---:|---:|
| Recall | {default_recall * 100:.2f}% | {tuned_recall * 100:.2f}% |
| False negatives / missed scrap | {cm["false_negative"]} | {selected_threshold["false_negative"]} |
| False positives / false alarms | {cm["false_positive"]} | {selected_threshold["false_positive"]} |

The tuned threshold improves recall by **{recall_improvement_pp:.2f} percentage points** and reduces missed scrap cases from **{cm["false_negative"]}** to **{selected_threshold["false_negative"]}** in the test set. The trade-off is an increase in false alarms from **{cm["false_positive"]}** to **{selected_threshold["false_positive"]}**.

This trade-off is acceptable for an early-warning quality monitoring scenario where missing defective parts may be more costly than additional inspection effort.

---

## Cost-Based Threshold Optimization

A cost-based threshold analysis was added to translate classification performance into an operational manufacturing decision.

The assumed costs are illustrative and can be adjusted for a real production environment:

| Cost Type | Assumed Cost |
|---|---:|
| Missed scrap / false negative | {cost_assumptions["missed_scrap_cost"]:.0f} {cost_assumptions["currency"]} |
| False alarm / additional inspection | {cost_assumptions["false_alarm_cost"]:.0f} {cost_assumptions["currency"]} |

Under these assumptions, the cost-optimized threshold is **{cost_optimized["threshold"]:.2f}**.

| Threshold Strategy | Threshold | Total Estimated Cost | Recall | False Negatives | False Positives |
|---|---:|---:|---:|---:|---:|
| Default threshold | 0.50 | {cost_comparison["default_threshold_0_50"]["total_cost"]:.0f} {cost_assumptions["currency"]} | {cost_comparison["default_threshold_0_50"]["recall"] * 100:.2f}% | {cost_comparison["default_threshold_0_50"]["false_negative"]} | {cost_comparison["default_threshold_0_50"]["false_positive"]} |
| Recall-tuned threshold | 0.30 | {cost_comparison["recall_tuned_threshold_0_30"]["total_cost"]:.0f} {cost_assumptions["currency"]} | {cost_comparison["recall_tuned_threshold_0_30"]["recall"] * 100:.2f}% | {cost_comparison["recall_tuned_threshold_0_30"]["false_negative"]} | {cost_comparison["recall_tuned_threshold_0_30"]["false_positive"]} |
| Cost-optimized threshold | {cost_optimized["threshold"]:.2f} | {cost_optimized["total_cost"]:.0f} {cost_assumptions["currency"]} | {cost_optimized["recall"] * 100:.2f}% | {cost_optimized["false_negative"]} | {cost_optimized["false_positive"]} |

The cost-optimized threshold reduces the estimated operational cost by **{cost_comparison["cost_savings_vs_default"]:.0f} {cost_assumptions["currency"]}** compared with the default threshold.

This demonstrates that classification thresholds should not be selected only by generic ML metrics. In a manufacturing quality context, the decision threshold should reflect the operational cost of missed scrap and additional inspection effort.

---

## Key Process Drivers

The following features had the highest importance in the Random Forest model:

{dataframe_to_markdown_table(feature_table)}

### Engineering Interpretation

The strongest model drivers indicate that scrap risk is influenced by both process conditions and machine behavior. In particular:

- Higher vibration may indicate tool wear, unstable machine condition, or mechanical imbalance.
- Longer cycle times may indicate process instability, waiting time, or machine-related delays.
- Higher process temperature can increase quality risk when the process window is exceeded.
- Machine-specific effects, especially for M2, suggest possible calibration or maintenance differences.

---

## Machine-Level Quality Analysis

{dataframe_to_markdown_table(machine_table)}

### Key Finding

**{highest_risk_machine}** has the highest observed scrap rate at **{percent(highest_machine_scrap_rate)}**, compared with the overall average of **{percent(overall_scrap_rate)}**.

This indicates that machine-level effects should be investigated before assuming the issue is only caused by material, operator, or shift-related variation.

---

{root_cause_section}

## Engineering Recommendations

1. **Inspect and calibrate {highest_risk_machine}.**  
   The scrap rate is significantly higher than the production average, suggesting potential calibration drift, machine wear, or unstable operating conditions.

2. **Monitor vibration trends.**  
   Vibration is one of the strongest model drivers and may indicate tool wear, bearing issues, fixture instability, or other mechanical problems.

3. **Investigate cycle time deviations above 50 seconds.**  
   Long cycle times may indicate unstable process behavior or machine-related delays that correlate with higher scrap risk.

4. **Review thermal process control.**  
   Scrap risk increases when process temperature exceeds the normal operating window, especially above 190°C.

5. **Use additional operator guidance for high-risk conditions.**  
   Checklists or process alerts may help reduce quality variation during night shifts, high-temperature runs, or less stable machine states.

---

## Limitations

This project uses synthetic data. The dataset was designed to simulate realistic manufacturing quality patterns, but it does not represent a specific real production line.

Important limitations:

- The model should not be used for real production decisions without validation on actual shop-floor data.
- Feature importance values are model-based indicators, not proof of physical causality.
- The current model uses static batch data and does not include real-time sensor streaming.
- Cost assumptions are illustrative and should be adjusted to match real inspection, scrap, and rework costs.
- Classification thresholds should be validated with production-specific quality and cost requirements.

---

## Future Improvements

Potential next steps:

- Add production-specific cost inputs for configurable threshold optimization.
- Add probability-based risk levels: low, medium, high.
- Include time-series sensor data for predictive maintenance analysis.
- Add model explainability with SHAP values.
- Validate the workflow with real or open manufacturing datasets.
- Extend the dashboard with a user-adjustable threshold and cost scenario panel.

---

## Project Summary

This project demonstrates an end-to-end AI workflow for manufacturing quality analytics:

- Synthetic production data generation
- Machine learning-based scrap prediction
- Model comparison and selection
- Threshold tuning for early-warning quality monitoring
- Cost-based threshold optimization
- Feature importance analysis
- Static dashboard visualization
- Automated engineering report generation

The result is a compact portfolio project connecting **mechanical engineering**, **production quality**, **machine learning**, and **Industry 4.0**.
"""

    return report


def save_report(report: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(report)


def main() -> None:
    (
        df,
        metrics,
        feature_importance,
        selected_threshold,
        model_comparison,
        best_model_summary,
        cost_optimization,
        prediction_results,
    ) = load_inputs()

    report = build_report(
        df,
        metrics,
        feature_importance,
        selected_threshold,
        model_comparison,
        best_model_summary,
        cost_optimization,
        prediction_results,
    )

    save_report(report)

    print("Quality report generated.")
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
