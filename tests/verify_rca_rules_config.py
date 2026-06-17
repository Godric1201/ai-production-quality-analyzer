from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from root_cause_analysis import analyze_root_causes  # noqa: E402


REQUIRED_OUTPUT_KEYS = {
    "suspected_drivers",
    "recommendations",
    "summary",
    "risk_level",
}


def base_clean_row() -> dict:
    """Return a low-risk row that should not trigger configured RCA drivers."""
    return {
        "part_id": "P_TEST",
        "machine_id": "M1",
        "temperature_c": 184.0,
        "pressure_bar": 5.8,
        "cycle_time_s": 46.0,
        "shift": "early",
        "material_batch": "B1",
        "operator_experience_years": 5.0,
        "vibration_mm_s": 2.1,
        "humidity_percent": 48.0,
        "scrap_probability": 0.12,
        "predicted_scrap_risk": "Low",
    }


def driver_names(analysis: dict) -> set[str]:
    return {driver["driver"] for driver in analysis["suspected_drivers"]}


def assert_required_keys(analysis: dict) -> None:
    missing_keys = REQUIRED_OUTPUT_KEYS - set(analysis)
    assert not missing_keys, f"Missing output keys: {missing_keys}"


def test_high_temperature_rule() -> None:
    row = base_clean_row()
    row["temperature_c"] = 193.0
    analysis = analyze_root_causes(row)

    assert_required_keys(analysis)
    assert driver_names(analysis) & {"High temperature", "Very high temperature"}, analysis


def test_high_vibration_rule() -> None:
    row = base_clean_row()
    row["vibration_mm_s"] = 3.2
    analysis = analyze_root_causes(row)

    assert_required_keys(analysis)
    assert "High vibration" in driver_names(analysis), analysis


def test_machine_m2_rule() -> None:
    row = base_clean_row()
    row["machine_id"] = "M2"
    analysis = analyze_root_causes(row)

    assert_required_keys(analysis)
    assert "Machine M2 risk pattern" in driver_names(analysis), analysis


def test_material_batch_b4_rule() -> None:
    row = base_clean_row()
    row["material_batch"] = "B4"
    analysis = analyze_root_causes(row)

    assert_required_keys(analysis)
    assert "Material batch B4" in driver_names(analysis), analysis


def test_high_risk_fallback_rule() -> None:
    row = base_clean_row()
    row["scrap_probability"] = 0.72
    row["predicted_scrap_risk"] = "High"
    analysis = analyze_root_causes(row)

    assert_required_keys(analysis)
    assert driver_names(analysis) == {"Elevated predicted scrap risk"}, analysis
    assert analysis["recommendations"], analysis


def test_low_risk_clean_row_has_no_driver() -> None:
    analysis = analyze_root_causes(base_clean_row())

    assert_required_keys(analysis)
    assert analysis["suspected_drivers"] == [], analysis
    assert analysis["risk_level"] == "low", analysis
    assert (
        analysis["summary"] == "No configured root cause driver was detected for this batch."
    ), analysis
    assert analysis["recommendations"] == [
        "No immediate engineering action required. Continue standard process monitoring."
    ], analysis


def main() -> None:
    tests = [
        test_high_temperature_rule,
        test_high_vibration_rule,
        test_machine_m2_rule,
        test_material_batch_b4_rule,
        test_high_risk_fallback_rule,
        test_low_risk_clean_row_has_no_driver,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All RCA rules config checks passed.")


if __name__ == "__main__":
    main()
