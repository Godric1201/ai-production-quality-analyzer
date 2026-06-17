from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
README_PATH = PROJECT_ROOT / "README.md"


def read_readme() -> str:
    assert README_PATH.exists(), "README.md does not exist."
    return README_PATH.read_text(encoding="utf-8").lower()


def test_readme_contains_portfolio_positioning() -> None:
    readme = read_readme()

    for expected in [
        "https://godric1201.github.io/ai-production-quality-analyzer/",
        "synthetic manufacturing dataset",
        "decision-support",
        "configurable engineering rulebook",
        "model evaluation",
        "engineering review trace",
        "python src/run_pipeline.py",
    ]:
        assert expected in readme, f"{expected} missing from README.md."


def test_readme_is_honest_about_limitations() -> None:
    readme = read_readme()

    for expected in [
        "limitations",
        "not real factory data",
        "not a final quality decision",
        "not validated for real factory deployment",
        "production readiness",
    ]:
        assert expected in readme, f"{expected} missing from README.md limitations."


def test_readme_describes_industrial_ai_workflow() -> None:
    readme = read_readme()

    for expected in [
        "data validation",
        "scrap-risk model training",
        "threshold tuning",
        "cost-based threshold analysis",
        "specification compliance checks",
        "feedback evaluation",
    ]:
        assert expected in readme, f"{expected} missing from workflow description."


def main() -> None:
    tests = [
        test_readme_contains_portfolio_positioning,
        test_readme_is_honest_about_limitations,
        test_readme_describes_industrial_ai_workflow,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All README portfolio positioning checks passed.")


if __name__ == "__main__":
    main()
