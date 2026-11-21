import json
import streamlit as st
from config import ROOT
from database.db import initialize_database
from services.auth_service import register_farmer, login_farmer, admin_exists, create_admin, login_admin

st.set_page_config(page_title="Namma Krushi", page_icon="🌱", layout="wide")
initialize_database()

def dictionary(language):
    """Load labels directly so translation edits appear after a Streamlit rerun."""
    filename = "ui_strings_kn.json" if language == "Kannada" else "ui_strings_en.json"
    return json.loads((ROOT / "translation" / filename).read_text(encoding="utf-8"))

def t(key):
    lang = st.session_state.get("language", "English")
    if not lang:
        lang = "English"
    dict_map = dictionary(lang)
    return dict_map.get(key, key.replace("_", " ").title())

def init_state():
    defaults={"authenticated":False,"admin_authenticated":False,"language":None,"current_page":"dashboard","current_chat_session":None,"chat_draft":"","theme_mode":"light"}
    for k,v in defaults.items(): st.session_state.setdefault(k,v)
init_state()

def style():
    theme = st.session_state.get("theme_mode", "light")
    is_dark = (theme == "dark")

    bg_app = "#0d1710" if is_dark else "#f3ecdc"
    bg_paper = "#152419" if is_dark else "#fffaf0"
    bg_input = "#1e3223" if is_dark else "#ffffff"
    bg_uploader = "#1a2b1e" if is_dark else "#fbf4e6"
    border_uploader = "1.5px dashed #3a5740" if is_dark else "1.5px dashed #c4b595"
    text_primary = "#eaf3e7" if is_dark else "#26301f"
    text_muted = "#9ab396" if is_dark else "#5b6552"
    line_color = "#294330" if is_dark else "#ded2b9"
    hero_bg = "radial-gradient(circle at 90% 20%, rgba(115,150,83,.22), transparent 28%), linear-gradient(120deg,#1b3322,#0d1710)" if is_dark else "radial-gradient(circle at 90% 20%, rgba(155,184,121,.22), transparent 28%), linear-gradient(120deg,#29462f,#14261a)"
    notice_bg = "#1c3021" if is_dark else "#f8efd9"
    notice_text = "#e2eedd" if is_dark else "#574c31"
    
    # RICH AGRICULTURAL GREEN FOR ALL BUTTONS (VIBRANT EMERALD IN DARK MODE)
    btn_green = "#228649" if is_dark else "#166534"
    btn_green_hover = "#1c733e" if is_dark else "#14532d"
    gold = "#e5b648" if is_dark else "#d7a83b"
    sidebar_bg = "linear-gradient(180deg, #09120c, #060b07)" if is_dark else "linear-gradient(180deg, #14261a, #102016)"

    badge_ok_bg = "rgba(115, 150, 83, 0.28)" if is_dark else "#e0eed7"
    badge_ok_text = "#9fe075" if is_dark else "#52723b"
    badge_warn_bg = "rgba(201, 77, 53, 0.28)" if is_dark else "#f7e4cf"
    badge_warn_text = "#ff9980" if is_dark else "#a14b28"

    st.markdown(f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Fraunces:ital,opsz,wght@0,9..144,100..900;1,9..144,100..900&display=swap');

    :root {{
      --forest:#14261a; --forest2:#1d3524; --forest3:#29462f;
      --leaf:#739653; --leaf2:#9bb879; --btn-green:{btn_green}; --btn-green-hover:{btn_green_hover};
      --gold:{gold}; --cream:#f6f0e3; --paper:{bg_paper};
      --ink:{text_primary}; --muted:{text_muted}; --line:{line_color}; --white:#fff;
      --shadow:0 14px 40px rgba(0,0,0,.18); --radius:16px;
    }}

    .stApp {{
        background-color: {bg_app} !important;
        color: {text_primary} !important;
        font-family: "DM Sans", sans-serif !important;
    }}

    h1, h2, h3, h4 {{
        font-family: "Fraunces", serif !important;
        color: {text_primary} !important;
    }}

    .block-container {{
        max-width: 1240px;
        /* Leave room for Streamlit's fixed header so the top action row
           never appears hidden behind the header ribbon. */
        padding-top: 4.25rem !important;
        padding-bottom: 3rem;
    }}

    [data-testid="stHeader"] {{
        background: {bg_app} !important;
        border-bottom: 1px solid {line_color};
    }}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        color: #f6f0e3 !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }}

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: #f6f0e3 !important;
    }}

    .brand-box {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 4px 16px 4px;
    }}

    .brand-logo {{
        width: 42px;
        height: 42px;
        border-radius: 13px;
        background: linear-gradient(145deg, #9bb879, #739653);
        display: grid;
        place-items: center;
        font-size: 22px;
        box-shadow: 0 7px 18px rgba(115,150,83,.3);
    }}

    .brand-title {{
        font-family: "Fraunces", serif;
        font-size: 22px;
        font-weight: 600;
        margin: 0;
        color: #fffaf0;
        line-height: 1.1;
    }}

    .brand-sub {{
        color: #b8c8ae;
        font-size: 11px;
        margin-top: 2px;
    }}

    .user-card {{
        margin: 0 0 14px;
        padding: 12px 14px;
        border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.05);
        border-radius: 12px;
        font-size: 11.5px;
        color: #bac6b2;
    }}

    .user-card b {{
        display: block;
        color: #f5f1e7;
        font-size: 13px;
        margin-bottom: 2px;
    }}

    /* Streamlit Primary & Action Buttons - RICH AGRICULTURAL GREEN */
    .stButton > button, .stDownloadButton > button {{
        background: {btn_green} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        min-height: 42px !important;
        box-shadow: 0 4px 12px rgba(22, 101, 52, 0.25) !important;
        transition: all 0.2s ease !important;
    }}

    .stButton > button:hover, .stDownloadButton > button:hover {{
        background: {btn_green_hover} !important;
        transform: translateY(-1px) !important;
    }}

    /* Sidebar Navigation Buttons */
    [data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        color: #bfc9b9 !important;
        border: none !important;
        text-align: left !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
        border-radius: 11px !important;
        box-shadow: none !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,.07) !important;
        color: #ffffff !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background: rgba(215,168,59,.18) !important;
        color: #ffffff !important;
        border-left: 3.5px solid {gold} !important;
        border-radius: 4px 11px 11px 4px !important;
        font-weight: 700 !important;
    }}

    /* Card & Tile Utilities */
    .hero {{
        margin: 0 0 24px 0;
        min-height: 160px;
        padding: 28px 32px;
        border-radius: 20px;
        position: relative;
        overflow: hidden;
        color: #f6f0e3;
        background: {hero_bg};
        box-shadow: 0 14px 40px rgba(0,0,0,.15);
    }}
    .hero:after {{
        content: "🌿";
        position: absolute;
        right: 35px;
        bottom: -25px;
        font-size: 110px;
        opacity: 0.12;
        transform: rotate(-12deg);
        pointer-events: none;
    }}
    .eyebrow {{
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: 10.5px;
        color: #c5d6b9;
        font-weight: 700;
    }}
    .hero h2 {{
        font-family: Fraunces, serif;
        font-size: 32px;
        line-height: 1.1;
        margin: 8px 0 9px;
        color: #fffaf0 !important;
    }}
    .hero p {{
        margin: 0;
        color: #d5dfcf;
        font-size: 13px;
        max-width: 650px;
        line-height: 1.6;
    }}

    .nk-card {{
        background: {bg_paper};
        border: 1px solid {line_color};
        border-radius: 16px;
        padding: 22px;
        box-shadow: 0 8px 24px rgba(0,0,0,.05);
        margin-bottom: 20px;
        color: {text_primary};
    }}

    .nk-tile {{
        background: {bg_paper};
        border: 1px solid {line_color};
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,.05);
        transition: all 0.2s ease;
        height: 100%;
        color: {text_primary};
    }}
    .nk-tile:hover {{
        transform: translateY(-3px);
        box-shadow: 0 14px 40px rgba(0,0,0,.15);
    }}

    .tileicon {{
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        font-size: 22px;
        margin-bottom: 12px;
    }}
    .red {{ background: rgba(115,150,83,.18); color: #739653; }}
    .green {{ background: rgba(115,150,83,.18); color: #739653; }}
    .gold {{ background: rgba(215,168,59,.18); color: {gold}; }}
    .blue {{ background: rgba(74,124,137,.16); color: #4a7c89; }}

    .badge-ok {{
        display: inline-flex;
        padding: 4px 10px;
        border-radius: 30px;
        font-size: 11px;
        font-weight: 700;
        background: {badge_ok_bg} !important;
        color: {badge_ok_text} !important;
    }}
    .badge-warn {{
        display: inline-flex;
        padding: 4px 10px;
        border-radius: 30px;
        font-size: 11px;
        font-weight: 700;
        background: {badge_warn_bg} !important;
        color: {badge_warn_text} !important;
    }}

    .nk-notice {{
        padding: 14px 16px;
        border-left: 4px solid {gold};
        background: {notice_bg};
        border-radius: 8px;
        font-size: 12.5px;
        color: {notice_text};
        line-height: 1.55;
        margin: 12px 0;
    }}

    /* ============================================================
       HIGH-CLASS TABS STYLING (Fixes washed-out tabs & red underline)
       ============================================================ */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px !important;
        background-color: transparent !important;
        border-bottom: 2px solid {line_color} !important;
        padding-bottom: 0px !important;
        margin-bottom: 16px !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 44px !important;
        padding: 8px 20px !important;
        border-radius: 8px 8px 0 0 !important;
        background-color: transparent !important;
        border: none !important;
        color: {text_muted} !important;
        font-family: "DM Sans", sans-serif !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: {btn_green} !important;
        background-color: rgba(22, 101, 52, 0.08) !important;
    }}

    .stTabs [aria-selected="true"] {{
        color: {btn_green} !important;
        font-weight: 700 !important;
        border-bottom: 3px solid {btn_green} !important;
        background-color: transparent !important;
    }}

    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {btn_green} !important;
    }}

    /* ============================================================
       HIGH-CLASS FORM & BUTTON STYLING (Fixes black form button)
       ============================================================ */
    [data-testid="stForm"] {{
        background: {bg_paper} !important;
        border: 1px solid {line_color} !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04) !important;
    }}

    .stButton button, 
    .stDownloadButton button, 
    .stFormSubmitButton button,
    div[data-testid="stFormSubmitButton"] button,
    button[data-testid^="baseButton"],
    button[kind="primary"],
    button[kind="secondary"],
    button[kind="formSubmit"] {{
        background: {btn_green} !important;
        background-color: {btn_green} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: "DM Sans", sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        min-height: 44px !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 14px rgba(22, 101, 52, 0.25) !important;
        transition: all 0.2s ease !important;
    }}

    .stButton button:hover, 
    .stDownloadButton button:hover, 
    .stFormSubmitButton button:hover,
    div[data-testid="stFormSubmitButton"] button:hover,
    button[data-testid^="baseButton"]:hover {{
        background: {btn_green_hover} !important;
        background-color: {btn_green_hover} !important;
        box-shadow: 0 6px 20px rgba(22, 101, 52, 0.35) !important;
        transform: translateY(-1px) !important;
    }}

    /* Ensure button text and nested spans/paragraphs are always clean white */
    .stButton button *, 
    .stDownloadButton button *, 
    .stFormSubmitButton button *,
    div[data-testid="stFormSubmitButton"] button *,
    button[data-testid^="baseButton"] * {{
        color: #ffffff !important;
    }}

    /* ============================================================
       FORM CONTROLS & COMPONENT CONTRAST FIXES
       ============================================================ */
    
    /* ALL WIDGET LABELS - Ensure crisp high contrast readability */
    label, 
    .stTextInput label, 
    .stSelectbox label, 
    .stNumberInput label, 
    .stTextArea label, 
    .stSlider label,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span {{
        color: {text_primary} !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        margin-bottom: 6px !important;
    }}

    /* Text Inputs, Selectboxes, Textareas, Number Inputs */
    .stTextInput input, 
    .stNumberInput input, 
    .stTextArea textarea,
    .stSelectbox select,
    div[data-baseweb="select"] > div {{
        background-color: {bg_input} !important;
        color: {text_primary} !important;
        border: 1.5px solid {line_color} !important;
        border-radius: 10px !important;
        font-size: 14px !important;
    }}

    .stTextInput input:focus, 
    .stNumberInput input:focus, 
    .stTextArea textarea:focus {{
        border-color: {btn_green} !important;
        box-shadow: 0 0 0 3px rgba(22, 101, 52, 0.18) !important;
    }}

    /* BaseWeb Selectbox dropdown container & options */
    div[data-baseweb="select"] * {{
        background-color: {bg_input} !important;
        color: {text_primary} !important;
    }}

    div[data-baseweb="menu"], ul[role="listbox"] {{
        background-color: {bg_paper} !important;
        border: 1px solid {line_color} !important;
    }}

    div[data-baseweb="menu"] li, ul[role="listbox"] li, li[role="option"] {{
        background-color: {bg_paper} !important;
        color: {text_primary} !important;
    }}

    div[data-baseweb="menu"] li:hover, li[role="option"]:hover {{
        background-color: {bg_input} !important;
    }}

    /* FILE UPLOADER FIX */
    [data-testid="stFileUploader"] {{
        background-color: transparent !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {bg_uploader} !important;
        border: {border_uploader} !important;
        border-radius: 14px !important;
        color: {text_primary} !important;
        padding: 24px 16px !important;
    }}
    [data-testid="stFileUploaderDropzone"] * {{
        color: {text_primary} !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background-color: {btn_green} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
    }}

    /* Metrics, Tables & Dataframes */
    table {{
        width: 100%;
        border-collapse: collapse;
        color: {text_primary} !important;
    }}
    th, td {{
        padding: 10px 12px;
        border-bottom: 1px solid {line_color} !important;
        color: {text_primary} !important;
    }}
    th {{
        color: {text_muted} !important;
        font-size: 12px !important;
        font-weight: 700 !important;
    }}
    [data-testid="stDataFrame"] {{
        background-color: {bg_paper} !important;
        border-radius: 12px !important;
    }}

    [data-testid="stMetricValue"] {{
        font-family: Fraunces, serif !important;
        color: {text_primary} !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {text_muted} !important;
    }}

    .stExpander, [data-testid="stExpander"] {{
        background-color: {bg_paper} !important;
        border: 1px solid {line_color} !important;
        border-radius: 12px !important;
    }}
    .stExpander summary span {{
        color: {text_primary} !important;
    }}
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary {{
        background-color: {bg_paper} !important;
        color: {text_primary} !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background-color: {bg_input} !important;
    }}
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary svg {{
        color: {text_primary} !important;
    }}

    /* Chat Messages */
    [data-testid="stChatMessage"] {{
        background-color: {bg_paper} !important;
        border: 1px solid {line_color} !important;
        border-radius: 14px !important;
        padding: 12px 16px !important;
        margin-bottom: 10px !important;
    }}
    [data-testid="stChatMessage"] * {{
        color: {text_primary} !important;
    }}
    /* Inline Markdown code (for example botanical names) uses the active
       theme rather than Streamlit's default light code-chip background. */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] :not(pre) > code {{
        background: {bg_input} !important;
        color: {text_primary} !important;
    }}

    /* The dashboard cards all reserve the same vertical space, which keeps
       their action controls on one horizontal baseline. */
    div[class*="st-key-dash_go_"] button {{
        width: 100% !important;
        min-height: 46px !important;
        justify-content: center !important;
    }}

    /* WhatsApp-like advisory conversation */
    .chat-sidebar-title {{ font-family: "Fraunces", serif; font-size: 19px; font-weight: 700; color: var(--ink); margin: 0 0 3px; }}
    .chat-sidebar-subtitle {{ color: var(--muted); font-size: 12px; margin-bottom: 14px; }}
    .chat-header {{ background: {bg_paper}; border: 1px solid {line_color}; border-radius: 16px 16px 0 0; padding: 14px 18px; display: flex; align-items: center; gap: 10px; color: {text_primary}; }}
    .chat-header-avatar {{ width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; background: {btn_green}; color: #fff; font-size: 17px; }}
    .chat-header-title {{ font-weight: 750; font-size: 14px; }}
    .chat-header-status {{ color: var(--muted); font-size: 11.5px; margin-top: 1px; }}
    .chat-empty {{ padding: 58px 24px; text-align: center; color: var(--muted); }}
    .chat-empty-icon {{ font-size: 38px; margin-bottom: 8px; }}
    div[class*="st-key-chat_menu_"] button {{
        min-width: 42px !important;
        padding: 0 !important;
        font-size: 22px !important;
        border-radius: 10px !important;
    }}
    [data-testid="stChatMessage"] {{ box-shadow: none !important; max-width: 86%; }}
    [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] form {{ background: {bg_paper} !important; border-top: 1px solid {line_color}; padding: 12px 14px 4px; border-radius: 0 0 16px 16px; }}
    [data-testid="stChatInput"] textarea {{ background: {bg_input} !important; color: {text_primary} !important; border: 1px solid {line_color} !important; border-radius: 22px !important; }}
    [data-testid="stChatInput"] button {{ background: {btn_green} !important; color: #fff !important; border: none !important; }}
    </style>""", unsafe_allow_html=True)
style()

def render_topbar():
    c_status, _, c_theme = st.columns([3, 3.3, 1.3])
    with c_status:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:8px; height:38px; font-size:12.5px; color:var(--muted); font-weight:600;">
            <span style="width:8px; height:8px; border-radius:50%; background:#22c55e; display:inline-block; box-shadow:0 0 8px #22c55e;"></span>
            <span>System ready · ವ್ಯವಸ್ಥೆ ಸಿದ್ಧವಾಗಿದೆ</span>
        </div>
        """, unsafe_allow_html=True)
    with c_theme:
        cur_theme = st.session_state.get("theme_mode", "light")
        btn_label = "🌙 Dark Mode" if cur_theme == "light" else "☀️ Light Mode"
        next_theme = "dark" if cur_theme == "light" else "light"
        cur_pg = st.session_state.get("current_page", "home")
        if st.button(btn_label, key=f"top_theme_btn_{cur_pg}", width="stretch"):
            st.session_state.theme_mode = next_theme
            st.rerun()
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

def language_screen():
    render_topbar()
    st.markdown("<br>", unsafe_allow_html=True)
    _,col,_=st.columns([1,2,1])
    with col:
        st.markdown("""
        <div class="nk-card" style="text-align:center; padding:36px 24px;">
            <div class="brand-logo" style="margin:0 auto 16px; width:54px; height:54px; font-size:28px;">🌱</div>
            <h1 style="margin-bottom:4px;">Namma Krushi</h1>
            <p style="color:var(--muted); font-size:14px; margin-bottom:24px;">ನಮ್ಮ ಕೃಷಿ · AI Farm Companion<br>Greenhouse Tomato Cultivation Advisory</p>
            <h3 style="font-size:16px; margin-bottom:16px;">Choose Language / ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ</h3>
        </div>
        """, unsafe_allow_html=True)
        a,b=st.columns(2)
        if a.button("ಕನ್ನಡ (Kannada)", width="stretch", type="primary"): st.session_state.language="Kannada"; st.rerun()
        if b.button("English", width="stretch"): st.session_state.language="English"; st.rerun()

def auth_screen():
    render_topbar()
    _, auth_col, _ = st.columns([1.5, 1.5, 1.5])
    with auth_col:
        st.markdown("""
        <div class="brand-box" style="margin-bottom:18px; justify-content:center; text-align:center;">
            <div class="brand-logo" style="width:48px; height:48px; font-size:24px; margin-right:4px;">🌱</div>
            <div style="text-align:left;">
                <div class="brand-title" style="color:var(--ink); font-size:24px;">Namma Krushi</div>
                <div class="brand-sub" style="color:var(--muted); font-size:11.5px;">ನಮ್ಮ ಕೃಷಿ · AI Farm Companion</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        tabs=st.tabs([t("login"), t("register"), t("admin")])
        with tabs[0]:
            with st.form("farmer_login"):
                username=st.text_input(t("username")); password=st.text_input(t("password"),type="password")
                if st.form_submit_button(t("login"), type="primary", width="stretch"):
                    user=login_farmer(username,password)
                    if user:
                        st.session_state.update(authenticated=True,user_id=user["user_id"],username=user["username"],name=user["name"],language=user["language"],current_page="dashboard"); st.rerun()
                    else:
                        st.error(t("incorrect_credentials"))
        with tabs[1]:
            with st.form("register"):
                name=st.text_input(t("name")); username=st.text_input(t("username")); password=st.text_input(t("password"),type="password")
                language=st.selectbox(
                    t("preferred_language"),
                    ["English","Kannada"],
                    index=0 if st.session_state.language=="English" else 1,
                    format_func=lambda value: t("language_english") if value == "English" else t("language_kannada"),
                )
                if st.form_submit_button(t("register"), type="primary", width="stretch"):
                    ok,result=register_farmer(name,username,password,language)
                    if ok:
                        st.success(t("registration_success"))
                    else:
                        st.error(t(result))
        with tabs[2]:
            if not admin_exists():
                st.info(t("admin_first_run"))
                with st.form("admin_setup"):
                    username=st.text_input(t("admin_username")); password=st.text_input(t("admin_password_hint"),type="password")
                    if st.form_submit_button(t("create_admin"), width="stretch"):
                        ok,msg=create_admin(username,password)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
            else:
                with st.form("admin_login"):
                    username=st.text_input(t("admin_username")); password=st.text_input(t("admin_password"),type="password")
                    if st.form_submit_button(t("admin_login"), width="stretch"):
                        if login_admin(username,password): st.session_state.admin_authenticated=True; st.rerun()
                        else: st.error(t("incorrect_admin_credentials"))

def farmer_shell():
    nav=["dashboard","advisory","schemes","history","profile"]
    nav_icons = {
        "dashboard": "⌂",
        "advisory": "🌱",
        "schemes": "🏛",
        "history": "◷",
        "profile": "○"
    }

    with st.sidebar:
        st.markdown("""
        <div class="brand-box">
            <div class="brand-logo">🌱</div>
            <div>
                <div class="brand-title">Namma Krushi</div>
                <div class="brand-sub">ನಮ್ಮ ಕೃಷಿ · farm companion</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        user_name = st.session_state.get("name", "Farmer")
        selected_language = t("language_kannada") if st.session_state.language == "Kannada" else t("language_english")
        
        st.markdown(f"""
        <div class="user-card">
            <b>{user_name}</b>
            {t("tomato_greenhouse_label")} · Karnataka ({selected_language})
        </div>
        """, unsafe_allow_html=True)

        # 1. Language Quick Switcher in Sidebar
        lang_choice = st.selectbox(
            "Language / ಭಾಷೆ",
            ["English", "Kannada"],
            index=0 if st.session_state.language == "English" else 1,
            key="sb_lang_select",
            label_visibility="collapsed"
        )
        if lang_choice != st.session_state.language:
            st.session_state.language = lang_choice
            st.rerun()

        # 2. MANDATORY Dark / Light Mode Switcher in Sidebar
        st.markdown("<div style='margin-top:6px; font-size:11px; color:#b8c8ae;'>Theme / ಥೀಮ್:</div>", unsafe_allow_html=True)
        theme_choice = st.selectbox(
            "Theme Mode",
            ["☀️ Light Mode", "🌙 Dark Mode"],
            index=0 if st.session_state.get("theme_mode", "light") == "light" else 1,
            key="sb_theme_select",
            label_visibility="collapsed"
        )
        target_mode = "light" if "Light" in theme_choice else "dark"
        if target_mode != st.session_state.get("theme_mode", "light"):
            st.session_state.theme_mode = target_mode
            st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        for key in nav:
            is_active = (key == st.session_state.current_page)
            icon = nav_icons.get(key, "•")
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon}  {t(key)}", width="stretch", key=f"nav_{key}", type=btn_type):
                st.session_state.current_page = key
                st.rerun()

        st.divider()
        if st.button(t("logout"), width="stretch"):
            for key in ["authenticated","user_id","username","name","current_chat_session","farm_assistant","fa_last_voice_nonce"]: st.session_state.pop(key,None)
            st.session_state.authenticated=False; st.session_state.language=None; st.rerun()

    import importlib
    from views import dashboard, advisory, schemes, history_reports, profile
    importlib.reload(dashboard)
    importlib.reload(schemes)
    routes = {
        "dashboard": dashboard.render,
        "advisory": advisory.render,
        "schemes": schemes.render,
        "history": history_reports.render,
        "profile": profile.render,
    }
    routes.get(st.session_state.current_page, dashboard.render)(st, t)

if st.session_state.admin_authenticated:
    from views.admin_dashboard import render
    if st.sidebar.button("Admin logout"): st.session_state.admin_authenticated=False; st.rerun()
    render(st)
elif st.session_state.language is None: language_screen()
elif not st.session_state.authenticated: auth_screen()
else: farmer_shell()
