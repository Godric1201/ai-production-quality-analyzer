from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STYLE_PATH = PROJECT_ROOT / "dashboard" / "style.css"
APP_PATH = PROJECT_ROOT / "dashboard" / "app.js"
INDEX_PATH = PROJECT_ROOT / "dashboard" / "index.html"


def read_lower(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(PROJECT_ROOT)} does not exist."
    return path.read_text(encoding="utf-8").lower()


def test_mobile_media_queries_exist() -> None:
    style = read_lower(STYLE_PATH)

    assert "@media" in style
    assert "max-width: 900px" in style
    assert "max-width: 700px" in style


def test_page_overflow_protection() -> None:
    style = read_lower(STYLE_PATH)

    for expected in [
        "overflow-x",
        "max-width: 100%",
        "min-width: 0",
        "box-sizing: border-box",
    ]:
        assert expected in style, f"{expected} missing from responsive CSS."


def test_responsive_table_solution_exists() -> None:
    style = read_lower(STYLE_PATH)
    index_html = read_lower(INDEX_PATH)

    assert "table-scroll" in style
    assert "table-scroll" in index_html
    assert "-webkit-overflow-scrolling: touch" in style
    assert "content: attr(data-label)" in style
    assert ".rulebook-table thead" in style
    assert ".evaluation-table thead" in style
    assert ".rca-table thead" in style


def test_generated_cells_include_data_labels() -> None:
    app_js = read_lower(APP_PATH)

    assert "dataset.label" in app_js
    for expected_label in [
        "recommended action",
        "possible cause",
        "actual scrap rate",
        "average predicted risk",
        "action preview",
    ]:
        assert expected_label in app_js


def test_dashboard_sections_still_referenced() -> None:
    combined = f"{read_lower(INDEX_PATH)}\n{read_lower(APP_PATH)}"

    for expected in [
        "engineering rulebook",
        "model evaluation",
        "engineering review trace",
    ]:
        assert expected in combined, f"{expected} missing from dashboard files."


def main() -> None:
    tests = [
        test_mobile_media_queries_exist,
        test_page_overflow_protection,
        test_responsive_table_solution_exists,
        test_generated_cells_include_data_labels,
        test_dashboard_sections_still_referenced,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")

    print("All mobile dashboard responsive checks passed.")


if __name__ == "__main__":
    main()
