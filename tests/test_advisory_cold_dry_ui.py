import re

from services.auth_service import register_farmer
import database.db as db
from test_advisory_ui import _button, _fill_readings, app  # noqa: F401  (isolated AppTest/database fixture)


def _login(app, name, username):
    app.run()
    ok, user_id = register_farmer(name, username, "demo_test_password", "English")
    assert ok
    db.execute("INSERT INTO disease_predictions(user_id,disease,confidence) VALUES(?,?,?)", (user_id, "Septoria_leaf_spot", 0.977))
    for key, value in {"authenticated": True, "user_id": user_id, "language": "English", "name": name, "current_page": "advisory"}.items():
        app.session_state[key] = value
    # These tests exercise the "reuse my earlier disease result" opt-in.
    app.session_state["fa_use_previous"] = True
    return user_id


def test_cold_dry_readings_get_specific_saved_advice(app):
    user_id = _login(app, "Cold dry farmer", "cold_dry_farmer")
    app.run()
    _fill_readings(app, temperature=14.0, humidity=75.0, soil_moisture=5.0, light=500.0, co2=800.0)
    _button(app, "Get AI Advice").click().run()
    assert not app.exception and not app.error
    response = db.fetch_chat_messages(app.session_state["current_chat_session"])[-1]["message"]
    assert "Septoria Leaf Spot (97.7%)" in response and "Unsuitable" in response
    assert "**Temperature: Low**" in response and "**Soil Moisture: Low**" in response
    assert "adjust irrigation" in response and "Check emitter flow and drainage" in response
    assert "cold-weather heating method" in response and "Sources" in response


def test_low_humidity_reading_reaches_saved_advice_in_both_languages(app):
    user_id = _login(app, "Dry air farmer", "dry_air_farmer")
    app.run()
    _fill_readings(app, humidity=15.0)
    _button(app, "Get AI Advice").click().run()
    assert not app.exception and not app.error
    greenhouse = db.fetch_one("SELECT prediction,humidity FROM greenhouse_analyses WHERE user_id=?", (user_id,))
    assert greenhouse["prediction"] == "Unsuitable" and greenhouse["humidity"] == 15
    session_id = app.session_state["current_chat_session"]
    response = db.fetch_chat_messages(session_id)[-1]["message"]
    assert "Septoria Leaf Spot (97.7%)" in response and "Unsuitable" in response
    assert "Recorded reading: 15%" in response and "Greenhouse model reference range: 65–90%" in response
    assert "Monitor temperature and humidity together" in response and "root-zone moisture is 75%" in response
    assert "not find enough agricultural evidence" not in response

    app.selectbox(key="sb_lang_select").select("Kannada").run()
    app.text_area(key="integrated_question").set_value("ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಏನು ಮಾಡಬೇಕು?")
    _button(app, "ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಸಲಹೆ ಪಡೆಯಿರಿ").click().run()
    kannada = db.fetch_chat_messages(session_id)[-1]["message"]
    assert "**ಆರ್ದ್ರತೆ: ಕಡಿಮೆ**" in kannada and "ಉಲ್ಲೇಖ ಶ್ರೇಣಿ: 65–90%" in kannada
    assert not re.search(r"[A-Za-z]", re.sub(r"\]\([^)]*\)", "]", kannada))
    assert not app.exception and not app.error
