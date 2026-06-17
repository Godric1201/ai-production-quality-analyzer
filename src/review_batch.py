from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

import joblib
import pandas as pd

from root_cause_analysis import analyze_root_causes
from train_model import CATEGORICAL_FEATURES, MODEL_PATH, NUMERIC_FEATURES
from validate_data import ENGINEERING_RANGES, EXPECTED_CATEGORIES, is_missing


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "new_production_batch.csv"
DEFAULT_OUTPUT_CSV_PATH = PROJECT_ROOT / "outputs" / "batch_review_results.csv"
DEFAULT_OUTPUT_JSON_PATH = PROJECT_ROOT / "outputs" / "batch_review_summary.json"
DEFAULT_OUTPUT_MARKDOWN_PATH = PROJECT_ROOT / "outputs" / "batch_review_report.md"
COST_OPTIMIZED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "cost_optimized_threshold.json"
SELECTED_THRESHOLD_PATH = PROJECT_ROOT / "outputs" / "selected_threshold.json"

SCORING_REQUIRED_COLUMNS = [
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
]

FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
FALLBACK_REVIEW_THRESHOLD = 0.50


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


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_threshold(payload: dict) -> float | None:
    """Extract a review threshold from known threshold output structures."""
    candidates = [
        payload.get("threshold"),
        payload.get("selected_threshold"),
        payload.get("cost_optimized_threshold", {}).get("threshold")
        if isinstance(payload.get("cost_optimized_threshold"), dict)
        else None,
    ]

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue

    return None


def load_review_threshold() -> tuple[float, str]:
    """Load the preferred review threshold, falling back to 0.50."""
    threshold_sources = [
        (COST_OPTIMIZED_THRESHOLD_PATH, "cost_optimized_threshold"),
        (SELECTED_THRESHOLD_PATH, "selected_threshold"),
    ]

    for path, source in threshold_sources:
        if not path.exists():
            continue
        threshold = extract_threshold(load_json(path))
        if threshold is not None:
            return threshold, source

    return FALLBACK_REVIEW_THRESHOLD, "fallback_0_50"


def load_model() -> object:
    """Load the trained scrap-risk model."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run `python src/train_model.py` first."
        )

    return joblib.load(MODEL_PATH)


def load_scoring_input(path: Path) -> pd.DataFrame:
    """Load the new production batch scoring input."""
    if not path.exists():
        raise FileNotFoundError(f"Scoring input file not found at {path}")

    return pd.read_csv(path)


def validate_scoring_input(df: pd.DataFrame) -> list[str]:
    """Validate scoring input columns and return non-blocking warnings."""
    missing_columns = [
        column for column in SCORING_REQUIRED_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"Scoring input is missing required columns: {missing_columns}")

    if df.empty:
        raise ValueError("Scoring input has zero rows.")

    invalid_numeric = {}
    for column in NUMERIC_FEATURES:
        missing_mask = is_missing(df[column])
        non_empty = df.loc[~missing_mask, column]
        numeric_values = pd.to_numeric(non_empty, errors="coerce")
        invalid_values = (
            non_empty[numeric_values.isna()].astype(str).drop_duplicates().head(5).tolist()
        )
        if invalid_values:
            invalid_numeric[column] = invalid_values

    if invalid_numeric:
        raise ValueError(f"Scoring input has invalid numeric values: {invalid_numeric}")

    warnings = []
    for column, expected_values in EXPECTED_CATEGORIES.items():
        observed = df.loc[~is_missing(df[column]), column].astype(str)
        unexpected_values = sorted(set(observed) - set(expected_values))
        if unexpected_values:
            warnings.append(
                f"{column} has unexpected categories: {', '.join(unexpected_values)}"
            )

    for column, (minimum, maximum) in ENGINEERING_RANGES.items():
        values = pd.to_numeric(df[column], errors="coerce")
        outside_count = int(((values < minimum) | (values > maximum)).sum())
        if outside_count:
            warnings.append(
                f"{column} has {outside_count} values outside illustrative monitoring range {minimum} to {maximum}."
            )

    return warnings


def prepare_scoring_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric scoring columns before model inference."""
    prepared = df.copy()
    for column in NUMERIC_FEATURES:
        prepared[column] = pd.to_numeric(prepared[column])
    return prepared


def classify_risk(probability: float) -> str:
    """Classify model probability into a simple review risk level."""
    if probability >= 0.60:
        return "High"
    if probability >= 0.30:
        return "Medium"
    return "Low"


def make_review_decision(probability: float, risk_level: str, threshold: float) -> tuple[str, str]:
    """Convert model risk into an engineering review workflow decision."""
    if probability >= threshold:
        return (
            "ENGINEERING_REVIEW_REQUIRED",
            "Probability exceeds configured review threshold.",
        )
    if risk_level == "High":
        return (
            "ENGINEERING_REVIEW_REQUIRED",
            "High predicted risk; engineering review is recommended even below the configured threshold.",
        )
    if risk_level == "Medium":
        return (
            "ADDITIONAL_MONITORING",
            "Medium predicted risk; monitor process conditions and review if pattern repeats.",
        )
    return (
        "STANDARD_MONITORING",
        "Low predicted risk; continue standard monitoring.",
    )


def format_recommendations(recommendations: list[str]) -> str:
    """Format recommendation text for CSV and Markdown outputs."""
    return "; ".join(recommendations)


def format_driver_names(suspected_drivers: list[dict], limit: int | None = None) -> str:
    """Format suspected driver names as readable text."""
    drivers = suspected_drivers if limit is None else suspected_drivers[:limit]
    return "; ".join(driver["driver"] for driver in drivers)


def review_batch(df: pd.DataFrame, model: object, review_threshold: float) -> pd.DataFrame:
    """Score and enrich one batch of new production records."""
    results = prepare_scoring_features(df)
    probabilities = model.predict_proba(results[FEATURE_COLUMNS])[:, 1]

    results["scrap_probability"] = probabilities.round(4)
    results["risk_level"] = results["scrap_probability"].apply(classify_risk)
    results["review_threshold"] = review_threshold

    review_decisions = results.apply(
        lambda row: make_review_decision(
            float(row["scrap_probability"]),
            str(row["risk_level"]),
            review_threshold,
        ),
        axis=1,
    )
    results["review_decision"] = [decision for decision, _ in review_decisions]
    results["decision_reason"] = [reason for _, reason in review_decisions]

    rca_rows = []
    for _, row in results.iterrows():
        rca_input = row.to_dict()
        rca_input["predicted_scrap_risk"] = row["risk_level"]
        analysis = analyze_root_causes(rca_input)
        suspected_drivers = analysis["suspected_drivers"]

        rca_rows.append(
            {
                "root_cause_summary": analysis["summary"],
                "suspected_driver_count": len(suspected_drivers),
                "top_suspected_drivers": format_driver_names(suspected_drivers, limit=3),
                "engineering_recommendations": format_recommendations(
                    analysis["recommendations"]
                ),
            }
        )

    return pd.concat([results, pd.DataFrame(rca_rows)], axis=1)


def count_values(series: pd.Series) -> dict:
    """Return deterministic value counts for JSON output."""
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def build_top_driver_summary(results: pd.DataFrame) -> list[dict]:
    """Build top suspected driver counts from formatted result rows."""
    counts: dict[str, int] = {}

    for value in results["top_suspected_drivers"]:
        for driver in str(value).split(";"):
            driver = driver.strip()
            if driver:
                counts[driver] = counts.get(driver, 0) + 1

    return [
        {"driver": driver, "count": count}
        for driver, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_summary(
    results: pd.DataFrame,
    input_path: Path,
    review_threshold: float,
    threshold_source: str,
    validation_warnings: list[str],
) -> dict:
    """Build the JSON batch review summary."""
    return {
        "input_path": display_path(input_path),
        "row_count": int(len(results)),
        "review_threshold": review_threshold,
        "threshold_source": threshold_source,
        "decision_counts": count_values(results["review_decision"]),
        "risk_level_counts": count_values(results["risk_level"]),
        "top_suspected_drivers": build_top_driver_summary(results),
        "validation_warnings": validation_warnings,
        "note": "Synthetic portfolio-prototype review support output; not a quality disposition authority.",
    }


def write_csv_results(results: pd.DataFrame, path: Path) -> None:
    """Write row-level batch review results."""
    path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(path, index=False)


def write_json_summary(summary: dict, path: Path) -> None:
    """Write the JSON batch review summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Convert a dataframe to Markdown without exposing pandas internals."""
    if df.empty:
        return "No rows met the high-priority engineering review criteria."
    return df.to_markdown(index=False)


def write_markdown_report(
    results: pd.DataFrame,
    summary: dict,
    path: Path,
) -> None:
    """Write a concise Markdown batch review report."""
    high_priority = results[
        results["review_decision"] == "ENGINEERING_REVIEW_REQUIRED"
    ].copy()
    high_priority = high_priority.sort_values("scrap_probability", ascending=False)

    high_priority_table = high_priority[
        [
            "part_id",
            "scrap_probability",
            "risk_level",
            "review_decision",
            "root_cause_summary",
            "engineering_recommendations",
        ]
    ].copy()
    high_priority_table["scrap_probability"] = high_priority_table[
        "scrap_probability"
    ].apply(lambda value: f"{float(value) * 100:.2f}%")

    decision_lines = "\n".join(
        f"- {decision}: {count}"
        for decision, count in summary["decision_counts"].items()
    ) or "- No decisions available."
    risk_lines = "\n".join(
        f"- {risk_level}: {count}"
        for risk_level, count in summary["risk_level_counts"].items()
    ) or "- No risk levels available."
    driver_lines = "\n".join(
        f"- {item['driver']}: {item['count']}"
        for item in summary["top_suspected_drivers"][:8]
    ) or "- No configured suspected drivers detected."
    warning_lines = "\n".join(
        f"- {warning}" for warning in summary["validation_warnings"]
    ) or "- No scoring-input validation warnings."

    report = f"""# Batch Review Report

## Overall Summary

- Input file: `{summary['input_path']}`
- Reviewed rows: {summary['row_count']}
- Review threshold: {summary['review_threshold']:.2f} (`{summary['threshold_source']}`)
- Purpose: engineering review support for synthetic portfolio data, not a quality disposition authority.

## Review Decision Counts

{decision_lines}

## Risk Level Counts

{risk_lines}

## Top Suspected Drivers

{driver_lines}

## High-Priority Engineering Review Items

{dataframe_to_markdown(high_priority_table)}

## Notes and Limitations

- This workflow uses a trained prototype model, configured thresholds, and illustrative RCA rules.
- Review decisions identify records for engineering attention, additional monitoring, or standard monitoring.
- The output supports review prioritization only and does not make quality dispositions.
- Scoring-input validation warnings:
{warning_lines}
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def run_batch_review(
    input_path: Path,
    output_csv_path: Path,
    output_json_path: Path,
    output_markdown_path: Path,
) -> tuple[pd.DataFrame, dict]:
    """Run the full batch review workflow."""
    df = load_scoring_input(input_path)
    validation_warnings = validate_scoring_input(df)
    model = load_model()
    review_threshold, threshold_source = load_review_threshold()

    results = review_batch(df, model, review_threshold)
    summary = build_summary(
        results=results,
        input_path=input_path,
        review_threshold=review_threshold,
        threshold_source=threshold_source,
        validation_warnings=validation_warnings,
    )

    write_csv_results(results, output_csv_path)
    write_json_summary(summary, output_json_path)
    write_markdown_report(results, summary, output_markdown_path)

    return results, summary


def parse_args() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Review a new synthetic production batch.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Path to the scoring CSV input.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV_PATH),
        help="Path for row-level review CSV output.",
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
    args = parse_args().parse_args()
    input_path = resolve_path(args.input)
    output_csv_path = resolve_path(args.output_csv)
    output_json_path = resolve_path(args.output_json)
    output_markdown_path = resolve_path(args.output_md)

    try:
        results, summary = run_batch_review(
            input_path=input_path,
            output_csv_path=output_csv_path,
            output_json_path=output_json_path,
            output_markdown_path=output_markdown_path,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"Batch review failed: {error}", file=sys.stderr)
        return 1

    print("Batch review completed.")
    print(f"Rows reviewed: {len(results)}")
    print(f"Review threshold: {summary['review_threshold']} ({summary['threshold_source']})")
    print(f"CSV results: {output_csv_path}")
    print(f"JSON summary: {output_json_path}")
    print(f"Markdown report: {output_markdown_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
