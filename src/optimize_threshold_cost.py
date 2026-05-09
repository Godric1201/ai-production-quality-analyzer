from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

THRESHOLD_METRICS_PATH = PROJECT_ROOT / "outputs" / "threshold_metrics.csv"
COST_OPTIMIZATION_PATH = PROJECT_ROOT / "outputs" / "cost_optimized_threshold.json"
COST_TABLE_PATH = PROJECT_ROOT / "outputs" / "threshold_cost_analysis.csv"


# Assumed operational costs for a manufacturing quality early-warning case.
# These are illustrative values and can be adjusted for a real production scenario.
MISSED_SCRAP_COST = 100.0
FALSE_ALARM_COST = 10.0


def load_threshold_metrics() -> pd.DataFrame:
    if not THRESHOLD_METRICS_PATH.exists():
        raise FileNotFoundError(
            f"Threshold metrics not found at {THRESHOLD_METRICS_PATH}. "
            "Run src/tune_threshold.py first."
        )

    return pd.read_csv(THRESHOLD_METRICS_PATH)


def calculate_costs(metrics_df: pd.DataFrame) -> pd.DataFrame:
    cost_df = metrics_df.copy()

    cost_df["missed_scrap_cost"] = cost_df["false_negative"] * MISSED_SCRAP_COST
    cost_df["false_alarm_cost"] = cost_df["false_positive"] * FALSE_ALARM_COST
    cost_df["total_cost"] = cost_df["missed_scrap_cost"] + cost_df["false_alarm_cost"]

    cost_df["missed_scrap_cost"] = cost_df["missed_scrap_cost"].round(2)
    cost_df["false_alarm_cost"] = cost_df["false_alarm_cost"].round(2)
    cost_df["total_cost"] = cost_df["total_cost"].round(2)

    return cost_df.sort_values("total_cost", ascending=True)


def build_cost_summary(cost_df: pd.DataFrame) -> dict:
    best = cost_df.iloc[0]

    default = cost_df[cost_df["threshold"] == 0.50].iloc[0]
    recall_tuned = cost_df[cost_df["threshold"] == 0.30].iloc[0]

    return {
        "cost_assumptions": {
            "missed_scrap_cost": MISSED_SCRAP_COST,
            "false_alarm_cost": FALSE_ALARM_COST,
            "currency": "EUR",
            "note": "Illustrative cost values for a manufacturing quality early-warning scenario.",
        },
        "cost_optimized_threshold": {
            "threshold": float(best["threshold"]),
            "total_cost": float(best["total_cost"]),
            "missed_scrap_cost": float(best["missed_scrap_cost"]),
            "false_alarm_cost": float(best["false_alarm_cost"]),
            "false_negative": int(best["false_negative"]),
            "false_positive": int(best["false_positive"]),
            "recall": float(best["recall"]),
            "precision": float(best["precision"]),
            "f1_score": float(best["f1_score"]),
        },
        "comparison": {
            "default_threshold_0_50": {
                "total_cost": float(default["total_cost"]),
                "false_negative": int(default["false_negative"]),
                "false_positive": int(default["false_positive"]),
                "recall": float(default["recall"]),
            },
            "recall_tuned_threshold_0_30": {
                "total_cost": float(recall_tuned["total_cost"]),
                "false_negative": int(recall_tuned["false_negative"]),
                "false_positive": int(recall_tuned["false_positive"]),
                "recall": float(recall_tuned["recall"]),
            },
            "cost_savings_vs_default": float(default["total_cost"] - best["total_cost"]),
        },
        "selection_reason": (
            "The cost-optimized threshold minimizes the estimated total cost from missed scrap "
            "and additional false alarms under the defined cost assumptions."
        ),
    }


def save_outputs(cost_df: pd.DataFrame, cost_summary: dict) -> None:
    COST_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    cost_df.to_csv(COST_TABLE_PATH, index=False)

    with open(COST_OPTIMIZATION_PATH, "w", encoding="utf-8") as file:
        json.dump(cost_summary, file, indent=2)


def print_summary(cost_df: pd.DataFrame, cost_summary: dict) -> None:
    best = cost_summary["cost_optimized_threshold"]
    assumptions = cost_summary["cost_assumptions"]

    print("Cost-based threshold optimization completed.")
    print("\nCost assumptions:")
    print(f"  Missed scrap cost: {assumptions['missed_scrap_cost']} {assumptions['currency']}")
    print(f"  False alarm cost: {assumptions['false_alarm_cost']} {assumptions['currency']}")

    print("\nCost analysis table:")
    print(
        cost_df[
            [
                "threshold",
                "precision",
                "recall",
                "false_positive",
                "false_negative",
                "missed_scrap_cost",
                "false_alarm_cost",
                "total_cost",
            ]
        ].to_string(index=False)
    )

    print("\nCost-optimized threshold:")
    print(f"  threshold: {best['threshold']}")
    print(f"  total_cost: {best['total_cost']} {assumptions['currency']}")
    print(f"  recall: {best['recall']}")
    print(f"  false_negative: {best['false_negative']}")
    print(f"  false_positive: {best['false_positive']}")

    print(f"\nSaved cost table to: {COST_TABLE_PATH}")
    print(f"Saved cost summary to: {COST_OPTIMIZATION_PATH}")


def main() -> None:
    metrics_df = load_threshold_metrics()
    cost_df = calculate_costs(metrics_df)
    cost_summary = build_cost_summary(cost_df)

    save_outputs(cost_df, cost_summary)
    print_summary(cost_df, cost_summary)


if __name__ == "__main__":
    main()