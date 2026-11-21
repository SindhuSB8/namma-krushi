"""History & Reports: everything the farmer has analysed or asked, in one place."""
import ast
import csv
import io
import re

from config import ROOT
from database.db import fetch_all, fetch_chat_messages, fetch_chat_sessions
from services.disease_actions import disease_action_plan
from services.localization import localize_chat_message, localize_chat_title, localize_condition, localize_disease, localize_xai


def _explanation(raw, language):
    """Stored as "Checks: [...]; Rec: ..." - show it as readable, localized text."""
    match = re.match(r"Checks:\s*(\[.*\]);\s*Rec:\s*(.*)$", raw or "", re.S)
    if match:
        try:
            return localize_xai(ast.literal_eval(match.group(1)), match.group(2), language)
        except (ValueError, SyntaxError):
            pass
    return raw


def _csv(rows, columns):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[column] for column in columns])
    return buffer.getvalue().encode("utf-8-sig")


def render(st, t):
    language = st.session_state.get("language", "English")
    user_id = st.session_state.user_id
    st.markdown(f"""
    <div class="hero"><div class="eyebrow">{t('fa_hist_eyebrow')}</div>
    <h2>{t('history')}</h2>
    <p>{t('fa_hist_intro')}</p></div>
    """, unsafe_allow_html=True)
    disease_tab, greenhouse_tab, chat_tab = st.tabs([t("tab_disease"), t("tab_greenhouse"), t("tab_chats")])

    with disease_tab:
        rows = fetch_all("SELECT * FROM disease_predictions WHERE user_id=? ORDER BY created_at DESC, prediction_id DESC", (user_id,))
        if not rows:
            st.info(t("no_disease_history"))
        else:
            st.download_button(t("fa_download_disease"), _csv(rows, ["disease", "confidence", "created_at"]),
                               "disease_results.csv", "text/csv", key="dl_disease")
        for row in rows:
            cols = st.columns([1, 4])
            image_path = ROOT / row["image_path"] if row["image_path"] else None
            if image_path and image_path.exists():
                cols[0].image(str(image_path), width=100)
            cols[1].markdown(f"**{localize_disease(row['disease'], language)}**  \n{t('confidence')}: {row['confidence']:.1%} · {row['created_at']}")
            plan = disease_action_plan(row["disease"], language)
            if plan["actions"]:
                with st.expander(t("hist_what_to_do")):
                    if plan["about"]:
                        st.markdown(f"**{t('hist_about')}**  \n{plan['about']}")
                    st.markdown(plan["actions"])
                    st.caption(t("hist_confirm_note"))
            st.divider()

    with greenhouse_tab:
        rows = fetch_all("SELECT * FROM greenhouse_analyses WHERE user_id=? ORDER BY created_at DESC, analysis_id DESC", (user_id,))
        if not rows:
            st.info(t("fa_no_gh_history"))
        else:
            st.download_button(t("fa_download_greenhouse"),
                               _csv(rows, ["temperature", "humidity", "soil_moisture", "light_intensity", "co2", "prediction", "created_at"]),
                               "greenhouse_readings.csv", "text/csv", key="dl_greenhouse")
        fields = [("temperature", "temperature", "°C"), ("humidity", "humidity", "%"), ("soil_moisture", "soil_moisture", "%"),
                  ("light_intensity", "light", "PAR"), ("co2", "co2", "ppm")]
        for row in rows:
            st.markdown(f"**{localize_condition(row['prediction'], language)}** · {row['created_at']}")
            for col, (key, label_key, unit) in zip(st.columns(5), fields):
                value = row[key]
                col.metric(t(label_key), f"{value:g} {unit}" if value is not None else "—")
            if row["xai_explanation"]:
                with st.expander(t("fa_explanation")):
                    st.markdown(_explanation(row["xai_explanation"], language))
            st.divider()

    with chat_tab:
        sessions = fetch_chat_sessions(user_id)
        if not sessions:
            st.info(t("no_chats_found"))
        for session in sessions:
            title = localize_chat_title(session.get("title") or t("untitled"), language)
            with st.expander(f"{title} · {session.get('created_at', '')}"):
                for message in fetch_chat_messages(session["session_id"]):
                    who = t("you") if message["role"] == "user" else t("assistant_label")
                    st.markdown(f"**{who}:** {localize_chat_message(message['message'], language, t('chat_other_language'))}")
                if st.button(t("open_chat"), key=f"continue_{session['session_id']}"):
                    st.session_state.current_chat_session = session["session_id"]
                    st.session_state.current_page = "advisory"
                    st.rerun()
