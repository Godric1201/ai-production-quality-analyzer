# Batch Review Report

## Overall Summary

- Input file: `data\new_production_batch.csv`
- Reviewed rows: 10
- Review threshold: 0.40 (`cost_optimized_threshold`)
- Purpose: engineering review support for synthetic portfolio data, not a quality disposition authority.

## Review Decision Counts

- ADDITIONAL_MONITORING: 1
- ENGINEERING_REVIEW_REQUIRED: 4
- STANDARD_MONITORING: 5

## Risk Level Counts

- High: 1
- Low: 5
- Medium: 4

## Top Suspected Drivers

- Elevated vibration: 3
- High temperature: 3
- Night shift production: 2
- Abnormal cycle time: 1
- High humidity: 1
- High pressure: 1
- High vibration: 1
- Long cycle time: 1

## High-Priority Engineering Review Items

| part_id   | scrap_probability   | risk_level   | review_decision             | root_cause_summary                                                                                            | engineering_recommendations                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:----------|:--------------------|:-------------|:----------------------------|:--------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| NB000001  | 72.48%              | High         | ENGINEERING_REVIEW_REQUIRED | The batch shows high scrap risk mainly due to very high temperature, high vibration, and abnormal cycle time. | Audit temperature setpoints, cooling performance, and recent thermal alarms before further review action.; Inspect machine vibration sources and check for tool wear, imbalance, or loose fixtures.; Investigate cycle time deviation, material handling delays, and machine wear indicators.; Review process temperature control and verify cooling stability around the affected batch.; Inspect pressure regulation, tooling restrictions, and fixture condition.; Trend vibration for the machine and inspect tooling if the signal persists.; Review cycle time drift and compare against recent setup or operator changes.; Use operator guidance, checklist support, or supervisor sign-off for this setup.; Inspect M2 calibration, maintenance status, and recent quality history.; Apply additional process checks during night shift production.; Quarantine or sample-check material batch B4 and compare against supplier lot history.; Check humidity controls and confirm material storage conditions. |
| NB000005  | 51.16%              | Medium       | ENGINEERING_REVIEW_REQUIRED | The batch shows medium scrap risk mainly due to machine m2 risk pattern and night shift production.           | Inspect M2 calibration, maintenance status, and recent quality history.; Apply additional process checks during night shift production.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| NB000010  | 43.04%              | Medium       | ENGINEERING_REVIEW_REQUIRED | The batch shows medium scrap risk mainly due to high temperature, low pressure, and elevated vibration.       | Review process temperature control and verify cooling stability around the affected batch.; Check for leaks, feed variation, clamp issues, or insufficient process force.; Trend vibration for the machine and inspect tooling if the signal persists.; Review cycle time drift and compare against recent setup or operator changes.; Use operator guidance, checklist support, or supervisor sign-off for this setup.; Inspect M2 calibration, maintenance status, and recent quality history.; Check humidity controls and confirm material storage conditions.; Review shift handoff notes and confirm standard work adherence.                                                                                                                                                                                                                                                                                                                                                                                   |
| NB000008  | 41.08%              | Medium       | ENGINEERING_REVIEW_REQUIRED | The batch shows medium scrap risk mainly due to high temperature, high pressure, and elevated vibration.      | Review process temperature control and verify cooling stability around the affected batch.; Inspect pressure regulation, tooling restrictions, and fixture condition.; Trend vibration for the machine and inspect tooling if the signal persists.; Review cycle time drift and compare against recent setup or operator changes.; Use operator guidance, checklist support, or supervisor sign-off for this setup.; Quarantine or sample-check material batch B4 and compare against supplier lot history.; Monitor M4 quality trend and confirm process settings remain within control limits.; Review shift handoff notes and confirm standard work adherence.                                                                                                                                                                                                                                                                                                                                                     |

## Notes and Limitations

- This workflow uses a trained prototype model, configured thresholds, and illustrative RCA rules.
- Review decisions identify records for engineering attention, additional monitoring, or standard monitoring.
- The output supports review prioritization only and does not make quality dispositions.
- Scoring-input validation warnings:
- No scoring-input validation warnings.
