from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42
N_ROWS = 5000

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "production_quality_data.csv"


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Convert risk scores into probabilities between 0 and 1."""
    return 1 / (1 + np.exp(-x))


def generate_production_data(n_rows: int = N_ROWS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate synthetic manufacturing quality data with realistic scrap-risk patterns."""
    rng = np.random.default_rng(seed)

    machine_id = rng.choice(["M1", "M2", "M3", "M4"], size=n_rows, p=[0.25, 0.25, 0.25, 0.25])
    shift = rng.choice(["early", "late", "night"], size=n_rows, p=[0.4, 0.35, 0.25])
    material_batch = rng.choice(["B1", "B2", "B3", "B4", "B5"], size=n_rows)

    operator_experience_years = np.round(
        np.clip(rng.gamma(shape=2.2, scale=2.0, size=n_rows), 0.2, 12.0),
        1,
    )

    base_temperature = rng.normal(loc=184, scale=5.5, size=n_rows)
    machine_temperature_effect = np.select(
        [machine_id == "M2", machine_id == "M3"],
        [3.0, -1.0],
        default=0.0,
    )
    temperature_c = np.round(base_temperature + machine_temperature_effect, 1)

    pressure_bar = np.round(rng.normal(loc=5.8, scale=0.35, size=n_rows), 2)

    base_cycle_time = rng.normal(loc=46, scale=3.8, size=n_rows)
    machine_cycle_effect = np.select(
        [machine_id == "M2", machine_id == "M4"],
        [2.2, 0.8],
        default=0.0,
    )
    cycle_time_s = np.round(base_cycle_time + machine_cycle_effect, 1)

    vibration_base = rng.normal(loc=2.3, scale=0.45, size=n_rows)
    machine_vibration_effect = np.select(
        [machine_id == "M2", machine_id == "M4"],
        [0.45, 0.2],
        default=0.0,
    )
    vibration_mm_s = np.round(np.clip(vibration_base + machine_vibration_effect, 0.8, 5.0), 2)

    humidity_percent = np.round(np.clip(rng.normal(loc=48, scale=8, size=n_rows), 25, 75), 1)

    # Scrap risk logic:
    # The coefficients below create visible but realistic manufacturing patterns.
    risk_score = np.full(n_rows, -3.25)

    risk_score += np.where(machine_id == "M2", 0.85, 0.0)
    risk_score += np.where(machine_id == "M4", 0.25, 0.0)

    risk_score += np.where(shift == "night", 0.35, 0.0)
    risk_score += np.where(shift == "late", 0.12, 0.0)

    risk_score += np.where(material_batch == "B4", 0.3, 0.0)

    risk_score += np.clip((temperature_c - 190) * 0.12, 0, 1.2)
    risk_score += np.clip((cycle_time_s - 50) * 0.14, 0, 1.4)
    risk_score += np.clip((vibration_mm_s - 2.7) * 0.6, 0, 1.5)
    risk_score += np.clip((humidity_percent - 60) * 0.03, 0, 0.6)

    risk_score -= np.clip(operator_experience_years * 0.035, 0, 0.35)

    scrap_probability = sigmoid(risk_score)
    scrap = rng.binomial(n=1, p=scrap_probability)

    part_id = [f"P{i:06d}" for i in range(1, n_rows + 1)]

    df = pd.DataFrame(
        {
            "part_id": part_id,
            "machine_id": machine_id,
            "temperature_c": temperature_c,
            "pressure_bar": pressure_bar,
            "cycle_time_s": cycle_time_s,
            "shift": shift,
            "material_batch": material_batch,
            "operator_experience_years": operator_experience_years,
            "vibration_mm_s": vibration_mm_s,
            "humidity_percent": humidity_percent,
            "scrap": scrap,
        }
    )

    return df


def print_summary(df: pd.DataFrame, output_path: Path) -> None:
    """Print a compact quality summary for validation."""
    overall_scrap_rate = df["scrap"].mean() * 100
    scrap_by_machine = df.groupby("machine_id")["scrap"].mean().sort_values(ascending=False) * 100

    print(f"Generated rows: {len(df)}")
    print(f"Overall scrap rate: {overall_scrap_rate:.2f}%")
    print("\nScrap rate by machine:")
    for machine, rate in scrap_by_machine.items():
        print(f"  {machine}: {rate:.2f}%")
    print(f"\nSaved to: {output_path}")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = generate_production_data()
    df.to_csv(OUTPUT_PATH, index=False)

    print_summary(df, OUTPUT_PATH)


if __name__ == "__main__":
    main()