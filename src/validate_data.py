from __future__ import annotations

from pathlib import Path
import json
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "outputs" / "data_quality_report.json"
DEFAULT_MARKDOWN_REPORT_PATH = PROJECT_ROOT / "outputs" / "data_quality_report.md"

REQUIRED_COLUMNS = [
    "part_id",
    "machine_id",
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "shift",
    "material_batch",
    "operator_experience_years",
    "vibration_mm_s",
    "humidity_percent",
    "scrap",
]

NUMERIC_COLUMNS = [
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "operator_experience_years",
    "vibration_mm_s",
    "humidity_percent",
]

EXPECTED_CATEGORIES = {
    "machine_id": ["M1", "M2", "M3", "M4"],
    "shift": ["early", "late", "night"],
    "material_batch": ["B1", "B2", "B3", "B4", "B5"],
}

# These are illustrative monitoring ranges for the synthetic portfolio dataset.
ENGINEERING_RANGES = {
    "temperature_c": (160, 210),
    "pressure_bar": (4.0, 7.5),
    "cycle_time_s": (30, 70),
    "operator_experience_years": (0, 20),
    "vibration_mm_s": (0, 6),
    "humidity_percent": (0, 100),
}

STATUS_ORDER = {
    "PASS": 0,
    "WARNING": 1,
    "FAIL": 2,
}


def make_check(name: str, status: str, message: str, details: dict | None = None) -> dict:
    """Create a normalized validation check record."""
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def worst_status(statuses: list[str]) -> str:
    """Return the most severe status from a list of status strings."""
    if not statuses:
        return "PASS"

    return max(statuses, key=lambda status: STATUS_ORDER[status])


def is_missing(series: pd.Series) -> pd.Series:
    """Treat null values and blank strings as missing."""
    return series.isna() | series.astype("string").str.strip().eq("")


def load_dataset(path: Path) -> pd.DataFrame:
    """Load the production quality dataset."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    return pd.read_csv(path)


def validate_schema(df: pd.DataFrame) -> list[dict]:
    """Validate required columns, unexpected columns, and empty datasets."""
    checks = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    unexpected_columns = [column for column in df.columns if column not in REQUIRED_COLUMNS]

    if missing_columns:
        checks.append(
            make_check(
                "schema_validation",
                "FAIL",
                "Required columns are missing.",
                {"missing_columns": missing_columns},
            )
        )
    else:
        checks.append(
            make_check(
                "schema_validation",
                "PASS",
                "All required columns are present.",
                {"missing_columns": []},
            )
        )

    if unexpected_columns:
        checks.append(
            make_check(
                "unexpected_columns",
                "WARNING",
                "Unexpected columns are present.",
                {"unexpected_columns": unexpected_columns},
            )
        )
    else:
        checks.append(
            make_check(
                "unexpected_columns",
                "PASS",
                "No unexpected columns found.",
                {"unexpected_columns": []},
            )
        )

    if len(df) == 0:
        checks.append(
            make_check(
                "empty_dataset",
                "FAIL",
                "Dataset has zero rows.",
                {"row_count": 0},
            )
        )
    else:
        checks.append(
            make_check(
                "empty_dataset",
                "PASS",
                "Dataset contains rows.",
                {"row_count": int(len(df))},
            )
        )

    return checks


def validate_missing_values(df: pd.DataFrame) -> list[dict]:
    """Validate missing values for each required column."""
    row_count = len(df)
    column_details = []
    statuses = []

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            continue

        missing_count = int(is_missing(df[column]).sum())
        missing_percentage = 0.0 if row_count == 0 else missing_count / row_count

        if missing_percentage == 0:
            status = "PASS"
        elif missing_percentage <= 0.05:
            status = "WARNING"
        else:
            status = "FAIL"

        statuses.append(status)
        column_details.append(
            {
                "column": column,
                "missing_count": missing_count,
                "missing_percentage": round(missing_percentage, 4),
                "status": status,
            }
        )

    status = worst_status(statuses)
    if status == "PASS":
        message = "No missing values found in required columns."
    elif status == "WARNING":
        message = "Missing values found within warning tolerance."
    else:
        message = "Missing values exceed failure threshold."

    return [
        make_check(
            "missing_values",
            status,
            message,
            {"columns": column_details},
        )
    ]


def validate_numeric_columns(df: pd.DataFrame) -> list[dict]:
    """Validate that non-empty numeric column values can be converted to numbers."""
    details = []
    invalid_columns = []

    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            continue

        missing_mask = is_missing(df[column])
        non_empty = df.loc[~missing_mask, column]
        numeric_values = pd.to_numeric(non_empty, errors="coerce")
        invalid_mask = numeric_values.isna()
        invalid_values = non_empty[invalid_mask].astype(str).drop_duplicates().head(5).tolist()
        invalid_count = int(invalid_mask.sum())

        if invalid_count:
            invalid_columns.append(column)

        details.append(
            {
                "column": column,
                "invalid_count": invalid_count,
                "invalid_examples": invalid_values,
                "status": "FAIL" if invalid_count else "PASS",
            }
        )

    if invalid_columns:
        return [
            make_check(
                "numeric_type_validation",
                "FAIL",
                "Invalid numeric values found.",
                {"columns": details, "invalid_columns": invalid_columns},
            )
        ]

    return [
        make_check(
            "numeric_type_validation",
            "PASS",
            "Numeric columns can be converted to numbers.",
            {"columns": details},
        )
    ]


def validate_categorical_columns(df: pd.DataFrame) -> list[dict]:
    """Validate categorical columns against expected synthetic categories."""
    details = []
    unexpected_columns = []

    for column, expected_values in EXPECTED_CATEGORIES.items():
        if column not in df.columns:
            continue

        observed = df.loc[~is_missing(df[column]), column].astype(str)
        unexpected_values = sorted(set(observed) - set(expected_values))

        if unexpected_values:
            unexpected_columns.append(column)

        details.append(
            {
                "column": column,
                "expected_values": expected_values,
                "unexpected_values": unexpected_values,
                "status": "WARNING" if unexpected_values else "PASS",
            }
        )

    if unexpected_columns:
        return [
            make_check(
                "categorical_validation",
                "WARNING",
                "Unexpected categorical values found.",
                {"columns": details, "unexpected_columns": unexpected_columns},
            )
        ]

    return [
        make_check(
            "categorical_validation",
            "PASS",
            "Categorical values match expected categories.",
            {"columns": details},
        )
    ]


def validate_target_column(df: pd.DataFrame) -> list[dict]:
    """Validate target values and summarize target distribution."""
    target_column = "scrap"
    if target_column not in df.columns:
        return [
            make_check(
                "target_validation",
                "FAIL",
                "Target column is missing.",
                {"target_column": target_column},
            )
        ]

    non_empty = df.loc[~is_missing(df[target_column]), target_column]
    numeric_target = pd.to_numeric(non_empty, errors="coerce")
    valid_mask = numeric_target.isin([0, 1])
    invalid_values = non_empty[~valid_mask].astype(str).drop_duplicates().head(10).tolist()

    total_rows = int(len(df))
    scrap_count = int((numeric_target == 1).sum())
    good_count = int((numeric_target == 0).sum())
    scrap_rate = 0.0 if total_rows == 0 else scrap_count / total_rows

    details = {
        "target_column": target_column,
        "total_rows": total_rows,
        "good_count": good_count,
        "scrap_count": scrap_count,
        "scrap_rate": round(scrap_rate, 4),
        "invalid_values": invalid_values,
    }

    if invalid_values:
        return [
            make_check(
                "target_validation",
                "FAIL",
                "Target column contains values other than 0 or 1.",
                details,
            )
        ]

    if total_rows > 0 and (scrap_rate < 0.03 or scrap_rate > 0.25):
        return [
            make_check(
                "target_validation",
                "WARNING",
                "Scrap rate is outside the expected interpretation range.",
                details,
            )
        ]

    return [
        make_check(
            "target_validation",
            "PASS",
            "Target column contains only 0 and 1 values.",
            details,
        )
    ]


def validate_engineering_ranges(df: pd.DataFrame) -> list[dict]:
    """Validate numeric values against plausible synthetic monitoring ranges."""
    details = []
    columns_outside_range = []

    for column, (minimum, maximum) in ENGINEERING_RANGES.items():
        if column not in df.columns:
            continue

        missing_mask = is_missing(df[column])
        numeric_values = pd.to_numeric(df.loc[~missing_mask, column], errors="coerce")
        below_count = int((numeric_values < minimum).sum())
        above_count = int((numeric_values > maximum).sum())
        outside_count = below_count + above_count

        if outside_count:
            columns_outside_range.append(column)

        details.append(
            {
                "column": column,
                "minimum": minimum,
                "maximum": maximum,
                "below_range_count": below_count,
                "above_range_count": above_count,
                "outside_range_count": outside_count,
                "status": "WARNING" if outside_count else "PASS",
            }
        )

    if columns_outside_range:
        return [
            make_check(
                "engineering_plausibility",
                "WARNING",
                "Values outside illustrative engineering ranges found.",
                {
                    "columns": details,
                    "columns_outside_range": columns_outside_range,
                },
            )
        ]

    return [
        make_check(
            "engineering_plausibility",
            "PASS",
            "Numeric values are within illustrative engineering ranges.",
            {"columns": details},
        )
    ]


def validate_duplicate_part_ids(df: pd.DataFrame) -> list[dict]:
    """Warn when duplicate part identifiers exist."""
    if "part_id" not in df.columns:
        return []

    duplicates = df.loc[df["part_id"].duplicated(keep=False), "part_id"]
    duplicate_values = duplicates.astype(str).drop_duplicates().head(10).tolist()
    duplicate_count = int(duplicates.shape[0])

    if duplicate_count:
        return [
            make_check(
                "duplicate_part_id",
                "WARNING",
                "Duplicate part_id values found.",
                {
                    "duplicate_row_count": duplicate_count,
                    "duplicate_examples": duplicate_values,
                },
            )
        ]

    return [
        make_check(
            "duplicate_part_id",
            "PASS",
            "No duplicate part_id values found.",
            {"duplicate_row_count": 0, "duplicate_examples": []},
        )
    ]


def build_report(df: pd.DataFrame, checks: list[dict]) -> dict:
    """Build a structured machine-readable report from validation checks."""
    status = worst_status([check["status"] for check in checks])
    warnings = [check for check in checks if check["status"] == "WARNING"]
    errors = [check for check in checks if check["status"] == "FAIL"]
    target_check = next(
        (check for check in checks if check["name"] == "target_validation"),
        {"details": {}},
    )
    missing_check = next(
        (check for check in checks if check["name"] == "missing_values"),
        {"details": {}},
    )
    categorical_check = next(
        (check for check in checks if check["name"] == "categorical_validation"),
        {"details": {}},
    )
    engineering_check = next(
        (check for check in checks if check["name"] == "engineering_plausibility"),
        {"details": {}},
    )

    return {
        "status": status,
        "input_path": str(DEFAULT_INPUT_PATH.relative_to(PROJECT_ROOT)),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "target_summary": target_check.get("details", {}),
        "missing_values": missing_check.get("details", {}),
        "categorical_issues": categorical_check.get("details", {}),
        "engineering_range_warnings": engineering_check.get("details", {}),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }


def write_json_report(report: dict, path: Path) -> None:
    """Write the JSON data quality report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


def format_status(status: str) -> str:
    """Format a status for Markdown output."""
    return f"**{status}**"


def get_check(report: dict, name: str) -> dict:
    """Find a check in a report by name."""
    return next((check for check in report["checks"] if check["name"] == name), {})


def write_markdown_report(report: dict, path: Path) -> None:
    """Write a concise Markdown data quality report."""
    schema_check = get_check(report, "schema_validation")
    unexpected_check = get_check(report, "unexpected_columns")
    missing_check = get_check(report, "missing_values")
    numeric_check = get_check(report, "numeric_type_validation")
    categorical_check = get_check(report, "categorical_validation")
    engineering_check = get_check(report, "engineering_plausibility")
    duplicate_check = get_check(report, "duplicate_part_id")
    target_summary = report.get("target_summary", {})

    lines = [
        "# Data Quality Report",
        "",
        "## Overall Status",
        "",
        f"Status: {format_status(report['status'])}",
        "",
        "## Dataset Summary",
        "",
        f"- Input path: `{report['input_path']}`",
        f"- Rows: {report['row_count']}",
        f"- Columns: {report['column_count']}",
        "",
        "## Target Distribution",
        "",
        f"- Target column: `{target_summary.get('target_column', 'scrap')}`",
        f"- Good count: {target_summary.get('good_count', 0)}",
        f"- Scrap count: {target_summary.get('scrap_count', 0)}",
        f"- Scrap rate: {target_summary.get('scrap_rate', 0):.4f}",
        f"- Status: {format_status(get_check(report, 'target_validation').get('status', 'FAIL'))}",
        "",
        "## Schema Checks",
        "",
        f"- Required columns: {format_status(schema_check.get('status', 'FAIL'))} - {schema_check.get('message', '')}",
        f"- Unexpected columns: {format_status(unexpected_check.get('status', 'FAIL'))} - {unexpected_check.get('message', '')}",
        f"- Duplicate part_id: {format_status(duplicate_check.get('status', 'PASS'))} - {duplicate_check.get('message', '')}",
        "",
        "## Missing Values",
        "",
        f"Status: {format_status(missing_check.get('status', 'FAIL'))}",
        "",
        "| Column | Missing Count | Missing Percentage | Status |",
        "| --- | ---: | ---: | --- |",
    ]

    for detail in missing_check.get("details", {}).get("columns", []):
        lines.append(
            "| {column} | {missing_count} | {missing_percentage:.4f} | {status} |".format(
                **detail
            )
        )

    lines.extend(
        [
            "",
            "## Numeric Checks",
            "",
            f"Status: {format_status(numeric_check.get('status', 'FAIL'))} - {numeric_check.get('message', '')}",
            "",
            "| Column | Invalid Count | Status |",
            "| --- | ---: | --- |",
        ]
    )

    for detail in numeric_check.get("details", {}).get("columns", []):
        lines.append(f"| {detail['column']} | {detail['invalid_count']} | {detail['status']} |")

    lines.extend(
        [
            "",
            "## Categorical Checks",
            "",
            f"Status: {format_status(categorical_check.get('status', 'FAIL'))} - {categorical_check.get('message', '')}",
            "",
            "| Column | Unexpected Values | Status |",
            "| --- | --- | --- |",
        ]
    )

    for detail in categorical_check.get("details", {}).get("columns", []):
        unexpected_values = ", ".join(detail["unexpected_values"]) or "None"
        lines.append(f"| {detail['column']} | {unexpected_values} | {detail['status']} |")

    lines.extend(
        [
            "",
            "## Engineering Plausibility Checks",
            "",
            f"Status: {format_status(engineering_check.get('status', 'FAIL'))} - {engineering_check.get('message', '')}",
            "",
            "| Column | Range | Below | Above | Status |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )

    for detail in engineering_check.get("details", {}).get("columns", []):
        expected_range = f"{detail['minimum']} to {detail['maximum']}"
        lines.append(
            "| {column} | {expected_range} | {below_range_count} | {above_range_count} | {status} |".format(
                expected_range=expected_range,
                **detail,
            )
        )

    if report["status"] == "FAIL":
        conclusion = "Validation failed. Stop the pipeline and review errors before training."
    elif report["status"] == "WARNING":
        conclusion = "Validation completed with warnings. The dataset can be used, but review warnings before interpreting results."
    else:
        conclusion = "Validation passed. The dataset is ready for the downstream prototype pipeline."

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            conclusion,
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_validation(input_path: Path = DEFAULT_INPUT_PATH) -> dict:
    """Run all validation checks and return a structured report."""
    df = load_dataset(input_path)
    checks = []

    checks.extend(validate_schema(df))
    checks.extend(validate_missing_values(df))
    checks.extend(validate_numeric_columns(df))
    checks.extend(validate_target_column(df))
    checks.extend(validate_categorical_columns(df))
    checks.extend(validate_engineering_ranges(df))
    checks.extend(validate_duplicate_part_ids(df))

    report = build_report(df, checks)
    report["input_path"] = (
        str(input_path.relative_to(PROJECT_ROOT))
        if input_path.is_relative_to(PROJECT_ROOT)
        else str(input_path)
    )
    return report


def main() -> int:
    report = run_validation(DEFAULT_INPUT_PATH)
    write_json_report(report, DEFAULT_JSON_REPORT_PATH)
    write_markdown_report(report, DEFAULT_MARKDOWN_REPORT_PATH)

    print("Data validation completed.")
    print(f"Status: {report['status']}")
    print(f"JSON report: {DEFAULT_JSON_REPORT_PATH}")
    print(f"Markdown report: {DEFAULT_MARKDOWN_REPORT_PATH}")

    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
