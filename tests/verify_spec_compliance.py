from __future__ import annotations

from pathlib import Path
import sys
import tempfile

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from check_spec_compliance import (  # noqa: E402
    load_spec_config,
    run_spec_compliance_check,
    validate_input_against_config,
)


EXPECTED_OUTPUT_COLUMNS = {
    "spec_compliance_status",
    "violation_count",
    "violated_requirement_ids",
    "recommended_actions",
}


def sample_input() -> pd.DataFrame:
    """Create rows for compliant, warning, and critical compliance outcomes."""
    return pd.DataFrame(
        [
            {
                "part_id": "CLEAN_001",
                "temperature_c": 184.0,
                "vibration_mm_s": 2.1,
            },
            {
                "part_id": "WARN_001",
                "temperature_c": 192.0,
                "vibration_mm_s": 2.4,
            },
            {
                "part_id": "CRIT_001",
                "temperature_c": 198.0,
                "vibration_mm_s": 3.4,
            },
        ]
    )


def sample_config() -> dict:
    """Create a compact specification config for verification."""
    return {
        "version": 1,
        "description": "Temporary illustrative spec checks for verification.",
        "requirements": [
            {
                "id": "TEMP_MAX_WARNING",
                "parameter": "temperature_c",
                "type": "numeric_limit",
                "operator": "<=",
                "value": 190,
                "severity": "warning",
                "requirement_text": "Temperature should remain in the normal band.",
                "engineering_rationale": "Elevated temperature may indicate drift.",
                "recommended_action": "Review temperature control.",
            },
            {
                "id": "TEMP_MAX_CRITICAL",
                "parameter": "temperature_c",
                "type": "numeric_limit",
                "operator": "<=",
                "value": 195,
                "severity": "critical",
                "requirement_text": "Temperature should remain below the critical limit.",
                "engineering_rationale": "Very high temperature may indicate instability.",
                "recommended_action": "Escalate for engineering review.",
            },
            {
                "id": "VIBRATION_MAX_CRITICAL",
                "parameter": "vibration_mm_s",
                "type": "numeric_limit",
                "operator": "<=",
                "value": 3.1,
                "severity": "critical",
                "requirement_text": "Vibration should remain below the critical limit.",
                "engineering_rationale": "High vibration may indicate mechanical instability.",
                "recommended_action": "Inspect machine condition.",
            },
        ],
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def write_yaml(payload: dict, path: Path) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_valid_spec_compliance_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / "input.csv"
        config_path = temp_path / "spec.yaml"
        output_csv = temp_path / "results.csv"
        output_json = temp_path / "summary.json"
        output_md = temp_path / "report.md"

        write_csv(sample_input(), input_path)
        write_yaml(sample_config(), config_path)

        results, summary = run_spec_compliance_check(
            input_path=input_path,
            config_path=config_path,
            output_csv_path=output_csv,
            output_json_path=output_json,
            output_markdown_path=output_md,
        )

        assert output_csv.exists(), output_csv
        assert output_json.exists(), output_json
        assert output_md.exists(), output_md

        output_df = pd.read_csv(output_csv)
        missing_columns = EXPECTED_OUTPUT_COLUMNS - set(output_df.columns)
        assert not missing_columns, f"Missing output columns: {missing_columns}"

        statuses = dict(zip(results["part_id"], results["spec_compliance_status"]))
        assert statuses["CLEAN_001"] == "COMPLIANT", statuses
        assert statuses["WARN_001"] == "WARNING_VIOLATION", statuses
        assert statuses["CRIT_001"] == "CRITICAL_VIOLATION", statuses
        assert summary["requirement_count"] == 3, summary


def test_missing_required_parameter_fails() -> None:
    df = sample_input().drop(columns=["temperature_c"])
    requirements = sample_config()["requirements"]

    try:
        validate_input_against_config(df, requirements)
    except ValueError as error:
        assert "missing required specification parameters" in str(error)
        return

    raise AssertionError("Missing required input parameter did not fail.")


def test_invalid_operator_fails() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config = sample_config()
        config["requirements"][0]["operator"] = "between"
        config_path = Path(temp_dir) / "bad_operator.yaml"
        write_yaml(config, config_path)

        try:
            load_spec_config(config_path)
        except ValueError as error:
            assert "unsupported operator" in str(error)
            return

    raise AssertionError("Invalid operator did not fail.")


def test_invalid_severity_fails() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config = sample_config()
        config["requirements"][0]["severity"] = "urgent"
        config_path = Path(temp_dir) / "bad_severity.yaml"
        write_yaml(config, config_path)

        try:
            load_spec_config(config_path)
        except ValueError as error:
            assert "unsupported severity" in str(error)
            return

    raise AssertionError("Invalid severity did not fail.")


def main() -> None:
    tests = [
        test_valid_spec_compliance_outputs,
        test_missing_required_parameter_fails,
        test_invalid_operator_fails,
        test_invalid_severity_fails,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All specification compliance checks passed.")


if __name__ == "__main__":
    main()
