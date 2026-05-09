# AI Production Quality Analyzer

Machine Learning Dashboard for Scrap Prediction and Process Improvement

## Overview

This project demonstrates an end-to-end AI workflow for manufacturing quality analytics. It uses a synthetic production dataset to predict scrap risk, identify key process drivers, visualize quality patterns, and generate engineering recommendations.

The goal is to show how machine learning can support production quality monitoring and process improvement in a manufacturing environment.

## Problem Statement

In manufacturing, scrap parts increase production cost, reduce process stability, and create additional inspection or rework effort. Quality engineers need to identify which machines, process parameters, or operating conditions contribute most to scrap risk.

This project addresses the following question:

> Can machine learning help identify high-risk production conditions and support structured process improvement?

## Project Output

The project produces four main outputs:

- A synthetic manufacturing quality dataset
- A trained Random Forest scrap prediction model
- A static HTML/CSS/JavaScript analytics dashboard
- An automated Markdown quality analysis report

## Dashboard Preview

The dashboard includes KPI cards, machine-level scrap analysis, shift comparison, temperature risk analysis, feature importance visualization, and engineering recommendations.

![Dashboard Preview](docs/dashboard-preview.png)

If the preview image is not available, run the dashboard locally using the instructions below.

## Key Features

- Synthetic production data generation with realistic manufacturing risk patterns
- Scrap prediction using a Random Forest classifier
- One-hot encoding for categorical production variables
- Feature importance analysis for process driver identification
- KPI dashboard for production quality monitoring
- Engineering recommendations based on model and process analysis
- Automated quality report generation in Markdown format

## Dataset

The dataset is synthetic but designed to simulate realistic production quality data.

Each row represents one produced part.

### Columns

| Column | Description |
|---|---|
| `part_id` | Unique part identifier |
| `machine_id` | Machine used for production |
| `temperature_c` | Process temperature in degrees Celsius |
| `pressure_bar` | Process pressure in bar |
| `cycle_time_s` | Production cycle time in seconds |
| `shift` | Production shift: early, late, or night |
| `material_batch` | Material batch identifier |
| `operator_experience_years` | Operator experience in years |
| `vibration_mm_s` | Machine vibration level |
| `humidity_percent` | Ambient humidity |
| `scrap` | Target variable: 1 = scrap, 0 = good part |

### Synthetic Risk Logic

The data generation process includes engineered quality patterns:

- Machine M2 has a higher scrap risk than other machines.
- Temperature above 190°C increases scrap risk.
- Cycle time above 50 seconds increases scrap risk.
- Night shift has slightly higher scrap risk.
- Higher vibration increases scrap risk.
- More operator experience slightly reduces scrap risk.

## Machine Learning Approach

The machine learning pipeline uses a Random Forest classifier to predict whether a part is likely to become scrap.

Pipeline steps:

1. Load production quality data
2. Split features and target variable
3. One-hot encode categorical features
4. Train a Random Forest classifier
5. Evaluate model performance
6. Export metrics, feature importances, and trained model
7. Export dashboard-ready JSON data

Random Forest was selected because it performs well on tabular data, handles nonlinear feature interactions, and provides interpretable feature importance values.

## Model Results

Current model performance:

| Metric | Value |
|---|---:|
| Accuracy | 0.868 |
| Precision | 0.203 |
| Recall | 0.292 |
| F1 Score | 0.240 |

The model achieves high overall accuracy, but the F1 score is lower because scrap cases are relatively rare compared with good parts. This is a typical issue in quality prediction problems with imbalanced production data.

For a real production use case, recall and threshold tuning would be important because missing defective parts may be more costly than generating false alarms.

## Key Findings

The analysis identified the following quality patterns:

- Overall scrap rate: 7.16%
- Highest-risk machine: M2
- M2 scrap rate: 14.47%
- Top model drivers include:
  - machine vibration
  - cycle time
  - process temperature
  - operator experience
  - machine-specific effects

## Engineering Recommendations

Based on the analysis, the following actions are recommended:

1. Inspect and calibrate machine M2.
2. Monitor machine vibration as an indicator of unstable machine condition or tool wear.
3. Investigate cycle time deviations above 50 seconds.
4. Review process temperature control, especially above 190°C.
5. Use additional checklists or process guidance for high-risk production conditions.

## Tech Stack

| Area | Technology |
|---|---|
| Data processing | Python, pandas, NumPy |
| Machine learning | scikit-learn |
| Model persistence | joblib |
| Dashboard | HTML, CSS, JavaScript |
| Charts | Chart.js |
| Report generation | Markdown |
| Version control | Git |

## Repository Structure

```text
ai-production-quality-analyzer/
│
├── data/
│   └── production_quality_data.csv
│
├── src/
│   ├── generate_data.py
│   ├── train_model.py
│   ├── analyze_quality.py
│   └── export_dashboard_data.py
│
├── dashboard/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── dashboard_data.json
│
├── outputs/
│   ├── feature_importance.csv
│   ├── model_metrics.json
│   ├── quality_report.md
│   └── scrap_prediction_model.joblib
│
├── requirements.txt
└── README.md