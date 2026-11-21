"""Regression tests for the integration fixes (no browser or CNN weights needed)."""
import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

import database.db as db
from services import disease_service, farm_assistant, greenhouse_service
from services.analysis_context import build_current_context, format_analysis_context, has_analysis_context
from services.rag_service import route
from services.translation_service import translate_rag_query_to_english as kn_to_en
from services.validation import check_new_password, clean_name


def _png(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _leaf(base=(60, 140, 50), background=(200, 200, 200)):
    rng = np.random.default_rng(1)
    image = Image.new("RGB", (300, 300), background)
    ImageDraw.Draw(image).ellipse((40, 30, 260, 270), fill=base)
    noisy = np.asarray(image).astype(int) + rng.integers(-10, 10, (300, 300, 3))
    return Image.fromarray(np.clip(noisy, 0, 255).astype("uint8"))


# -- 1. leaf image validation -------------------------------------------------

@pytest.mark.parametrize("image,reason", [
    (Image.new("RGB", (300, 300), (120, 170, 230)), disease_service.REASON_NOT_PLANT),   # sky
    (Image.new("RGB", (300, 300), (250, 250, 250)), disease_service.REASON_BLANK),       # white page
    (Image.new("RGB", (30, 30), (0, 150, 0)), disease_service.REASON_TOO_SMALL),
    (_leaf(base=(200, 30, 30)), disease_service.REASON_NOT_PLANT),                        # red object
])
def test_non_leaf_images_are_rejected_before_the_model_runs(image, reason):
    assert disease_service.check_image(_png(image)) == (False, reason)


def test_leaf_like_and_unreadable_images():
    assert disease_service.check_image(_png(_leaf())) == (True, None)
    assert disease_service.check_image(_png(_leaf(base=(140, 100, 40), background=(230, 230, 230)))) == (True, None)
    assert disease_service.check_image(b"not an image") == (False, disease_service.REASON_UNREADABLE)


def test_uncertain_predictions_are_unreliable():
    assert disease_service.assess_scores([0.95] + [0.005] * 10) == (True, None)
    assert disease_service.assess_scores([1 / 11] * 11)[0] is False            # flat
    assert disease_service.assess_scores([0.5, 0.3] + [0.025] * 8 + [0])[0] is False   # low top score
    assert disease_service.assess_scores([0.55, 0.45] + [0] * 9)[0] is False   # two-way tie


def test_unreliable_image_is_not_saved_or_used_as_current_disease(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "t.db")
    db.initialize_database()
    uid = db.execute("INSERT INTO users(name,username,password_hash) VALUES(?,?,?)", ("Ann", "ann", "x"))
    monkeypatch.setattr(disease_service, "predict_checked",
                        lambda _bytes: {"reliable": False, "reason": "not_plant", "top": []})
    result = farm_assistant.analyze_leaf_image(uid, b"x", uploads_dir=tmp_path / "u" / "d")
    assert result["reliable"] is False and result["disease"] is None
    assert db.fetch_one("SELECT 1 FROM disease_predictions WHERE user_id=?", (uid,)) is None
    assert not has_analysis_context(build_current_context(disease=result))


def test_reliable_image_is_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "t.db")
    db.initialize_database()
    uid = db.execute("INSERT INTO users(name,username,password_hash) VALUES(?,?,?)", ("Ann", "ann", "x"))
    top = [("Early_blight", 0.93), ("Late_blight", 0.04), ("Septoria_leaf_spot", 0.02)]
    monkeypatch.setattr(disease_service, "predict_checked", lambda _b: {"reliable": True, "reason": None, "top": top})
    root = tmp_path / "uploads" / "disease_images"
    result = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert result["disease"] == "Early_blight" and result["reliable"]
    assert db.fetch_one("SELECT disease FROM disease_predictions WHERE user_id=?", (uid,))["disease"] == "Early_blight"


# -- 2. greenhouse -------------------------------------------------------------

GOOD = dict(temperature=22, humidity=78, soil_moisture=78, light_intensity=400, co2=700)


def test_three_statuses_and_specific_advice():
    assert greenhouse_service.predict(GOOD)[0] == "Suitable" and greenhouse_service.adjustments(GOOD) == []
    marginal = {**GOOD, "temperature": 29}
    assert greenhouse_service.predict(marginal)[0] == "Needs Adjustment"
    assert [(a["feature"], a["direction"], a["level"]) for a in greenhouse_service.adjustments(marginal)] == [("temperature", "High", "yellow")]
    bad = dict(temperature=38, humidity=95, soil_moisture=20, light_intensity=900, co2=400)
    assert greenhouse_service.predict(bad)[0] == "Unsuitable"
    found = {(a["feature"], a["direction"]): a for a in greenhouse_service.adjustments(bad)}
    assert set(found) == {("temperature", "High"), ("humidity", "High"), ("soil_moisture", "Low")}
    assert all(a["level"] == "red" and a["advice_en"] and a["advice_kn"] for a in found.values())


def test_every_direction_has_english_and_kannada_advice():
    from services.greenhouse_advice import ADVICE
    assert len(ADVICE) == 10
    assert all(en and any("\u0c80" <= c <= "\u0cff" for c in kn) for en, kn in ADVICE.values())


@pytest.mark.parametrize("bad", [
    {**GOOD, "temperature": -1}, {**GOOD, "temperature": 46}, {**GOOD, "humidity": 101}, {**GOOD, "co2": 249},
    {**GOOD, "light_intensity": 2001}, {**GOOD, "soil_moisture": float("nan")}, {**GOOD, "co2": None}, {"temperature": 20},
])
def test_invalid_sensor_readings_are_rejected(bad):
    assert greenhouse_service.validate(bad) is False


def test_boundary_values_are_accepted():
    assert greenhouse_service.validate(dict(temperature=0, humidity=0, soil_moisture=0, light_intensity=0, co2=250))
    assert greenhouse_service.validate(dict(temperature=45, humidity=100, soil_moisture=100, light_intensity=2000, co2=2500))


def test_greenhouse_prediction_has_no_feature_name_warning():
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        greenhouse_service.predict(GOOD)
    assert not [w for w in caught if "feature names" in str(w.message)]


# -- 3/5. current results only ------------------------------------------------

def test_current_context_contains_only_this_submission_unless_opted_in():
    result = {"label": "Needs Adjustment", "confidence": 0.9, "values": {**GOOD, "humidity": 93.0}}
    current = build_current_context(greenhouse=result)
    assert current["greenhouse"]["available"] and not current["disease"]["available"]
    previous = {"disease": {"available": True, "crop": "Tomato", "disease": "Late Blight", "confidence": 90.0, "created_at": "x"},
                "greenhouse": {"available": False}}
    assert not build_current_context(greenhouse=result)["disease"]["available"]          # not mixed in
    merged = build_current_context(greenhouse=result, previous=previous)
    assert merged["disease"]["previous"] is True and "earlier saved result" in format_analysis_context(merged)


def test_current_results_win_over_previous():
    disease = {"reliable": True, "disease": "Early_blight", "confidence": 0.9}
    previous = {"disease": {"available": True, "crop": "Tomato", "disease": "Late Blight", "confidence": 50.0, "created_at": "x"},
                "greenhouse": {"available": False}}
    merged = build_current_context(disease=disease, previous=previous)
    assert merged["disease"]["disease"] == "Early Blight" and merged["disease"]["previous"] is False


# -- 4. Kannada -> English ----------------------------------------------------

@pytest.mark.parametrize("question,expected,forbidden", [
    ("ಹಸಿರುಮನೆಯಲ್ಲಿ ಆರ್ದ್ರತೆ ಹೆಚ್ಚು ಇದೆ, ತಾಪಮಾನ ಕಡಿಮೆ ಇದೆ ಏನು ಮಾಡಲಿ?",
     ["high humidity", "low temperature", "what should I do"], ["high temperature", "low humidity"]),
    ("ತಾಪಮಾನ ಕಡಿಮೆ ಆದರೆ ಆರ್ದ್ರತೆ ಹೆಚ್ಚು", ["low temperature", "high humidity"], ["high temperature"]),
    ("ತಾಪಮಾನ ಮತ್ತು ಆರ್ದ್ರತೆ ಹೆಚ್ಚು ಇದೆ", ["high temperature", "high humidity"], []),
    ("ನೀರು ಹಾಕಬೇಡಿ", ["do not", "water"], []),
    ("ಎಲೆಯಲ್ಲಿ ಕಂದು ಚುಕ್ಕೆ ಇದೆ ಏನು ಮಾಡಬೇಕು", ["leaf", "brown spots", "what should I do"], []),
    ("ಬಿಳಿ ನೊಣ ನಿಯಂತ್ರಣ ಹೇಗೆ", ["whitefly", "control", "how"], ["white "]),
])
def test_kannada_question_keeps_direction_negation_and_symptoms(question, expected, forbidden):
    query, complete = kn_to_en(question)
    assert complete
    for phrase in expected:
        assert phrase in query, (phrase, query)
    for phrase in forbidden:
        assert phrase not in query, (phrase, query)


def test_short_kannada_roots_do_not_match_inside_unrelated_words(monkeypatch):
    from services import translation_service
    monkeypatch.setattr(translation_service, "translate", lambda *a: ("", False))
    assert kn_to_en("ಹೂಡಿಕೆ ಬಗ್ಗೆ") == ("", False)      # "investment" must not become "flower"


def test_failed_translation_is_reported_not_guessed(monkeypatch):
    from services import translation_service
    monkeypatch.setattr(translation_service, "translate", lambda *a: ("ignored", False))
    assert kn_to_en("ಏನೋ ಗೊತ್ತಿಲ್ಲದ ವಾಕ್ಯ") == ("", False)


# -- 6. scheme routing --------------------------------------------------------

@pytest.mark.parametrize("question", [
    "how to apply copper fungicide on leaves", "apply neem oil for whitefly", "what benefit does ventilation give",
    "my polyhouse humidity is high", "drip irrigation for tomato", "why are leaves yellow",
])
def test_everyday_farming_questions_are_not_scheme_questions(question):
    assert route(question) == "agriculture"


@pytest.mark.parametrize("question", [
    "solar pump subsidy under PM-KUSUM", "National Horticulture Mission NHM", "How do I apply for PM Kisan",
    "polyhouse subsidy in karnataka", "greenhouse loan", "eligibility for crop insurance", "documents needed for KCC",
    "micro irrigation subsidy", "soil health card", "government schemes for farmers", "apply for e-NAM",
])
def test_scheme_questions_still_route_to_schemes(question):
    assert route(question) == "schemes"


# -- 9. profile validation ----------------------------------------------------

@pytest.mark.parametrize("raw,error", [("", "profile_name_empty"), ("   ", "profile_name_empty"), ("A", "profile_name_invalid"),
                                       ("12345", "profile_name_invalid"), ("x" * 61, "profile_name_invalid"), ("Ra\x00vi", "profile_name_invalid")])
def test_invalid_names_are_rejected(raw, error):
    assert clean_name(raw)[1] == error


def test_valid_names_are_cleaned():
    assert clean_name("  Ravi   Kumar ") == ("Ravi Kumar", None)
    assert clean_name("ರಾಮ ಗೌಡ")[1] is None


def test_password_rules():
    assert check_new_password("old", "short") == "password_too_short"
    assert check_new_password("oldpass1", "oldpass1") == "password_same"
    assert check_new_password("old", "x" * 80) == "password_too_long"
    assert check_new_password("old", "newpass1") is None


def test_registration_rejects_blank_names(monkeypatch, tmp_path):
    from services.auth_service import register_farmer
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "r.db")
    db.initialize_database()
    assert register_farmer("   ", "u1", "secret12", "English") == (False, "fields_required")
    assert register_farmer("1234", "u2", "secret12", "English") == (False, "profile_name_invalid")
    assert register_farmer("Ravi", "u3", "secret12", "English")[0]


def test_new_ui_strings_exist_in_both_languages():
    import json
    from config import ROOT
    en = json.loads((ROOT / "translation" / "ui_strings_en.json").read_text(encoding="utf-8"))
    kn = json.loads((ROOT / "translation" / "ui_strings_kn.json").read_text(encoding="utf-8"))
    assert set(en) == set(kn)
    for key in ("fa_use_previous", "fa_disease_card", "fa_greenhouse_card", "fa_img_reason_not_plant", "profile_name_empty", "password_same"):
        assert en[key] and kn[key] and en[key] != kn[key]
