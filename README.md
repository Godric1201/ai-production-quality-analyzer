# AI Production Quality Analyzer

Industrial quality decision-support prototype for manufacturing data validation, scrap-risk prediction, engineering rule checks, and review traceability.

Live dashboard demo: https://godric1201.github.io/ai-production-quality-analyzer/

Built with Python, pandas, scikit-learn, YAML-based engineering rules, and a static HTML/CSS/JS dashboard.

This is an interview-ready portfolio prototype using a synthetic manufacturing dataset. It is not a validated production factory AI system.

## Project Summary

This project demonstrates how manufacturing quality data can be transformed into an engineering decision-support workflow. It validates production data, trains a scrap-risk early-warning model, evaluates threshold trade-offs, applies configurable RCA and specification rules, reviews new production batches, compares review decisions with later feedback, and exposes the workflow through a static dashboard.

## Dashboard Preview

![Dashboard overview](docs/screenshots/dashboard-overview.png)

![High-risk RCA investigation table](docs/screenshots/rca-investigation-table.png)

![Model threshold and cost analysis](docs/screenshots/model-threshold-cost.png)

## What This Project Demonstrates

- Data quality validation before model training.
- Tabular ML model for scrap-risk early warning.
- Threshold tuning and cost-based trade-off reasoning.
- Risk-band evaluation instead of blindly trusting accuracy.
- Configurable engineering rulebook from YAML files.
- Specification compliance checks.
- Root cause analysis support.
- Batch review workflow.
- Feedback loop for missed issues and false alarms.
- Traceable engineering review case in the dashboard.

## Dashboard Demo

Live demo: https://godric1201.github.io/ai-production-quality-analyzer/

The dashboard is a static portfolio demo generated from repository outputs. It includes:

1. Workflow Overview
2. Engineering Rulebook / Configured Checks
3. Model Evaluation & Risk Bands
4. Engineering Review Trace
5. High-Risk RCA / Recommendations
6. Model performance and threshold analysis

The public dashboard is deployed with GitHub Pages from generated dashboard files in the repository.

## Workflow Architecture

```text
Synthetic production dataset
        |
        v
Data validation
        |
        v
Scrap-risk model training
        |
        v
Model comparison + threshold tuning
        |
        v
Cost-based threshold analysis
        |
        v
Model evaluation + risk bands
        |
        v
Batch review + RCA
        |
        v
Specification compliance checks
        |
        v
Feedback evaluation
        |
        v
Dashboard + engineering review trace
```

## Repository Structure

| Folder | Purpose |
|---|---|
| `src/` | Python pipeline scripts |
| `config/` | YAML-based RCA and specification rules |
| `data/` | Synthetic dataset and new batch examples |
| `outputs/` | Generated reports, model outputs, and evaluation files |
| `dashboard/` | Static dashboard files |
| `tests/` | Verification scripts |
| `.github/` | GitHub Pages deployment workflow |

## How to Run Locally

Windows PowerShell:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/run_pipeline.py
python -m http.server 8000
```

macOS / Linux activation:

```bash
source .venv/bin/activate
```

Open the local dashboard:

```text
http://localhost:8000/dashboard/
```

## Key Outputs

- `outputs/data_quality_report.md`
- `outputs/model_evaluation_report.md`
- `outputs/batch_review_report.md`
- `outputs/spec_compliance_report.md`
- `outputs/review_feedback_report.md`
- `dashboard/dashboard_data.json`

## Limitations

- Uses synthetic manufacturing data, not real factory data.
- Rules and thresholds are illustrative.
- The model is evaluated as early-warning decision support, not final quality approval.
- The system does not control production, certify parts, or replace engineers.
- No real MES, SCADA, PLC, QMS, or shop-floor integration is included.
- Not production-ready and not validated for real factory deployment.
- A real deployment would require domain expert validation, real production data, governance, monitoring, and integration with shop-floor systems.

## Relevance to Industrial AI

This prototype focuses on the workflow around industrial AI, not just the model. It shows how engineering context, configurable rules, specification checks, feedback, and traceability can be combined into a decision-support system for manufacturing quality review.

The project is relevant to industrial AI and engineering data roles because it connects model outputs with review routing, transparent rule checks, threshold trade-offs, and feedback evaluation rather than presenting prediction scores in isolation.
