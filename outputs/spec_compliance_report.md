# Engineering Specification Compliance Report

## Overall Summary

- Input file: `data\new_production_batch.csv`
- Config file: `config\spec_requirements.yaml`
- Reviewed rows: 10
- Configured requirements: 10
- Purpose: engineering review and decision support for synthetic production records.

## Compliance Status Counts

- COMPLIANT: 5
- CRITICAL_VIOLATION: 1
- WARNING_VIOLATION: 4

## Most Common Violated Requirements

- CYCLE_TIME_MAX_WARNING (warning, cycle_time_s): 4
- TEMP_MAX_WARNING (warning, temperature_c): 4
- VIBRATION_MAX_WARNING (warning, vibration_mm_s): 4
- HUMIDITY_MAX_WARNING (warning, humidity_percent): 3
- LOW_OPERATOR_EXPERIENCE_WARNING (warning, operator_experience_years): 3
- PRESSURE_MAX_WARNING (warning, pressure_bar): 2
- CYCLE_TIME_MAX_CRITICAL (critical, cycle_time_s): 1
- PRESSURE_MIN_WARNING (warning, pressure_bar): 1

## Critical Violation Records

| part_id   | spec_compliance_status   | violated_requirement_ids                                                                                                                                                                                         | violation_summary                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | recommended_actions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|:----------|:-------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| NB000001  | CRITICAL_VIOLATION       | TEMP_MAX_WARNING; TEMP_MAX_CRITICAL; VIBRATION_MAX_WARNING; VIBRATION_MAX_CRITICAL; CYCLE_TIME_MAX_WARNING; CYCLE_TIME_MAX_CRITICAL; PRESSURE_MAX_WARNING; HUMIDITY_MAX_WARNING; LOW_OPERATOR_EXPERIENCE_WARNING | TEMP_MAX_WARNING: temperature_c=196.2 does not satisfy <= 190; TEMP_MAX_CRITICAL: temperature_c=196.2 does not satisfy <= 195; VIBRATION_MAX_WARNING: vibration_mm_s=3.35 does not satisfy <= 2.7; VIBRATION_MAX_CRITICAL: vibration_mm_s=3.35 does not satisfy <= 3.1; CYCLE_TIME_MAX_WARNING: cycle_time_s=54.1 does not satisfy <= 50; CYCLE_TIME_MAX_CRITICAL: cycle_time_s=54.1 does not satisfy <= 53; PRESSURE_MAX_WARNING: pressure_bar=6.55 does not satisfy <= 6.4; HUMIDITY_MAX_WARNING: humidity_percent=62 does not satisfy <= 60; LOW_OPERATOR_EXPERIENCE_WARNING: operator_experience_years=1.2 does not satisfy >= 2 | Review temperature control and cooling stability for affected records.; Escalate for engineering review and check thermal process settings.; Trend vibration and inspect tooling if the signal persists.; Perform engineering review of machine condition, tooling, and fixture stability.; Compare against setup records and operator notes.; Investigate machine condition and recent setup changes.; Inspect pressure regulation and tooling restrictions.; Check humidity controls and material storage conditions.; Use operator guidance, checklist support, or supervisor review. |

## Engineering Interpretation

Critical violations identify records with at least one configured critical limit breach. Warning violations identify records outside illustrative monitoring bands. Compliant records satisfied the configured requirements in this synthetic scenario.

## Notes and Limitations

- This report uses synthetic production data.
- Requirements are illustrative engineering process checks, not validated factory limits.
- This is not a validated factory quality release system.
- Compliance output is for engineering review and decision support only.
- The checker does not make autonomous quality dispositions.
