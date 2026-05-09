from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "outputs" / "scrap_prediction_model.joblib"


SAMPLE_PART = {
    "machine_id": "M2",
    "temperature_c": 194.0,
    "pressure_bar": 6.1,
    "cycle_time_s": 52.0,
    "shift": "night",
    "material_batch": "B4",
    "operator_experience_years": 1.5,
    "vibration_mm_s": 3.2,
    "humidity_percent": 55.0,
}


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run src/train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def classify_risk(probability: float) -> str:
    if probability >= 0.6:
        return "High"
    if probability >= 0.3:
        return "Medium"
    return "Low"


def build_recommendations(part: dict, probability: float) -> list[str]:
    recommendations = []

    if part["machine_id"] == "M2":
        recommendations.append("Inspect M2 calibration and machine condition.")

    if part["temperature_c"] > 190:
        recommendations.append("Review process temperature control above 190°C.")

    if part["cycle_time_s"] > 50:
        recommendations.append("Investigate cycle time deviation above 50 seconds.")

    if part["vibration_mm_s"] > 2.7:
        recommendations.append("Check vibration level for possible tool wear or mechanical instability.")

    if part["shift"] == "night":
        recommendations.append("Apply additional process checks during night shift production.")

    if part["operator_experience_years"] < 2:
        recommendations.append("Use operator guidance or checklist support for low-experience operation.")

    if probability < 0.3:
        recommendations.append("No immediate action required. Continue standard process monitoring.")

    return recommendations


def predict_scrap_risk(part: dict) -> dict:
    model = load_model()
    input_df = pd.DataFrame([part])

    probability = model.predict_proba(input_df)[0][1]
    risk_level = classify_risk(probability)

    return {
        "scrap_probability": probability,
        "risk_level": risk_level,
        "recommendations": build_recommendations(part, probability),
    }


def print_prediction(part: dict, prediction: dict) -> None:
    print("New Part Scrap Risk Prediction")
    print("=" * 36)

    print("\nInput conditions:")
    for key, value in part.items():
        print(f"  {key}: {value}")

    print("\nPrediction:")
    print(f"  Scrap probability: {prediction['scrap_probability'] * 100:.2f}%")
    print(f"  Risk level: {prediction['risk_level']}")

    print("\nRecommendations:")
    for recommendation in prediction["recommendations"]:
        print(f"  - {recommendation}")


def main() -> None:
    prediction = predict_scrap_risk(SAMPLE_PART)
    print_prediction(SAMPLE_PART, prediction)


if __name__ == "__main__":
    main()