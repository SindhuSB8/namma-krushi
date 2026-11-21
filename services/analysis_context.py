"""User-scoped, normalized analysis data shared by advisory UI and generation."""
import json
import math
import re

from config import ROOT
from database.db import fetch_one
from services.disease_service import crop_name
from services.greenhouse_service import decode_label, interpret_parameters
from services.localization import localize_condition, localize_disease, localize_feature, localize_status


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def get_latest_analysis_context(user_id):
    """Read only this farmer's latest persisted results, with stable tie ordering.

    No caching: a new prediction must be visible on the next chat rerun.
    Neither analysis module depends on the other.
    """
    context = {"disease": {"available": False}, "greenhouse": {"available": False}}
    if user_id is None:
        return context
    disease = fetch_one(
        "SELECT disease,confidence,created_at FROM disease_predictions "
        "WHERE user_id=? ORDER BY created_at DESC,prediction_id DESC LIMIT 1",
        (user_id,),
    )
    greenhouse = fetch_one(
        "SELECT prediction,temperature,humidity,soil_moisture,light_intensity,co2,created_at "
        "FROM greenhouse_analyses WHERE user_id=? "
        "ORDER BY created_at DESC,analysis_id DESC LIMIT 1",
        (user_id,),
    )
    if disease:
        confidence = _number(disease["confidence"])
        context["disease"] = {
            "available": True,
            # The current CNN is crop-specific; rows do not have a crop column.
            "crop": crop_name(),
            "disease": localize_disease(disease["disease"], "English") if disease["disease"] else "Unknown",
            "confidence": confidence * 100 if confidence is not None else None,
            "created_at": disease["created_at"],
        }
    if greenhouse:
        values = {key: _number(greenhouse[key]) for key in ("temperature", "humidity", "soil_moisture", "light_intensity", "co2")}
        parameters = interpret_parameters(values)
        context["greenhouse"] = {
            "available": True,
            "status": decode_label(greenhouse["prediction"]),
            **values,
            "parameters": parameters,
            "problem_parameters": [p for p in parameters if p["status"] != "suitable"],
            "created_at": greenhouse["created_at"],
        }
    return context


def build_current_context(disease=None, greenhouse=None, previous=None):
    """Context made from *this submission's* results only.

    ``disease`` / ``greenhouse`` are the dicts returned by
    ``analyze_leaf_image`` / ``analyze_greenhouse``.  ``previous`` is a context
    from ``get_latest_analysis_context`` and is passed in **only** when the
    farmer has agreed to reuse earlier saved results; each part it supplies is
    flagged ``"previous": True`` so the answer says it is not new.
    Unreliable disease results are never included.
    """
    context = {"disease": {"available": False}, "greenhouse": {"available": False}}
    if disease and disease.get("reliable", True) and disease.get("disease"):
        confidence = _number(disease.get("confidence"))
        context["disease"] = {
            "available": True, "crop": crop_name(),
            "disease": localize_disease(disease["disease"], "English"),
            "confidence": confidence * 100 if confidence is not None else None,
            "created_at": None, "previous": False,
        }
    if greenhouse and greenhouse.get("values"):
        values = {key: _number(greenhouse["values"].get(key)) for key in ("temperature", "humidity", "soil_moisture", "light_intensity", "co2")}
        parameters = interpret_parameters(values)
        context["greenhouse"] = {
            "available": True, "status": decode_label(greenhouse["label"]), **values,
            "parameters": parameters,
            "problem_parameters": [p for p in parameters if p["status"] != "suitable"],
            "created_at": None, "previous": False,
        }
    if previous:
        for key in ("disease", "greenhouse"):
            if not context[key]["available"] and previous.get(key, {}).get("available"):
                context[key] = {**previous[key], "previous": True}
    return context


def has_analysis_context(context):
    return isinstance(context, dict) and any(context.get(key, {}).get("available") for key in ("disease", "greenhouse"))


def format_parameter_concern(parameter, language="English"):
    direction = parameter["direction"]
    if language == "Kannada":
        direction = {"High": "ಹೆಚ್ಚು", "Low": "ಕಡಿಮೆ", "Within range": "ಶ್ರೇಣಿಯೊಳಗೆ"}.get(direction, "")
    return f"{localize_feature(parameter['feature'], language)}: {direction}"


def _reading_units(language):
    kn = language == "Kannada"
    return {"temperature": " ಸೆಲ್ಸಿಯಸ್" if kn else " °C", "humidity": "%", "soil_moisture": "%", "light_intensity": " ದ್ಯುತಿಸಂಶ್ಲೇಷಣಾ ಕಿರಣ" if kn else " PAR", "co2": " ಪ್ರತಿ ದಶಲಕ್ಷದ ಭಾಗ" if kn else " ppm"}


def format_parameter_reference(parameter, language="English"):
    """Explain a reading using the deployed model's policy, not a crop target."""
    bounds = parameter.get("suitable_range")
    if not bounds or parameter.get("value") is None:
        return ""
    unit = _reading_units(language)[parameter["feature"]]
    reading = f"{parameter['value']:g}{unit}"
    reference = f"{bounds[0]:g}–{bounds[1]:g}{unit}"
    text = f"ದಾಖಲಾದ ಅಳತೆ: {reading}. ಹಸಿರುಮನೆ ಮಾದರಿಯ ಉಲ್ಲೇಖ ಶ್ರೇಣಿ: {reference}." if language == "Kannada" else f"Recorded reading: {reading}. Greenhouse model reference range: {reference}."
    if parameter["feature"] == "soil_moisture":
        text += " ಈ ಶ್ರೇಣಿಯು ಬೆಳವಣಿಗೆ ಮಾಧ್ಯಮದ ನೀರಿನ ಅಂಶಕ್ಕೆ ಸಂಬಂಧಿಸಿದೆ; ಜಮೀನಿನ ಮಣ್ಣಿನ ಗುರಿಯನ್ನು ಮಣ್ಣು ಮತ್ತು ಸಂವೇದಕಕ್ಕೆ ತಕ್ಕಂತೆ ನಿರ್ಧರಿಸಬೇಕು." if language == "Kannada" else " This reference describes substrate water content; field-soil targets depend on soil and sensor calibration."
    return text


def format_analysis_context(context, language="English", compact=False):
    """Human-readable facts only, safe for the UI, prompt and offline answer."""
    if not has_analysis_context(context):
        return ""
    kn = language == "Kannada"
    lines = []
    disease = context.get("disease", {})
    if disease.get("available"):
        crop = disease["crop"]
        if kn:
            crop = "ಟೊಮ್ಯಾಟೊ" if crop.casefold() == "tomato" else "ಮಾದರಿ ಬೆಳೆ"
        name = localize_disease(disease["disease"], language)
        if kn and any(c.isascii() and c.isalpha() for c in name):
            name = "ಗುರುತಿಸಲಾಗದ ರೋಗದ ಹೆಸರು"
        confidence = disease.get("confidence")
        percentage = f" ({confidence:.1f}%)" if confidence is not None else ""
        earlier = (" (ಈ ಹಿಂದೆ ಉಳಿಸಿದ ಫಲಿತಾಂಶ)" if kn else " (earlier saved result)") if disease.get("previous") else ""
        lines.append(("ರೋಗ ಪತ್ತೆ" if kn else "Disease detection") + f": {crop} — {name}{percentage}{earlier}")
    greenhouse = context.get("greenhouse", {})
    if greenhouse.get("available"):
        status = localize_condition(greenhouse["status"], language)
        if kn and status == "Unknown":
            status = "ಲಭ್ಯವಿಲ್ಲ"
        earlier = (" (ಈ ಹಿಂದೆ ಉಳಿಸಿದ ಫಲಿತಾಂಶ)" if kn else " (earlier saved result)") if greenhouse.get("previous") else ""
        lines.append(("ಹಸಿರುಮನೆ ಸ್ಥಿತಿ" if kn else "Greenhouse status") + f": {status}{earlier}")
        if not compact:
            units = _reading_units(language)
            readings = [f"{localize_feature(key, language)}: {greenhouse[key]:g}{unit}" for key, unit in units.items() if greenhouse.get(key) is not None]
            lines.append("; ".join(readings))
        concerns = greenhouse.get("problem_parameters", [])
        lines.append("ಗಮನ ಅಗತ್ಯವಿರುವ ಅಂಶಗಳು:" if kn else "Parameters requiring attention:")
        for p in concerns:
            lines.append(f"- {format_parameter_concern(p, language)} ({localize_status(p['status'], language)})")
        if not concerns:
            lines.append("- ಲಭ್ಯವಿರುವ ಅಳತೆಗಳಲ್ಲಿ ಯಾವುದೇ ಸಮಸ್ಯೆಯನ್ನು ಗುರುತಿಸಿಲ್ಲ." if kn else "- No concerns identified in the available readings.")
    return "\n\n".join(lines)


def build_retrieval_query(question, context):
    """Enrich a question with labels and concerns, never a dump of readings."""
    if not has_analysis_context(context):
        return question
    parts = []
    disease = context.get("disease", {})
    if disease.get("available"):
        parts.append(f"{disease['crop']} {disease['disease']} management prevention")
    greenhouse = context.get("greenhouse", {})
    if greenhouse.get("available"):
        parts.append(f"greenhouse {greenhouse['status']}")
        for p in greenhouse.get("problem_parameters", []):
            parts.append(f"{p['direction'].lower()} {p['label']} management")
    return " ".join(parts + [question])


def analysis_evidence_routes(context):
    """Use the KB's existing CNN and XAI routing metadata for focused evidence."""
    taxonomy = json.loads((ROOT / "namma_krushi_master_kb" / "metadata" / "taxonomy_and_routing.json").read_text(encoding="utf-8"))
    routes = {"disease": set(), "greenhouse": set(), "greenhouse_parameters": {}}
    disease = context.get("disease", {})
    if disease.get("available"):
        normalize = lambda text: re.sub(r"[^a-z0-9]", "", text.casefold())
        for label, path in taxonomy["cnn_label_map"].items():
            if normalize(label) == normalize(disease["disease"]):
                routes["disease"].add(path.rsplit("/", 1)[-1].removesuffix(".md"))
    greenhouse = context.get("greenhouse", {})
    if greenhouse.get("available"):
        for p in greenhouse.get("problem_parameters", []):
            parameter_routes = routes["greenhouse_parameters"].setdefault(p["feature"], set())
            paths = list(taxonomy["greenhouse_xai_route"].get(p["feature"], []))
            # Dry air and root-zone water are separate readings. Retrieve the
            # existing irrigation checks before proposing a water change.
            if p["feature"] == "humidity" and p["direction"] == "Low" and greenhouse.get("soil_moisture") is not None:
                paths.extend(taxonomy["greenhouse_xai_route"].get("soil_moisture", []))
            for path in paths:
                document_id = path.rsplit("/", 1)[-1].removesuffix(".md")
                parameter_routes.add(document_id)
                routes["greenhouse"].add(document_id)
    return routes


def greenhouse_evidence_matches(item, context, parameter=None):
    """Reject a condition-specific section when the actual finding disagrees."""
    heading = item.get("text", "").lstrip().splitlines()[0].casefold() if item.get("text") else ""
    parameters = [parameter] if parameter is not None else context.get("greenhouse", {}).get("problem_parameters", [])
    concerns = {(p["feature"], p["direction"]) for p in parameters}
    if "high humidity" in heading:
        return ("humidity", "High") in concerns
    if "heat" in heading or "high temperature" in heading:
        return ("temperature", "High") in concerns
    if "low light" in heading or "low-light" in heading:
        return ("light_intensity", "Low") in concerns
    return True
