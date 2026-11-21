import json
import re

import pytest

import database.db as db
from services.analysis_context import build_retrieval_query, format_analysis_context, get_latest_analysis_context
from services.advisory_service import answer_farmer_question
import services.llm_service as llm


@pytest.fixture
def farmers(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", tmp_path / "farm.db")
    monkeypatch.setattr(llm, "ENABLE_OLLAMA", False)
    db.initialize_database()
    users = [db.execute("INSERT INTO users(name,username,password_hash) VALUES(?,?,?)", (name, name, "test")) for name in ("A", "B")]
    return users


def save_disease(user_id, disease="Early_blight", confidence=0.94, timestamp="2026-10-06 10:00:00"):
    return db.execute("INSERT INTO disease_predictions(user_id,disease,confidence,created_at) VALUES(?,?,?,?)", (user_id, disease, confidence, timestamp))


def save_greenhouse(user_id, status="1", humidity=93, timestamp="2026-10-06 10:00:00"):
    return db.execute(
        "INSERT INTO greenhouse_analyses(user_id,prediction,temperature,humidity,soil_moisture,light_intensity,co2,created_at,xai_explanation) VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, status, 24, humidity, 75, 500, 600, timestamp, "Legacy free text must not enter the prompt"),
    )


def test_latest_is_user_scoped_and_timestamps_have_id_tiebreakers(farmers):
    a, b = farmers
    save_disease(a, "Late_blight", 0.8)
    save_disease(a)
    save_disease(a, "healthy", 0.99, "2026-10-05 10:00:00")  # higher ID, older timestamp
    save_greenhouse(a, "2", 97)
    save_greenhouse(a)
    save_disease(b, "Septoria_leaf_spot", 0.88, "2026-10-06 11:00:00")
    save_greenhouse(b, "0", 75, "2026-10-06 11:00:00")

    context = get_latest_analysis_context(a)
    assert context["disease"]["disease"] == "Early Blight"
    assert context["disease"]["confidence"] == 94
    assert context["disease"]["crop"] == "Tomato"  # deployed CNN metadata
    assert context["greenhouse"]["status"] == "Needs Adjustment"
    assert [p["feature"] for p in context["greenhouse"]["problem_parameters"]] == ["humidity"]
    assert context["greenhouse"]["problem_parameters"][0]["direction"] == "High"
    assert get_latest_analysis_context(b)["disease"]["disease"] == "Septoria Leaf Spot"
    text = format_analysis_context(context)
    assert "93%" in text and "94.0%" in text
    assert "Legacy" not in text and "image_path" not in text and "user_id" not in text
    # No stale per-user cache after a new prediction.
    save_disease(a, "Leaf_Mold", 0.91)
    assert get_latest_analysis_context(a)["disease"]["disease"] == "Leaf Mold"


@pytest.mark.parametrize("disease,greenhouse", [(True, True), (True, False), (False, True), (False, False)])
def test_four_context_cases_with_real_persisted_rag(farmers, disease, greenhouse):
    a, b = farmers
    if disease:
        save_disease(a)
    if greenhouse:
        save_greenhouse(a)
    context = get_latest_analysis_context(a)
    response, results, generated, _ = answer_farmer_question("What should I do for my tomato crop?", "English", context)
    assert bool(context["disease"]["available"]) == disease
    assert bool(context["greenhouse"]["available"]) == greenhouse
    assert ("Disease detection:" in response) == disease
    assert ("Greenhouse status:" in response) == greenhouse
    assert not generated and results
    assert get_latest_analysis_context(b) == {"disease": {"available": False}, "greenhouse": {"available": False}}
    if disease:
        assert "Early Blight (94.0%)" in response
        assert "Remove heavily infected debris" in response
    if greenhouse:
        assert "Needs Adjustment" in response and "Humidity: High" in response
        assert "ventilate" in response
    if disease or greenhouse:
        assert "share your" not in response.lower() and "chatbot should" not in response.lower()


def test_enriched_generic_query_has_only_actual_concerns(farmers):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    context = get_latest_analysis_context(farmers[0])
    query = build_retrieval_query("What should I do?", context)
    assert "Early Blight" in query and "high Humidity" in query
    assert "temperature" not in query.lower() and "500" not in query and "93" not in query
    response, results, _, _ = answer_farmer_question("What should I do?", "English", context)
    documents = {r["document_id"] for r in results}
    assert {"03_early_blight", "05_temperature_humidity_and_ventilation"} <= documents
    assert "04_late_blight" not in documents
    assert "Greenhouse adjustments" in response


def test_context_off_uses_original_query(farmers, monkeypatch):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    import services.advisory_service as advisory
    queries = []
    monkeypatch.setattr(advisory, "retrieve", lambda query: queries.append(query) or [])
    response, _, _, _ = advisory.answer_farmer_question("What should I do?", "English", "")
    assert queries == ["What should I do?"]
    assert "Early Blight" not in response and "Greenhouse status" not in response


def test_kannada_combined_answer_is_entirely_kannada(farmers):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    response, results, generated, _ = answer_farmer_question("ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಏನು ಮಾಡಬೇಕು?", "Kannada", get_latest_analysis_context(farmers[0]))
    assert "ಮುಂಚಿನ ಅಂಗಮಾರಿ" in response and "94.0%" in response
    assert "ತಿದ್ದುಪಡಿ ಅಗತ್ಯ" in response and "ಆರ್ದ್ರತೆ: ಹೆಚ್ಚು" in response
    assert "ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮಗಳು" in response and "ಹಸಿರುಮನೆ ಹೊಂದಾಣಿಕೆಗಳು" in response
    assert not re.search(r"[A-Za-z]", response)
    assert results and not generated


def test_kannada_generic_question_still_uses_context_when_translation_fails(farmers, monkeypatch):
    import services.advisory_service as advisory
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    monkeypatch.setattr(advisory, "translate_rag_query_to_english", lambda q: ("agricultural advice", False))
    response, results, _, translated = advisory.answer_farmer_question("ನಾನು ಏನು ಮಾಡಬೇಕು?", "Kannada", get_latest_analysis_context(farmers[0]))
    assert "ಮುಂಚಿನ ಅಂಗಮಾರಿ" in response and "ತಿದ್ದುಪಡಿ ಅಗತ್ಯ" in response
    assert results and not translated


@pytest.mark.parametrize("question", ["What should I do?", "Which government scheme offers polyhouse subsidy?"])
def test_prompt_has_separate_facts_evidence_and_question(farmers, monkeypatch, question):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    context = get_latest_analysis_context(farmers[0])
    captured = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "Improve airflow and avoid unnecessary leaf wetness."}

    monkeypatch.setattr(llm, "ollama_available", lambda: True)
    monkeypatch.setattr(llm.requests, "post", lambda url, **kw: captured.append(kw["json"]["prompt"]) or Response())
    response, _, generated, _ = answer_farmer_question(question, "English", context)
    prompt = captured[0]
    assert "APPLICATION ANALYSIS CONTEXT:" in prompt
    assert "RETRIEVED AGRICULTURAL KNOWLEDGE:" in prompt and f"FARMER QUESTION:\n{question}" in prompt
    assert "Early Blight" in prompt and "Humidity: High" in prompt
    assert "Do not claim a greenhouse condition caused a disease" in prompt
    assert "Address each flagged greenhouse parameter separately" in prompt
    assert "Do not invent a heating method, irrigation volume or schedule" in prompt
    assert "Greenhouse model reference range: 65–90%" in prompt
    assert "low air humidity alone does not establish an irrigation need" in prompt
    assert "Do not invent a humidification method or equipment setting" in prompt
    assert "Legacy free text" not in prompt and "user_id" not in prompt
    assert generated and "Early Blight (94.0%)" in response and "Needs Adjustment" in response
    if "scheme" in question:
        assert "MIDH" in prompt and "do not establish scheme eligibility" in prompt


def test_insufficient_evidence_and_failed_llm_preserve_analysis(farmers, monkeypatch):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    context = get_latest_analysis_context(farmers[0])
    response, generated = llm.answer("What should I do?", [], "English", context)
    assert "Early Blight" in response and "Needs Adjustment" in response
    assert "not find enough agricultural evidence" in response and not generated
    monkeypatch.setattr(llm, "ollama_available", lambda: True)
    monkeypatch.setattr(llm.requests, "post", lambda *a, **kw: (_ for _ in ()).throw(ConnectionError()))
    response, results, generated, _ = answer_farmer_question("What should I do?", "English", context)
    assert "Remove heavily infected debris" in response and "Greenhouse adjustments" in response
    assert results and not generated


def test_nighttime_light_is_not_flagged_and_missing_readings_are_not_invented(farmers):
    db.execute("INSERT INTO greenhouse_analyses(user_id,prediction,humidity,light_intensity) VALUES(?,?,?,?)", (farmers[0], "0", 75, 0))
    context = get_latest_analysis_context(farmers[0])
    assert context["greenhouse"]["status"] == "Suitable"
    assert context["greenhouse"]["temperature"] is None
    assert context["greenhouse"]["problem_parameters"] == []
    assert "Temperature:" not in format_analysis_context(context)


def test_low_humidity_never_gets_high_humidity_management(farmers):
    save_greenhouse(farmers[0], "2", 40)
    response, results, _, _ = answer_farmer_question("What should I do?", "English", get_latest_analysis_context(farmers[0]))
    assert "Humidity: Low" in response
    assert "avoid excessive irrigation that raises humidity" not in response.lower()
    assert not any("high humidity problems" in r["text"].lower() for r in results)


@pytest.mark.parametrize("language,question", [
    ("English", "What should I do for my tomato crop?"),
    ("Kannada", "ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಏನು ಮಾಡಬೇಕು?"),
])
def test_septoria_and_low_air_humidity_get_interpretation_and_grounded_checks(farmers, language, question):
    save_disease(farmers[0], "Septoria_leaf_spot", 0.977)
    save_greenhouse(farmers[0], "Unsuitable", 15)
    context = get_latest_analysis_context(farmers[0])
    response, results, generated, _ = answer_farmer_question(question, language, context)
    assert not generated
    assert [p["feature"] for p in context["greenhouse"]["problem_parameters"]] == ["humidity"]
    assert {"06_septoria_leaf_spot", "05_temperature_humidity_and_ventilation", "07_irrigation_and_soil_moisture"} <= {r["document_id"] for r in results}
    assert any("Check emitter flow" in r["text"] for r in results)
    if language == "English":
        assert "Septoria Leaf Spot (97.7%)" in response and "Greenhouse status: Unsuitable" in response
        greenhouse = response.split("**Greenhouse adjustments**", 1)[1].split("**Why this advice**", 1)[0]
        assert "**Humidity: Low**" in greenhouse and "Recorded reading: 15%" in greenhouse
        assert "Greenhouse model reference range: 65–90%" in greenhouse
        assert "Monitor temperature and humidity together" in greenhouse
        assert "Your root-zone moisture is 75%, within this model's reference range" in greenhouse
        assert "emitter flow and drainage" in greenhouse
        assert "prioritise correcting air humidity" in greenhouse
        assert "does not specify a humidity-control method or equipment setting" in greenhouse
        assert not re.search(r"increase (?:irrigation|watering)|ventilate|heat stress|not find enough agricultural evidence", greenhouse, re.IGNORECASE)
    else:
        assert "ಸೆಪ್ಟೋರಿಯಾ ಎಲೆ ಚುಕ್ಕೆ" in response and "97.7%" in response
        assert "**ಆರ್ದ್ರತೆ: ಕಡಿಮೆ**" in response and "ದಾಖಲಾದ ಅಳತೆ: 15%" in response
        assert "ಹಸಿರುಮನೆ ಮಾದರಿಯ ಉಲ್ಲೇಖ ಶ್ರೇಣಿ: 65–90%" in response
        assert "ತಾಪಮಾನ ಮತ್ತು ಆರ್ದ್ರತೆಯನ್ನು ಒಟ್ಟಿಗೆ ಗಮನಿಸಿ" in response
        assert "ಬೇರು ವಲಯದ ತೇವಾಂಶ 75%" in response and "ಡ್ರಿಪ್ಪರ್ ಹರಿವು" in response
        assert not re.search(r"[A-Za-z]", response)


def test_low_humidity_does_not_treat_dry_roots_as_suitable(farmers):
    db.execute(
        "INSERT INTO greenhouse_analyses(user_id,prediction,temperature,humidity,soil_moisture,light_intensity,co2) VALUES(?,?,?,?,?,?,?)",
        (farmers[0], "Unsuitable", 24, 15, 5, 500, 600),
    )
    response, _, _, _ = answer_farmer_question("What should I do?", "English", get_latest_analysis_context(farmers[0]))
    assert "**Humidity: Low**" in response and "**Soil Moisture: Low**" in response
    assert "within this model's reference range" not in response
    assert "If dryness is confirmed, adjust irrigation" in response
    assert "This reference describes substrate water content" in response


def test_low_humidity_missing_readings_and_evidence_are_not_invented(farmers):
    db.execute("INSERT INTO greenhouse_analyses(user_id,prediction,humidity) VALUES(?,?,?)", (farmers[0], "Unsuitable", 15))
    context = get_latest_analysis_context(farmers[0])
    response, generated = llm.answer("What should I do?", [], "English", context)
    assert not generated and "Recorded reading: 15%" in response
    assert "Recheck the humidity sensor" in response
    assert "does not specify a humidity-control method or equipment setting" in response
    assert "root-zone moisture is" not in response and "emitter flow" not in response
    assert "Monitor temperature and humidity together" not in response


def test_model_reference_is_loaded_from_policy_not_hardcoded(farmers, tmp_path, monkeypatch):
    import services.greenhouse_service as greenhouse_service
    policy = json.loads(greenhouse_service.POLICY_PATH.read_text(encoding="utf-8"))
    policy["relative_humidity_percent"]["suitable"] = [60, 85]
    changed_policy = tmp_path / "policy.json"
    changed_policy.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(greenhouse_service, "POLICY_PATH", changed_policy)
    save_greenhouse(farmers[0], "Unsuitable", 15)
    response, _, _, _ = answer_farmer_question("What should I do?", "English", get_latest_analysis_context(farmers[0]))
    assert "Greenhouse model reference range: 60–85%" in response
    assert "65–90%" not in response


@pytest.mark.parametrize("language,question", [
    ("English", "Which government scheme offers polyhouse subsidy?"),
    ("Kannada", "ಪಾಲಿಹೌಸ್ ಸಹಾಯಧನ ಯೋಜನೆ ಬಗ್ಗೆ ಹೇಳಿ"),
])
def test_scheme_question_connects_scheme_knowledge_and_farmer_analyses(farmers, language, question):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    response, results, generated, _ = answer_farmer_question(question, language, get_latest_analysis_context(farmers[0]))
    assert any(item.get("category") == "scheme" for item in results)
    assert any(item.get("document_id") == "03_early_blight" for item in results)
    assert any(item.get("document_id") == "05_temperature_humidity_and_ventilation" for item in results)
    assert not generated
    if language == "Kannada":
        assert "ಸರ್ಕಾರಿ ಯೋಜನೆ ಮಾಹಿತಿ" in response and "ಮುಂಚಿನ ಅಂಗಮಾರಿ" in response
        assert "ತಿದ್ದುಪಡಿ ಅಗತ್ಯ" in response and "ಅರ್ಹತೆಯನ್ನು ದೃಢಪಡಿಸುವುದಿಲ್ಲ" in response
        assert not re.search(r"[A-Za-z]", response)
    else:
        assert "Government scheme information" in response and "MIDH" in response
        assert "Early Blight (94.0%)" in response and "Humidity: High" in response
        assert "do not establish scheme eligibility" in response


@pytest.mark.parametrize("language,question", [
    ("English", "Which government scheme offers polyhouse subsidy?"),
    ("Kannada", "ಬೆಳೆ ಪಾಲಿಹೌಸ್ ಸಹಾಯಧನ ಯೋಜನೆ ಬಗ್ಗೆ ಹೇಳಿ"),
])
def test_scheme_context_off_is_generic_even_when_farmer_has_analyses(farmers, language, question):
    save_disease(farmers[0])
    save_greenhouse(farmers[0])
    response, results, _, _ = answer_farmer_question(question, language, "")
    assert results and all(item.get("category") == "scheme" for item in results)
    assert "Early Blight" not in response and "Greenhouse status" not in response
    if language == "Kannada":
        assert "ಯೋಜನೆ" in response and "ಮುಂಚಿನ ಅಂಗಮಾರಿ" not in response
        assert not re.search(r"[A-Za-z]", response)


@pytest.mark.parametrize("language,question", [
    ("English", "What should I do for my tomato crop?"),
    ("Kannada", "ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಏನು ಮಾಡಬೇಕು?"),
])
def test_septoria_with_cold_temperature_and_dry_root_zone(farmers, language, question):
    save_disease(farmers[0], "Septoria_leaf_spot", 0.977)
    db.execute(
        "INSERT INTO greenhouse_analyses(user_id,prediction,temperature,humidity,soil_moisture,light_intensity,co2) VALUES(?,?,?,?,?,?,?)",
        (farmers[0], "Unsuitable", 14, 75, 5, 500, 800),
    )
    context = get_latest_analysis_context(farmers[0])
    response, results, generated, _ = answer_farmer_question(question, language, context)
    assert not generated
    assert {p["feature"] for p in context["greenhouse"]["problem_parameters"]} == {"temperature", "soil_moisture"}
    assert any(r["document_id"] == "07_irrigation_and_soil_moisture" and "Better irrigation decisions" in r["text"] for r in results)
    if language == "English":
        assert "Septoria Leaf Spot (97.7%)" in response and "Greenhouse status: Unsuitable" in response
        assert "**Temperature: Low**" in response and "**Soil Moisture: Low**" in response
        assert "adjust irrigation" in response and "Check emitter flow and drainage" in response
        assert "monitor day and night temperatures" in response
        assert "does not specify a cold-weather heating method" in response
        assert "I could not find enough agricultural evidence" not in response
        assert "ventilate when conditions allow" not in response
    else:
        assert "ಸೆಪ್ಟೋರಿಯಾ ಎಲೆ ಚುಕ್ಕೆ" in response and "97.7%" in response
        assert "**ತಾಪಮಾನ: ಕಡಿಮೆ**" in response and "**ಮಣ್ಣಿನ ತೇವಾಂಶ: ಕಡಿಮೆ**" in response
        assert "ನೀರಾವರಿ ಹೊಂದಿಸಿ" in response and "ಡ್ರಿಪ್ಪರ್ ಹರಿವು" in response
        assert not re.search(r"[A-Za-z]", response)


def test_shared_temperature_humidity_article_does_not_mix_opposite_adjustments(farmers):
    db.execute(
        "INSERT INTO greenhouse_analyses(user_id,prediction,temperature,humidity,soil_moisture,light_intensity,co2) VALUES(?,?,?,?,?,?,?)",
        (farmers[0], "Unsuitable", 14, 97, 75, 500, 800),
    )
    response, _, _, _ = answer_farmer_question("What should I do?", "English", get_latest_analysis_context(farmers[0]))
    temperature = response.split("**Temperature: Low**", 1)[1].split("**Humidity: High**", 1)[0]
    humidity = response.split("**Humidity: High**", 1)[1]
    assert "cold-weather heating method" in temperature
    assert "ventilate" not in temperature
    assert "ventilate when conditions allow" in humidity
