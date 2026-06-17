from __future__ import annotations

from pathlib import Path
import sys
import tempfile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from generate_data import generate_production_data  # noqa: E402
from validate_data import run_validation  # noqa: E402


def write_temp_dataset(df: pd.DataFrame, directory: Path) -> Path:
    """Write a temporary dataset and return its path."""
    path = directory / "production_quality_data.csv"
    df.to_csv(path, index=False)
    return path


def base_valid_dataset() -> pd.DataFrame:
    """Create a compact valid dataset with a stable non-edge scrap rate."""
    rows = []

    for index in range(1, 21):
        rows.append(
            {
                "part_id": f"P{index:06d}",
                "machine_id": "M1" if index % 2 else "M2",
                "temperature_c": 184.0,
                "pressure_bar": 5.8,
                "cycle_time_s": 46.0,
                "shift": "early" if index % 3 else "late",
                "material_batch": "B1",
                "operator_experience_years": 4.0,
                "vibration_mm_s": 2.2,
                "humidity_percent": 48.0,
                "scrap": 1 if index in (5, 10) else 0,
            }
        )

    return pd.DataFrame(rows)


def validate_frame(df: pd.DataFrame) -> dict:
    """Run validation against a temporary CSV without touching real outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = write_temp_dataset(df, Path(temp_dir))
        return run_validation(path)


def test_valid_generated_dataset_not_fail() -> None:
    df = generate_production_data(n_rows=1000, seed=42)
    report = validate_frame(df)

    assert report["status"] in {"PASS", "WARNING"}, report


def test_missing_required_column_fails() -> None:
    df = base_valid_dataset().drop(columns=["pressure_bar"])
    report = validate_frame(df)

    assert report["status"] == "FAIL", report
    assert any(check["name"] == "schema_validation" for check in report["errors"])


def test_invalid_scrap_values_fail() -> None:
    df = base_valid_dataset()
    df.loc[0, "scrap"] = 2
    report = validate_frame(df)

    assert report["status"] == "FAIL", report
    assert any(check["name"] == "target_validation" for check in report["errors"])


def test_unknown_categories_warn_only() -> None:
    df = base_valid_dataset()
    df.loc[0, "machine_id"] = "M99"
    report = validate_frame(df)

    assert report["status"] == "WARNING", report
    assert any(check["name"] == "categorical_validation" for check in report["warnings"])
    assert not report["errors"], report


def test_engineering_out_of_range_warn_only() -> None:
    df = base_valid_dataset()
    df.loc[0, "temperature_c"] = 999.0
    report = validate_frame(df)

    assert report["status"] == "WARNING", report
    assert any(check["name"] == "engineering_plausibility" for check in report["warnings"])
    assert not report["errors"], report


def main() -> None:
    tests = [
        test_valid_generated_dataset_not_fail,
        test_missing_required_column_fails,
        test_invalid_scrap_values_fail,
        test_unknown_categories_warn_only,
        test_engineering_out_of_range_warn_only,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All data validation checks passed.")


if __name__ == "__main__":
    main()
