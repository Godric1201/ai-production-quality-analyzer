from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
INDEX_PATH = PROJECT_ROOT / "dashboard" / "index.html"
APP_PATH = PROJECT_ROOT / "dashboard" / "app.js"
STYLE_PATH = PROJECT_ROOT / "dashboard" / "style.css"


def run_pipeline() -> None:
    """Run the project pipeline so dashboard data is regenerated."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py")],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("src/run_pipeline.py failed during case trace verification.")


def load_dashboard_data() -> dict:
    assert DASHBOARD_DATA_PATH.exists(), "dashboard/dashboard_data.json was not generated."
    return json.loads(DASHBOARD_DATA_PATH.read_text(encoding="utf-8"))


def test_case_trace_data() -> None:
    run_pipeline()
    data = load_dashboard_data()
    assert "case_trace" in data, "case_trace missing from dashboard data."

    case_trace = data["case_trace"]
    if case_trace.get("status") == "missing":
        assert case_trace.get("message"), "Missing case_trace should include a message."
        return

    assert case_trace.get("part_id"), "case_trace part_id missing."
    for key in [
        "input_conditions",
        "model_review",
        "rca",
        "spec_compliance",
        "feedback",
        "trace_summary",
    ]:
        assert key in case_trace, f"{key} missing from case_trace."


def test_dashboard_files_reference_trace() -> None:
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    app_js = APP_PATH.read_text(encoding="utf-8")
    style_css = STYLE_PATH.read_text(encoding="utf-8")

    assert "Engineering Review Trace" in index_html
    assert "case_trace" in app_js
    assert "case-trace" in style_css


def test_trace_label_polish() -> None:
    app_js = APP_PATH.read_text(encoding="utf-8")
    style_css = STYLE_PATH.read_text(encoding="utf-8")

    for raw_value, display_label in [
        ("ENGINEERING_REVIEW_REQUIRED", "Review Required"),
        ("TRUE_POSITIVE_REVIEW", "Confirmed Issue"),
        ("CRITICAL_VIOLATION", "Critical Violation"),
    ]:
        assert raw_value in app_js, f"{raw_value} missing from trace label mapping."
        assert display_label in app_js, f"{display_label} missing from trace label mapping."

    assert "\\u00b7" in app_js, "Trace risk display should use a centered-dot separator."
    assert "High - " not in app_js, "Trace risk display should not use a hyphen separator."
    assert "trace-chip" in style_css, "Trace driver chip styling missing."
    assert "overflow-wrap" in style_css, "Trace wrapping styling missing."


def main() -> None:
    tests = [
        test_case_trace_data,
        test_dashboard_files_reference_trace,
        test_trace_label_polish,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All dashboard case trace checks passed.")


if __name__ == "__main__":
    main()
