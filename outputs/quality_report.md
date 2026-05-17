# AI Production Quality Analysis Report

## Executive Summary

This report analyzes a synthetic manufacturing quality dataset containing **5,000 production records**. The overall scrap rate is **7.16%**, corresponding to **358 scrap parts**.

The analysis identifies **M2** as the highest-risk machine, with a scrap rate of **14.47%**. The machine learning model highlights vibration, cycle time, temperature, and machine-specific effects as relevant drivers of scrap risk.

The project demonstrates how machine learning can support production quality monitoring, early risk detection, threshold optimization, cost-aware decision-making, and structured process improvement in a manufacturing environment.

---

## Dataset Overview

The dataset simulates manufacturing process data for a production quality control scenario. Each row represents one produced part and contains process parameters, machine information, shift information, material batch information, and the final quality outcome.

### Dataset Size

| Metric | Value |
|---|---:|
| Total production records | 5,000 |
| Scrap parts | 358 |
| Overall scrap rate | 7.16% |
| Number of machines | 4 |
| Number of shifts | 3 |
| Number of material batches | 5 |

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

| model               |   accuracy |   precision |   recall |   f1_score |
|:--------------------|-----------:|------------:|---------:|-----------:|
| Random Forest       |     0.868  |      0.2031 |   0.2921 |     0.2396 |
| Logistic Regression |     0.6808 |      0.1362 |   0.6517 |     0.2252 |
| Gradient Boosting   |     0.9272 |      0.25   |   0.0112 |     0.0215 |

### Model Selection

The best model by F1 score is **Random Forest** with an F1 score of **0.240**.

The selected production model is **Random Forest**. Random Forest is used as the main production model because it provides a practical balance between predictive performance, robustness on tabular production data, and interpretable feature importance values for engineering analysis.

Gradient Boosting achieved high accuracy but detected very few scrap cases, which makes it unsuitable for this imbalanced quality prediction scenario. Logistic Regression achieved higher recall but produced more false positives and a lower F1 score.

---

## Model Performance

| Metric | Value |
|---|---:|
| Accuracy | 0.868 |
| Precision | 0.203 |
| Recall | 0.292 |
| F1 Score | 0.240 |

### Confusion Matrix

| Prediction Result | Count |
|---|---:|
| True Negative | 1059 |
| False Positive | 102 |
| False Negative | 63 |
| True Positive | 26 |

### Interpretation

The model achieves high overall accuracy, but the F1 score is lower because scrap cases are relatively rare compared with good parts. This is typical for quality prediction problems with imbalanced production data.

For a real production deployment, recall would likely be prioritized over raw accuracy because missing defective parts can be more costly than generating false alarms.

---

## Threshold Tuning for Early-Warning Quality Monitoring

The default classification threshold is **0.50**. For a manufacturing quality early-warning use case, the decision threshold was tuned to **0.30** to prioritize recall and reduce missed scrap cases.

| Metric | Default Threshold 0.50 | Tuned Threshold 0.30 |
|---|---:|---:|
| Recall | 29.21% | 74.16% |
| False negatives / missed scrap | 63 | 23 |
| False positives / false alarms | 102 | 525 |

The tuned threshold improves recall by **44.95 percentage points** and reduces missed scrap cases from **63** to **23** in the test set. The trade-off is an increase in false alarms from **102** to **525**.

This trade-off is acceptable for an early-warning quality monitoring scenario where missing defective parts may be more costly than additional inspection effort.

---

## Cost-Based Threshold Optimization

A cost-based threshold analysis was added to translate classification performance into an operational manufacturing decision.

The assumed costs are illustrative and can be adjusted for a real production environment:

| Cost Type | Assumed Cost |
|---|---:|
| Missed scrap / false negative | 100 EUR |
| False alarm / additional inspection | 10 EUR |

Under these assumptions, the cost-optimized threshold is **0.40**.

| Threshold Strategy | Threshold | Total Estimated Cost | Recall | False Negatives | False Positives |
|---|---:|---:|---:|---:|---:|
| Default threshold | 0.50 | 7320 EUR | 29.21% | 63 | 102 |
| Recall-tuned threshold | 0.30 | 7550 EUR | 74.16% | 23 | 525 |
| Cost-optimized threshold | 0.40 | 6850 EUR | 48.31% | 46 | 225 |

The cost-optimized threshold reduces the estimated operational cost by **470 EUR** compared with the default threshold.

This demonstrates that classification thresholds should not be selected only by generic ML metrics. In a manufacturing quality context, the decision threshold should reflect the operational cost of missed scrap and additional inspection effort.

---

## Key Process Drivers

The following features had the highest importance in the Random Forest model:

| feature                   |   importance |
|:--------------------------|-------------:|
| vibration_mm_s            |       0.1586 |
| cycle_time_s              |       0.1371 |
| temperature_c             |       0.1303 |
| humidity_percent          |       0.108  |
| operator_experience_years |       0.1041 |
| pressure_bar              |       0.0997 |
| machine_id_M2             |       0.0952 |
| material_batch_B4         |       0.0289 |

### Engineering Interpretation

The strongest model drivers indicate that scrap risk is influenced by both process conditions and machine behavior. In particular:

- Higher vibration may indicate tool wear, unstable machine condition, or mechanical imbalance.
- Longer cycle times may indicate process instability, waiting time, or machine-related delays.
- Higher process temperature can increase quality risk when the process window is exceeded.
- Machine-specific effects, especially for M2, suggest possible calibration or maintenance differences.

---

## Machine-Level Quality Analysis

| machine_id   |   total_parts |   scrap_parts | scrap_rate   |   avg_temperature_c |   avg_cycle_time_s |   avg_vibration_mm_s |
|:-------------|--------------:|--------------:|:-------------|--------------------:|-------------------:|---------------------:|
| M2           |          1258 |           182 | 14.47%       |               187   |               48.3 |                 2.73 |
| M4           |          1240 |            62 | 5.00%        |               184.3 |               46.6 |                 2.48 |
| M1           |          1287 |            61 | 4.74%        |               184.3 |               46   |                 2.29 |
| M3           |          1215 |            53 | 4.36%        |               183.4 |               46.1 |                 2.29 |

### Key Finding

**M2** has the highest observed scrap rate at **14.47%**, compared with the overall average of **7.16%**.

This indicates that machine-level effects should be investigated before assuming the issue is only caused by material, operator, or shift-related variation.

---

## Root Cause Analysis & Engineering Actions

The prediction export includes **2,291 elevated-risk rows with root cause analysis**. The rule-based analysis converts high-risk model predictions into concise engineering context for report review and dashboard follow-up.

### Most Recurring Root Cause Drivers

- Machine M2 Risk Pattern: 1115 elevated-risk rows
- Material Batch B4: 593 elevated-risk rows
- Elevated Vibration: 539 elevated-risk rows
- Night Shift Production: 516 elevated-risk rows
- Late Shift Production: 488 elevated-risk rows

### Representative High-Risk Parts / Batches

| part_id   | scrap_probability   | predicted_scrap_risk   | root_cause_summary                                                                                                |
|:----------|:--------------------|:-----------------------|:------------------------------------------------------------------------------------------------------------------|
| P000977   | 81.09%              | High                   | The batch shows high scrap risk mainly due to very high temperature, high vibration, and machine m2 risk pattern. |
| P002546   | 80.21%              | High                   | The batch shows high scrap risk mainly due to very high temperature, high vibration, and machine m2 risk pattern. |
| P001643   | 78.02%              | High                   | The batch shows high scrap risk mainly due to high vibration, long cycle time, and machine m2 risk pattern.       |
| P003015   | 77.29%              | High                   | The batch shows high scrap risk mainly due to very high temperature, abnormal cycle time, and elevated vibration. |
| P004071   | 77.00%              | High                   | The batch shows high scrap risk mainly due to high vibration, high temperature, and long cycle time.              |

### Concise Engineering Actions

- Inspect M2 calibration, maintenance status, and recent quality history.
- Review shift handoff notes and confirm standard work adherence.
- Quarantine or sample-check material batch B4 and compare against supplier lot history.
- Apply additional process checks during night shift production.
- Trend vibration for the machine and inspect tooling if the signal persists.

---

## Engineering Recommendations

1. **Inspect and calibrate M2.**  
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
