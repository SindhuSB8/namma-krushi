import io
import re

import pytest
from streamlit.testing.v1 import AppTest

import database.db as db
from config import ROOT
from services.auth_service import register_farmer
from services.localization import localize_disease
import services.llm_service as llm
import views.advisory as advisory_view


def _page_text(at):
    return "\n".join(item.value for item in at.markdown)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "ui.db")
    monkeypatch.setattr(llm, "ENABLE_OLLAMA", False)
    # Browser microphone interaction is external to AppTest.
    monkeypatch.setattr(advisory_view, "voice_input", lambda *a, **kw: None, raising=False)
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)


def _button(at, label):
    return next(button for button in at.button if button.label == label)


def _fill_readings(app, temperature=24.0, humidity=75.0, soil_moisture=75.0, light=500.0, co2=600.0):
    """Readings start blank; the farmer must type all five."""
    for key, value in (("farm_temperature", temperature), ("farm_humidity", humidity),
                       ("farm_soil_moisture", soil_moisture), ("farm_light", light), ("farm_co2", co2)):
        app.number_input(key=key).set_value(value)


def _speak(monkeypatch, text, nonce):
    events = [{"nonce": nonce, "status": "result", "transcript": text}]
    monkeypatch.setattr(advisory_view, "voice_input", lambda *a, **kw: events.pop(0) if events else None)


@pytest.mark.skip(reason="Voice input was removed from the text-only advisory page; the saved-disease flow is covered by tests/test_disease_history_and_admin_counts.py")
def test_complete_demo_with_existing_models_and_saved_tomato_image(app, tmp_path, monkeypatch):
    import streamlit as st
    import config

    images = sorted((ROOT / "uploads" / "disease_images").rglob("*.jpg"))
    if not images:
        pytest.skip("A supported saved tomato image is required for real CNN verification")
    upload = io.BytesIO(images[0].read_bytes())
    upload.name = "tomato.jpg"
    monkeypatch.setattr(st, "file_uploader", lambda *a, **kw: upload)
    monkeypatch.setattr(config, "UPLOADS", tmp_path / "uploads" / "disease_images")

    # Real registration and login forms on the entrypoint.
    app.run()
    _button(app, "English").click().run()
    app.text_input[2].set_value("Demo farmer")
    app.text_input[3].set_value("demo_farmer")
    app.text_input[4].set_value("demo_test_password")
    _button(app, "Register").click().run()
    assert app.success and not app.exception
    app.text_input[0].set_value("demo_farmer")
    app.text_input[1].set_value("demo_test_password")
    _button(app, "Login").click().run()
    assert app.session_state["authenticated"] and not app.exception
    user_id = app.session_state["user_id"]

    # Navigation: all five pages render without exceptions.
    for page in ("advisory", "schemes", "history", "profile", "dashboard"):
        app.button(key=f"nav_{page}").click().run()
        assert not app.exception, page

    # One page, one button: image + readings go through the independent models,
    # are saved to history and combined by the advisory engine.
    app.button(key="nav_advisory").click().run()
    _fill_readings(app, humidity=93.0)
    _button(app, "Get AI Advice").click().run()
    assert not app.exception and not app.error
    disease = db.fetch_one("SELECT disease,confidence FROM disease_predictions WHERE user_id=?", (user_id,))
    assert disease and 0 <= disease["confidence"] <= 1
    greenhouse = db.fetch_one("SELECT prediction,humidity FROM greenhouse_analyses WHERE user_id=?", (user_id,))
    assert greenhouse and greenhouse["prediction"] == "Needs Adjustment" and greenhouse["humidity"] == 93
    session_id = app.session_state["current_chat_session"]
    response = db.fetch_chat_messages(session_id)[-1]["message"]
    actual_disease = localize_disease(disease["disease"], "English")
    assert actual_disease in response and f"{disease['confidence'] * 100:.1f}%" in response
    assert "Needs Adjustment" in response and "Humidity: High" in response
    assert "Sources" in response and "https://" in response
    assert "chatbot should" not in response
    panel = _page_text(app)
    assert "Analysis used for this answer" in panel and "AI Advisory" in panel and actual_disease in panel

    # Follow-up questions reuse the saved results only because the farmer opts in.
    app.checkbox(key="fa_use_previous").check()
    # Scheme question by voice: scheme info is pulled in alongside the analysis.
    _speak(monkeypatch, "Which government scheme offers polyhouse subsidy?", "scheme_q")
    app.run()
    scheme_response = db.fetch_chat_messages(session_id)[-1]["message"]
    assert "Government scheme information" in scheme_response and "MIDH" in scheme_response
    assert "chatbot" not in scheme_response.lower() and "Source note" not in scheme_response
    assert not app.exception and not app.error

    # Kannada: page and response obey the language.
    app.selectbox(key="sb_lang_select").select("Kannada").run()
    assert "ಈ ಉತ್ತರಕ್ಕೆ ಬಳಸಿದ ವಿಶ್ಲೇಷಣೆ" in _page_text(app) or "ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ" in _page_text(app)
    _speak(monkeypatch, "ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಏನು ಮಾಡಬೇಕು?", "kn_q")
    app.run()
    kannada = db.fetch_chat_messages(session_id)[-1]["message"]
    assert "ಹಸಿರುಮನೆ ಹೊಂದಾಣಿಕೆಗಳು" in kannada and "ಆರ್ದ್ರತೆ: ಹೆಚ್ಚು" in kannada
    assert not re.search(r"[A-Za-z]", re.sub(r"\]\([^)]*\)", "]", kannada))
    assert not app.exception and not app.error
    app.selectbox(key="sb_lang_select").select("English").run()

    # History & Reports and Dashboard show the persisted records.
    app.button(key="nav_history").click().run()
    assert not app.exception and actual_disease in _page_text(app)
    app.button(key="nav_dashboard").click().run()
    assert not app.exception
    app.button(key="nav_schemes").click().run()
    assert not app.exception and app.selectbox(key="schemes_dropdown_widget")

    # A second farmer sees neither this farmer's results nor conversation.
    ok, second_user = register_farmer("Second farmer", "second_farmer", "demo_test_password", "English")
    assert ok
    app.session_state["user_id"] = second_user
    app.session_state["current_page"] = "advisory"
    app.run()
    assert actual_disease not in _page_text(app) and "Analysis used for this answer" not in _page_text(app)
    app.number_input(key="farm_temperature").set_value(24.0)   # partly filled readings
    _button(app, "Get AI Advice").click().run()
    assert app.warning and not app.exception
    assert db.fetch_one("SELECT 1 FROM greenhouse_analyses WHERE user_id=?", (second_user,)) is None


def _seed_previous_results(app, name, username):
    app.run()
    ok, user_id = register_farmer(name, username, "voice_test_password", "English")
    assert ok
    db.execute("INSERT INTO disease_predictions(user_id,disease,confidence) VALUES(?,?,?)", (user_id, "Septoria_leaf_spot", 0.89))
    db.execute("INSERT INTO greenhouse_analyses(user_id,prediction,temperature,humidity,soil_moisture,light_intensity,co2) VALUES(?,?,?,?,?,?,?)", (user_id, "1", 30, 75, 75, 500, 600))
    for key, value in {"authenticated": True, "user_id": user_id, "language": "English", "current_page": "advisory", "name": name}.items():
        app.session_state[key] = value
    return user_id


@pytest.mark.skip(reason="Voice input was removed from the text-only advisory page; the saved-disease flow is covered by tests/test_disease_history_and_admin_counts.py")
def test_voice_question_uses_saved_analysis_only_when_the_farmer_opts_in(app, monkeypatch):
    _seed_previous_results(app, "Voice farmer", "voice_farmer")
    app.session_state["fa_use_previous"] = True
    _speak(monkeypatch, "What should I do?", "voice_test")
    app.run()
    assert not app.exception and not app.error
    answer = db.fetch_chat_messages(app.session_state["current_chat_session"])[-1]["message"]
    assert "Septoria Leaf Spot (89.0%)" in answer and "Temperature: High" in answer
    assert "Greenhouse adjustments" in answer
    assert "earlier saved result" in answer      # clearly labelled as not new


def test_question_only_ignores_older_saved_results_by_default(app, monkeypatch):
    _seed_previous_results(app, "Stale farmer", "stale_farmer")
    app.run()
    assert app.checkbox(key="fa_use_previous").value is False   # offered, but off
    app.text_area(key="integrated_question").set_value("How should I irrigate tomato?")
    _button(app, "Get AI Advice").click().run()
    assert not app.exception and not app.error
    answer = db.fetch_chat_messages(app.session_state["current_chat_session"])[-1]["message"]
    assert "Septoria" not in answer and "Temperature: High" not in answer
    assert "Analysis used for this answer" not in _page_text(app)


@pytest.mark.skip(reason="Voice input was removed from the text-only advisory page; the saved-disease flow is covered by tests/test_disease_history_and_admin_counts.py")
def test_voice_question_without_opt_in_does_not_use_older_results(app, monkeypatch):
    _seed_previous_results(app, "Voice two", "voice_two")
    _speak(monkeypatch, "What should I do?", "voice_no_optin")
    app.run()
    assert not app.exception and not app.error
    answer = db.fetch_chat_messages(app.session_state["current_chat_session"])[-1]["message"]
    assert "Septoria" not in answer


def test_question_only_and_empty_submissions(app, monkeypatch):
    app.run()
    ok, user_id = register_farmer("Plain farmer", "plain_farmer", "demo_test_password", "English")
    assert ok
    for key, value in {"authenticated": True, "user_id": user_id, "language": "English", "current_page": "advisory", "name": "Plain farmer"}.items():
        app.session_state[key] = value
    app.run()
    _button(app, "Get AI Advice").click().run()           # nothing supplied
    assert app.warning and not app.exception
    assert db.fetch_one("SELECT 1 FROM chat_sessions WHERE user_id=?", (user_id,)) is None
    app.text_area(key="integrated_question").set_value("How should I irrigate tomato?")   # form values commit on submit
    _button(app, "Get AI Advice").click().run()           # question only: no analyses needed
    assert not app.exception and not app.error
    assert db.fetch_chat_messages(app.session_state["current_chat_session"])
