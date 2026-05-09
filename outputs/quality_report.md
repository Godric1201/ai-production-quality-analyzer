# AI Production Quality Analysis Report

## Executive Summary

This report analyzes a synthetic manufacturing quality dataset containing **5,000 production records**. The overall scrap rate is **7.16%**, corresponding to **358 scrap parts**.

The analysis identifies **M2** as the highest-risk machine, with a scrap rate of **14.47%**. The machine learning model highlights vibration, cycle time, temperature, and machine-specific effects as relevant drivers of scrap risk.

The project demonstrates how machine learning can support production quality monitoring, early risk detection, and structured process improvement in a manufacturing environment.

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
3. Training a Random Forest classifier
4. Evaluating classification performance
5. Exporting model metrics and feature importance values
6. Preparing dashboard-ready JSON data for visualization

Random Forest was selected because it performs well on tabular data, handles nonlinear interactions, and provides interpretable feature importance values.

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
- The classification threshold has not yet been optimized for production-specific cost trade-offs.

---

## Future Improvements

Potential next steps:

- Add threshold tuning to increase recall for early scrap warning.
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
