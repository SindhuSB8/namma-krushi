"""Government Schemes view with dropdown selection, Kannada typing, voice dictation, and neural speech."""
import logging
from services.rag_service import retrieve, sources, load_index
from services.text_cleaning import clean_farmer_text
from services.localization import localize_rag_item, localize_rag_items
from services.translation_service import translate_rag_query_to_english
from services.speech_service import transcribe
from services.tts_service import browser_speak_component
from components.browser_voice import voice_input
from components.kannada_keyboard import keyboard
from components.source_cards import show_sources

logger = logging.getLogger(__name__)

# Canonical scheme definitions mapped to document IDs
SCHEMES_LIST = [
    {
        "id": "01_midh_protected_cultivation",
        "title_kn": "🏛️ ಎಂಐಡಿಎಚ್ ಮತ್ತು ಪಾಲಿಹೌಸ್ ಸಹಾಯಧನ (MIDH & Polyhouse)",
        "title_en": "🏛️ MIDH & Protected Cultivation (Polyhouse Subsidy)",
        "badge_kn": "ಸಹಾಯಧನ & ಪಾಲಿಹೌಸ್",
        "badge_en": "Subsidy & Polyhouse",
    },
    {
        "id": "02_pm_kisan",
        "title_kn": "🌾 ಪಿಎಂ-ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ (PM-KISAN ₹6,000/ವರ್ಷ)",
        "title_en": "🌾 PM-KISAN Income Support (₹6,000/year)",
        "badge_kn": "ಆದಾಯ ಬೆಂಬಲ",
        "badge_en": "Income Support",
    },
    {
        "id": "03_kisan_credit_card",
        "title_kn": "💳 ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ (KCC ಕೃಷಿ ಸಾಲ)",
        "title_en": "💳 Kisan Credit Card (KCC Cultivation Loan)",
        "badge_kn": "ಕೃಷಿ ಸಾಲ",
        "badge_en": "Credit & Loan",
    },
    {
        "id": "04_pmfby_crop_insurance",
        "title_kn": "🛡️ ಪ್ರಧಾನಮಂತ್ರಿ ಫಸಲ್ ಬಿಮಾ ಯೋಜನೆ (PMFBY ಬೆಳೆ ವಿಮೆ)",
        "title_en": "🛡️ PMFBY Crop Insurance (Crop Damage Cover)",
        "badge_kn": "ಬೆಳೆ ವಿಮೆ",
        "badge_en": "Crop Insurance",
    },
    {
        "id": "05_agriculture_infrastructure_fund",
        "title_kn": "🏗️ ಕೃಷಿ ಮೂಲಸೌಕರ್ಯ ನಿಧಿ (AIF ಗೋದಾಮು & ಶೀತಲ ಶೇಖರಣೆ)",
        "title_en": "🏗️ Agriculture Infrastructure Fund (Storage & Cold Chain)",
        "badge_kn": "ಮೂಲಸೌಕರ್ಯ",
        "badge_en": "Infrastructure",
    },
    {
        "id": "07_pm_kusum_solar_pumps",
        "title_kn": "☀️ ಪಿಎಂ-ಕುಸುಮ್ ಸೌರ ಪಂಪ್ (PM-KUSUM)",
        "title_en": "☀️ PM-KUSUM Solar Pumps (Irrigation Subsidy)",
        "badge_kn": "ಸೌರ ಪಂಪ್",
        "badge_en": "Solar Pumps",
    },
    {
        "id": "08_national_horticulture_mission",
        "title_kn": "🍅 ರಾಷ್ಟ್ರೀಯ ತೋಟಗಾರಿಕಾ ಮಿಷನ್ (NHM)",
        "title_en": "🍅 National Horticulture Mission (NHM)",
        "badge_kn": "ತೋಟಗಾರಿಕಾ ಮಿಷನ್",
        "badge_en": "Horticulture Mission",
    },
    {
        "id": "06_karnataka_scheme_discovery",
        "title_kn": "🚜 ಕರ್ನಾಟಕ ರಾಜ್ಯ ಯೋಜನೆಗಳು / ರೈತ ಮಿತ್ರ (Karnataka Schemes)",
        "title_en": "🚜 Karnataka State Agriculture & Horticulture Schemes",
        "badge_kn": "ರಾಜ್ಯ ಯೋಜನೆಗಳು",
        "badge_en": "State Schemes",
    },
    {"id": "09_pmksy_per_drop_more_crop", "title_kn": "💧 ಪ್ರತಿ ಹನಿಗೆ ಹೆಚ್ಚು ಬೆಳೆ (ಹನಿ ನೀರಾವರಿ ಸಹಾಯಧನ)", "title_en": "💧 Per Drop More Crop (Drip Irrigation Subsidy)", "badge_kn": "ಹನಿ ನೀರಾವರಿ", "badge_en": "Drip Irrigation"},
    {"id": "10_modified_interest_subvention", "title_kn": "🏦 ಕೆಸಿಸಿ ಬಡ್ಡಿ ಸಹಾಯಧನ (ಎಂಐಎಸ್‌ಎಸ್)", "title_en": "🏦 Interest Subvention on KCC Loans (MISS)", "badge_kn": "ಬಡ್ಡಿ ಸಹಾಯಧನ", "badge_en": "Interest Benefit"},
    {"id": "11_pm_kisan_maandhan_pension", "title_kn": "👴 ಪಿಎಂ ಕಿಸಾನ್ ಮಾನ್‌ಧನ್ (ರೈತ ಪಿಂಚಣಿ)", "title_en": "👴 PM Kisan Maandhan (Farmer Pension)", "badge_kn": "ಪಿಂಚಣಿ", "badge_en": "Pension"},
    {"id": "12_soil_health_card", "title_kn": "🧪 ಮಣ್ಣಿನ ಆರೋಗ್ಯ ಕಾರ್ಡ್", "title_en": "🧪 Soil Health Card", "badge_kn": "ಮಣ್ಣು ಪರೀಕ್ಷೆ", "badge_en": "Soil Testing"},
    {"id": "13_enam_online_market", "title_kn": "📱 ಇ-ನಾಮ್ ಆನ್‌ಲೈನ್ ಮಾರುಕಟ್ಟೆ", "title_en": "📱 e-NAM Online Market", "badge_kn": "ಇ-ನಾಮ್", "badge_en": "e-NAM"},
    {"id": "14_smam_farm_mechanization", "title_kn": "🚜 ಕೃಷಿ ಯಾಂತ್ರೀಕರಣ ಸಹಾಯಧನ (ಎಸ್‌ಎಂಎಎಂ)", "title_en": "🚜 Farm Mechanization Subsidy (SMAM)", "badge_kn": "ಯಂತ್ರೋಪಕರಣ", "badge_en": "Machinery"},
    {"id": "15_pmfme_food_processing", "title_kn": "🍅 ಆಹಾರ ಸಂಸ್ಕರಣಾ ಸಹಾಯಧನ (ಪಿಎಂಎಫ್‌ಎಂಇ)", "title_en": "🍅 Food Processing Subsidy (PMFME)", "badge_kn": "ಸಂಸ್ಕರಣೆ", "badge_en": "Processing"},
    {"id": "16_fpo_formation_promotion", "title_kn": "🤝 ರೈತ ಉತ್ಪಾದಕ ಸಂಸ್ಥೆ (ಎಫ್‌ಪಿಒ) ಯೋಜನೆ", "title_en": "🤝 Farmer Producer Organisation (FPO) Scheme", "badge_kn": "ಎಫ್‌ಪಿಒ", "badge_en": "FPO"},
    {"id": "17_midh_nursery_planting_material", "title_kn": "🌱 ನರ್ಸರಿ ಮತ್ತು ನಾಟಿ ವಸ್ತು ಸಹಾಯಧನ", "title_en": "🌱 Nursery & Planting Material Subsidy (MIDH)", "badge_kn": "ನರ್ಸರಿ", "badge_en": "Nursery"},
    {"id": "18_nhb_protected_cultivation_projects", "title_kn": "🏗️ ಎನ್‌ಎಚ್‌ಬಿ ಹಸಿರುಮನೆ ಯೋಜನೆಗಳು", "title_en": "🏗️ NHB Greenhouse / Protected Cultivation Projects", "badge_kn": "ಎನ್‌ಎಚ್‌ಬಿ ಹಸಿರುಮನೆ", "badge_en": "NHB Greenhouse"},
    {"id": "19_cold_storage_post_harvest_subsidy", "title_kn": "❄️ ಶೀತಲ ಸಂಗ್ರಹ ಮತ್ತು ಕೊಯ್ಲಿನ ನಂತರದ ಸಹಾಯಧನ", "title_en": "❄️ Cold Storage & Post-Harvest Subsidy", "badge_kn": "ಶೀತಲ ಸಂಗ್ರಹ", "badge_en": "Cold Storage"},
    {"id": "20_operation_greens", "title_kn": "🍅 ಆಪರೇಷನ್ ಗ್ರೀನ್ಸ್ (ಟೊಮ್ಯಾಟೊ ಸಾಗಣೆ, ಸಂಗ್ರಹ)", "title_en": "🍅 Operation Greens (Tomato Transport & Storage)", "badge_kn": "ಆಪರೇಷನ್ ಗ್ರೀನ್ಸ್", "badge_en": "Operation Greens"},
    {"id": "21_market_intervention_scheme", "title_kn": "📉 ಮಾರುಕಟ್ಟೆ ಹಸ್ತಕ್ಷೇಪ ಯೋಜನೆ (ಬೆಲೆ ಬೆಂಬಲ)", "title_en": "📉 Market Intervention Scheme (Tomato Price Support)", "badge_kn": "ಬೆಲೆ ಬೆಂಬಲ", "badge_en": "Price Support"},
    {"id": "22_pm_kisan_sampada_cold_chain", "title_kn": "🚚 ಪಿಎಂ ಕಿಸಾನ್ ಸಂಪದ (ಶೀತಲ ಸರಪಳಿ)", "title_en": "🚚 PM Kisan SAMPADA (Cold Chain)", "badge_kn": "ಶೀತಲ ಸರಪಳಿ", "badge_en": "Cold Chain"},
    {"id": "23_rkvy_raftaar", "title_kn": "🏛️ ರಾಷ್ಟ್ರೀಯ ಕೃಷಿ ವಿಕಾಸ ಯೋಜನೆ - ರಫ್ತಾರ್", "title_en": "🏛️ RKVY-RAFTAAR (State Agri Development)", "badge_kn": "ಆರ್‌ಕೆವಿವೈ", "badge_en": "RKVY"},
    {"id": "24_organic_natural_farming", "title_kn": "🌿 ಸಾವಯವ ಮತ್ತು ನೈಸರ್ಗಿಕ ಕೃಷಿ", "title_en": "🌿 Organic & Natural Farming (PKVY, NMNF)", "badge_kn": "ಸಾವಯವ ಕೃಷಿ", "badge_en": "Organic Farming"},
    {"id": "25_karnataka_protected_cultivation", "title_kn": "📍 ಕರ್ನಾಟಕ: ಪಾಲಿಹೌಸ್ ಮತ್ತು ಹಸಿರುಮನೆ ಸಹಾಯಧನ", "title_en": "📍 Karnataka: Polyhouse & Greenhouse Subsidy", "badge_kn": "ಕರ್ನಾಟಕ", "badge_en": "Karnataka"},
    {"id": "26_tamil_nadu_horticulture_subsidies", "title_kn": "📍 ತಮಿಳುನಾಡು: ತೋಟಗಾರಿಕೆ ಮತ್ತು ಪಾಲಿಹೌಸ್ ಸಹಾಯಧನ", "title_en": "📍 Tamil Nadu: Horticulture & Polyhouse Subsidies", "badge_kn": "ತಮಿಳುನಾಡು", "badge_en": "Tamil Nadu"},
    {"id": "27_maharashtra_polyhouse_pocra", "title_kn": "📍 ಮಹಾರಾಷ್ಟ್ರ: ಮಹಾಡಿಬಿಟಿ ಮತ್ತು ಪೋಕ್ರಾ", "title_en": "📍 Maharashtra: MahaDBT & PoCRA", "badge_kn": "ಮಹಾರಾಷ್ಟ್ರ", "badge_en": "Maharashtra"},
    {"id": "28_gujarat_ikhedut_horticulture", "title_kn": "📍 ಗುಜರಾತ್: ಐಖೇದೂತ್ ತೋಟಗಾರಿಕೆ ಸಹಾಯಧನ", "title_en": "📍 Gujarat: iKhedut Horticulture Subsidy", "badge_kn": "ಗುಜರಾತ್", "badge_en": "Gujarat"},
    {"id": "29_rajasthan_polyhouse_subsidy", "title_kn": "📍 ರಾಜಸ್ಥಾನ: ಪಾಲಿಹೌಸ್ ಸಹಾಯಧನ", "title_en": "📍 Rajasthan: Polyhouse Subsidy", "badge_kn": "ರಾಜಸ್ಥಾನ", "badge_en": "Rajasthan"},
    {"id": "30_north_india_haryana_punjab_himachal", "title_kn": "📍 ಹರಿಯಾಣ, ಪಂಜಾಬ್ ಮತ್ತು ಹಿಮಾಚಲ ಪ್ರದೇಶ", "title_en": "📍 Haryana, Punjab & Himachal Pradesh", "badge_kn": "ಹರಿಯಾಣ·ಪಂಜಾಬ್·ಹಿ.ಪ್ರ.", "badge_en": "Haryana·Punjab·HP"},
    {"id": "31_telangana_andhra_horticulture", "title_kn": "📍 ತೆಲಂಗಾಣ ಮತ್ತು ಆಂಧ್ರಪ್ರದೇಶ", "title_en": "📍 Telangana & Andhra Pradesh", "badge_kn": "ತೆಲಂಗಾಣ·ಆಂ.ಪ್ರ.", "badge_en": "Telangana·AP"},
]

# Topic groups used by the category filter (every scheme belongs to exactly one).
SCHEME_CATEGORY = {
    "01_midh_protected_cultivation": "greenhouse",
    "08_national_horticulture_mission": "greenhouse",
    "05_agriculture_infrastructure_fund": "greenhouse",
    "07_pm_kusum_solar_pumps": "water",
    "09_pmksy_per_drop_more_crop": "water",
    "03_kisan_credit_card": "credit",
    "10_modified_interest_subvention": "credit",
    "04_pmfby_crop_insurance": "credit",
    "02_pm_kisan": "income",
    "11_pm_kisan_maandhan_pension": "income",
    "06_karnataka_scheme_discovery": "income",
    "12_soil_health_card": "inputs",
    "14_smam_farm_mechanization": "inputs",
    "13_enam_online_market": "market",
    "16_fpo_formation_promotion": "market",
    "15_pmfme_food_processing": "postharvest",
    "17_midh_nursery_planting_material": "greenhouse",
    "18_nhb_protected_cultivation_projects": "greenhouse",
    "19_cold_storage_post_harvest_subsidy": "postharvest",
    "20_operation_greens": "market",
    "21_market_intervention_scheme": "market",
    "22_pm_kisan_sampada_cold_chain": "postharvest",
    "23_rkvy_raftaar": "inputs",
    "24_organic_natural_farming": "inputs",
    "25_karnataka_protected_cultivation": "states",
    "26_tamil_nadu_horticulture_subsidies": "states",
    "27_maharashtra_polyhouse_pocra": "states",
    "28_gujarat_ikhedut_horticulture": "states",
    "29_rajasthan_polyhouse_subsidy": "states",
    "30_north_india_haryana_punjab_himachal": "states",
    "31_telangana_andhra_horticulture": "states",
}
CATEGORIES = ["greenhouse", "water", "credit", "income", "postharvest", "market", "inputs", "states"]


def _scheme_groups():
    """Return {document_id: [chunks in order]} so every section of a scheme
    (benefits, eligibility, how to apply) is shown, not just the first chunk."""
    try:
        _, metadata = load_index("schemes")
    except Exception as exc:
        logger.warning("Could not load schemes metadata directly: %s", exc)
        return {}
    groups = {}
    for m in sorted(metadata, key=lambda m: (m.get("document_id") or "", m.get("chunk_index") or 0)):
        if m.get("document_id"):
            groups.setdefault(m["document_id"], []).append(m)
    return groups


def _merged_item(chunks):
    """One display item for a whole scheme document."""
    parts = [clean_farmer_text(c.get("text", ""), style_headings=True) for c in chunks]
    return {**chunks[0], "text": "\n\n".join(part for part in parts if part)}


def _pick_scheme(scheme_id):
    # Runs as a button callback, i.e. before the selectbox is re-instantiated,
    # so it may legally set the selectbox's own session-state key.
    import streamlit as st
    st.session_state["schemes_dropdown_widget"] = scheme_id


def _render_scheme_card(st, item, lang, t):
    """Render a clean card with description, read-aloud, and a link to the official source."""
    with st.container(border=True):
        body = clean_farmer_text(item.get("text", ""), style_headings=True)
        st.subheader(item.get("topic") or t("government_scheme"))
        st.write(body)

        spoken_content = f"{item.get('topic', '')}. {body.replace('**', '')[:600]}"
        browser_speak_component(
            spoken_content,
            lang,
            {
                "controls": t("read_aloud_controls"),
                "listen": t("listen"),
                "pause": t("pause"),
                "resume": t("resume"),
                "stop": t("stop_reading"),
                "paused": t("speech_paused"),
                "unsupported": t("speech_unsupported"),
                "unavailable": t("speech_kannada_voice_unavailable"),
            },
            autoplay=False,
        )

        source_url = item.get("source_url")
        source_name = item.get("source_name") or t("official_source")
        if source_url:
            st.markdown(f"🔗 **{t('official_source')}:** [{source_name}]({source_url})")


def render(st, t):
    lang = st.session_state.get("language", "English")

    st.markdown(f"""
    <div class="hero">
        <div class="eyebrow">Karnataka · Government of India</div>
        <h2>{t('schemes')}</h2>
        <p>{t('schemes_intro')}</p>
    </div>
    """, unsafe_allow_html=True)


    # State initialization
    if "schemes_dropdown" not in st.session_state:
        st.session_state.schemes_dropdown = "all"
    if "schemes_query" not in st.session_state:
        st.session_state.schemes_query = ""

    groups = _scheme_groups()
    # Only offer schemes that are actually in the search index (new knowledge
    # documents appear after scripts/build_faiss.py is re-run).
    available = [x for x in SCHEMES_LIST if x["id"] in groups] or SCHEMES_LIST
    category_labels = {"all": t("cat_all"), **{c: t(f"cat_{c}") for c in CATEGORIES}}
    category = st.selectbox(t("scheme_category"), ["all", *CATEGORIES], format_func=category_labels.get, key="schemes_category_widget")
    if category != "all":
        available = [x for x in available if SCHEME_CATEGORY.get(x["id"]) == category]
    all_label, custom_label = t("all_schemes"), t("custom_search")
    labels = {"all": all_label, "custom": custom_label}
    for x in available:
        labels[x["id"]] = x["title_kn"] if lang == "Kannada" else x["title_en"]
    option_ids = ["all", *[x["id"] for x in available], "custom"]
    # Option ids are language-independent, so the selection survives a
    # language switch and quick buttons can set it directly.
    if st.session_state.get("schemes_dropdown_widget") not in option_ids:
        st.session_state["schemes_dropdown_widget"] = "all"

    selected_id = st.selectbox(
        t("select_scheme"),
        options=option_ids,
        format_func=labels.get,
        key="schemes_dropdown_widget",
    )

    # One-tap buttons for the schemes in the chosen topic (4 per row so they stay readable on phones)
    for start in range(0, len(available) if category != "all" else 0, 4):
        row = available[start:start + 4]
        for col, x in zip(st.columns(len(row)), row):
            badge = x["badge_kn"] if lang == "Kannada" else x["badge_en"]
            col.button(badge, key=f"quick_btn_{x['id']}", width="stretch",
                       on_click=_pick_scheme, args=(x["id"],))

    st.divider()

    if selected_id == "all":
        st.subheader(all_label)
        if groups:
            for doc_id in (x["id"] for x in available):
                if doc_id in groups:
                    _render_scheme_card(st, localize_rag_item(_merged_item(groups[doc_id]), lang), lang, t)
        else:
            for item in localize_rag_items(retrieve("scheme subsidy agriculture", "schemes"), lang):
                _render_scheme_card(st, item, lang, t)

    elif selected_id in groups:
        _render_scheme_card(st, localize_rag_item(_merged_item(groups[selected_id]), lang), lang, t)

    elif selected_id != "custom":
        for item in localize_rag_items(retrieve(selected_id, "schemes")[:1], lang):
            _render_scheme_card(st, item, lang, t)

    else:
        # Custom Search Mode (with Keyboard, Microphone, Audio recording)
        st.subheader(custom_label)

        # Keyboard toggle
        show_keyboard = st.toggle(t("kannada_keyboard"), value=False, key="schemes_kannada_keyboard")

        # Browser live voice dictation
        voice_event = voice_input(
            lang,
            t("voice_browser_start"),
            t("voice_browser_stop"),
            t("voice_browser_unsupported"),
            t("voice_listening"),
            t("voice_dictation_error"),
            key=f"schemes_browser_voice_{lang}",
            kannada_voice_unavailable_label=t("speech_kannada_voice_unavailable"),
        )
        if isinstance(voice_event, dict):
            nonce = voice_event.get("nonce")
            if nonce and nonce != st.session_state.get("last_schemes_voice_nonce"):
                st.session_state.last_schemes_voice_nonce = nonce
                if voice_event.get("status") == "result" and voice_event.get("transcript"):
                    transcript = voice_event["transcript"].strip()
                    st.session_state.schemes_query = transcript
                    st.success(t("voice_dictation_ready"))
                    st.rerun()
                elif voice_event.get("status") == "error":
                    st.warning(
                        t("voice_browser_unsupported")
                        if voice_event.get("error") == "unsupported"
                        else t("voice_dictation_error")
                    )

        # Audio file recording fallback
        with st.expander(t("audio_fallback")):
            audio = st.audio_input(f"🎙️ {t('dictate_question')}", key="schemes_audio_input") if hasattr(st, "audio_input") else None
            if audio and st.button(t("transcribe_recording"), key="schemes_transcribe_btn"):
                with st.spinner(t("voice_processing")):
                    transcript, error_key = transcribe(audio.getvalue(), lang)
                if error_key:
                    st.warning(t(error_key))
                elif transcript:
                    st.session_state.schemes_query = transcript
                    st.success(t("voice_dictation_ready"))
                    st.rerun()

        # Virtual Kannada keyboard
        if show_keyboard:
            keyboard(st, t, state_key="schemes_query", key_prefix="schemes")

        # Search box & button
        query = st.text_input(
            t("search_schemes"),
            key="schemes_query",
            placeholder=t("search_schemes_placeholder"),
        )
        search_clicked = st.button(t("search_schemes"), type="primary", key="schemes_search_btn")

        if query and query.strip():
            try:
                retrieval_query = query.strip()
                if lang == "Kannada":
                    retrieval_query, translated = translate_rag_query_to_english(query.strip())
                    if not translated:
                        st.info(t("translation_retry"))
                        return

                results = retrieve(retrieval_query, "schemes")
                if not results:
                    st.info(t("no_schemes_found"))
                    return

                display_results = localize_rag_items(results, lang)
                for item in display_results:
                    _render_scheme_card(st, item, lang, t)

                show_sources(st, sources(results), t, lang)

            except Exception as exc:
                logger.exception("Government schemes search failed: %s", exc)
                st.error(t("scheme_search_unavailable"))
