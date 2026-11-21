"""Disease-prediction history is saved exactly once and the admin counts are live."""
import sqlite3

import pytest

import database.db as db
from services import disease_service, farm_assistant

TOP = [("Early_blight", 0.93), ("Late_blight", 0.04), ("Septoria_leaf_spot", 0.02)]


@pytest.fixture
def farmer(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "namma_krushi.db")
    db._INITIALIZED_DATABASES.clear()
    db.initialize_database()
    uid = db.execute("INSERT INTO users(name,username,password_hash) VALUES(?,?,?)", ("Ann", "ann", "x"))
    monkeypatch.setattr(disease_service, "predict_checked",
                        lambda _b: {"reliable": True, "reason": None, "top": TOP})
    return uid, tmp_path / "uploads" / "disease_images"


def _rows():
    return db.fetch_all("SELECT * FROM disease_predictions ORDER BY prediction_id")


def test_successful_prediction_saves_all_fields(farmer):
    uid, root = farmer
    result = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert result["saved"] is True and result["prediction_id"] is not None
    (row,) = _rows()
    assert row["user_id"] == uid
    assert row["disease"] == "Early_blight" and row["confidence"] == pytest.approx(0.93)
    assert row["created_at"]
    assert row["image_path"].startswith("uploads/disease_images/%d/" % uid) and "\\" not in row["image_path"]
    assert (root.parent.parent / row["image_path"]).read_bytes() == b"img"


def test_repeated_submit_of_same_result_is_saved_once(farmer):
    uid, root = farmer
    first = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    second = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert len(_rows()) == 1
    assert second["saved"] is True and second["prediction_id"] == first["prediction_id"]
    # The duplicate's image file is removed; only the saved one remains.
    assert len(list((root / str(uid)).glob("*.jpg"))) == 1


def test_a_different_result_is_a_new_record(farmer, monkeypatch):
    uid, root = farmer
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    monkeypatch.setattr(disease_service, "predict_checked", lambda _b: {
        "reliable": True, "reason": None, "top": [("Late_blight", 0.88), ("Early_blight", 0.05), ("Leaf_Mold", 0.02)]})
    farm_assistant.analyze_leaf_image(uid, b"img2", uploads_dir=root)
    assert [r["disease"] for r in _rows()] == ["Early_blight", "Late_blight"]


def test_old_duplicate_outside_window_is_a_new_record(farmer):
    uid, root = farmer
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    db.execute("UPDATE disease_predictions SET created_at=datetime('now','-1 hour')")
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert len(_rows()) == 2


def test_unreliable_prediction_is_not_saved(farmer, monkeypatch):
    uid, root = farmer
    monkeypatch.setattr(disease_service, "predict_checked",
                        lambda _b: {"reliable": False, "reason": "low_confidence", "top": TOP})
    result = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert result["saved"] is False and result["disease"] is None
    assert _rows() == [] and not (root / str(uid)).exists()


def test_unknown_user_is_reported_not_saved_and_leaves_no_orphan_image(farmer):
    _uid, root = farmer
    result = farm_assistant.analyze_leaf_image(4242, b"img", uploads_dir=root)
    assert result["reliable"] is True and result["saved"] is False
    assert _rows() == []
    assert not list(root.rglob("*.jpg"))


def test_database_failure_is_reported_not_swallowed(farmer, monkeypatch):
    uid, root = farmer

    def boom(*_a, **_k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(farm_assistant, "save_disease_prediction", boom)
    result = farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    assert result["saved"] is False and result["disease"] == "Early_blight"
    assert not list(root.rglob("*.jpg"))


def test_admin_counts_are_live_and_include_advisory_interactions(farmer):
    uid, root = farmer
    assert db.get_admin_counts() == {
        "farmers": 1, "disease_predictions": 0, "greenhouse_analyses": 0,
        "advisory_interactions": 0, "chat_sessions": 0}
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    db.execute("INSERT INTO greenhouse_analyses(user_id,prediction) VALUES(?,?)", (uid, "Optimal"))
    sid = db.save_chat_exchange(uid, None, "t", "q1", "a1")
    db.save_chat_exchange(uid, sid, "t", "q2", "a2")
    db.execute("INSERT INTO users(name,username,password_hash) VALUES(?,?,?)", ("Bob", "bob", "x"))
    assert db.get_admin_counts() == {
        "farmers": 2, "disease_predictions": 1, "greenhouse_analyses": 1,
        "advisory_interactions": 2, "chat_sessions": 1}


def test_admin_dashboard_page_shows_the_database_counts(farmer):
    from streamlit.testing.v1 import AppTest
    uid, root = farmer
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)
    db.save_chat_exchange(uid, None, "t", "q", "a")

    def page():
        import streamlit as st
        from views.admin_dashboard import render
        render(st)

    at = AppTest.from_function(page).run(timeout=60)
    assert not at.exception, at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics == {
        "Registered farmers": "1", "Disease predictions": "1",
        "Greenhouse analyses": "0", "AI advisory interactions": "1"}


def test_end_to_end_ui_with_real_model_saves_once_and_admin_sees_it(tmp_path, monkeypatch):
    """Real app.py + real EfficientNetB0 + real leaf photo, through the Streamlit UI."""
    import io
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    import config
    import services.llm_service as llm

    images = sorted((config.ROOT / "uploads" / "disease_images").rglob("*.jpg"))
    if not images:
        pytest.skip("A saved tomato leaf image is required for the real-model check")
    upload = io.BytesIO(images[0].read_bytes())
    upload.name = "leaf.jpg"

    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "namma_krushi.db")
    db._INITIALIZED_DATABASES.clear()
    monkeypatch.setattr(llm, "ENABLE_OLLAMA", False)
    monkeypatch.setattr(config, "UPLOADS", tmp_path / "uploads" / "disease_images")
    monkeypatch.setattr(st, "file_uploader", lambda *a, **kw: upload)

    def button(at, label):
        return next(b for b in at.button if b.label == label)

    app = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=180)
    app.run()
    button(app, "English").click().run()
    app.text_input[2].set_value("E2E farmer")
    app.text_input[3].set_value("e2e_farmer")
    app.text_input[4].set_value("e2e_password")
    button(app, "Register").click().run()
    app.text_input[0].set_value("e2e_farmer")
    app.text_input[1].set_value("e2e_password")
    button(app, "Login").click().run()
    assert app.session_state["authenticated"] and not app.exception
    user_id = app.session_state["user_id"]

    app.button(key="nav_advisory").click().run()
    assert db.get_admin_counts()["disease_predictions"] == 0

    button(app, "Get AI Advice").click().run()
    assert not app.exception and not app.error
    rows = db.fetch_all("SELECT * FROM disease_predictions")
    assert len(rows) == 1
    assert rows[0]["user_id"] == user_id and 0 < rows[0]["confidence"] <= 1 and rows[0]["disease"]
    assert (tmp_path / rows[0]["image_path"]).exists()
    assert any("Saved to your History" in c.value for c in app.caption)

    # Streamlit reruns (any widget interaction) must not write again.
    app.run()
    app.run()
    assert len(db.fetch_all("SELECT * FROM disease_predictions")) == 1
    # Pressing the button twice in a row is also one record.
    button(app, "Get AI Advice").click().run()
    assert len(db.fetch_all("SELECT * FROM disease_predictions")) == 1

    # AI advisory question + answer were stored in chat_messages of the same DB.
    counts = db.get_admin_counts()
    assert counts["disease_predictions"] == 1
    assert counts["advisory_interactions"] >= 1
    raw = sqlite3.connect(tmp_path / "namma_krushi.db")
    try:
        assert raw.execute("SELECT COUNT(*) FROM chat_messages WHERE role='user'").fetchone()[0] == counts["advisory_interactions"]
        assert raw.execute("SELECT COUNT(*) FROM chat_messages WHERE role='assistant'").fetchone()[0] == counts["advisory_interactions"]
    finally:
        raw.close()

    # History page shows it for this farmer.
    app.button(key="nav_history").click().run()
    assert not app.exception


# ----------------------------------------------------------------------------
# History page: "What should I do?" for every saved disease scan
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("language,expected", [("English", "What should I do?"), ("Kannada", "ನಾನು ಏನು ಮಾಡಬೇಕು?")])
def test_history_shows_what_to_do_for_each_saved_scan(farmer, language, expected):
    from streamlit.testing.v1 import AppTest
    uid, root = farmer
    farm_assistant.analyze_leaf_image(uid, b"img", uploads_dir=root)

    def page():
        import json
        import streamlit as st
        import config
        from views import history_reports
        lang = st.session_state["language"]
        strings = json.loads((config.ROOT / "translation" / ("ui_strings_kn.json" if lang == "Kannada" else "ui_strings_en.json")).read_text(encoding="utf-8"))
        history_reports.render(st, lambda k: strings.get(k, k))

    at = AppTest.from_function(page, default_timeout=60)
    at.session_state["language"] = language
    at.session_state["user_id"] = uid
    at.run()
    assert not at.exception, at.exception
    assert [e.label for e in at.expander] == [expected]
    body = " ".join(m.value for m in at.markdown)
    assert body.strip()
    if language == "English":
        assert "Remove heavily infected debris" in body      # Early_blight management text from the KB
