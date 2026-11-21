from services.localization import (
    localize_disease,
    localize_disease_advice,
    localize_rag_item,
)
from services.translation_service import translate_rag_query_to_english
from services.tts_service import _speech_controls_html


def test_kannada_query_is_translated_locally_for_fast_english_rag():
    query, complete = translate_rag_query_to_english(
        "ಟೊಮ್ಯಾಟೊ ಗಿಡಕ್ಕೆ ಎಷ್ಟು ನೀರು ಹಾಕಬೇಕು?"
    )

    assert complete
    assert "tomato" in query
    assert "water" in query
    assert "irrigation" in query


def test_dynamic_rag_pages_have_curated_kannada_content():
    greenhouse = localize_rag_item(
        {
            "document_id": "05_temperature_humidity_and_ventilation",
            "topic": "Temperature, Humidity and Ventilation",
            "text": "English greenhouse prose",
        },
        "Kannada",
    )
    scheme = localize_rag_item(
        {
            "document_id": "02_pm_kisan",
            "topic": "PM-KISAN",
            "text": "English scheme prose",
        },
        "Kannada",
    )

    assert greenhouse["topic"] == "ತಾಪಮಾನ, ಆರ್ದ್ರತೆ ಮತ್ತು ಗಾಳಿಯಾಡುವಿಕೆ"
    assert "English" not in greenhouse["text"]
    assert scheme["topic"] == "ಪಿಎಂ-ಕಿಸಾನ್"
    assert "English" not in scheme["text"]


def test_leaf_class_and_advice_are_kannada_even_for_legacy_name():
    legacy = "Spider mites Two-spotted spider mite"

    assert localize_disease(legacy, "Kannada") == "ಜೇಡ ಹುಳುಗಳು (ಎರಡು-ಚುಕ್ಕೆ)"
    assert "ಶಂಕೆಯಿದೆ" in localize_disease_advice(legacy, "Kannada")


def test_read_aloud_component_has_pause_resume_stop_and_escapes_script_text():
    html = _speech_controls_html(
        "answer </script><script>alert(1)</script>",
        "Kannada",
        {
            "controls": "ಗಟ್ಟಿಯಾಗಿ ಓದುವ ನಿಯಂತ್ರಣಗಳು",
            "listen": "ಆಲಿಸಿ",
            "pause": "ವಿರಾಮ",
            "resume": "ಮುಂದುವರಿಸಿ",
            "stop": "ನಿಲ್ಲಿಸಿ",
            "paused": "ವಿರಾಮದಲ್ಲಿದೆ",
            "unsupported": "ಲಭ್ಯವಿಲ್ಲ",
        },
    )

    assert 'id="pause"' in html
    assert 'id="resume"' in html
    assert 'id="stop"' in html
    assert "answer </script><script>alert" not in html
    assert 'lang="kn"' in html
