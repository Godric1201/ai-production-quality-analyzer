# Data Quality Report

## Overall Status

Status: **PASS**

## Dataset Summary

- Input path: `data\production_quality_data.csv`
- Rows: 5000
- Columns: 11

## Target Distribution

- Target column: `scrap`
- Good count: 4642
- Scrap count: 358
- Scrap rate: 0.0716
- Status: **PASS**

## Schema Checks

- Required columns: **PASS** - All required columns are present.
- Unexpected columns: **PASS** - No unexpected columns found.
- Duplicate part_id: **PASS** - No duplicate part_id values found.

## Missing Values

Status: **PASS**

| Column | Missing Count | Missing Percentage | Status |
| --- | ---: | ---: | --- |
| part_id | 0 | 0.0000 | PASS |
| machine_id | 0 | 0.0000 | PASS |
| temperature_c | 0 | 0.0000 | PASS |
| pressure_bar | 0 | 0.0000 | PASS |
| cycle_time_s | 0 | 0.0000 | PASS |
| shift | 0 | 0.0000 | PASS |
| material_batch | 0 | 0.0000 | PASS |
| operator_experience_years | 0 | 0.0000 | PASS |
| vibration_mm_s | 0 | 0.0000 | PASS |
| humidity_percent | 0 | 0.0000 | PASS |
| scrap | 0 | 0.0000 | PASS |

## Numeric Checks

Status: **PASS** - Numeric columns can be converted to numbers.

| Column | Invalid Count | Status |
| --- | ---: | --- |
| temperature_c | 0 | PASS |
| pressure_bar | 0 | PASS |
| cycle_time_s | 0 | PASS |
| operator_experience_years | 0 | PASS |
| vibration_mm_s | 0 | PASS |
| humidity_percent | 0 | PASS |

## Categorical Checks

Status: **PASS** - Categorical values match expected categories.

| Column | Unexpected Values | Status |
| --- | --- | --- |
| machine_id | None | PASS |
| shift | None | PASS |
| material_batch | None | PASS |

## Engineering Plausibility Checks

Status: **PASS** - Numeric values are within illustrative engineering ranges.

| Column | Range | Below | Above | Status |
| --- | --- | ---: | ---: | --- |
| temperature_c | 160 to 210 | 0 | 0 | PASS |
| pressure_bar | 4.0 to 7.5 | 0 | 0 | PASS |
| cycle_time_s | 30 to 70 | 0 | 0 | PASS |
| operator_experience_years | 0 to 20 | 0 | 0 | PASS |
| vibration_mm_s | 0 to 6 | 0 | 0 | PASS |
| humidity_percent | 0 to 100 | 0 | 0 | PASS |

## Conclusion

Validation passed. The dataset is ready for the downstream prototype pipeline.
