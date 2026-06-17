from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REVIEW_RESULTS_PATH = PROJECT_ROOT / "outputs" / "batch_review_results.csv"
DEFAULT_FEEDBACK_PATH = PROJECT_ROOT / "data" / "batch_review_feedback.csv"
DEFAULT_OUTPUT_CSV_PATH = PROJECT_ROOT / "outputs" / "review_feedback_cases.csv"
DEFAULT_OUTPUT_JSON_PATH = PROJECT_ROOT / "outputs" / "review_feedback_summary.json"
DEFAULT_OUTPUT_MARKDOWN_PATH = PROJECT_ROOT / "outputs" / "review_feedback_report.md"

REQUIRED_REVIEW_COLUMNS = [
    "part_id",
    "scrap_probability",
    "risk_level",
    "review_threshold",
    "review_decision",
    "root_cause_summary",
    "top_suspected_drivers",
    "engineering_recommendations",
]

REQUIRED_FEEDBACK_COLUMNS = [
    "part_id",
    "actual_scrap",
    "engineer_review_outcome",
    "review_notes",
]

THRESHOLD_SCENARIOS = [0.30, 0.40, 0.50, 0.60]


def resolve_path(path_value: str | Path) -> Path:
    """Resolve CLI paths relative to the project root when needed."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def display_path(path: Path) -> str:
    """Return a compact path string for reports."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_csv(path: Path, label: str) -> pd.DataFrame:
    """Load a CSV input with a clear missing-file error."""
    if not path.exists():
        raise FileNotFoundError(f"{label} file not found at {path}")
    return pd.read_csv(path)


def validate_required_columns(df: pd.DataFrame, required_columns: list[str], label: str) -> None:
    """Fail when required columns are missing."""
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"{label} is missing required columns: {missing_columns}")


def validate_feedback(feedback_df: pd.DataFrame) -> None:
    """Validate feedback data fields that affect evaluation correctness."""
    duplicate_part_ids = (
        feedback_df.loc[feedback_df["part_id"].duplicated(), "part_id"]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )
    if duplicate_part_ids:
        raise ValueError(f"Feedback contains duplicate part_id values: {duplicate_part_ids}")

    numeric_actual = pd.to_numeric(feedback_df["actual_scrap"], errors="coerce")
    invalid_values = (
        feedback_df.loc[~numeric_actual.isin([0, 1]), "actual_scrap"]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )
    if invalid_values:
        raise ValueError(f"Feedback actual_scrap contains invalid values: {invalid_values}")


def validate_inputs(review_df: pd.DataFrame, feedback_df: pd.DataFrame) -> list[str]:
    """Validate input schemas and return coverage warnings."""
    validate_required_columns(review_df, REQUIRED_REVIEW_COLUMNS, "Review results")
    validate_required_columns(feedback_df, REQUIRED_FEEDBACK_COLUMNS, "Feedback")
    validate_feedback(feedback_df)

    review_part_ids = set(review_df["part_id"].astype(str))
    feedback_part_ids = set(feedback_df["part_id"].astype(str))
    extra_feedback = sorted(feedback_part_ids - review_part_ids)
    missing_feedback = sorted(review_part_ids - feedback_part_ids)

    warnings = []
    if extra_feedback:
        warnings.append(
            f"Feedback contains part IDs not present in review results: {', '.join(extra_feedback)}"
        )
    if missing_feedback:
        warnings.append(
            f"Review results contain part IDs without feedback: {', '.join(missing_feedback)}"
        )

    return warnings


def classify_feedback_case(review_decision: str, actual_scrap: int) -> str:
    """Classify one review decision against later synthetic feedback."""
    review_required = review_decision == "ENGINEERING_REVIEW_REQUIRED"
    actual_issue = actual_scrap == 1

    if review_required and actual_issue:
        return "TRUE_POSITIVE_REVIEW"
    if review_required and not actual_issue:
        return "FALSE_ALARM_REVIEW"
    if not review_required and actual_issue:
        return "MISSED_ISSUE"
    return "TRUE_NEGATIVE_MONITORING"


def feedback_priority(classification: str) -> str:
    """Map feedback classifications to review priority."""
    priorities = {
        "MISSED_ISSUE": "highest",
        "FALSE_ALARM_REVIEW": "medium",
        "TRUE_POSITIVE_REVIEW": "high",
        "TRUE_NEGATIVE_MONITORING": "low",
    }
    return priorities[classification]


def feedback_interpretation(classification: str) -> str:
    """Return concise engineering interpretation text for one classified case."""
    interpretations = {
        "TRUE_POSITIVE_REVIEW": "Model-based review correctly prioritized a later confirmed issue.",
        "FALSE_ALARM_REVIEW": "Engineering review was required, but no issue was later confirmed. This may be an acceptable false alarm depending on inspection cost.",
        "MISSED_ISSUE": "Actual issue was not prioritized for engineering review. This is the most important case for threshold or rule adjustment.",
        "TRUE_NEGATIVE_MONITORING": "Standard monitoring matched later clean feedback.",
    }
    return interpretations[classification]


def merge_review_feedback(review_df: pd.DataFrame, feedback_df: pd.DataFrame) -> pd.DataFrame:
    """Merge review results with feedback and classify matched cases."""
    review = review_df.copy()
    feedback = feedback_df.copy()
    review["part_id"] = review["part_id"].astype(str)
    feedback["part_id"] = feedback["part_id"].astype(str)
    feedback["actual_scrap"] = pd.to_numeric(feedback["actual_scrap"]).astype(int)

    merged = review.merge(
        feedback,
        on="part_id",
        how="inner",
        validate="one_to_one",
    )
    merged["scrap_probability"] = pd.to_numeric(merged["scrap_probability"])
    merged["review_threshold"] = pd.to_numeric(merged["review_threshold"])
    merged["feedback_classification"] = merged.apply(
        lambda row: classify_feedback_case(
            str(row["review_decision"]),
            int(row["actual_scrap"]),
        ),
        axis=1,
    )
    merged["feedback_priority"] = merged["feedback_classification"].apply(feedback_priority)
    merged["feedback_interpretation"] = merged["feedback_classification"].apply(
        feedback_interpretation
    )
    return merged


def count_values(series: pd.Series) -> dict:
    """Return deterministic value counts for JSON output."""
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def calculate_effectiveness(cases_df: pd.DataFrame) -> dict:
    """Calculate review effectiveness metrics from classified cases."""
    actual_issue_count = int((cases_df["actual_scrap"] == 1).sum())
    review_required_count = int(
        (cases_df["review_decision"] == "ENGINEERING_REVIEW_REQUIRED").sum()
    )
    missed_issue_count = int(
        (cases_df["feedback_classification"] == "MISSED_ISSUE").sum()
    )
    false_alarm_count = int(
        (cases_df["feedback_classification"] == "FALSE_ALARM_REVIEW").sum()
    )
    true_positive_count = int(
        (cases_df["feedback_classification"] == "TRUE_POSITIVE_REVIEW").sum()
    )

    issue_capture_rate = (
        0.0 if actual_issue_count == 0 else true_positive_count / actual_issue_count
    )
    false_alarm_rate = (
        0.0 if review_required_count == 0 else false_alarm_count / review_required_count
    )

    return {
        "actual_issue_count": actual_issue_count,
        "review_required_count": review_required_count,
        "missed_issue_count": missed_issue_count,
        "false_alarm_count": false_alarm_count,
        "issue_capture_rate": round(issue_capture_rate, 4),
        "false_alarm_rate_among_reviews": round(false_alarm_rate, 4),
    }


def build_driver_summary(cases_df: pd.DataFrame) -> list[dict]:
    """Count suspected drivers among later confirmed issue rows."""
    confirmed = cases_df[cases_df["actual_scrap"] == 1]
    counts: dict[str, int] = {}

    for value in confirmed["top_suspected_drivers"].fillna(""):
        for driver in str(value).split(";"):
            driver = driver.strip()
            if driver:
                counts[driver] = counts.get(driver, 0) + 1

    return [
        {"driver": driver, "count": count}
        for driver, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def classify_threshold_scenario(probability: float, actual_scrap: int, threshold: float) -> str:
    """Classify a case under a simulated probability threshold."""
    if probability >= threshold and actual_scrap == 1:
        return "TRUE_POSITIVE_REVIEW"
    if probability >= threshold and actual_scrap == 0:
        return "FALSE_ALARM_REVIEW"
    if probability < threshold and actual_scrap == 1:
        return "MISSED_ISSUE"
    return "TRUE_NEGATIVE_MONITORING"


def build_threshold_scenarios(cases_df: pd.DataFrame) -> list[dict]:
    """Simulate review outcomes under a few simple probability thresholds."""
    scenarios = []
    actual_issue_count = int((cases_df["actual_scrap"] == 1).sum())

    for threshold in THRESHOLD_SCENARIOS:
        classifications = cases_df.apply(
            lambda row: classify_threshold_scenario(
                float(row["scrap_probability"]),
                int(row["actual_scrap"]),
                threshold,
            ),
            axis=1,
        )
        counts = count_values(classifications)
        review_required_count = int((cases_df["scrap_probability"] >= threshold).sum())
        true_positive_count = counts.get("TRUE_POSITIVE_REVIEW", 0)
        false_alarm_count = counts.get("FALSE_ALARM_REVIEW", 0)

        issue_capture_rate = (
            0.0 if actual_issue_count == 0 else true_positive_count / actual_issue_count
        )
        false_alarm_rate = (
            0.0 if review_required_count == 0 else false_alarm_count / review_required_count
        )

        scenarios.append(
            {
                "threshold": threshold,
                "true_positive_reviews": counts.get("TRUE_POSITIVE_REVIEW", 0),
                "false_alarm_reviews": false_alarm_count,
                "missed_issues": counts.get("MISSED_ISSUE", 0),
                "true_negative_monitoring": counts.get("TRUE_NEGATIVE_MONITORING", 0),
                "review_required_count": review_required_count,
                "issue_capture_rate": round(issue_capture_rate, 4),
                "false_alarm_rate_among_reviews": round(false_alarm_rate, 4),
            }
        )

    return scenarios


def build_summary(
    cases_df: pd.DataFrame,
    review_df: pd.DataFrame,
    feedback_df: pd.DataFrame,
    warnings: list[str],
    review_results_path: Path,
    feedback_path: Path,
) -> dict:
    """Build the JSON review feedback summary."""
    review_part_ids = set(review_df["part_id"].astype(str))
    feedback_part_ids = set(feedback_df["part_id"].astype(str))

    return {
        "review_results_path": display_path(review_results_path),
        "feedback_path": display_path(feedback_path),
        "row_count": int(len(cases_df)),
        "feedback_coverage": {
            "review_rows": int(len(review_df)),
            "feedback_rows": int(len(feedback_df)),
            "matched_rows": int(len(cases_df)),
            "missing_feedback_rows": int(len(review_part_ids - feedback_part_ids)),
            "extra_feedback_rows": int(len(feedback_part_ids - review_part_ids)),
        },
        "classification_counts": count_values(cases_df["feedback_classification"]),
        "review_effectiveness": calculate_effectiveness(cases_df),
        "driver_summary_for_confirmed_issues": build_driver_summary(cases_df),
        "threshold_scenarios": build_threshold_scenarios(cases_df),
        "warnings": warnings,
        "note": "Synthetic feedback loop for portfolio-prototype industrial AI decision support; not a validated factory quality system.",
    }


def write_cases_csv(cases_df: pd.DataFrame, path: Path) -> None:
    """Write per-case feedback evaluation output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cases_df.to_csv(path, index=False)


def write_json_summary(summary: dict, path: Path) -> None:
    """Write the JSON feedback evaluation summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Convert a dataframe to Markdown with a concise empty-state message."""
    if df.empty:
        return "No cases in this category."
    return df.to_markdown(index=False)


def build_threshold_table(scenarios: list[dict]) -> pd.DataFrame:
    """Create a readable threshold scenario table for Markdown."""
    table = pd.DataFrame(scenarios)
    if table.empty:
        return table

    table = table.rename(
        columns={
            "threshold": "threshold",
            "true_positive_reviews": "true_positive_reviews",
            "false_alarm_reviews": "false_alarm_reviews",
            "missed_issues": "missed_issues",
            "true_negative_monitoring": "true_negative_monitoring",
            "review_required_count": "review_required_count",
            "issue_capture_rate": "issue_capture_rate",
            "false_alarm_rate_among_reviews": "false_alarm_rate_among_reviews",
        }
    )
    return table


def write_markdown_report(cases_df: pd.DataFrame, summary: dict, path: Path) -> None:
    """Write a concise engineering-focused feedback report."""
    missed = cases_df[cases_df["feedback_classification"] == "MISSED_ISSUE"].copy()
    false_alarms = cases_df[
        cases_df["feedback_classification"] == "FALSE_ALARM_REVIEW"
    ].copy()

    missed_table = missed[
        [
            "part_id",
            "scrap_probability",
            "risk_level",
            "review_decision",
            "root_cause_summary",
            "review_notes",
        ]
    ].copy()
    false_alarm_table = false_alarms[
        [
            "part_id",
            "scrap_probability",
            "risk_level",
            "root_cause_summary",
            "review_notes",
        ]
    ].copy()

    for table in [missed_table, false_alarm_table]:
        if not table.empty:
            table["scrap_probability"] = table["scrap_probability"].apply(
                lambda value: f"{float(value) * 100:.2f}%"
            )

    classification_lines = "\n".join(
        f"- {classification}: {count}"
        for classification, count in summary["classification_counts"].items()
    ) or "- No classifications available."
    coverage = summary["feedback_coverage"]
    effectiveness = summary["review_effectiveness"]
    driver_lines = "\n".join(
        f"- {item['driver']}: {item['count']}"
        for item in summary["driver_summary_for_confirmed_issues"][:8]
    ) or "- No suspected drivers were available for confirmed issue rows."
    warning_lines = "\n".join(f"- {warning}" for warning in summary["warnings"]) or "- None"

    threshold_table = build_threshold_table(summary["threshold_scenarios"])

    report = f"""# Review Feedback Report

## Overall Summary

- Review results: `{summary['review_results_path']}`
- Feedback file: `{summary['feedback_path']}`
- Matched feedback rows: {summary['row_count']}
- Purpose: demonstrate a synthetic feedback loop for industrial AI decision-support workflows.

## Feedback Coverage

- Review rows: {coverage['review_rows']}
- Feedback rows: {coverage['feedback_rows']}
- Matched rows: {coverage['matched_rows']}
- Missing feedback rows: {coverage['missing_feedback_rows']}
- Extra feedback rows: {coverage['extra_feedback_rows']}

Warnings:
{warning_lines}

## Classification Counts

{classification_lines}

## Review Effectiveness

- Actual issue count: {effectiveness['actual_issue_count']}
- Review-required count: {effectiveness['review_required_count']}
- Missed issue count: {effectiveness['missed_issue_count']}
- False alarm count: {effectiveness['false_alarm_count']}
- Issue capture rate: {effectiveness['issue_capture_rate']:.2f}
- False alarm rate among reviews: {effectiveness['false_alarm_rate_among_reviews']:.2f}

## Missed Issues

{dataframe_to_markdown(missed_table)}

## False Alarms

{dataframe_to_markdown(false_alarm_table)}

## Confirmed Issues and Suspected Drivers

{driver_lines}

## Threshold Scenario Analysis

{dataframe_to_markdown(threshold_table)}

## Engineering Interpretation

Missed issues are the highest-priority feedback cases because they show where the review workflow did not prioritize a later confirmed issue. False alarms show the cost of additional engineering attention. True positive reviews and true negative monitoring indicate where the illustrative workflow aligned with later synthetic feedback.

## Limitations

- The feedback file is synthetic and created for a portfolio prototype.
- This is not a validated factory quality system.
- The workflow evaluates engineering review prioritization, not autonomous control or disposition.
- Threshold scenario results are illustrative and should not be treated as production policy.
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def run_feedback_evaluation(
    review_results_path: Path,
    feedback_path: Path,
    output_csv_path: Path,
    output_json_path: Path,
    output_markdown_path: Path,
) -> tuple[pd.DataFrame, dict]:
    """Run the full review feedback evaluation workflow."""
    review_df = load_csv(review_results_path, "Review results")
    feedback_df = load_csv(feedback_path, "Feedback")
    warnings = validate_inputs(review_df, feedback_df)
    cases_df = merge_review_feedback(review_df, feedback_df)
    summary = build_summary(
        cases_df=cases_df,
        review_df=review_df,
        feedback_df=feedback_df,
        warnings=warnings,
        review_results_path=review_results_path,
        feedback_path=feedback_path,
    )

    write_cases_csv(cases_df, output_csv_path)
    write_json_summary(summary, output_json_path)
    write_markdown_report(cases_df, summary, output_markdown_path)

    return cases_df, summary


def build_parser() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Evaluate batch review decisions against later feedback.")
    parser.add_argument(
        "--review-results",
        default=str(DEFAULT_REVIEW_RESULTS_PATH),
        help="Path to batch review result CSV.",
    )
    parser.add_argument(
        "--feedback",
        default=str(DEFAULT_FEEDBACK_PATH),
        help="Path to synthetic review feedback CSV.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV_PATH),
        help="Path for per-case feedback CSV output.",
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
        cases_df, summary = run_feedback_evaluation(
            review_results_path=resolve_path(args.review_results),
            feedback_path=resolve_path(args.feedback),
            output_csv_path=resolve_path(args.output_csv),
            output_json_path=resolve_path(args.output_json),
            output_markdown_path=resolve_path(args.output_md),
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"Review feedback evaluation failed: {error}", file=sys.stderr)
        return 1

    print("Review feedback evaluation completed.")
    print(f"Matched rows: {len(cases_df)}")
    print(
        "Issue capture rate: "
        f"{summary['review_effectiveness']['issue_capture_rate']:.2f}"
    )
    print(
        "False alarm rate among reviews: "
        f"{summary['review_effectiveness']['false_alarm_rate_among_reviews']:.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
