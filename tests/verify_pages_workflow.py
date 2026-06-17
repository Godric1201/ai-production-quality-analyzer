from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "deploy-dashboard-pages.yml"
README_PATH = PROJECT_ROOT / "README.md"


def normalized_text(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(PROJECT_ROOT)} does not exist."
    return path.read_text(encoding="utf-8").lower()


def test_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists(), "GitHub Pages deployment workflow is missing."


def test_workflow_triggers_and_actions() -> None:
    workflow = normalized_text(WORKFLOW_PATH)

    for expected in [
        "workflow_dispatch",
        "push:",
        "actions/configure-pages",
        "actions/upload-pages-artifact",
        "actions/deploy-pages",
        "python src/run_pipeline.py",
    ]:
        assert expected in workflow, f"{expected} missing from Pages workflow."


def test_workflow_publishes_static_site_directory() -> None:
    workflow = normalized_text(WORKFLOW_PATH)

    assert "mkdir" in workflow and "site" in workflow
    assert "dashboard/index.html" in workflow
    assert "dashboard/app.js" in workflow
    assert "dashboard/style.css" in workflow
    assert "dashboard/dashboard_data.json" in workflow
    assert "path: site" in workflow or "path: ./site" in workflow


def test_readme_documents_pages_demo() -> None:
    readme = normalized_text(README_PATH)

    for expected in [
        "github pages",
        "static dashboard",
        "python src/run_pipeline.py",
        "http://localhost:8000/dashboard/",
    ]:
        assert expected in readme, f"{expected} missing from README."


def main() -> None:
    tests = [
        test_workflow_exists,
        test_workflow_triggers_and_actions,
        test_workflow_publishes_static_site_directory,
        test_readme_documents_pages_demo,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All GitHub Pages workflow checks passed.")


if __name__ == "__main__":
    main()
