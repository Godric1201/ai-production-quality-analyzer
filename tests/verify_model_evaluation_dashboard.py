from __future__ import annotations

from pathlib import Path
import csv
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = PROJECT_ROOT / "outputs" / "model_evaluation_summary.json"
RISK_BAND_PATH = PROJECT_ROOT / "outputs" / "risk_band_evaluation.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "model_evaluation_report.md"
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
INDEX_PATH = PROJECT_ROOT / "dashboard" / "index.html"
APP_PATH = PROJECT_ROOT / "dashboard" / "app.js"


def run_pipeline() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py")],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("src/run_pipeline.py failed during model evaluation verification.")


def load_json(path: Path) -> dict:
    assert path.exists(), f"{path.relative_to(PROJECT_ROOT)} was not generated."
    return json.loads(path.read_text(encoding="utf-8"))


def load_risk_band_rows() -> list[dict]:
    assert RISK_BAND_PATH.exists(), "outputs/risk_band_evaluation.csv was not generated."
    with open(RISK_BAND_PATH, "r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_pipeline_and_outputs() -> None:
    run_pipeline()

    for path in [SUMMARY_PATH, RISK_BAND_PATH, REPORT_PATH]:
        assert path.exists(), f"{path.relative_to(PROJECT_ROOT)} missing after pipeline run."


def test_summary_fields() -> None:
    summary = load_json(SUMMARY_PATH)

    for key in ["roc_auc", "pr_auc", "baseline_scrap_rate", "model_role"]:
        assert key in summary, f"{key} missing from model evaluation summary."

    assert summary["model_role"] == "early_warning_decision_support"
    assert 0 <= float(summary["roc_auc"]) <= 1
    assert 0 <= float(summary["pr_auc"]) <= 1
    assert 0 <= float(summary["baseline_scrap_rate"]) <= 1


def test_risk_band_output() -> None:
    rows = load_risk_band_rows()
    bands = {row["risk_band"] for row in rows}

    assert {"Low risk", "Medium risk", "High risk"}.issubset(bands)
    for row in rows:
        assert "review_priority" in row
        assert "actual_scrap_rate" in row
        assert "average_predicted_risk" in row


def test_dashboard_data_model_evaluation() -> None:
    data = load_json(DASHBOARD_DATA_PATH)

    assert "model_evaluation" in data, "model_evaluation missing from dashboard data."
    model_evaluation = data["model_evaluation"]
    assert model_evaluation.get("summary", {}).get("model_role") == (
        "early_warning_decision_support"
    )
    assert len(model_evaluation.get("risk_bands", [])) >= 3
    assert 0 < len(model_evaluation.get("threshold_tradeoff", [])) <= 5


def test_frontend_references() -> None:
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    app_js = APP_PATH.read_text(encoding="utf-8")
    combined = f"{index_html}\n{app_js}"

    assert "Model Evaluation" in combined
    assert "Risk Bands" in combined
    assert "early-warning" in combined
    assert "not a validated production" in combined
    assert "model_evaluation" in app_js


def main() -> None:
    tests = [
        test_pipeline_and_outputs,
        test_summary_fields,
        test_risk_band_output,
        test_dashboard_data_model_evaluation,
        test_frontend_references,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All model evaluation dashboard checks passed.")


if __name__ == "__main__":
    main()
