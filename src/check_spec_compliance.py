from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "new_production_batch.csv"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "spec_requirements.yaml"
DEFAULT_OUTPUT_CSV_PATH = PROJECT_ROOT / "outputs" / "spec_compliance_results.csv"
DEFAULT_OUTPUT_JSON_PATH = PROJECT_ROOT / "outputs" / "spec_compliance_summary.json"
DEFAULT_OUTPUT_MARKDOWN_PATH = PROJECT_ROOT / "outputs" / "spec_compliance_report.md"

SUPPORTED_OPERATORS = {"<=", "<", ">=", ">", "==", "!="}
SUPPORTED_SEVERITIES = {"info", "warning", "critical"}
SUPPORTED_REQUIREMENT_TYPES = {"numeric_limit"}

REQUIRED_REQUIREMENT_FIELDS = [
    "id",
    "parameter",
    "type",
    "operator",
    "value",
    "severity",
    "requirement_text",
]


def resolve_path(path_value: str | Path) -> Path:
    """Resolve CLI paths relative to the project root when needed."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def display_path(path: Path) -> str:
    """Return a compact path string for generated reports."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_input_data(path: Path) -> pd.DataFrame:
    """Load the production batch input for specification checks."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found at {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("Input file has zero rows.")
    return df


def load_spec_config(path: Path) -> dict:
    """Load and validate the engineering specification config."""
    if not path.exists():
        raise FileNotFoundError(f"Specification config file not found at {path}")

    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Specification config must be a YAML mapping.")

    requirements = config.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("Specification config must contain a non-empty 'requirements' list.")

    for index, requirement in enumerate(requirements, start=1):
        validate_requirement(requirement, index)

    return config


def validate_requirement(requirement: dict, index: int) -> None:
    """Validate one configured specification requirement."""
    if not isinstance(requirement, dict):
        raise ValueError(f"Requirement #{index} must be a mapping.")

    missing_fields = [
        field for field in REQUIRED_REQUIREMENT_FIELDS if field not in requirement
    ]
    if missing_fields:
        raise ValueError(
            f"Requirement #{index} is missing required fields: {missing_fields}"
        )

    requirement_type = requirement["type"]
    if requirement_type not in SUPPORTED_REQUIREMENT_TYPES:
        raise ValueError(
            f"Requirement '{requirement['id']}' has unsupported type '{requirement_type}'."
        )

    operator = requirement["operator"]
    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(
            f"Requirement '{requirement['id']}' has unsupported operator '{operator}'."
        )

    severity = str(requirement["severity"]).lower()
    if severity not in SUPPORTED_SEVERITIES:
        raise ValueError(
            f"Requirement '{requirement['id']}' has unsupported severity '{requirement['severity']}'."
        )
    requirement["severity"] = severity

    try:
        float(requirement["value"])
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Requirement '{requirement['id']}' must define a numeric value."
        ) from error


def validate_input_against_config(df: pd.DataFrame, requirements: list[dict]) -> None:
    """Validate that all configured parameters are available and numeric."""
    required_parameters = sorted({requirement["parameter"] for requirement in requirements})
    missing_parameters = [
        parameter for parameter in required_parameters if parameter not in df.columns
    ]
    if missing_parameters:
        raise ValueError(
            f"Input file is missing required specification parameters: {missing_parameters}"
        )

    invalid_numeric: dict[str, list[str]] = {}
    for parameter in required_parameters:
        values = pd.to_numeric(df[parameter], errors="coerce")
        invalid_mask = values.isna() & df[parameter].notna()
        invalid_values = (
            df.loc[invalid_mask, parameter].astype(str).drop_duplicates().head(5).tolist()
        )
        if invalid_values:
            invalid_numeric[parameter] = invalid_values

    if invalid_numeric:
        raise ValueError(
            f"Input file has non-numeric values for specification parameters: {invalid_numeric}"
        )


def compare_values(actual_value: float, operator: str, limit_value: float) -> bool:
    """Return whether a numeric requirement is satisfied."""
    if operator == "<=":
        return actual_value <= limit_value
    if operator == "<":
        return actual_value < limit_value
    if operator == ">=":
        return actual_value >= limit_value
    if operator == ">":
        return actual_value > limit_value
    if operator == "==":
        return actual_value == limit_value
    if operator == "!=":
        return actual_value != limit_value
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_requirement(row: pd.Series, requirement: dict) -> dict | None:
    """Evaluate one numeric specification requirement against one record."""
    actual_value = float(row[requirement["parameter"]])
    limit_value = float(requirement["value"])

    if compare_values(actual_value, requirement["operator"], limit_value):
        return None

    return {
        "requirement_id": requirement["id"],
        "parameter": requirement["parameter"],
        "actual_value": actual_value,
        "operator": requirement["operator"],
        "limit_value": limit_value,
        "severity": requirement["severity"],
        "requirement_text": requirement["requirement_text"],
        "engineering_rationale": requirement.get("engineering_rationale", ""),
        "recommended_action": requirement.get("recommended_action", ""),
    }


def compliance_status(violations: list[dict]) -> str:
    """Convert violation severities into a record-level compliance status."""
    if any(violation["severity"] == "critical" for violation in violations):
        return "CRITICAL_VIOLATION"
    if any(violation["severity"] == "warning" for violation in violations):
        return "WARNING_VIOLATION"
    return "COMPLIANT"


def format_violation_summary(violations: list[dict]) -> str:
    """Create a concise readable violation summary."""
    return "; ".join(
        "{requirement_id}: {parameter}={actual_value:g} does not satisfy {operator} {limit_value:g}".format(
            **violation
        )
        for violation in violations
    )


def format_unique(values: list[str]) -> str:
    """Return semicolon-separated unique values while preserving order."""
    formatted: list[str] = []
    for value in values:
        if value and value not in formatted:
            formatted.append(value)
    return "; ".join(formatted)


def evaluate_compliance(df: pd.DataFrame, requirements: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    """Evaluate all records against configured specification requirements."""
    results = df.copy()
    all_record_violations = []
    result_rows = []

    for _, row in results.iterrows():
        violations = [
            violation
            for requirement in requirements
            if (violation := evaluate_requirement(row, requirement)) is not None
        ]
        all_record_violations.append(
            {
                "part_id": str(row.get("part_id", "")),
                "violations": violations,
            }
        )

        critical_count = sum(
            1 for violation in violations if violation["severity"] == "critical"
        )
        warning_count = sum(
            1 for violation in violations if violation["severity"] == "warning"
        )
        result_rows.append(
            {
                "spec_compliance_status": compliance_status(violations),
                "violation_count": len(violations),
                "critical_violation_count": critical_count,
                "warning_violation_count": warning_count,
                "violated_requirement_ids": format_unique(
                    [violation["requirement_id"] for violation in violations]
                ),
                "violation_summary": format_violation_summary(violations),
                "recommended_actions": format_unique(
                    [violation["recommended_action"] for violation in violations]
                ),
            }
        )

    return pd.concat([results, pd.DataFrame(result_rows)], axis=1), all_record_violations


def count_values(series: pd.Series) -> dict:
    """Return deterministic value counts for JSON output."""
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def build_violation_counts_by_requirement(
    requirements: list[dict],
    all_record_violations: list[dict],
) -> list[dict]:
    """Summarize violation frequency by configured requirement."""
    requirement_lookup = {requirement["id"]: requirement for requirement in requirements}
    counts: dict[str, int] = {}

    for record in all_record_violations:
        for violation in record["violations"]:
            requirement_id = violation["requirement_id"]
            counts[requirement_id] = counts.get(requirement_id, 0) + 1

    rows = []
    for requirement_id, count in sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        requirement = requirement_lookup[requirement_id]
        rows.append(
            {
                "requirement_id": requirement_id,
                "parameter": requirement["parameter"],
                "severity": requirement["severity"],
                "count": count,
            }
        )
    return rows


def build_critical_records(results: pd.DataFrame) -> list[dict]:
    """Return a compact list of records with critical specification violations."""
    critical_records = results[
        results["spec_compliance_status"] == "CRITICAL_VIOLATION"
    ].copy()
    rows = []

    for _, row in critical_records.iterrows():
        rows.append(
            {
                "part_id": str(row.get("part_id", "")),
                "critical_violation_count": int(row["critical_violation_count"]),
                "violated_requirement_ids": [
                    value.strip()
                    for value in str(row["violated_requirement_ids"]).split(";")
                    if value.strip()
                ],
            }
        )
    return rows


def build_summary(
    results: pd.DataFrame,
    requirements: list[dict],
    all_record_violations: list[dict],
    input_path: Path,
    config_path: Path,
) -> dict:
    """Build the JSON specification compliance summary."""
    return {
        "input_path": display_path(input_path),
        "config_path": display_path(config_path),
        "row_count": int(len(results)),
        "requirement_count": int(len(requirements)),
        "status_counts": count_values(results["spec_compliance_status"]),
        "violation_counts_by_requirement": build_violation_counts_by_requirement(
            requirements,
            all_record_violations,
        ),
        "critical_records": build_critical_records(results),
        "note": "Synthetic specification checks for engineering review support; not a validated factory quality gate.",
    }


def write_csv_results(results: pd.DataFrame, path: Path) -> None:
    """Write row-level specification compliance results."""
    path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(path, index=False)


def write_json_summary(summary: dict, path: Path) -> None:
    """Write JSON specification compliance summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Convert a dataframe to Markdown with a concise empty-state message."""
    if df.empty:
        return "No records in this category."
    return df.to_markdown(index=False)


def write_markdown_report(results: pd.DataFrame, summary: dict, path: Path) -> None:
    """Write a concise engineering-focused Markdown compliance report."""
    status_lines = "\n".join(
        f"- {status}: {count}" for status, count in summary["status_counts"].items()
    ) or "- No status counts available."
    violation_lines = "\n".join(
        f"- {item['requirement_id']} ({item['severity']}, {item['parameter']}): {item['count']}"
        for item in summary["violation_counts_by_requirement"][:8]
    ) or "- No specification violations detected."

    critical_records = results[
        results["spec_compliance_status"] == "CRITICAL_VIOLATION"
    ][
        [
            "part_id",
            "spec_compliance_status",
            "violated_requirement_ids",
            "violation_summary",
            "recommended_actions",
        ]
    ].copy()

    report = f"""# Engineering Specification Compliance Report

## Overall Summary

- Input file: `{summary['input_path']}`
- Config file: `{summary['config_path']}`
- Reviewed rows: {summary['row_count']}
- Configured requirements: {summary['requirement_count']}
- Purpose: engineering review and decision support for synthetic production records.

## Compliance Status Counts

{status_lines}

## Most Common Violated Requirements

{violation_lines}

## Critical Violation Records

{dataframe_to_markdown(critical_records)}

## Engineering Interpretation

Critical violations identify records with at least one configured critical limit breach. Warning violations identify records outside illustrative monitoring bands. Compliant records satisfied the configured requirements in this synthetic scenario.

## Notes and Limitations

- This report uses synthetic production data.
- Requirements are illustrative engineering process checks, not validated factory limits.
- This is not a validated factory quality release system.
- Compliance output is for engineering review and decision support only.
- The checker does not make autonomous quality dispositions.
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def run_spec_compliance_check(
    input_path: Path,
    config_path: Path,
    output_csv_path: Path,
    output_json_path: Path,
    output_markdown_path: Path,
) -> tuple[pd.DataFrame, dict]:
    """Run the full specification compliance check workflow."""
    df = load_input_data(input_path)
    config = load_spec_config(config_path)
    requirements = config["requirements"]
    validate_input_against_config(df, requirements)

    results, all_record_violations = evaluate_compliance(df, requirements)
    summary = build_summary(
        results=results,
        requirements=requirements,
        all_record_violations=all_record_violations,
        input_path=input_path,
        config_path=config_path,
    )

    write_csv_results(results, output_csv_path)
    write_json_summary(summary, output_json_path)
    write_markdown_report(results, summary, output_markdown_path)
    return results, summary


def build_parser() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Check synthetic production records against engineering specification requirements.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Path to production batch CSV input.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to YAML specification requirements.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV_PATH),
        help="Path for row-level compliance CSV output.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON_PATH),
        help="Path for JSON summary output.",
    )
    parser.add_argument(
        "--output-md",
        default=str(DEFAULT_OUTPUT_MARKDOWN_PATH),
        help="Path for Markdown report output.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        results, summary = run_spec_compliance_check(
            input_path=resolve_path(args.input),
            config_path=resolve_path(args.config),
            output_csv_path=resolve_path(args.output_csv),
            output_json_path=resolve_path(args.output_json),
            output_markdown_path=resolve_path(args.output_md),
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"Specification compliance check failed: {error}", file=sys.stderr)
        return 1

    print("Specification compliance check completed.")
    print(f"Rows checked: {len(results)}")
    print(f"Configured requirements: {summary['requirement_count']}")
    print(f"CSV results: {resolve_path(args.output_csv)}")
    print(f"JSON summary: {resolve_path(args.output_json)}")
    print(f"Markdown report: {resolve_path(args.output_md)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
