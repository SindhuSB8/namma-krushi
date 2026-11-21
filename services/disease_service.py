import io, json
from pathlib import Path
from functools import lru_cache
import os
import numpy as np
from config import ARTIFACTS

MODEL_PATH = ARTIFACTS / "disease" / "model_artifacts" / "tomato_disease_model.keras"
CLASS_PATH = ARTIFACTS / "disease" / "class_names.json"

def class_names(): return json.loads(CLASS_PATH.read_text(encoding="utf-8"))

def crop_name():
    """Read the supported crop from the deployed model's existing metadata."""
    deployment = ARTIFACTS / "disease" / "model_artifacts" / "deployment_info.json"
    return json.loads(deployment.read_text(encoding="utf-8"))["module"].removesuffix(" Disease Detection")

@lru_cache(maxsize=1)
def load_model():
    """Load the saved Keras artifact once.

    TensorFlow is used where available.  On Python versions for which it has no
    distribution (including the current Python 3.14 environment), standalone
    Keras uses the installed PyTorch backend instead.  Both paths load the same
    unmodified `.keras` artifact.
    """
    try:
        import tensorflow as tf
        return tf.keras.models.load_model(MODEL_PATH, compile=False)
    except ModuleNotFoundError as exc:
        if exc.name != "tensorflow":
            raise
    os.environ.setdefault("KERAS_BACKEND", "torch")
    import keras
    return keras.saving.load_model(MODEL_PATH, compile=False)

def preprocess(image_bytes):
    from PIL import Image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224,224))
    return np.expand_dims(np.asarray(image, dtype=np.float32), axis=0)

# --- Input validation -------------------------------------------------------
# The CNN has no "not a leaf" class, so it will always name *some* disease.
# Two guards stop unreliable results from reaching the farmer:
#   1. cheap image checks before inference (unreadable, tiny, blank, no plant colours);
#   2. confidence checks after inference (low top score, small margin, high entropy).
# Thresholds are deliberately conservative and should be re-calibrated with
# real field photos and genuine non-leaf images when those are available.
MIN_IMAGE_SIDE = 64
MIN_PLANT_PIXEL_FRACTION = 0.12
MIN_PIXEL_STD = 8.0
MIN_TOP_CONFIDENCE = 0.60
MIN_TOP_MARGIN = 0.10
MAX_NORMALISED_ENTROPY = 0.55

REASON_UNREADABLE = "unreadable"
REASON_TOO_SMALL = "too_small"
REASON_BLANK = "blank"
REASON_NOT_PLANT = "not_plant"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_AMBIGUOUS = "ambiguous"


def _plant_pixel_fraction(rgb):
    """Share of pixels with leaf-like colour: green, yellow-green, yellow, olive/brown lesions."""
    arr = rgb.astype(np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx, mn = arr.max(axis=-1), arr.min(axis=-1)
    delta = mx - mn
    sat = np.where(mx > 0, delta / np.maximum(mx, 1e-6), 0)
    safe = np.maximum(delta, 1e-6)
    hue = np.where(mx == r, ((g - b) / safe) % 6,
          np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4)) * 60.0
    plant = (hue >= 25) & (hue <= 170) & (sat >= 0.18) & (mx >= 0.15)
    return float(plant.mean())


def check_image(image_bytes):
    """Return ``(ok, reason)``; ``reason`` is None when the picture can be analysed."""
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        image = image.convert("RGB")
    except Exception:
        return False, REASON_UNREADABLE
    if min(image.size) < MIN_IMAGE_SIDE:
        return False, REASON_TOO_SMALL
    small = np.asarray(image.resize((128, 128)))
    if float(small.std()) < MIN_PIXEL_STD:
        return False, REASON_BLANK
    if _plant_pixel_fraction(small) < MIN_PLANT_PIXEL_FRACTION:
        return False, REASON_NOT_PLANT
    return True, None


def assess_scores(scores):
    """Return ``(reliable, reason)`` for a softmax vector."""
    scores = np.asarray(scores, dtype=float)
    order = np.sort(scores)[::-1]
    if order[0] < MIN_TOP_CONFIDENCE:
        return False, REASON_LOW_CONFIDENCE
    if len(order) > 1 and (order[0] - order[1]) < MIN_TOP_MARGIN:
        return False, REASON_AMBIGUOUS
    total = scores.sum()
    if total > 0 and len(scores) > 1:
        p = scores / total
        entropy = -float(np.sum(p[p > 0] * np.log(p[p > 0]))) / float(np.log(len(scores)))
        if entropy > MAX_NORMALISED_ENTROPY:
            return False, REASON_LOW_CONFIDENCE
    return True, None


def _scores(image_bytes):
    return np.asarray(load_model().predict(preprocess(image_bytes), verbose=0)[0], dtype=float)


def _top3(scores):
    names = class_names()
    order = scores.argsort()[::-1][:3]
    # Preserve canonical class IDs. Display formatting/localization belongs in
    # the view; replacing underscores here made some Kannada names impossible
    # to match (notably the two-spotted spider-mite class).
    return [(names[int(i)], float(scores[i])) for i in order]


def predict(image_bytes):
    return _top3(_scores(image_bytes))


def predict_checked(image_bytes):
    """Validate, predict and say whether the result can be trusted.

    Returns ``{"reliable": bool, "reason": str | None, "top": [(class, score), ...]}``.
    Unreliable results keep ``top`` (when the model ran) so the page can show
    them as "possible, unconfirmed" - but they must never be saved or used as
    the current disease.
    """
    ok, reason = check_image(image_bytes)
    if not ok:
        return {"reliable": False, "reason": reason, "top": []}
    scores = _scores(image_bytes)
    reliable, reason = assess_scores(scores)
    return {"reliable": reliable, "reason": reason, "top": _top3(scores)}
