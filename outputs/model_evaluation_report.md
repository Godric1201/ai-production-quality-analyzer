# Model Evaluation & Risk Bands

This report evaluates the scrap-risk model as an early-warning signal for engineering review.

## Summary

- ROC-AUC: 0.7129
- PR-AUC: 0.2099
- Baseline scrap rate: 0.0712
- Selected threshold: 0.3
- Cost-optimized threshold: 0.4
- Model role: early_warning_decision_support

## Risk Bands

| risk_band   |   row_count |   actual_scrap_count |   actual_scrap_rate |   average_predicted_risk | review_priority             |
|:------------|------------:|---------------------:|--------------------:|-------------------------:|:----------------------------|
| Low risk    |         659 |                   23 |              0.0349 |                   0.2443 | Standard monitoring         |
| Medium risk |         463 |                   40 |              0.0864 |                   0.372  | Additional monitoring       |
| High risk   |         128 |                   26 |              0.2031 |                   0.569  | Engineering review priority |

## Threshold Trade-off

Lower thresholds catch more scrap but create more false alarms. Higher thresholds reduce false alarms but miss more scrap. The cost-optimized threshold is used as a decision-support trade-off, not as a final acceptance rule.

|   threshold |   recall |   false_positive |   false_negative |   total_cost |
|------------:|---------:|-----------------:|-----------------:|-------------:|
|        0.4  |   0.4831 |              225 |               46 |         6850 |
|        0.35 |   0.5843 |              329 |               37 |         6990 |
|        0.45 |   0.3708 |              157 |               56 |         7170 |
|        0.5  |   0.2921 |              102 |               63 |         7320 |
|        0.3  |   0.7416 |              525 |               23 |         7550 |

## Interpretation

The model is useful as an early-warning signal for engineering review, but its precision and recall trade-offs mean it should not be treated as an autonomous release or certification decision.
