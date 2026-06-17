# Review Feedback Report

## Overall Summary

- Review results: `outputs\batch_review_results.csv`
- Feedback file: `data\batch_review_feedback.csv`
- Matched feedback rows: 10
- Purpose: demonstrate a synthetic feedback loop for industrial AI decision-support workflows.

## Feedback Coverage

- Review rows: 10
- Feedback rows: 10
- Matched rows: 10
- Missing feedback rows: 0
- Extra feedback rows: 0

Warnings:
- None

## Classification Counts

- FALSE_ALARM_REVIEW: 1
- MISSED_ISSUE: 1
- TRUE_NEGATIVE_MONITORING: 5
- TRUE_POSITIVE_REVIEW: 3

## Review Effectiveness

- Actual issue count: 4
- Review-required count: 4
- Missed issue count: 1
- False alarm count: 1
- Issue capture rate: 0.75
- False alarm rate among reviews: 0.25

## Missed Issues

| part_id   | scrap_probability   | risk_level   | review_decision     | root_cause_summary                                                                                      | review_notes                                                                            |
|:----------|:--------------------|:-------------|:--------------------|:--------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------|
| NB000003  | 23.23%              | Low          | STANDARD_MONITORING | The batch shows low scrap risk mainly due to high temperature, elevated vibration, and long cycle time. | Synthetic feedback marks a later issue that was not prioritized for engineering review. |

## False Alarms

| part_id   | scrap_probability   | risk_level   | root_cause_summary                                                                                       | review_notes                                                                                  |
|:----------|:--------------------|:-------------|:---------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------|
| NB000008  | 41.08%              | Medium       | The batch shows medium scrap risk mainly due to high temperature, high pressure, and elevated vibration. | Synthetic review did not confirm a quality issue and shows an inspection false alarm example. |

## Confirmed Issues and Suspected Drivers

- Elevated vibration: 2
- High temperature: 2
- Abnormal cycle time: 1
- High vibration: 1
- Long cycle time: 1
- Low pressure: 1
- Machine M2 risk pattern: 1
- Night shift production: 1

## Threshold Scenario Analysis

|   threshold |   true_positive_reviews |   false_alarm_reviews |   missed_issues |   true_negative_monitoring |   review_required_count |   issue_capture_rate |   false_alarm_rate_among_reviews |
|------------:|------------------------:|----------------------:|----------------:|---------------------------:|------------------------:|---------------------:|---------------------------------:|
|         0.3 |                       3 |                     2 |               1 |                          4 |                       5 |                 0.75 |                             0.4  |
|         0.4 |                       3 |                     1 |               1 |                          5 |                       4 |                 0.75 |                             0.25 |
|         0.5 |                       2 |                     0 |               2 |                          6 |                       2 |                 0.5  |                             0    |
|         0.6 |                       1 |                     0 |               3 |                          6 |                       1 |                 0.25 |                             0    |

## Engineering Interpretation

Missed issues are the highest-priority feedback cases because they show where the review workflow did not prioritize a later confirmed issue. False alarms show the cost of additional engineering attention. True positive reviews and true negative monitoring indicate where the illustrative workflow aligned with later synthetic feedback.

## Limitations

- The feedback file is synthetic and created for a portfolio prototype.
- This is not a validated factory quality system.
- The workflow evaluates engineering review prioritization, not autonomous control or disposition.
- Threshold scenario results are illustrative and should not be treated as production policy.
