def sources_markdown(items, t=None, language="English"):
    """Use the same source labels in result cards and persisted chat answers."""
    if not items:
        return ""
    heading = t("sources") if t else "Sources"
    lines = [f"#### {heading}"]
    for index, item in enumerate(items, start=1):
        if language == "Kannada":
            # Institution and article names in RAG metadata are canonical
            # English. Keep the official URL, but use an entirely Kannada
            # farmer-facing label rather than leaking that metadata.
            official = t("official_source") if t else "ಅಧಿಕೃತ ಮೂಲ"
            read_more = t("read_more") if t else "ಇನ್ನಷ್ಟು ಓದಿ"
            label = f"{official} {index} — {read_more}"
        else:
            label = f"{item['name']} — {item['topic']}"
        lines.append(f"- [{label}]({item['url']})")
    return "\n\n".join(lines)


def show_sources(st, items, t=None, language=None):
    language = language or st.session_state.get("language", "English")
    text = sources_markdown(items, t, language)
    if text:
        st.markdown(text)
