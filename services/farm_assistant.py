"""One-step farm analysis for the AI Farming Assistant page.

The farmer can supply a tomato leaf image, greenhouse readings, a question, or
any combination.  Each analysis uses the existing deployed model and saves its
result to the existing tables, so History, the dashboard and the advisory
context all read the same records as before.  Nothing is retrained.
"""
import logging
import uuid
from datetime import datetime

import config
from database.db import execute, save_disease_prediction
from services import disease_service, greenhouse_service

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500


def analyze_leaf_image(user_id, image_bytes, uploads_dir=None):
    """Validate the picture, run the CNN and - only if reliable - save it.

    Returns ``{"reliable", "reason", "disease", "confidence", "top", "saved",
    "prediction_id"}``.

    * An image that cannot be reliably analysed (not a leaf, blurry, unreadable,
      or an uncertain prediction) is *not* saved to History and is never
      reported as the farmer's current disease: ``disease`` and ``confidence``
      are None and ``saved`` is False.
    * A reliable prediction is written to ``disease_predictions`` exactly once.
      ``saved`` tells the page whether that really happened, so a failure is
      shown to the farmer and logged instead of being silently ignored.
    * If the database write fails (or the result is a duplicate of one just
      saved) the image file that was written for it is removed, so no orphan
      pictures are left behind.
    * Model errors propagate so the page can show a localized message.
    """
    checked = disease_service.predict_checked(image_bytes)
    top = checked["top"]
    if not checked["reliable"]:
        return {
            "reliable": False, "reason": checked["reason"], "disease": None,
            "confidence": None, "top": top, "saved": False, "prediction_id": None,
        }
    disease, confidence = top[0]
    prediction_id = _save_disease_history(user_id, image_bytes, disease, confidence, uploads_dir)
    return {
        "reliable": True, "reason": None, "disease": disease, "confidence": confidence,
        "top": top, "saved": prediction_id is not None, "prediction_id": prediction_id,
    }


def _save_disease_history(user_id, image_bytes, disease, confidence, uploads_dir=None):
    """Write the image and its ``disease_predictions`` row; return the row id or None."""
    root = uploads_dir or config.UPLOADS
    folder = root / str(user_id)
    saved = None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        saved = folder / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.jpg"
        saved.write_bytes(image_bytes)
        prediction_id, created = save_disease_prediction(
            user_id,
            # Forward slashes keep the stored path identical on Windows and Linux.
            saved.relative_to(root.parent.parent).as_posix(),
            disease,
            confidence,
        )
        if not created:
            # Same result was saved moments ago (double click / rerun): keep
            # the single existing record and drop the duplicate image file.
            saved.unlink(missing_ok=True)
            logger.info("Duplicate disease prediction ignored (existing id %s)", prediction_id)
        return prediction_id
    except Exception:
        logger.exception("Could not save disease prediction history (user_id=%r)", user_id)
        if saved is not None:
            try:
                saved.unlink(missing_ok=True)
            except OSError:
                pass
        return None


def analyze_greenhouse(user_id, values):
    """Run the greenhouse model on the five readings and save the result.

    Returns ``{"label", "confidence", "checks", "recommendation", "values",
    "adjustments"}`` or
    ``None`` when a reading is outside the model's supported range.
    """
    if not greenhouse_service.validate(values):
        return None
    label, confidence = greenhouse_service.predict(values)
    checks, recommendation = greenhouse_service.explain(values)
    saved = False
    try:
        execute(
            """INSERT INTO greenhouse_analyses(user_id,temperature,humidity,soil_moisture,light_intensity,co2,prediction,confidence,xai_explanation)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (user_id, *[values[f] for f in config.GREENHOUSE_FEATURES], label, confidence,
             f"Checks: {checks}; Rec: {recommendation}"),
        )
        saved = True
    except Exception:
        logger.exception("Could not save greenhouse analysis history")
    return {
        "label": label, "confidence": confidence, "checks": checks, "recommendation": recommendation,
        "values": {f: float(values[f]) for f in config.GREENHOUSE_FEATURES},
        "adjustments": greenhouse_service.adjustments(values),
        "saved": saved,
    }
