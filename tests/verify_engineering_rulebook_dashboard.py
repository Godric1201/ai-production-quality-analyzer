from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA_PATH = PROJECT_ROOT / "dashboard" / "dashboard_data.json"
APP_PATH = PROJECT_ROOT / "dashboard" / "app.js"
INDEX_PATH = PROJECT_ROOT / "dashboard" / "index.html"
SPEC_CONFIG_PATH = PROJECT_ROOT / "config" / "spec_requirements.yaml"
RCA_CONFIG_PATH = PROJECT_ROOT / "config" / "rca_rules.yaml"


def run_pipeline() -> None:
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "run_pipeline.py")],
        cwd=PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("src/run_pipeline.py failed during rulebook verification.")


def load_dashboard_data() -> dict:
    assert DASHBOARD_DATA_PATH.exists(), "dashboard/dashboard_data.json was not generated."
    return json.loads(DASHBOARD_DATA_PATH.read_text(encoding="utf-8"))


def test_rulebook_export() -> None:
    run_pipeline()
    data = load_dashboard_data()

    assert "engineering_rulebook" in data, "engineering_rulebook missing from dashboard data."
    rulebook = data["engineering_rulebook"]
    summary = rulebook.get("summary", {})

    assert summary.get("spec_requirement_count", 0) > 0
    assert summary.get("rca_rule_count", 0) > 0
    assert "config/spec_requirements.yaml" in summary.get("source_files", [])
    assert "config/rca_rules.yaml" in summary.get("source_files", [])

    exported_text = json.dumps(rulebook, ensure_ascii=False)
    assert "Temperature" in exported_text
    assert "Vibration" in exported_text


def test_rulebook_frontend_references() -> None:
    app_js = APP_PATH.read_text(encoding="utf-8")
    index_html = INDEX_PATH.read_text(encoding="utf-8")

    assert "engineering_rulebook" in app_js
    assert "Engineering Rulebook" in index_html
    assert "illustrative" in index_html
    assert "domain experts" in index_html


def test_rulebook_source_files_exist() -> None:
    assert SPEC_CONFIG_PATH.exists(), "config/spec_requirements.yaml should remain the rule source."
    assert RCA_CONFIG_PATH.exists(), "config/rca_rules.yaml should remain the rule source."


def main() -> None:
    tests = [
        test_rulebook_export,
        test_rulebook_frontend_references,
        test_rulebook_source_files_exist,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All engineering rulebook dashboard checks passed.")


if __name__ == "__main__":
    main()
