"""
helpers.py – Convenience functions for disease prediction and greenhouse XAI.
"""
import json
from pathlib import Path
from typing import List

from .config import KB_ROOT, logger
from .retriever import retrieve
from .schemas import RetrievalResult


def _load_taxonomy():
    path = KB_ROOT / "metadata" / "taxonomy_and_routing.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def retrieve_for_disease(disease_label: str, top_k: int = 5) -> List[RetrievalResult]:
    """
    Given a CNN disease label (e.g. 'Early Blight'), retrieve relevant
    chunks from the agriculture index.
    """
    taxonomy = _load_taxonomy()
    cnn_map = taxonomy.get("cnn_label_map", {})
    md_file = cnn_map.get(disease_label)
    if md_file:
        query = f"{disease_label} tomato disease symptoms treatment management"
    else:
        query = f"{disease_label} tomato"
    logger.info(f"Disease helper: label='{disease_label}' -> query='{query}'")
    return retrieve(query, index_name="agriculture", top_k=top_k)


def retrieve_for_greenhouse_feature(feature: str, top_k: int = 5) -> List[RetrievalResult]:
    """
    Given a greenhouse sensor feature name (temperature, humidity,
    soil_moisture, light_intensity, co2), retrieve relevant advisory chunks.
    """
    taxonomy = _load_taxonomy()
    xai_map = taxonomy.get("greenhouse_xai_route", {})
    md_files = xai_map.get(feature, [])

    # Build a natural-language query from the feature name
    feature_readable = feature.replace("_", " ")
    query = f"greenhouse tomato {feature_readable} management optimal range advisory"
    logger.info(f"Greenhouse helper: feature='{feature}' -> query='{query}'")
    return retrieve(query, index_name="agriculture", top_k=top_k)
