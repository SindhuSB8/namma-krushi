"""Regression tests for the audit fixes (schemes page, scheme routing, new KB)."""
import json

import pytest
from streamlit.testing.v1 import AppTest

from config import ROOT


def _schemes_page():
    import json as _json
    import streamlit as st
    from config import ROOT as root
    st.session_state.setdefault("language", "English")
    strings = _json.loads((root / "translation" / "ui_strings_en.json").read_text(encoding="utf-8"))
    from views import schemes
    schemes.render(st, lambda key: strings.get(key, key))


def test_scheme_quick_buttons_change_the_selected_scheme():
    app = AppTest.from_function(_schemes_page, default_timeout=60).run()
    assert not app.exception
    app.selectbox(key="schemes_category_widget").select("credit").run()   # quick buttons appear per topic
    app.button(key="quick_btn_03_kisan_credit_card").click().run()
    assert not app.exception
    assert app.selectbox(key="schemes_dropdown_widget").value == "03_kisan_credit_card"
    assert [s.value for s in app.subheader][:1] == ["Kisan Credit Card (KCC)"]


def test_scheme_page_shows_every_section_not_only_the_first_chunk():
    app = AppTest.from_function(_schemes_page, default_timeout=60).run()
    app.selectbox(key="schemes_dropdown_widget").select("01_midh_protected_cultivation").run()
    text = " ".join(m.value for m in app.markdown)
    assert "Exact admissible cost" in text and "Mission for Integrated Development" in text


def test_scheme_question_about_growing_tomatoes_is_not_answered_with_the_yield_script():
    from services.advisory_service import answer_farmer_question
    response, results, _, _ = answer_farmer_question(
        "Is there a subsidy to grow tomatoes in a polyhouse?", "English", ""
    )
    assert "cannot safely force tomato yield" not in response
    assert any(r.get("category") == "scheme" for r in results)


def test_scheme_terms_route_kusum_and_nhm_to_schemes():
    from services.rag_service import route
    assert route("solar pump subsidy under PM-KUSUM") == "schemes"
    assert route("National Horticulture Mission NHM") == "schemes"


def test_new_scheme_documents_are_retrievable_once_indexed(monkeypatch):
    """Simulate a rebuilt schemes index (BGE-M3 is not needed for lexical search)."""
    from rag.document_loader import load_documents
    from services import rag_service

    _, metadata = rag_service.load_index("schemes")
    rows = list(metadata)
    for doc in load_documents():
        if doc["document_id"] in {"07_pm_kusum_solar_pumps", "08_national_horticulture_mission"}:
            rows.append({
                "chunk_id": f"scheme_{doc['document_id']}_0000", "document_id": doc["document_id"],
                "category": "scheme", "topic": doc["topic"], "section": None,
                "source_name": doc["source"]["org"], "source_url": doc["source"]["url"],
                "language": "English", "file_path": doc["relative_path"], "chunk_index": 0,
                "text": doc["text"].split("## Source note")[0],
            })
    monkeypatch.setattr(rag_service, "load_index", lambda name: (None, rows))
    assert rag_service.retrieve("PM-KUSUM solar pump subsidy", "schemes")[0]["document_id"] == "07_pm_kusum_solar_pumps"
    assert rag_service.retrieve("National Horticulture Mission polyhouse Karnataka", "schemes")[0]["document_id"] in {
        "08_national_horticulture_mission", "01_midh_protected_cultivation"}


def test_new_scheme_documents_have_kannada_text_and_sources():
    from services.localization import localize_rag_item
    for doc_id in ("07_pm_kusum_solar_pumps", "08_national_horticulture_mission"):
        item = localize_rag_item({"document_id": doc_id, "topic": "x", "text": "y"}, "Kannada")
        assert not any(c.isascii() and c.isalpha() for c in item["topic"].replace("PM", "").replace("NHM", "").replace("KUSUM", ""))
        assert len(item["text"]) > 200
    sources = json.loads((ROOT / "namma_krushi_master_kb/metadata/sources.json").read_text(encoding="utf-8"))["sources"]
    assert "S35" in {s["id"] for s in sources}


def test_light_status_uses_the_labeling_policy():
    from services.greenhouse_service import explain
    base = dict(temperature=24, humidity=75, soil_moisture=75, co2=600)
    status = lambda light: dict(explain({**base, "light_intensity": light})[0])["Light"]
    assert status(0) == "suitable" and status(500) == "suitable" and status(900) == "suitable"
    assert status(30) == "needs adjustment" and status(1000) == "needs adjustment"
    assert status(1500) == "outside the recommended range"


def test_greenhouse_model_is_cached():
    from services import greenhouse_service as g
    assert g.load_model() is g.load_model()


def test_rag_config_root_is_not_hard_coded_to_another_machine():
    from rag import config
    assert config.PROJECT_ROOT == ROOT and (config.KB_ROOT / "schemes").is_dir()


def test_schemes_page_never_shows_builder_notes():
    app = AppTest.from_function(_schemes_page, default_timeout=60).run()
    text = " ".join(m.value for m in app.markdown).lower()
    for internal in ("chatbot", "source note", "response pattern", "source ids"):
        assert internal not in text
    assert "pm-kisan" in text and "kisan credit card" in text


def test_every_indexed_scheme_can_be_found_by_search():
    from services.rag_service import retrieve
    expected = {
        "PM-KISAN income support eligibility": "02_pm_kisan",
        "Kisan credit card loan": "03_kisan_credit_card",
        "crop insurance PMFBY": "04_pmfby_crop_insurance",
        "agriculture infrastructure fund": "05_agriculture_infrastructure_fund",
        "polyhouse subsidy MIDH": "01_midh_protected_cultivation",
    }
    for query, document_id in expected.items():
        results = retrieve(query, "schemes", top_k=3)
        assert results and results[0]["document_id"] == document_id, query
        assert all("chatbot" not in r["text"].lower() and "source note" not in r["text"].lower() for r in results)


# --- more schemes, topics and the official-site fetcher ---------------------

NEW_SCHEMES = {
    "drip irrigation subsidy": "09_pmksy_per_drop_more_crop",
    "interest subvention KCC": "10_modified_interest_subvention",
    "pension for farmers": "11_pm_kisan_maandhan_pension",
    "soil testing card": "12_soil_health_card",
    "sell tomato online mandi": "13_enam_online_market",
    "tractor machinery subsidy": "14_smam_farm_mechanization",
    "tomato sauce processing subsidy": "15_pmfme_food_processing",
    "farmer producer organisation": "16_fpo_formation_promotion",
    "PM-KUSUM solar pump": "07_pm_kusum_solar_pumps",
    "National Horticulture Mission": "08_national_horticulture_mission",
}


@pytest.mark.parametrize("query,document_id", NEW_SCHEMES.items())
def test_new_schemes_are_found_without_rebuilding_the_index(query, document_id):
    from services.rag_service import retrieve
    results = retrieve(query, "schemes", top_k=1)
    assert results and results[0]["document_id"] == document_id
    assert results[0]["source_url"].startswith("https://")


def test_scheme_question_in_chat_uses_the_new_schemes():
    from services.advisory_service import answer_farmer_question
    response, results, _, _ = answer_farmer_question("What pension scheme is there for small farmers?", "English", "")
    assert any(r["document_id"] == "11_pm_kisan_maandhan_pension" for r in results)
    assert "PM-KMY" in response


def test_every_scheme_has_a_topic_and_kannada_text():
    from views.schemes import CATEGORIES, SCHEME_CATEGORY, SCHEMES_LIST
    from services.localization import _SCHEME_KN
    ids = {s["id"] for s in SCHEMES_LIST}
    assert len(ids) == 31 and ids == set(SCHEME_CATEGORY) and set(SCHEME_CATEGORY.values()) <= set(CATEGORIES)
    assert ids <= set(_SCHEME_KN)


def test_topic_filter_limits_the_scheme_list():
    app = AppTest.from_function(_schemes_page, default_timeout=60).run()
    app.selectbox(key="schemes_category_widget").select("water").run()
    assert not app.exception
    assert sorted(o for o in app.selectbox(key="schemes_dropdown_widget").options) != []
    titles = [s.value for s in app.subheader][1:]     # first subheader is the "View All" heading
    assert len(titles) == 2 and any("Per Drop" in t for t in titles) and any("PM-KUSUM" in t for t in titles)


# --- nursery, greenhouse, tomato price support and state schemes -------------

MORE_SCHEMES = {
    "hi-tech nursery subsidy": "17_midh_nursery_planting_material",
    "NHB greenhouse project subsidy 56 lakh": "18_nhb_protected_cultivation_projects",
    "cold storage subsidy": "19_cold_storage_post_harvest_subsidy",
    "operation greens tomato transport subsidy": "20_operation_greens",
    "tomato price crash market intervention": "21_market_intervention_scheme",
    "integrated cold chain": "22_pm_kisan_sampada_cold_chain",
    "RKVY agri startup": "23_rkvy_raftaar",
    "organic farming PKVY": "24_organic_natural_farming",
    "polyhouse subsidy Karnataka": "25_karnataka_protected_cultivation",
    "Tamil Nadu polyhouse subsidy": "26_tamil_nadu_horticulture_subsidies",
    "polyhouse subsidy Maharashtra MahaDBT": "27_maharashtra_polyhouse_pocra",
    "Gujarat iKhedut": "28_gujarat_ikhedut_horticulture",
    "Rajasthan polyhouse subsidy": "29_rajasthan_polyhouse_subsidy",
    "Haryana polyhouse subsidy": "30_north_india_haryana_punjab_himachal",
    "Telangana polyhouse subsidy": "31_telangana_andhra_horticulture",
}


@pytest.mark.parametrize("query,document_id", MORE_SCHEMES.items())
def test_nursery_greenhouse_tomato_and_state_schemes_are_searchable(query, document_id):
    from services.rag_service import retrieve
    results = retrieve(query, "schemes", top_k=1)
    assert results and results[0]["document_id"] == document_id and results[0]["source_url"].startswith("https://")


def test_generic_polyhouse_question_prefers_national_schemes_over_state_articles():
    from services.rag_service import retrieve
    top = [r["document_id"] for r in retrieve("polyhouse subsidy", "schemes", top_k=3)]
    assert top[0] == "01_midh_protected_cultivation" and not any(t[:2] in {"25", "26", "27", "28", "29", "30", "31"} for t in top[:2])


def test_every_topic_has_schemes_and_a_label():
    import json
    from views.schemes import CATEGORIES, SCHEME_CATEGORY
    for lang in ("en", "kn"):
        strings = json.loads((ROOT / "translation" / f"ui_strings_{lang}.json").read_text(encoding="utf-8"))
        assert all(strings.get(f"cat_{c}") for c in CATEGORIES)
    assert set(SCHEME_CATEGORY.values()) == set(CATEGORIES)


def test_state_topic_lists_all_state_articles_without_builder_notes():
    app = AppTest.from_function(_schemes_page, default_timeout=60).run()
    app.selectbox(key="schemes_category_widget").select("states").run()
    assert not app.exception
    titles = [s.value for s in app.subheader][1:]
    assert len(titles) == 7 and any("Karnataka" in t for t in titles) and any("Tamil Nadu" in t for t in titles)
    page = " ".join(m.value for m in app.markdown).lower()
    assert "chatbot" not in page and "source note" not in page
