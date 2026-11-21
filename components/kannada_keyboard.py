KAN = ["ಅ","ಆ","ಇ","ಈ","ಉ","ಊ","ಋ","ಎ","ಏ","ಐ","ಒ","ಓ","ಔ","ಕ","ಖ","ಗ","ಘ","ಙ","ಚ","ಛ","ಜ","ಝ","ಞ","ಟ","ಠ","ಡ","ಢ","ಣ","ತ","ಥ","ದ","ಧ","ನ","ಪ","ಫ","ಬ","ಭ","ಮ","ಯ","ರ","ಲ","ವ","ಶ","ಷ","ಸ","ಹ","ಳ","ಾ","ಿ","ೀ","ು","ೂ","ೃ","ೆ","ೇ","ೈ","ೊ","ೋ","ೌ","್","ಂ","ಃ"]

def keyboard(st, t=None, state_key="chat_draft", key_prefix=""):
    st.caption("ಕನ್ನಡ ಕೀಬೋರ್ಡ್")
    prefix = f"{key_prefix}_" if key_prefix else ""
    for start in range(0, len(KAN), 10):
        cols = st.columns(10)
        for col, char in zip(cols, KAN[start:start+10]):
            if col.button(char, key=f"{prefix}kan_{start}_{char}"):
                st.session_state[state_key] = st.session_state.get(state_key, "") + char
                st.rerun()
    a, b, c = st.columns(3)
    label = (lambda key, fallback: t(key) if t else fallback)
    if a.button(label("space", "Space"), key=f"{prefix}kan_space"):
        st.session_state[state_key] = st.session_state.get(state_key, "") + " "
        st.rerun()
    if b.button(label("backspace", "Backspace"), key=f"{prefix}kan_back"):
        st.session_state[state_key] = st.session_state.get(state_key, "")[:-1]
        st.rerun()
    if c.button(label("clear", "Clear"), key=f"{prefix}kan_clear"):
        st.session_state[state_key] = ""
        st.rerun()
