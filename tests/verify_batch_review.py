from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from review_batch import (  # noqa: E402
    MODEL_PATH,
    load_scoring_input,
    run_batch_review,
    validate_scoring_input,
)


EXPECTED_OUTPUT_COLUMNS = {
    "scrap_probability",
    "risk_level",
    "review_decision",
    "root_cause_summary",
}


def ensure_model_exists() -> None:
    """Train the model if the review workflow has no model artifact available."""
    if MODEL_PATH.exists():
        return

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "train_model.py")],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not train the model required for batch review verification. "
            "Run `python src/train_model.py` and retry."
        )


def sample_scoring_rows() -> pd.DataFrame:
    """Create a compact scoring batch with clear high-risk and clean examples."""
    return pd.DataFrame(
        [
            {
                "part_id": "TEST_HIGH_001",
                "machine_id": "M2",
                "temperature_c": 198.0,
                "pressure_bar": 6.7,
                "cycle_time_s": 56.0,
                "shift": "night",
                "material_batch": "B4",
                "operator_experience_years": 1.0,
                "vibration_mm_s": 3.6,
                "humidity_percent": 65.0,
            },
            {
                "part_id": "TEST_CLEAN_001",
                "machine_id": "M1",
                "temperature_c": 183.0,
                "pressure_bar": 5.7,
                "cycle_time_s": 44.5,
                "shift": "early",
                "material_batch": "B1",
                "operator_experience_years": 7.0,
                "vibration_mm_s": 2.0,
                "humidity_percent": 46.0,
            },
            {
                "part_id": "TEST_MEDIUM_001",
                "machine_id": "M4",
                "temperature_c": 191.0,
                "pressure_bar": 6.0,
                "cycle_time_s": 51.0,
                "shift": "late",
                "material_batch": "B2",
                "operator_experience_years": 3.0,
                "vibration_mm_s": 2.9,
                "humidity_percent": 55.0,
            },
        ]
    )


def write_temp_csv(df: pd.DataFrame, directory: Path, name: str = "batch.csv") -> Path:
    path = directory / name
    df.to_csv(path, index=False)
    return path


def test_review_batch_outputs() -> None:
    ensure_model_exists()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = write_temp_csv(sample_scoring_rows(), temp_path)
        output_csv = temp_path / "review_results.csv"
        output_json = temp_path / "review_summary.json"
        output_md = temp_path / "review_report.md"

        results, _ = run_batch_review(
            input_path=input_path,
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

        high_row = results[results["part_id"] == "TEST_HIGH_001"].iloc[0]
        assert high_row["review_decision"] == "ENGINEERING_REVIEW_REQUIRED", high_row

        clean_row = results[results["part_id"] == "TEST_CLEAN_001"].iloc[0]
        assert clean_row["review_decision"] in {
            "STANDARD_MONITORING",
            "ADDITIONAL_MONITORING",
        }, clean_row


def test_missing_required_column_fails() -> None:
    df = sample_scoring_rows().drop(columns=["pressure_bar"])

    try:
        validate_scoring_input(df)
    except ValueError as error:
        assert "missing required columns" in str(error)
        return

    raise AssertionError("Missing required scoring column did not fail.")


def test_invalid_numeric_value_fails() -> None:
    df = sample_scoring_rows()
    df["temperature_c"] = df["temperature_c"].astype(object)
    df.loc[0, "temperature_c"] = "not-a-number"

    try:
        validate_scoring_input(df)
    except ValueError as error:
        assert "invalid numeric values" in str(error)
        return

    raise AssertionError("Invalid numeric value did not fail.")


def test_load_scoring_input_missing_file_fails() -> None:
    try:
        load_scoring_input(PROJECT_ROOT / "data" / "does_not_exist.csv")
    except FileNotFoundError:
        return

    raise AssertionError("Missing scoring input file did not fail.")


def main() -> None:
    tests = [
        test_review_batch_outputs,
        test_missing_required_column_fails,
        test_invalid_numeric_value_fails,
        test_load_scoring_input_missing_file_fails,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All batch review checks passed.")


if __name__ == "__main__":
    main()
