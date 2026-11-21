from database.db import fetch_all
from services.greenhouse_service import explain
from services.localization import localize_condition, localize_feature, localize_status


def _snapshot_cards(analysis, language, t):
    """Build the home-page KPIs from one persisted greenhouse analysis."""
    values = {
        "temperature": analysis["temperature"],
        "humidity": analysis["humidity"],
        "soil_moisture": analysis["soil_moisture"],
        "light_intensity": analysis["light_intensity"],
        "co2": analysis["co2"],
    }
    checks, _ = explain(values)
    statuses = dict(checks)
    cards = (
        ("temperature", "Temperature", values["temperature"], "°C"),
        ("humidity", "Humidity", values["humidity"], "%"),
        ("soil_moisture", "Root-zone moisture", values["soil_moisture"], "%"),  # check names come from the model service
    )
    result = []
    for key, check_name, value, unit in cards:
        status = statuses[check_name]
        is_ok = status == "suitable"
        status_text = (
            localize_status(status, language)
            if language == "Kannada"
            else (t("fa_within_range") if is_ok else t("fa_needs_attention"))
        )
        result.append({
            "label": localize_feature(key, language),
            "value": f"{float(value):g}{unit}",
            "status": status_text,
            "badge_class": "badge-ok" if is_ok else "badge-warn",
        })
    return result

def render(st, t):
    lang = st.session_state.get("language", "English")
    user_name = st.session_state.get("name", "Farmer")

    # Hero Banner
    st.markdown(f"""
    <div class="hero">
        <div class="eyebrow">{t('dashboard_eyebrow')}</div>
        <h2>{t('welcome_message').format(name=user_name)}</h2>
        <p>{t('dashboard_intro')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Home-page shortcuts mirror the five-page frontend. Disease detection and
    # greenhouse analysis now live inside the integrated AI Farming Assistant.
    tiles_data = [
        ("green", "🌱", "advisory", t("assistant_title"), t("fa_tile_assistant")),
        ("blue", "🏛", "schemes", t("schemes"), t("schemes_tile_description")),
        ("red", "◷", "history", t("history"), t("fa_tile_history")),
        ("green", "○", "profile", t("profile"), t("fa_tile_profile")),
    ]

    for row_idx in range(0, len(tiles_data), 2):
        cols = st.columns(2)
        for col, (color, icon, page_key, title, desc) in zip(cols, tiles_data[row_idx:row_idx+2]):
            with col:
                st.markdown(f"""
                <div class="nk-tile" style="height: 168px; display: flex; flex-direction: column; justify-content: flex-start; margin-bottom: 8px; padding: 18px;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                        <div class="tileicon {color}" style="margin-bottom:0; width:36px; height:36px; font-size:18px;">{icon}</div>
                        <div style="font-family:'Fraunces',serif; font-size:15px; font-weight:700; color:var(--ink); line-height:1.2;">{title}</div>
                    </div>
                    <div style="color:var(--muted); font-size:12px; line-height:1.45; overflow:hidden;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"{t('view')} →", key=f"dash_go_{page_key}", width="stretch"):
                    st.session_state.current_page = page_key
                    st.rerun()

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # Greenhouse Snapshot KPIs
    st.markdown(f"<h3 style='font-size:18px; margin-bottom:12px;'>{t('recent_greenhouse')}</h3>", unsafe_allow_html=True)
    
    # Fetch once so the snapshot and history always represent the same data.
    # analysis_id breaks ties when multiple checks are saved in one second.
    analyses = fetch_all(
        "SELECT analysis_id,temperature,humidity,soil_moisture,light_intensity,co2,"
        "prediction,created_at FROM greenhouse_analyses WHERE user_id=? "
        "ORDER BY created_at DESC,analysis_id DESC LIMIT 5",
        (st.session_state.user_id,),
    )
    if analyses:
        for column, card in zip(st.columns(3), _snapshot_cards(analyses[0], lang, t)):
            with column:
                st.markdown(f"""
                <div class="nk-card" style="padding:16px;">
                    <div style="color:var(--muted); font-size:12px;">{card['label']}</div>
                    <div style="font-family:'Fraunces',serif; font-size:24px; font-weight:700; margin:4px 0;">{card['value']}</div>
                    <span class="{card['badge_class']}">{card['status']}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info(t("no_greenhouse_readings"))

    # Recent Analyses History Table
    if analyses:
        st.markdown(f"""
        <div class="nk-card">
            <h3 style="font-size:16px; margin-bottom:12px;">{t('recent_greenhouse_records')}</h3>
        """, unsafe_allow_html=True)
        display_analyses = [
            {
                t("condition"): localize_condition(row["prediction"], lang),
                t("date_time"): row["created_at"]
            }
            for row in analyses
        ]
        st.dataframe(display_analyses, hide_index=True, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
