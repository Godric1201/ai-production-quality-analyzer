from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


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


def _add_driver(
    drivers: list[dict[str, str]],
    driver: str,
    severity: str,
    evidence: str,
    engineering_interpretation: str,
) -> None:
    """Append a suspected driver using the public output structure."""
    drivers.append(
        {
            "driver": driver,
            "severity": severity,
            "evidence": evidence,
            "engineering_interpretation": engineering_interpretation,
        }
    )


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


def analyze_root_causes(row: dict | pd.Series) -> dict:
    """Analyze one production row and return likely quality risk drivers.

    The analysis is intentionally rule-based and deterministic. It checks only
    the fields present in the supplied row, so it can be used with partial data
    from model scoring, dashboards, or report generation pipelines.
    """
    normalized_row = _normalize_row(_row_to_dict(row))
    drivers: list[dict[str, str]] = []

    temperature = _as_float(_get_value(normalized_row, "temperature"))
    if temperature is not None:
        if temperature >= 195:
            _add_driver(
                drivers,
                "Very high temperature",
                "high",
                "temperature is well above the configured risk threshold",
                "Potential thermal drift, overheating, resin degradation, or process setpoint issue.",
            )
        elif temperature > 190:
            _add_driver(
                drivers,
                "High temperature",
                "medium",
                "temperature is above the configured risk threshold",
                "Possible thermal process drift or insufficient cooling control.",
            )
        elif temperature < 175:
            _add_driver(
                drivers,
                "Low temperature",
                "medium",
                "temperature is below the expected operating range",
                "Possible under-heating, poor material flow, or incomplete process stabilization.",
            )

    pressure = _as_float(_get_value(normalized_row, "pressure"))
    if pressure is not None:
        if pressure >= 6.4:
            _add_driver(
                drivers,
                "High pressure",
                "medium",
                "pressure is above the expected operating range",
                "Possible restriction, blocked flow path, fixture issue, or aggressive process setting.",
            )
        elif pressure <= 5.1:
            _add_driver(
                drivers,
                "Low pressure",
                "medium",
                "pressure is below the expected operating range",
                "Possible leakage, poor clamping, feed variation, or insufficient process force.",
            )

    vibration = _as_float(_get_value(normalized_row, "vibration"))
    if vibration is not None:
        if vibration >= 3.1:
            _add_driver(
                drivers,
                "High vibration",
                "high",
                "vibration is above the configured risk threshold",
                "Possible mechanical instability, tool wear, imbalance, or maintenance issue.",
            )
        elif vibration > 2.7:
            _add_driver(
                drivers,
                "Elevated vibration",
                "medium",
                "vibration is above the normal monitoring band",
                "Potential early signal of tool wear, loose fixtures, or machine imbalance.",
            )

    cycle_time = _as_float(_get_value(normalized_row, "cycle_time"))
    if cycle_time is not None:
        if cycle_time >= 53:
            _add_driver(
                drivers,
                "Abnormal cycle time",
                "high",
                "cycle time is materially above the configured risk threshold",
                "Possible process slowdown, material handling delay, machine wear, or unstable settings.",
            )
        elif cycle_time > 50:
            _add_driver(
                drivers,
                "Long cycle time",
                "medium",
                "cycle time is above the configured risk threshold",
                "Possible setup drift, slower material flow, or operator intervention during the batch.",
            )

    machine = _as_text(_get_value(normalized_row, "machine"))
    if machine in {"m2", "machine 2"}:
        _add_driver(
            drivers,
            "Machine M2 risk pattern",
            "medium",
            "machine is M2, which is configured as a higher-risk asset",
            "This asset may need calibration review, maintenance inspection, or process capability checks.",
        )
    elif machine in {"m4", "machine 4"}:
        _add_driver(
            drivers,
            "Machine M4 risk pattern",
            "low",
            "machine is M4, which carries a mild configured risk signal",
            "Monitor for recurring variation before scheduling deeper engineering action.",
        )

    shift = _as_text(_get_value(normalized_row, "shift"))
    if shift == "night":
        _add_driver(
            drivers,
            "Night shift production",
            "medium",
            "batch was produced during night shift",
            "Higher scrap risk may reflect staffing, handoff, environmental, or monitoring differences.",
        )
    elif shift == "late":
        _add_driver(
            drivers,
            "Late shift production",
            "low",
            "batch was produced during late shift",
            "Consider checking shift handoff notes and process adherence if this pattern repeats.",
        )

    material = _as_text(_get_value(normalized_row, "material"))
    if material in {"b4", "batch b4", "material b4"}:
        _add_driver(
            drivers,
            "Material batch B4",
            "medium",
            "material batch is B4, which is configured as a higher-risk batch",
            "Possible incoming material variation, storage condition issue, or supplier lot effect.",
        )

    operator_experience = _as_float(_get_value(normalized_row, "operator_experience"))
    if operator_experience is not None and operator_experience < 2:
        _add_driver(
            drivers,
            "Low operator experience",
            "medium",
            "operator experience is below 2 years",
            "Additional checklist support or supervisor review may reduce setup and handling variation.",
        )

    humidity = _as_float(_get_value(normalized_row, "humidity"))
    if humidity is not None and humidity > 60:
        _add_driver(
            drivers,
            "High humidity",
            "low",
            "humidity is above the configured monitoring band",
            "Possible environmental contribution to material behavior, handling, or surface quality.",
        )

    risk_level = _risk_level(normalized_row)
    if risk_level == "high" and not drivers:
        _add_driver(
            drivers,
            "Elevated predicted scrap risk",
            "medium",
            "model output indicates high scrap risk, but no configured process driver was present",
            "Review additional process signals or recent production notes not captured by this module.",
        )

    suspected_drivers = [driver for _, driver in _sort_drivers(drivers)]
    analysis = {
        "suspected_drivers": suspected_drivers,
        "recommendations": generate_engineering_recommendations(suspected_drivers),
        "summary": "",
        "risk_level": risk_level,
    }
    analysis["summary"] = format_root_cause_summary(analysis)
    return analysis


def generate_engineering_recommendations(root_causes: list[dict]) -> list[str]:
    """Convert suspected root causes into concise engineering actions."""
    recommendation_map = {
        "Very high temperature": "Audit temperature setpoints, cooling performance, and recent thermal alarms before releasing the batch.",
        "High temperature": "Review process temperature control and verify cooling stability around the affected batch.",
        "Low temperature": "Check heating stability, warm-up completion, and material flow conditions.",
        "High pressure": "Inspect pressure regulation, tooling restrictions, and fixture condition.",
        "Low pressure": "Check for leaks, feed variation, clamp issues, or insufficient process force.",
        "High vibration": "Inspect machine vibration sources and check for tool wear, imbalance, or loose fixtures.",
        "Elevated vibration": "Trend vibration for the machine and inspect tooling if the signal persists.",
        "Abnormal cycle time": "Investigate cycle time deviation, material handling delays, and machine wear indicators.",
        "Long cycle time": "Review cycle time drift and compare against recent setup or operator changes.",
        "Machine M2 risk pattern": "Inspect M2 calibration, maintenance status, and recent quality history.",
        "Machine M4 risk pattern": "Monitor M4 quality trend and confirm process settings remain within control limits.",
        "Night shift production": "Apply additional process checks during night shift production.",
        "Late shift production": "Review shift handoff notes and confirm standard work adherence.",
        "Material batch B4": "Quarantine or sample-check material batch B4 and compare against supplier lot history.",
        "Low operator experience": "Use operator guidance, checklist support, or supervisor sign-off for this setup.",
        "High humidity": "Check humidity controls and confirm material storage conditions.",
        "Elevated predicted scrap risk": "Review model inputs, production notes, and recent maintenance history for uncaptured risk factors.",
    }

    recommendations: list[str] = []
    for root_cause in root_causes:
        recommendation = recommendation_map.get(root_cause.get("driver"))
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)

    if not recommendations:
        recommendations.append("No immediate engineering action required. Continue standard process monitoring.")

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
