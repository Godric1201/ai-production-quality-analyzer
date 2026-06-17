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
        raise RuntimeError("src/run_pipeline.py failed during dashboard verification.")


def load_dashboard_data() -> dict:
    assert DASHBOARD_DATA_PATH.exists(), "dashboard/dashboard_data.json was not generated."
    return json.loads(DASHBOARD_DATA_PATH.read_text(encoding="utf-8"))


def test_workflow_overview_data() -> None:
    run_pipeline()
    data = load_dashboard_data()
    assert "workflow_overview" in data, "workflow_overview missing from dashboard data."

    workflow = data["workflow_overview"]
    for key in ["data_quality", "batch_review", "spec_compliance", "feedback_loop"]:
        assert key in workflow, f"{key} missing from workflow_overview."


def test_dashboard_files_reference_overview() -> None:
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    app_js = APP_PATH.read_text(encoding="utf-8")
    style_css = STYLE_PATH.read_text(encoding="utf-8")

    assert "Industrial Quality Workflow Overview" in index_html
    assert "workflow_overview" in app_js
    assert "workflow-overview" in style_css


def main() -> None:
    tests = [
        test_workflow_overview_data,
        test_dashboard_files_reference_overview,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All dashboard workflow overview checks passed.")


if __name__ == "__main__":
    main()
