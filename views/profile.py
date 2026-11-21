from database.db import execute, fetch_one
from services.auth_service import verify_password, hash_password
from services.validation import check_language, check_new_password, clean_name

def render(st, t):
    st.markdown(f"""
    <div class="hero">
        <div class="eyebrow">{t('profile_eyebrow')}</div>
        <h2>{t('profile')}</h2>
        <p>{t('profile_intro')}</p>
    </div>
    """, unsafe_allow_html=True)

    user = fetch_one("SELECT * FROM users WHERE user_id=?", (st.session_state.user_id,))
    
    with st.form("profile_form"):
        name = st.text_input(t("name"), user["name"])
        st.text_input(t("username"), user["username"], disabled=True)
        language = st.selectbox(
            t("preferred_language"),
            ["English", "Kannada"],
            index=0 if user["language"] == "English" else 1,
            format_func=lambda value: t("language_english") if value == "English" else t("language_kannada"),
        )
        save = st.form_submit_button(t("save_profile"), type="primary", width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    if save:
        clean, name_error = clean_name(name)
        if name_error:
            st.error(t(name_error))          # nothing is saved
        elif check_language(language) is None:
            st.error(t("profile_language_invalid"))
        else:
            execute("UPDATE users SET name=?,language=? WHERE user_id=?", (clean, language, user["user_id"]))
            st.session_state.name = clean
            st.session_state.language = language
            st.success(t("profile_saved"))
            st.rerun()

    with st.expander(t("change_password")):
        old = st.text_input(t("current_password"), type="password")
        new = st.text_input(t("new_password"), type="password")
        if st.button(t("update_password"), type="primary"):
            problem = check_new_password(old, new)
            if not verify_password(old, user["password_hash"]):
                st.error(t("password_wrong"))
            elif problem:
                st.error(t(problem))
            else:
                execute("UPDATE users SET password_hash=? WHERE user_id=?", (hash_password(new), user["user_id"]))
                st.success(t("password_updated"))

