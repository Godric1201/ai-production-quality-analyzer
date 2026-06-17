from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evaluate_review_feedback import (  # noqa: E402
    run_feedback_evaluation,
    validate_inputs,
)


EXPECTED_CASE_COLUMNS = {
    "feedback_classification",
    "feedback_priority",
    "feedback_interpretation",
}


def sample_review_results() -> pd.DataFrame:
    """Create compact review results that exercise feedback classifications."""
    return pd.DataFrame(
        [
            {
                "part_id": "TP_001",
                "scrap_probability": 0.72,
                "risk_level": "High",
                "review_threshold": 0.40,
                "review_decision": "ENGINEERING_REVIEW_REQUIRED",
                "root_cause_summary": "High risk mainly due to high vibration.",
                "top_suspected_drivers": "High vibration; Machine M2 risk pattern",
                "engineering_recommendations": "Inspect vibration sources.",
            },
            {
                "part_id": "FA_001",
                "scrap_probability": 0.48,
                "risk_level": "Medium",
                "review_threshold": 0.40,
                "review_decision": "ENGINEERING_REVIEW_REQUIRED",
                "root_cause_summary": "Medium risk mainly due to high temperature.",
                "top_suspected_drivers": "High temperature",
                "engineering_recommendations": "Review process temperature control.",
            },
            {
                "part_id": "MISS_001",
                "scrap_probability": 0.22,
                "risk_level": "Low",
                "review_threshold": 0.40,
                "review_decision": "STANDARD_MONITORING",
                "root_cause_summary": "No configured root cause driver was detected.",
                "top_suspected_drivers": "",
                "engineering_recommendations": "Continue standard process monitoring.",
            },
            {
                "part_id": "TN_001",
                "scrap_probability": 0.18,
                "risk_level": "Low",
                "review_threshold": 0.40,
                "review_decision": "STANDARD_MONITORING",
                "root_cause_summary": "No configured root cause driver was detected.",
                "top_suspected_drivers": "",
                "engineering_recommendations": "Continue standard process monitoring.",
            },
        ]
    )


def sample_feedback() -> pd.DataFrame:
    """Create compact synthetic feedback for review verification."""
    return pd.DataFrame(
        [
            {
                "part_id": "TP_001",
                "actual_scrap": 1,
                "engineer_review_outcome": "confirmed_issue",
                "review_notes": "Synthetic issue confirmed.",
            },
            {
                "part_id": "FA_001",
                "actual_scrap": 0,
                "engineer_review_outcome": "false_alarm",
                "review_notes": "Synthetic review found no issue.",
            },
            {
                "part_id": "MISS_001",
                "actual_scrap": 1,
                "engineer_review_outcome": "missed_issue",
                "review_notes": "Synthetic issue was not prioritized.",
            },
            {
                "part_id": "TN_001",
                "actual_scrap": 0,
                "engineer_review_outcome": "no_issue",
                "review_notes": "Synthetic feedback remained clean.",
            },
        ]
    )


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


def test_valid_feedback_evaluation_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        review_path = temp_path / "review.csv"
        feedback_path = temp_path / "feedback.csv"
        output_csv = temp_path / "cases.csv"
        output_json = temp_path / "summary.json"
        output_md = temp_path / "report.md"

        write_csv(sample_review_results(), review_path)
        write_csv(sample_feedback(), feedback_path)

        cases_df, summary = run_feedback_evaluation(
            review_results_path=review_path,
            feedback_path=feedback_path,
            output_csv_path=output_csv,
            output_json_path=output_json,
            output_markdown_path=output_md,
        )

        assert output_csv.exists(), output_csv
        assert output_json.exists(), output_json
        assert output_md.exists(), output_md

        output_cases = pd.read_csv(output_csv)
        missing_columns = EXPECTED_CASE_COLUMNS - set(output_cases.columns)
        assert not missing_columns, f"Missing output case columns: {missing_columns}"

        assert "MISSED_ISSUE" in set(cases_df["feedback_classification"]), cases_df
        assert "FALSE_ALARM_REVIEW" in set(cases_df["feedback_classification"]), cases_df
        assert "threshold_scenarios" in summary, summary
        assert summary["threshold_scenarios"], summary

        saved_summary = json.loads(output_json.read_text(encoding="utf-8"))
        assert saved_summary["threshold_scenarios"], saved_summary


def test_duplicate_feedback_part_id_fails() -> None:
    review_df = sample_review_results()
    feedback_df = sample_feedback()
    feedback_df.loc[1, "part_id"] = "TP_001"

    try:
        validate_inputs(review_df, feedback_df)
    except ValueError as error:
        assert "duplicate part_id" in str(error)
        return

    raise AssertionError("Duplicate feedback part_id did not fail.")


def test_invalid_actual_scrap_fails() -> None:
    review_df = sample_review_results()
    feedback_df = sample_feedback()
    feedback_df["actual_scrap"] = feedback_df["actual_scrap"].astype(object)
    feedback_df.loc[0, "actual_scrap"] = "unknown"

    try:
        validate_inputs(review_df, feedback_df)
    except ValueError as error:
        assert "actual_scrap contains invalid values" in str(error)
        return

    raise AssertionError("Invalid actual_scrap value did not fail.")


def main() -> None:
    tests = [
        test_valid_feedback_evaluation_outputs,
        test_duplicate_feedback_part_id_fails,
        test_invalid_actual_scrap_fails,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All review feedback checks passed.")


if __name__ == "__main__":
    main()
