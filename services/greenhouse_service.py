import json
import logging
import warnings
from functools import lru_cache
import joblib
import numpy as np
import pandas as pd
from config import ARTIFACTS, GREENHOUSE_FEATURES

MODEL_PATH = ARTIFACTS / "greenhouse" / "model_artifacts" / "greenhouse_model.pkl"
POLICY_PATH = ARTIFACTS / "greenhouse" / "greenhouse_labeling_policy.json"
LABEL_MAP_PATH = ARTIFACTS / "greenhouse" / "label_mapping.json"

# Build reverse label map: {0: "Suitable", 1: "Needs Adjustment", 2: "Unsuitable"}
_LABEL_MAP = {v: k for k, v in json.loads(LABEL_MAP_PATH.read_text(encoding="utf-8")).items()}

def decode_label(raw_label):
    """Decode current predictions and numeric labels saved by older versions."""
    label = str(raw_label).strip()
    for name in _LABEL_MAP.values():
        if label.casefold() == name.casefold():
            return name
    try:
        return _LABEL_MAP.get(int(label), "Unknown")
    except (ValueError, TypeError):
        return "Unknown"

@lru_cache(maxsize=1)
def load_model():
    """Load the trained model; say clearly (once) if scikit-learn differs from training."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = joblib.load(MODEL_PATH)
    if any("version" in str(w.message).lower() for w in caught):
        logging.getLogger(__name__).warning(
            "greenhouse_model.pkl was trained with scikit-learn 1.6.1 but a different version is installed. "
            "Install the pinned version (pip install -r requirements.txt) for guaranteed identical predictions."
        )
    return model

@lru_cache(maxsize=4)
def _load_policy(path):
    return json.loads(path.read_text(encoding="utf-8"))

def _policy():
    # Cached per path, so the policy is read once but a different POLICY_PATH is honoured.
    return _load_policy(POLICY_PATH)

def predict(values):
    model = load_model()
    # A DataFrame with the training column names avoids scikit-learn's
    # "X does not have valid feature names" warning.
    array = pd.DataFrame([[float(values[f]) for f in GREENHOUSE_FEATURES]], columns=GREENHOUSE_FEATURES)
    raw_label = model.predict(array)[0]
    label = decode_label(raw_label)
    confidence = float(max(model.predict_proba(array)[0])) if hasattr(model, "predict_proba") else None
    return label, confidence

def _range_status(value, suitable, marginal):
    if suitable[0] <= value <= suitable[1]:
        return "suitable"
    if marginal[0] <= value <= marginal[1]:
        return "needs adjustment"
    return "outside the recommended range"

def explain(values):
    """Return structured XAI data as a list of (feature, status) tuples and a recommendation."""
    policy = _policy()
    checks = [
        ("Temperature", _range_status(values["temperature"], policy["temperature_celsius"]["suitable"], policy["temperature_celsius"]["marginal"])),
        ("Humidity", _range_status(values["humidity"], policy["relative_humidity_percent"]["suitable"], policy["relative_humidity_percent"]["marginal"])),
        ("Root-zone moisture", _range_status(values["soil_moisture"], policy["substrate_water_content_percent"]["suitable"], policy["substrate_water_content_percent"]["marginal"])),
        ("CO₂", _range_status(values["co2"], policy["co2_ppm"]["suitable"], policy["co2_ppm"]["marginal"])),
    ]
    light, lp = values["light_intensity"], policy["light_PAR"]
    # Thresholds come from the labeling policy (single source of truth).
    light_status = ("suitable" if light == 0 or lp["suitable"][0] <= light <= lp["suitable"][1]
                    else "needs adjustment" if lp["marginal_low"][0] <= light <= lp["marginal_high"][1]
                    else "outside the recommended range")
    checks.append(("Light", light_status))
    concern = [(f, s) for f, s in checks if s != "suitable"]
    recommendation = "Maintain the current conditions and continue monitoring." if not concern else "Prioritise " + ", ".join(f.lower() for f, _ in concern) + "; adjust one factor at a time and recheck sensors."
    return checks, recommendation

def validate(values):
    """True only when all five readings are present, finite and in range."""
    try:
        return _validate(values)
    except (KeyError, TypeError, ValueError):
        return False


def adjustments(values):
    """One specific, KB-grounded recommendation per abnormal reading.

    Each item: ``feature``, ``label``, ``value``, ``direction`` (High/Low),
    ``level`` (``yellow`` = needs adjustment, ``red`` = outside the range) and
    the ``advice`` text in English and Kannada.
    """
    from services.greenhouse_advice import ADVICE, SOURCE_DOCUMENTS
    items = []
    for p in interpret_parameters(values):
        if p["status"] == "suitable" or p["direction"] not in ("High", "Low"):
            continue
        en, kn = ADVICE[(p["feature"], p["direction"])]
        items.append({
            "feature": p["feature"], "label": p["label"], "value": p["value"],
            "direction": p["direction"], "suitable_range": p["suitable_range"],
            "level": "yellow" if p["status"] == "needs adjustment" else "red",
            "advice_en": en, "advice_kn": kn, "source": SOURCE_DOCUMENTS[p["feature"]],
        })
    return items


def _validate(values):
    limits = {"temperature": (0,45), "humidity": (0,100), "soil_moisture": (0,100), "light_intensity": (0,2000), "co2": (250,2500)}
    for key, (low, high) in limits.items():
        number = float(values[key])
        if not (number == number and low <= number <= high):   # NaN fails both
            return False
    return True

def interpret_parameters(values):
    """Reuse the analysis XAI checks and policy to identify actual concerns.

    Missing historical readings stay unavailable; they are never invented.
    """
    policy = _policy()
    features = [
        ("temperature", "Temperature", "temperature_celsius"),
        ("humidity", "Humidity", "relative_humidity_percent"),
        ("soil_moisture", "Root-zone moisture", "substrate_water_content_percent"),
        ("co2", "CO₂", "co2_ppm"),
        ("light_intensity", "Light", "light_PAR"),
    ]
    # explain() is the same interpretation used on the greenhouse page.
    checks = dict(explain(values)[0]) if all(values.get(f) is not None for f in GREENHOUSE_FEATURES) else {}
    parameters = []
    for feature, label, policy_key in features:
        value = values.get(feature)
        if value is None:
            continue
        bounds = policy[policy_key]
        low, high = bounds["suitable"]
        if feature == "light_intensity":
            status = "suitable" if value == 0 or low <= value <= high else ("needs adjustment" if 1 <= value <= bounds["marginal_high"][1] else "outside the recommended range")
        else:
            status = _range_status(value, bounds["suitable"], bounds["marginal"])
        status = checks.get(label, status)
        parameters.append({
            "feature": feature,
            "label": label,
            "value": value,
            "status": status,
            "direction": "High" if value > high else "Low" if value < low and status != "suitable" else "Within range",
            "suitable_range": list(bounds["suitable"]),
        })
    return parameters
