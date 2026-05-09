from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
METRICS_PATH = PROJECT_ROOT / "outputs" / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "outputs" / "feature_importance.csv"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"
REPORT_PATH = PROJECT_ROOT / "outputs" / "quality_report.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_inputs() -> tuple[pd.DataFrame, dict, pd.DataFrame, dict]:
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

    df = pd.read_csv(DATA_PATH)
    metrics = load_json(METRICS_PATH)
    feature_importance = pd.read_csv(FEATURE_IMPORTANCE_PATH)
    selected_threshold = load_json(SELECTED_THRESHOLD_PATH)

    return df, metrics, feature_importance, selected_threshold


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


def build_report(
    df: pd.DataFrame,
    metrics: dict,
    feature_importance: pd.DataFrame,
    selected_threshold: dict,
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

    cm = metrics["confusion_matrix"]
    default_recall = metrics["recall"]
    tuned_recall = selected_threshold["recall"]
    recall_improvement_pp = (tuned_recall - default_recall) * 100

    report = f"""# AI Production Quality Analysis Report

## Executive Summary

This report analyzes a synthetic manufacturing quality dataset containing **{total_parts:,} production records**. The overall scrap rate is **{percent(overall_scrap_rate)}**, corresponding to **{scrap_parts} scrap parts**.

The analysis identifies **{highest_risk_machine}** as the highest-risk machine, with a scrap rate of **{percent(highest_machine_scrap_rate)}**. The machine learning model highlights vibration, cycle time, temperature, and machine-specific effects as relevant drivers of scrap risk.

The project demonstrates how machine learning can support production quality monitoring, early risk detection, and structured process improvement in a manufacturing environment.

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
3. Training a Random Forest classifier
4. Evaluating classification performance
5. Exporting model metrics and feature importance values
6. Preparing dashboard-ready JSON data for visualization

Random Forest was selected because it performs well on tabular data, handles nonlinear interactions, and provides interpretable feature importance values.

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
- The classification threshold has not yet been optimized for production-specific cost trade-offs.

---

## Future Improvements

Potential next steps:

- Add cost-based threshold optimization using production-specific inspection and scrap costs.
- Add probability-based risk levels: low, medium, high.
- Include time-series sensor data for predictive maintenance analysis.
- Add model explainability with SHAP values.
- Deploy the static dashboard through GitHub Pages.
- Validate the workflow with real or open manufacturing datasets.

---

## Project Summary

This project demonstrates an end-to-end AI workflow for manufacturing quality analytics:

- Synthetic production data generation
- Machine learning-based scrap prediction
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
    df, metrics, feature_importance, selected_threshold = load_inputs()
    report = build_report(df, metrics, feature_importance, selected_threshold)
    save_report(report)

    print("Quality report generated.")
    print(f"Saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()