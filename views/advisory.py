
"""AI Farming Assistant: leaf disease + greenhouse analysis + grounded advice on one page.

Every input is optional. Whatever the farmer supplies is analysed by its own
independent module, saved to History, and then passed - together with the
question - to the central advisory engine (RAG + government schemes).

This version uses text-only interaction. No microphone or audio features.
"""

import html
import logging

from components.source_cards import show_sources, sources_markdown
from database.db import (
    fetch_chat_messages,
    fetch_chat_sessions,
    save_chat_exchange,
)
from services.advisory_service import answer_farmer_question
from services.analysis_context import (
    build_current_context,
    format_analysis_context,
    get_latest_analysis_context,
    has_analysis_context,
)
from services.farm_assistant import (
    MAX_QUESTION_CHARS,
    analyze_greenhouse,
    analyze_leaf_image,
)
from services.localization import (
    localize_chat_message,
    localize_chat_title,
    localize_condition,
    localize_disease,
    localize_feature,
    localize_status,
)
from services.rag_service import sources

logger = logging.getLogger(__name__)

READING_FIELDS = (
    "temperature",
    "humidity",
    "soil_moisture",
    "light_intensity",
    "co2",
)

_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "soil_moisture": "%",
    "light_intensity": "PAR",
    "co2": "ppm",
}

_CHECK_FEATURE = {
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Root-zone moisture": "soil_moisture",
    "CO₂": "co2",
    "Light": "light_intensity",
}

# One consistent traffic-light palette: (text/border, background)
_LEVEL_COLOURS = {
    "green": ("#166534", "#dcfce7"),
    "yellow": ("#854d0e", "#fef9c3"),
    "red": ("#991b1b", "#fee2e2"),
}

_CONDITION_LEVEL = {
    "Suitable": "green",
    "Needs Adjustment": "yellow",
    "Unsuitable": "red",
}

_CHECK_LEVEL = {
    "suitable": "green",
    "needs adjustment": "yellow",
    "outside the recommended range": "red",
}

_LEVEL_ICON = {
    "green": "🟢",
    "yellow": "🟡",
    "red": "🔴",
}


def _esc(value):
    return html.escape(str(value))


def _state(st):
    """Results of this session, kept per farmer so a new login starts clean."""
    state = st.session_state.get("farm_assistant")

    if not state or state.get("user_id") != st.session_state.user_id:
        state = {
            "user_id": st.session_state.user_id,
            "disease": None,
            "greenhouse": None,
            "answer": None,
        }
        st.session_state["farm_assistant"] = state

    return state


def _card(st, title, level, body_html):
    """A bordered result card; level is green / yellow / red / neutral."""
    colour, background = _LEVEL_COLOURS.get(
        level,
        ("#065f46", "#ecfdf5"),
    )

    st.markdown(
        f'<div style="border:1px solid {colour};'
        f'border-left:8px solid {colour};'
        f'background:{background};'
        f'color:#14301f;border-radius:14px;'
        f'padding:16px 18px;margin:6px 0 14px 0;">'
        f'<div style="font-weight:700;color:{colour};'
        f'font-size:0.95rem;letter-spacing:.02em;'
        f'margin-bottom:6px;">{_esc(title)}</div>'
        f'{body_html}</div>',
        unsafe_allow_html=True,
    )


def _previous_context(st):
    """Earlier saved results, read only when the farmer agrees to reuse them."""
    try:
        return get_latest_analysis_context(st.session_state.user_id)
    except Exception:
        logger.exception("Could not read the latest analyses")
        return None


def _answer(st, t, language, question, use_previous=False, skip=()):
    """Answer using current results and optionally earlier saved analyses.

    Earlier saved analyses are used only when the farmer ticks
    'use my previous saved results'.
    """
    state = _state(st)
    previous = None

    if use_previous:
        previous = _previous_context(st)

        if previous is None:
            st.warning(t("analysis_context_error"))
        else:
            for key in skip:
                previous[key] = {"available": False}

    context = build_current_context(
        state["disease"],
        state["greenhouse"],
        previous,
    )

    context_text = (
        format_analysis_context(context, language)
        if has_analysis_context(context)
        else ""
    )

    try:
        with st.spinner(t("fa_preparing_advice")):
            response, results, _generated, _translated = (
                answer_farmer_question(
                    question,
                    language,
                    context,
                )
            )

    except Exception:
        logger.exception("Advisory response failed")
        st.error(t("advisory_error"))
        return

    found = sources(results)
    source_text = sources_markdown(found, t, language)

    # Save a snapshot of the analysis used for this answer.
    saved_response = response

    if context_text:
        saved_response += (
            f"\n\n**{t('fa_analysis_used')}**\n{context_text}"
        )

    if source_text:
        saved_response += "\n\n" + source_text

    try:
        session_id = save_chat_exchange(
            st.session_state.user_id,
            st.session_state.get("current_chat_session"),
            question[:60].strip().title() or t("untitled"),
            question,
            saved_response,
        )

        st.session_state.current_chat_session = session_id

    except Exception:
        logger.exception("Advisory history save failed")
        st.warning(t("advisory_save_error"))

    state["answer"] = {
        "question": question,
        "response": response,
        "sources": found,
        "context": context_text,
    }


def _run(
    st,
    t,
    language,
    image_bytes=None,
    values=None,
    question="",
    use_previous=False,
):
    """Run independent modules that have input, then the advisory engine.

    Every submission starts from a clean slate.
    """
    state = _state(st)

    state.update({
        "disease": None,
        "greenhouse": None,
        "answer": None,
    })

    analysed = False

    # Disease detection
    if image_bytes:
        try:
            with st.spinner(t("fa_analyzing_image")):
                state["disease"] = analyze_leaf_image(
                    st.session_state.user_id,
                    image_bytes,
                )

            analysed = bool(
                state["disease"]
                and state["disease"]["reliable"]
            )

        except Exception:
            logger.exception("Disease detection failed")
            st.error(t("disease_model_error"))

    # Greenhouse analysis
    if values:
        try:
            with st.spinner(t("fa_analyzing_readings")):
                result = analyze_greenhouse(
                    st.session_state.user_id,
                    values,
                )

            if result is None:
                st.error(t("sensor_range_error"))
            else:
                state["greenhouse"] = result
                analysed = True

        except Exception:
            logger.exception("Greenhouse analysis failed")
            st.error(t("greenhouse_model_error"))

    question = (question or "").strip()[:MAX_QUESTION_CHARS]

    # If analysis is submitted without a question,
    # generate the default advisory question.
    if not question and analysed:
        question = t("default_advice_question")

    if question:
        skip = tuple(
            key
            for key, given in (
                ("disease", image_bytes),
                ("greenhouse", values),
            )
            if given
        )

        _answer(
            st,
            t,
            language,
            question,
            use_previous=use_previous,
            skip=skip,
        )


def _form(st, t, language):
    """Collect farmer inputs using text-only interaction."""

    st.markdown(f"### {t('step_upload_image')}")

    image_file = st.file_uploader(
        t("tomato_leaf_image"),
        type=["jpg", "jpeg", "png"],
        key="integrated_leaf_upload",
        help=t("image_help"),
    )

    if image_file:
        st.image(
            image_file.getvalue(),
            caption=t("fa_image_caption"),
            width=240,
        )

    # Greenhouse readings
    st.markdown(f"### {t('step_enter_readings')}")
    st.caption(t("readings_hint"))

    c1, c2 = st.columns(2)

    values = {
        "temperature": c1.number_input(
            f"{t('temperature')} (°C)",
            0.0,
            45.0,
            None,
            step=0.5,
            placeholder="24",
            key="farm_temperature",
        ),
        "humidity": c2.number_input(
            f"{t('humidity')} (%)",
            0.0,
            100.0,
            None,
            step=1.0,
            placeholder="75",
            key="farm_humidity",
        ),
        "soil_moisture": c1.number_input(
            f"{t('soil_moisture')} (%)",
            0.0,
            100.0,
            None,
            step=1.0,
            placeholder="75",
            key="farm_soil_moisture",
        ),
        "light_intensity": c2.number_input(
            f"{t('light_intensity')} (PAR)",
            0.0,
            2000.0,
            None,
            step=10.0,
            placeholder="500",
            key="farm_light",
        ),
        "co2": c1.number_input(
            f"{t('co2')} (ppm)",
            250.0,
            2500.0,
            None,
            step=10.0,
            placeholder="600",
            key="farm_co2",
        ),
    }

    # Text-only farmer question
    st.markdown(f"### {t('step_ask_question')}")

    question = st.text_area(
        t("your_question"),
        placeholder=t("farm_question_placeholder"),
        height=100,
        max_chars=MAX_QUESTION_CHARS,
        key="integrated_question",
        label_visibility="collapsed",
    )

    # Option to reuse previous analysis
    use_previous = False
    previous = _previous_context(st)

    if previous and has_analysis_context(previous):
        st.markdown("---")

        use_previous = st.checkbox(
            t("fa_use_previous"),
            value=False,
            key="fa_use_previous",
        )

        st.caption(t("fa_use_previous_help"))

        with st.expander(t("fa_previous_preview")):
            st.markdown(
                format_analysis_context(
                    previous,
                    st.session_state.get("language", "English"),
                    compact=True,
                )
            )

    submitted = st.button(
        t("get_ai_advice"),
        type="primary",
        width="stretch",
        key="integrated_get_advice",
    )

    return (
        submitted,
        image_file,
        values,
        question,
        use_previous,
    )


def _disease_card(st, t, language, disease):
    reason_key = f"fa_img_reason_{disease.get('reason')}"

    if not disease["reliable"]:
        body = (
            f"<div>{_esc(t(reason_key))}</div>"
            f"<div style='margin-top:6px;'>"
            f"{_esc(t('fa_img_try_again'))}</div>"
        )

        if disease["top"]:
            rows = "".join(
                f"<li>{_esc(localize_disease(name, language))}"
                f" — {score:.0%}</li>"
                for name, score in disease["top"]
            )

            body += (
                f"<div style='margin-top:8px;font-weight:600;'>"
                f"{_esc(t('fa_unconfirmed_matches'))}</div>"
                f"<ul style='margin:4px 0 0 18px;'>{rows}</ul>"
            )

        _card(
            st,
            "⚠️ " + t("fa_disease_card"),
            "yellow",
            body,
        )
        return

    name = localize_disease(disease["disease"], language)
    healthy = "healthy" in disease["disease"].lower()
    level = "green" if healthy else "red"

    rows = "".join(
        f"<tr>"
        f"<td style='padding:2px 14px 2px 0;'>"
        f"{_esc(localize_disease(n, language))}</td>"
        f"<td>{score:.1%}</td>"
        f"</tr>"
        for n, score in disease["top"]
    )

    body = (
        f"<div style='font-size:1.45rem;font-weight:800;'>"
        f"{_LEVEL_ICON[level]} {_esc(name)}</div>"
        f"<div style='margin:4px 0 10px 0;'>"
        f"{_esc(t('confidence'))}: "
        f"<b>{disease['confidence']:.1%}</b></div>"
        f"<div style='font-weight:600;'>"
        f"{_esc(t('fa_top_predictions'))}</div>"
        f"<table style='border-collapse:collapse;margin-top:4px;'>"
        f"{rows}</table>"
    )

    _card(
        st,
        t("fa_disease_card"),
        level,
        body,
    )


def _greenhouse_card(st, t, language, greenhouse):
    level = _CONDITION_LEVEL.get(
        greenhouse["label"],
        "yellow",
    )

    confidence = greenhouse.get("confidence")

    confidence_html = (
        f"<div style='margin:4px 0 10px 0;'>"
        f"{_esc(t('confidence'))}: "
        f"<b>{confidence:.1%}</b></div>"
        if confidence is not None
        else ""
    )

    rows = ""

    for feature_name, status in greenhouse["checks"]:
        key = _CHECK_FEATURE.get(
            feature_name,
            feature_name,
        )

        row_level = _CHECK_LEVEL.get(
            status,
            "yellow",
        )

        value = greenhouse.get(
            "values",
            {},
        ).get(key)

        value_text = (
            f"{value:g} {_UNITS.get(key, '')}".strip()
            if value is not None
            else ""
        )

        rows += (
            f"<tr>"
            f"<td style='padding:2px 12px 2px 0;'>"
            f"{_LEVEL_ICON[row_level]}</td>"
            f"<td style='padding:2px 14px 2px 0;font-weight:600;'>"
            f"{_esc(localize_feature(key, language))}</td>"
            f"<td style='padding:2px 14px 2px 0;'>"
            f"{_esc(value_text)}</td>"
            f"<td>{_esc(localize_status(status, language))}</td>"
            f"</tr>"
        )

    body = (
        f"<div style='font-size:1.45rem;font-weight:800;'>"
        f"{_LEVEL_ICON[level]} "
        f"{_esc(localize_condition(greenhouse['label'], language))}"
        f"</div>"
        f"{confidence_html}"
        f"<div style='font-weight:600;'>"
        f"{_esc(t('fa_why_this_status'))}</div>"
        f"<table style='border-collapse:collapse;margin-top:4px;'>"
        f"{rows}</table>"
    )

    adjustments = greenhouse.get("adjustments") or []

    if adjustments:
        items = "".join(
            f"<li style='margin-bottom:6px;'>"
            f"{_LEVEL_ICON[a['level']]} "
            f"<b>{_esc(localize_feature(a['feature'], language))}</b> "
            f"({a['value']:g} "
            f"{_esc(_UNITS.get(a['feature'], ''))}): "
            f"{_esc(a['advice_kn'] if language == 'Kannada' else a['advice_en'])}"
            f"</li>"
            for a in adjustments
        )

        body += (
            f"<div style='margin-top:12px;font-weight:600;'>"
            f"{_esc(t('fa_adjustments'))}</div>"
            f"<ul style='margin:4px 0 0 18px;'>{items}</ul>"
        )

    else:
        body += (
            f"<div style='margin-top:12px;'>"
            f"{_esc(t('fa_all_in_range'))}</div>"
        )

    _card(
        st,
        t("fa_greenhouse_card"),
        level,
        body,
    )


def _save_status(st, t, result, reliable_only=False):
    """Tell the farmer whether this result really reached History.

    Only shown when the analysis itself succeeded; an unreliable image is
    intentionally never saved, so it gets no "not saved" warning.
    """
    if reliable_only and not result.get("reliable"):
        return
    saved = result.get("saved")
    if saved is True:
        st.caption("✅ " + t("fa_history_saved"))
    elif saved is False:
        st.warning(t("fa_history_not_saved"))


def _show_results(st, t, language, state):
    disease = state["disease"]
    greenhouse = state["greenhouse"]
    answer = state["answer"]

    if disease or greenhouse:
        st.markdown("---")

        left, right = st.columns(2)

        with left:
            if disease:
                _disease_card(
                    st,
                    t,
                    language,
                    disease,
                )
                _save_status(st, t, disease, reliable_only=True)

        with right:
            if greenhouse:
                _greenhouse_card(
                    st,
                    t,
                    language,
                    greenhouse,
                )
                _save_status(st, t, greenhouse)

    if answer:
        st.markdown("---")

        if answer["context"]:
            st.markdown(
                f"### {t('fa_analysis_used')}"
            )
            st.info(answer["context"])

        elif not (disease or greenhouse):
            st.caption(t("fa_no_analysis_note"))

        st.markdown(
            f"### {t('fa_advice_heading')}"
        )

        st.markdown(answer["response"])

        show_sources(
            st,
            answer["sources"],
            t,
            language,
        )


def _previous_chats(st, t, language):
    st.markdown("---")
    st.markdown(f"### {t('fa_prev_chats')}")

    if st.session_state.get("current_chat_session"):
        st.caption(t("fa_continuing"))

        if st.button(
            t("fa_new_conversation"),
            key="fa_new_conversation",
        ):
            st.session_state.current_chat_session = None
            st.rerun()

    sessions = fetch_chat_sessions(
        st.session_state.user_id
    )

    if not sessions:
        st.caption(t("fa_prev_chats_empty"))

    for session in sessions[:8]:
        title = localize_chat_title(
            session.get("title") or t("untitled"),
            language,
        )

        with st.expander(
            f"{title} · {session.get('created_at', '')}"
        ):
            for message in fetch_chat_messages(
                session["session_id"]
            ):
                who = (
                    t("you")
                    if message["role"] == "user"
                    else t("assistant_label")
                )

                st.markdown(
                    f"**{who}:** "
                    f"{localize_chat_message(message['message'], language, t('chat_other_language'))}"
                )


def render(st, t):
    language = st.session_state.get(
        "language",
        "English",
    )

    state = _state(st)

    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">{t('fa_eyebrow')}</div>
          <h2>{t('assistant_title')}</h2>
          <p>{t('fa_intro')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        submitted,
        image_file,
        values,
        question,
        use_previous,
    ) = _form(
        st,
        t,
        language,
    )

    if submitted:
        filled = [
            value is not None
            for value in values.values()
        ]

        if any(filled) and not all(filled):
            st.warning(t("readings_incomplete"))

        elif not (
            image_file
            or all(filled)
            or (question and question.strip())
        ):
            st.warning(t("fa_need_input"))

        else:
            _run(
                st,
                t,
                language,
                image_file.getvalue() if image_file else None,
                {
                    name: float(values[name])
                    for name in READING_FIELDS
                } if all(filled) else None,
                question,
                use_previous,
            )

    _show_results(
        st,
        t,
        language,
        state,
    )

    _previous_chats(
        st,
        t,
        language,
    )
