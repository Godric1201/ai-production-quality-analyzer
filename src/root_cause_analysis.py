from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "rca_rules.yaml"

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}

SUPPORTED_COLUMNS = {
    "temperature": ("temperature", "temperature_c", "temp_c", "process_temperature"),
    "pressure": ("pressure", "pressure_bar", "process_pressure"),
    "vibration": ("vibration", "vibration_mm_s", "vibration_level"),
    "cycle_time": ("cycle_time", "cycle_time_s", "cycle_seconds"),
    "machine": ("machine", "machine_id"),
    "operator": ("operator", "operator_id"),
    "operator_experience": ("operator_experience_years", "experience_years"),
    "material": ("material", "material_batch", "material_lot"),
    "shift": ("shift", "production_shift"),
    "humidity": ("humidity", "humidity_percent"),
    "scrap_probability": ("scrap_probability", "scrap_risk_probability"),
    "predicted_scrap_risk": ("predicted_scrap_risk", "risk_level"),
}

COLUMN_ALIAS_TO_LOGICAL = {
    alias.lower(): logical_column
    for logical_column, aliases in SUPPORTED_COLUMNS.items()
    for alias in aliases
}


def _row_to_dict(row: dict | pd.Series) -> dict[str, Any]:
    """Convert a dictionary-like row or pandas Series into a plain dictionary."""
    if isinstance(row, pd.Series):
        return row.to_dict()
    if isinstance(row, Mapping):
        return dict(row)
    raise TypeError("row must be a dict-like object or pandas.Series")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize row keys to lowercase strings for resilient column lookup."""
    return {str(key).lower(): value for key, value in row.items()}


def _get_value(row: dict[str, Any], logical_column: str) -> Any | None:
    """Return the first available value for a supported logical column."""
    for column in SUPPORTED_COLUMNS[logical_column]:
        value = row.get(column.lower())
        if pd.notna(value):
            return value
    return None


def _get_configured_value(row: dict[str, Any], column: str) -> Any | None:
    """Return a row value for a configured column, including supported aliases."""
    normalized_column = str(column).lower()
    direct_value = row.get(normalized_column)
    if direct_value is not None and pd.notna(direct_value):
        return direct_value

    logical_column = COLUMN_ALIAS_TO_LOGICAL.get(normalized_column)
    if logical_column:
        return _get_value(row, logical_column)

    return None


def _as_float(value: Any) -> float | None:
    """Convert numeric-looking values to float while tolerating blanks."""
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    """Convert non-empty values to stripped lowercase text."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text.lower() if text else None


def _sort_drivers(drivers: list[dict[str, str]]) -> list[tuple[int, dict[str, str]]]:
    """Sort drivers deterministically by severity and insertion order."""
    return sorted(
        enumerate(drivers),
        key=lambda item: (-SEVERITY_RANK.get(item[1]["severity"], 0), item[0]),
    )


def _risk_level(row: dict[str, Any]) -> str:
    """Infer a simple risk level from available model prediction columns."""
    explicit_risk = _get_value(row, "predicted_scrap_risk")
    if explicit_risk is not None:
        normalized_risk = str(explicit_risk).strip().lower()
        if normalized_risk in {"high", "medium", "low"}:
            return normalized_risk

    probability = _as_float(_get_value(row, "scrap_probability"))
    if probability is None:
        return "unknown"
    if probability >= 0.60:
        return "high"
    if probability >= 0.30:
        return "medium"
    return "low"


@lru_cache(maxsize=4)
def load_rca_rules(config_path: Path | None = None) -> dict:
    """Load and validate the configured RCA rules."""
    path = config_path or DEFAULT_RULES_PATH
    if not path.exists():
        raise FileNotFoundError(f"RCA rules config not found at {path}")

    with open(path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("RCA rules config must be a YAML mapping.")

    rules = config.get("rules")
    if not isinstance(rules, list):
        raise ValueError("RCA rules config must contain a 'rules' list.")

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            raise ValueError(f"RCA rule #{index} must be a mapping.")
        _validate_rule(rule, index)

    fallback = config.get("fallback", {})
    if fallback and not isinstance(fallback, dict):
        raise ValueError("RCA rules config 'fallback' must be a mapping.")

    return config


def _validate_rule(rule: dict, index: int) -> None:
    """Validate one configured RCA rule."""
    required_fields = {
        "id",
        "column",
        "type",
        "driver",
        "severity",
        "evidence",
        "engineering_interpretation",
    }
    missing_fields = sorted(required_fields - set(rule))
    if missing_fields:
        raise ValueError(
            f"RCA rule #{index} is missing required fields: {missing_fields}"
        )

    rule_type = rule["type"]
    if rule_type == "numeric_threshold":
        if rule.get("operator") not in {">", ">=", "<", "<="}:
            raise ValueError(
                f"RCA rule '{rule['id']}' has unsupported numeric operator."
            )
        if _as_float(rule.get("value")) is None:
            raise ValueError(f"RCA rule '{rule['id']}' must define a numeric value.")
    elif rule_type == "categorical_match":
        values = rule.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError(
                f"RCA rule '{rule['id']}' must define non-empty categorical values."
            )
    else:
        raise ValueError(f"RCA rule '{rule['id']}' has unsupported type '{rule_type}'.")

    if rule["severity"] not in SEVERITY_RANK:
        raise ValueError(f"RCA rule '{rule['id']}' has unsupported severity.")


def evaluate_rule(row: dict, rule: dict) -> dict | None:
    """Evaluate one configured RCA rule against a normalized row."""
    rule_type = rule["type"]

    if rule_type == "numeric_threshold":
        value = _as_float(_get_configured_value(row, rule["column"]))
        threshold = _as_float(rule["value"])
        if value is None or threshold is None:
            return None

        operator = rule["operator"]
        matched = (
            (operator == ">" and value > threshold)
            or (operator == ">=" and value >= threshold)
            or (operator == "<" and value < threshold)
            or (operator == "<=" and value <= threshold)
        )
    elif rule_type == "categorical_match":
        value = _as_text(_get_configured_value(row, rule["column"]))
        expected_values = {_as_text(item) for item in rule["values"]}
        expected_values.discard(None)
        matched = value in expected_values
    else:
        raise ValueError(f"Unsupported RCA rule type: {rule_type}")

    if not matched:
        return None

    return {
        "driver": rule["driver"],
        "severity": rule["severity"],
        "evidence": rule["evidence"],
        "engineering_interpretation": rule["engineering_interpretation"],
    }


def evaluate_rules(row: dict, rules_config: dict) -> list[dict]:
    """Evaluate configured RCA rules against a normalized row."""
    drivers = []

    for rule in rules_config["rules"]:
        driver = evaluate_rule(row, rule)
        if driver is not None:
            drivers.append(driver)

    return drivers


def _build_fallback_driver(rules_config: dict) -> dict | None:
    """Build the configured high-risk fallback driver."""
    fallback = rules_config.get("fallback", {}).get("high_risk_no_driver")
    if not fallback:
        return None

    return {
        "driver": fallback["driver"],
        "severity": fallback["severity"],
        "evidence": fallback["evidence"],
        "engineering_interpretation": fallback["engineering_interpretation"],
    }


def analyze_root_causes(row: dict | pd.Series) -> dict:
    """Analyze one production row and return likely quality risk drivers.

    The analysis is intentionally rule-based and deterministic. Rules are loaded
    from config/rca_rules.yaml so prototype thresholds and recommendation text
    can be reviewed without changing Python code.
    """
    rules_config = load_rca_rules()
    normalized_row = _normalize_row(_row_to_dict(row))
    drivers = evaluate_rules(normalized_row, rules_config)

    risk_level = _risk_level(normalized_row)
    if risk_level == "high" and not drivers:
        fallback_driver = _build_fallback_driver(rules_config)
        if fallback_driver is not None:
            drivers.append(fallback_driver)

    suspected_drivers = [driver for _, driver in _sort_drivers(drivers)]
    analysis = {
        "suspected_drivers": suspected_drivers,
        "recommendations": generate_engineering_recommendations(
            suspected_drivers,
            rules_config,
        ),
        "summary": "",
        "risk_level": risk_level,
    }
    analysis["summary"] = format_root_cause_summary(analysis)
    return analysis


def generate_engineering_recommendations(
    suspected_drivers: list[dict],
    rules_config: dict | None = None,
) -> list[str]:
    """Convert suspected root causes into configured engineering actions."""
    config = rules_config or load_rca_rules()
    recommendations_by_driver = {
        rule["driver"]: rule.get("recommendation")
        for rule in config.get("rules", [])
    }

    fallback = config.get("fallback", {}).get("high_risk_no_driver", {})
    if fallback:
        recommendations_by_driver[fallback["driver"]] = fallback.get("recommendation")

    recommendations: list[str] = []
    for root_cause in suspected_drivers:
        recommendation = recommendations_by_driver.get(root_cause.get("driver"))
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)

    if not recommendations:
        default_recommendation = config.get(
            "default_recommendation",
            "No immediate engineering action required. Continue standard process monitoring.",
        )
        recommendations.append(default_recommendation)

    return recommendations


def format_root_cause_summary(analysis: dict) -> str:
    """Format analysis output as concise text for reports or dashboards."""
    drivers = analysis.get("suspected_drivers", [])
    risk_level = analysis.get("risk_level", "unknown")

    if not drivers:
        if risk_level in {"low", "unknown"}:
            return "No configured root cause driver was detected for this batch."
        return f"The batch has {risk_level} predicted scrap risk, but no configured process driver was detected."

    driver_names = [driver["driver"].lower() for driver in drivers[:3]]
    if len(driver_names) == 1:
        driver_text = driver_names[0]
    elif len(driver_names) == 2:
        driver_text = " and ".join(driver_names)
    else:
        driver_text = ", ".join(driver_names[:-1]) + f", and {driver_names[-1]}"

    risk_phrase = "" if risk_level == "unknown" else f"{risk_level} "
    return f"The batch shows {risk_phrase}scrap risk mainly due to {driver_text}."
