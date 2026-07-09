import streamlit as st
from openai import OpenAI
from pathlib import Path
try:
    from PIL import Image
except Exception:
    Image = None
import base64
import html
from datetime import datetime, timezone
from config import supabase

# ============================================================
# App Paths / API
# ============================================================

BASE_DIR = Path(__file__).parent.parent
APP_DIR = Path(__file__).parent
LOGO_FILE = APP_DIR / "logo.png"

PAGE_ICON = "🚗"
if Image is not None and LOGO_FILE.exists():
    try:
        PAGE_ICON = Image.open(LOGO_FILE)
    except Exception:
        PAGE_ICON = "🚗"

api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

TECHNICAL_VECTOR_STORE_ID = "vs_6a4e9facdf2c8191b6c712329e398490"
SALES_VECTOR_STORE_ID = "vs_6a4eaf5d33a081919722e8628a1c5e71"

st.set_page_config(
    page_title="AutoTecPro AI",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Styling
# ============================================================

def inject_base_css():
    st.markdown(
        """
        <style>
        :root {
            --atp-red: #ef4444;
            --atp-red-dark: #dc2626;
            --atp-bg: #050b16;
            --atp-card: rgba(15, 23, 42, 0.88);
            --atp-border: rgba(148, 163, 184, 0.20);
            --atp-text: #f8fafc;
            --atp-muted: #94a3b8;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(239,68,68,0.15), transparent 28%),
                radial-gradient(circle at bottom right, rgba(59,130,246,0.08), transparent 24%),
                linear-gradient(135deg, #050b16 0%, #0b1220 45%, #020617 100%);
            color: var(--atp-text);
        }

        header[data-testid="stHeader"] { background: transparent; }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #07111f 0%, #020617 100%);
            border-right: 1px solid rgba(148,163,184,0.12);
        }

        section[data-testid="stSidebar"] * { color: #e5e7eb; }

        .stTextInput > label,
        .stSelectbox > label,
        .stFileUploader > label,
        .stTextArea > label {
            color: #e5e7eb !important;
            font-weight: 650;
        }

        .stTextInput input,
        .stTextArea textarea {
            background-color: rgba(15, 23, 42, 0.96) !important;
            color: #ffffff !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
        }

        .stTextInput input { height: 46px; }

        /* Fix password field / eye icon alignment */
        div[data-testid="stTextInputRootElement"] {
            background-color: rgba(15, 23, 42, 0.96) !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            min-height: 46px !important;
            overflow: hidden !important;
        }

        div[data-testid="stTextInputRootElement"] input {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInputRootElement"]:focus-within {
            border: 1px solid var(--atp-red) !important;
            box-shadow: 0 0 0 1px var(--atp-red) !important;
        }

        div[data-testid="stTextInputRootElement"] button {
            background: rgba(148, 163, 184, 0.18) !important;
            border: none !important;
            box-shadow: none !important;
            width: 46px !important;
            height: 46px !important;
            border-radius: 0 12px 12px 0 !important;
            color: white !important;
            transform: none !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border: 1px solid var(--atp-red) !important;
            box-shadow: 0 0 0 1px var(--atp-red) !important;
        }

        /* Orange / red action buttons */
        .stButton > button,
        .stFormSubmitButton > button {
            width: 100%;
            height: 52px;
            border-radius: 12px;
            border: none !important;
            background: linear-gradient(135deg, #ff5a3d 0%, #ff3b30 45%, #e10600 100%) !important;
            color: white !important;
            font-weight: 800;
            font-size: 16px;
            transition: 0.22s ease;
            box-shadow: 0 10px 26px rgba(255, 80, 40, 0.34);
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: linear-gradient(135deg, #ff7255 0%, #ff4d3d 45%, #ff2d20 100%) !important;
            color: white !important;
            transform: translateY(-1px);
            box-shadow: 0 14px 30px rgba(255, 80, 40, 0.44);
        }

        .stButton > button:active,
        .stFormSubmitButton > button:active {
            transform: scale(0.98);
        }

        div[data-testid="stForm"] {
            background: rgba(15, 23, 42, 0.36);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 18px;
            padding: 26px;
            backdrop-filter: blur(14px);
            box-shadow: 0 16px 42px rgba(0,0,0,0.22);
        }

        .app-header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 28px;
            padding: 18px 22px;
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 22px;
            box-shadow: 0 18px 45px rgba(0,0,0,0.22);
            backdrop-filter: blur(12px);
        }

        .app-header img {
            width: 92px;
            height: 92px;
            border-radius: 18px;
            object-fit: contain;
        }

        .app-title {
            margin: 0;
            padding: 0;
            font-size: 46px;
            font-weight: 850;
            letter-spacing: -1px;
            line-height: 1.02;
            color: #ffffff;
        }

        .app-subtitle {
            margin-top: 8px;
            width: 260px;
            color: #9CA3AF;
            font-size: 16px;
            line-height: 1.3;
        }

        .workspace-card {
            background: rgba(15, 23, 42, 0.52);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 18px 45px rgba(0,0,0,0.18);
            margin-bottom: 18px;
        }

        .sidebar-profile {
            padding: 14px 12px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 16px;
            background: rgba(15, 23, 42, 0.58);
            margin-bottom: 14px;
        }

        .history-title {
            color: #cbd5e1;
            font-size: 14px;
            font-weight: 800;
            margin-top: 14px;
            margin-bottom: 8px;
            letter-spacing: .2px;
        }

        .history-count {
            color: #64748b;
            font-size: 12px;
            margin-bottom: 8px;
        }

        div[data-testid="stSidebar"] .stButton > button {
            height: auto;
            min-height: 38px;
            padding: 8px 10px;
            text-align: left;
            justify-content: flex-start;
            background: rgba(15, 23, 42, 0.72) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            box-shadow: none !important;
            font-size: 13px;
            font-weight: 650;
        }

        div[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(30, 41, 59, 0.95) !important;
            border-color: rgba(239, 68, 68, 0.35) !important;
            transform: none;
        }

        /* Hide default Streamlit chat message shells if any old calls remain */
        [data-testid="stChatMessage"] {
            display: none !important;
        }

        .chat-row {
            display: flex;
            align-items: flex-start;
            gap: 14px;
            margin: 18px 0;
            width: 100%;
        }

        .chat-icon {
            width: 54px;
            height: 54px;
            min-width: 54px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            line-height: 1;
            font-weight: 800;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        }

        .user-icon {
            background: linear-gradient(135deg, #ff5a2f 0%, #ef233c 100%);
            color: white;
        }

        .assistant-icon {
            background: #ffffff;
            color: #222222;
            border: 1px solid rgba(255,255,255,0.80);
        }

        .assistant-icon img {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            object-fit: contain;
            display: block;
        }

        .chat-bubble {
            width: 100%;
            background: rgba(30, 41, 59, 0.74);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            padding: 15px 18px;
            color: #f8fafc;
            line-height: 1.58;
            overflow-wrap: anywhere;
            box-shadow: 0 14px 32px rgba(0,0,0,0.16);
        }

        .user-bubble {
            background: rgba(30, 64, 175, 0.34);
            border-color: rgba(96, 165, 250, 0.22);
        }

        .assistant-bubble {
            background: rgba(15, 23, 42, 0.58);
            border-color: rgba(245, 158, 11, 0.22);
        }

        .chat-bubble h1,
        .chat-bubble h2,
        .chat-bubble h3 {
            margin-top: 8px;
            margin-bottom: 10px;
            color: #ffffff;
            line-height: 1.2;
        }

        .chat-bubble ul {
            margin-top: 6px;
            margin-bottom: 10px;
            padding-left: 22px;
        }

        .chat-bubble li {
            margin-bottom: 3px;
        }

        .chat-bubble table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 14px;
            line-height: 1.45;
            overflow: hidden;
            border-radius: 10px;
        }

        .chat-bubble th {
            background: rgba(148, 163, 184, 0.18);
            color: #f8fafc;
            font-weight: 750;
            text-align: left;
            padding: 8px 10px;
            border: 1px solid rgba(148, 163, 184, 0.22);
        }

        .chat-bubble td {
            color: #e5e7eb;
            padding: 8px 10px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            vertical-align: top;
        }

        .chat-bubble tr:nth-child(even) td {
            background: rgba(15, 23, 42, 0.22);
        }

        .assistant-section-card {
            background: rgba(15, 23, 42, 0.52);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 20px;
            padding: 22px 24px;
            margin-bottom: 18px;
            box-shadow: 0 18px 45px rgba(0,0,0,0.18);
        }

        .assistant-section-title {
            color: #ffffff;
            font-size: 31px;
            font-weight: 850;
            margin: 0 0 8px 0;
        }

        .assistant-section-subtitle {
            color: #94a3b8;
            font-size: 15px;
            margin: 0;
        }

        [data-testid="stFileUploader"] {
            background: rgba(15, 23, 42, 0.45);
            border: 1px dashed rgba(148, 163, 184, 0.28);
            border-radius: 18px;
            padding: 14px;
        }

        .footer-note {
            text-align: center;
            color: #94a3b8;
            margin-top: 34px;
            font-size: 14px;
        }


        /* ============================================================
           Compact ChatGPT-style UI refinements
        ============================================================ */
        .chat-row {
            gap: 10px !important;
            margin: 12px 0 !important;
        }

        .chat-icon {
            width: 40px !important;
            height: 40px !important;
            min-width: 40px !important;
            border-radius: 12px !important;
            font-size: 22px !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.20) !important;
        }

        .assistant-icon img {
            width: 32px !important;
            height: 32px !important;
            border-radius: 9px !important;
        }

        .chat-bubble {
            font-size: 15px !important;
            line-height: 1.62 !important;
            padding: 13px 16px !important;
            border-radius: 14px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
        }

        .chat-bubble h1 {
            font-size: 22px !important;
            line-height: 1.25 !important;
            margin: 6px 0 10px 0 !important;
        }

        .chat-bubble h2 {
            font-size: 19px !important;
            line-height: 1.28 !important;
            margin: 12px 0 8px 0 !important;
        }

        .chat-bubble h3 {
            font-size: 16px !important;
            line-height: 1.35 !important;
            margin: 10px 0 6px 0 !important;
        }

        .chat-bubble div,
        .chat-bubble li {
            font-size: 15px !important;
        }

        .chat-bubble ul {
            margin-top: 4px !important;
            margin-bottom: 8px !important;
            padding-left: 20px !important;
        }

        .assistant-section-card {
            padding: 18px 20px !important;
            border-radius: 18px !important;
            margin-bottom: 14px !important;
        }

        .assistant-section-title {
            font-size: 26px !important;
            line-height: 1.2 !important;
        }

        .assistant-section-subtitle {
            font-size: 14px !important;
        }

        /* ChatGPT-style compact sidebar history */
        .history-title {
            font-size: 13px !important;
            font-weight: 700 !important;
            color: #cbd5e1 !important;
            margin: 14px 0 6px 0 !important;
        }

        .history-count {
            font-size: 11px !important;
            color: #8b97a8 !important;
            margin-bottom: 6px !important;
        }

        div[data-testid="stSidebar"] .stButton > button {
            min-height: 32px !important;
            height: auto !important;
            padding: 6px 8px !important;
            border-radius: 9px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            color: #dbe7f5 !important;
            box-shadow: none !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            line-height: 1.25 !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }

        div[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(148, 163, 184, 0.12) !important;
            border-color: rgba(148, 163, 184, 0.10) !important;
            color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stSidebar"] button[kind="secondary"] {
            box-shadow: none !important;
        }

        .sidebar-profile {
            padding: 12px 11px !important;
            border-radius: 14px !important;
        }

        .history-current-note {
            color: #94a3b8;
            font-size: 11px;
            margin-top: 6px;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def apply_login_layout_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 680px !important;
            padding-top: 64px !important;
            padding-bottom: 40px !important;
        }

        section[data-testid="stSidebar"] { display: none !important; }

        .login-logo {
            text-align: center;
            margin-bottom: 22px;
        }

        .login-logo img {
            width: 310px;
            max-width: 92%;
            border-radius: 16px;
            object-fit: contain;
            filter: drop-shadow(0 18px 34px rgba(0,0,0,0.30));
        }

        .login-heading {
            text-align: center;
            margin-top: 4px;
            margin-bottom: 30px;
        }

        .login-heading-main {
            font-size: 38px;
            font-weight: 850;
            color: #ffffff;
            line-height: 1.15;
            letter-spacing: -0.5px;
        }

        .login-heading-sub {
            font-size: 18px;
            color: #B6BDC8;
            margin-top: 8px;
            letter-spacing: 0.4px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def apply_app_layout_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1550px !important;
            padding-top: 34px !important;
            padding-bottom: 50px !important;
            padding-left: 54px !important;
            padding-right: 54px !important;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 18px !important;
                padding-right: 18px !important;
            }

            .app-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .app-title { font-size: 36px; }
            .app-subtitle { width: 240px; }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


inject_base_css()

# ============================================================
# Helpers
# ============================================================

@st.cache_data(show_spinner=False)
def get_logo_base64():
    if LOGO_FILE.exists():
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def now_iso():
    return datetime.now(timezone.utc).isoformat()

def inline_format(text):
    """Escape text and support simple markdown bold inside custom HTML bubbles."""
    safe = html.escape(str(text or ""))
    parts = safe.split("**")
    if len(parts) > 1:
        rebuilt = ""
        for i, part in enumerate(parts):
            rebuilt += f"<strong>{part}</strong>" if i % 2 else part
        safe = rebuilt
    return safe


def is_markdown_table_separator(line):
    """Return True for markdown separator rows like |---|---|."""
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if not cells:
        return False
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def split_markdown_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_to_html(table_lines):
    """Convert a basic markdown table to HTML."""
    if len(table_lines) < 2:
        return ""

    headers = split_markdown_table_row(table_lines[0])
    body_lines = table_lines[2:] if is_markdown_table_separator(table_lines[1]) else table_lines[1:]

    html_rows = ["<table>"]
    html_rows.append("<thead><tr>")
    for header in headers:
        html_rows.append(f"<th>{inline_format(header)}</th>")
    html_rows.append("</tr></thead>")

    html_rows.append("<tbody>")
    for row_line in body_lines:
        cells = split_markdown_table_row(row_line)
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        html_rows.append("<tr>")
        for cell in cells[:len(headers)]:
            html_rows.append(f"<td>{inline_format(cell)}</td>")
        html_rows.append("</tr>")
    html_rows.append("</tbody></table>")
    return "\n".join(html_rows)


def html_from_text(text):
    """Small markdown-like renderer for custom chat bubbles, including basic tables."""
    if text is None:
        return ""

    lines = str(text).splitlines()
    html_lines = []
    in_ul = False
    i = 0

    def close_ul():
        nonlocal in_ul
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            close_ul()
            html_lines.append("<br>")
            i += 1
            continue

        stripped = line.strip()

        # Markdown table support:
        # | Header | Header |
        # |---|---|
        # | Cell | Cell |
        if (
            "|" in stripped
            and i + 1 < len(lines)
            and is_markdown_table_separator(lines[i + 1])
        ):
            close_ul()
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            html_lines.append(table_to_html(table_lines))
            continue

        if stripped.startswith("### "):
            close_ul()
            html_lines.append(f"<h3>{inline_format(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_ul()
            html_lines.append(f"<h2>{inline_format(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_ul()
            html_lines.append(f"<h1>{inline_format(stripped[2:])}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("• "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{inline_format(stripped[2:])}</li>")
        else:
            close_ul()
            html_lines.append(f"<div>{inline_format(stripped)}</div>")

        i += 1

    close_ul()
    return "\n".join(html_lines)


def render_chat_message(role, content):
    if role == "user":
        icon_html = "👤"
        icon_class = "user-icon"
        bubble_class = "user-bubble"
    else:
        logo_base64 = get_logo_base64()
        if logo_base64:
            icon_html = f'<img src="data:image/png;base64,{logo_base64}" alt="AutoTecPro AI">'
        else:
            icon_html = "AI"
        icon_class = "assistant-icon"
        bubble_class = "assistant-bubble"

    st.markdown(
        f"""
        <div class="chat-row">
            <div class="chat-icon {icon_class}">{icon_html}</div>
            <div class="chat-bubble {bubble_class}">
                {html_from_text(content)}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def create_login_session(username, role):
    result = supabase.table("login_sessions").insert({
        "username": username,
        "role": role,
        "active": True,
        "created_at": now_iso()
    }).execute()
    return result.data[0]["id"]


def restore_login_session():
    token = st.query_params.get("session")
    if not token:
        return

    try:
        result = (
            supabase
            .table("login_sessions")
            .select("*")
            .eq("id", token)
            .eq("active", True)
            .execute()
        )

        if result.data:
            session = result.data[0]
            st.session_state.logged_in = True
            st.session_state.username = session["username"]
            st.session_state.role = session["role"]
            if "messages" not in st.session_state:
                st.session_state.messages = []
            if "conversation_id" not in st.session_state:
                st.session_state.conversation_id = None
    except Exception:
        # If the login_sessions table does not exist yet, fall back to normal login.
        return


def logout_user():
    token = st.query_params.get("session")

    if token:
        try:
            supabase.table("login_sessions").update({
                "active": False
            }).eq("id", token).execute()
        except Exception:
            pass

    st.query_params.clear()
    st.session_state.logged_in = False
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()


# ============================================================
# Login Screen
# ============================================================

def login_screen():
    apply_login_layout_css()
    logo_base64 = get_logo_base64()

    if logo_base64:
        st.markdown(
            f"""
            <div class="login-logo">
                <img src="data:image/png;base64,{logo_base64}">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="login-logo">
                <h1 style="font-size:48px;margin:0;color:white;">AutoTecPro</h1>
                <p style="color:#94a3b8;margin-top:6px;">Driven by Innovation</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="login-heading">
            <div class="login-heading-main">AutoTecPro AI Login</div>
            <div class="login-heading-sub">Internal AI Assistant</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", placeholder="Enter your password", type="password")
        login_submitted = st.form_submit_button("Login", use_container_width=True)

    if login_submitted:
        username = username.strip()

        if not username or not password:
            st.warning("Please enter your username and password.")
            return

        try:
            result = (
                supabase
                .table("users")
                .select("*")
                .eq("username", username)
                .eq("password", password)
                .eq("active", True)
                .execute()
            )

            if result.data:
                user = result.data[0]
                try:
                    session_id = create_login_session(user["username"], user["role"])
                    st.query_params["session"] = session_id
                except Exception:
                    # If login_sessions table is not created yet, login still works for this session.
                    pass

                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.role = user["role"]
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.rerun()
            else:
                st.error("Invalid username or password.")

        except Exception as e:
            st.error(f"Login failed: {e}")

    st.markdown(
        '<div class="footer-note">© 2026 AutoTecPro. All rights reserved.</div>',
        unsafe_allow_html=True
    )


# ============================================================
# Login Check
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    restore_login_session()

if not st.session_state.logged_in:
    login_screen()
    st.stop()

apply_app_layout_css()

# ============================================================
# Header After Login
# ============================================================

logo_base64 = get_logo_base64()

if logo_base64:
    st.markdown(
        f"""
        <div class="app-header">
            <img src="data:image/png;base64,{logo_base64}">
            <div style="display:flex;flex-direction:column;justify-content:center;">
                <h1 class="app-title">AutoTecPro AI</h1>
                <div class="app-subtitle">
                    Internal AI Assistant<br>
                    for AutoTecPro
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.title("AutoTecPro AI")
    st.caption("Internal AI Assistant for AutoTecPro")

# ============================================================
# Session Defaults
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# ============================================================
# Sidebar
# ============================================================

st.sidebar.markdown(
    f"""
    <div class="sidebar-profile">
        <div style="font-size:15px;color:#94a3b8;">Logged in as</div>
        <div style="font-size:20px;font-weight:800;color:white;margin-top:4px;">
            👤 {st.session_state.username}
        </div>
        <div style="font-size:13px;color:#cbd5e1;margin-top:6px;">
            Role: <b>{st.session_state.role}</b>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

menu_items = [
    "🔧 Technical Support",
    "📈 Sales & Marketing",
    "🎨 Graphic Marketing"
]

if st.session_state.role == "admin":
    menu_items.append("⚙️ Admin Panel")

assistant = st.sidebar.radio("AI Workspace", menu_items)

if "current_assistant" not in st.session_state:
    st.session_state.current_assistant = assistant

if st.session_state.current_assistant != assistant:
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.current_assistant = assistant
    st.rerun()

if st.sidebar.button("🧹 New Case / Clear Chat"):
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()

if st.sidebar.button("Logout"):
    logout_user()

# ============================================================
# AI Helper Functions
# ============================================================

def image_to_data_url(uploaded_file):
    encoded = base64.b64encode(uploaded_file.getvalue()).decode()
    return f"data:{uploaded_file.type};base64,{encoded}"


def get_instructions(selected_assistant):
    if selected_assistant == "🔧 Technical Support":
        return """
You are AutoTecPro Technical Support AI.

Always search the Technical Support Vector Store first.

Use previous messages as context.

Answer in this order when useful:
1. Vehicle Identification
2. Summary
3. Likely Cause
4. Troubleshooting
5. Information to Request
6. Customer Reply Draft
7. Escalation

Never invent technical information.
If documentation is unavailable, clearly say so.
"""

    if selected_assistant == "📈 Sales & Marketing":
        return """
You are AutoTecPro Sales & Marketing AI.

Always search the Sales & Marketing Vector Store before answering.

Help with product recommendations, compatibility, specifications,
dealer messages, customer replies, Amazon listings, website copy,
social media, promotions, warranty, and return policy.

Never invent pricing or compatibility.
"""

    return """
You are AutoTecPro Graphic Marketing AI.

Analyze uploaded images when provided.

Help create ads, banners, YouTube thumbnails, product photography ideas,
social media posts, marketing campaigns, and image prompts.
"""


def build_user_input(prompt_text, uploaded_files):
    content = []

    if st.session_state.messages:
        memory_text = "Previous conversation in this case:\n\n"

        for msg in st.session_state.messages[-10:]:
            memory_text += f"{msg['role'].upper()}: {msg['content']}\n\n"

        content.append({"type": "input_text", "text": memory_text})

    if prompt_text:
        content.append({"type": "input_text", "text": prompt_text})

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.type.startswith("image/"):
                content.append({
                    "type": "input_image",
                    "image_url": image_to_data_url(uploaded_file)
                })
            else:
                uploaded_openai_file = client.files.create(
                    file=uploaded_file,
                    purpose="assistants"
                )

                content.append({
                    "type": "input_file",
                    "file_id": uploaded_openai_file.id
                })

    return [{"role": "user", "content": content}]


def ask_ai(prompt_text, uploaded_files):
    user_input = build_user_input(prompt_text, uploaded_files)
    instructions = get_instructions(assistant)

    if assistant == "🔧 Technical Support":
        response = client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            tools=[{"type": "file_search", "vector_store_ids": [TECHNICAL_VECTOR_STORE_ID]}],
            input=user_input
        )

    elif assistant == "📈 Sales & Marketing":
        response = client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            tools=[{"type": "file_search", "vector_store_ids": [SALES_VECTOR_STORE_ID]}],
            input=user_input
        )

    else:
        response = client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            input=user_input
        )

    return response.output_text


def upload_to_vector_store(uploaded_file, vector_store_id):
    openai_file = client.files.create(file=uploaded_file, purpose="assistants")
    client.vector_stores.files.create(vector_store_id=vector_store_id, file_id=openai_file.id)
    return openai_file.id

# ============================================================
# Supabase Chat History Helpers
# ============================================================


def clean_assistant_label(assistant_name):
    """Normalize assistant labels so history works even when labels include emoji."""
    value = str(assistant_name or "")
    for icon in ["🔧", "📈", "🎨", "⚙️", "⚙"]:
        value = value.replace(icon, "")
    return value.strip()


def conversation_title_from_text(text):
    clean = str(text or "").replace("\n", " ").strip()
    if not clean:
        return "New Case"
    return clean[:55]


def create_conversation(username, assistant_name, first_message=None):
    """Create a new conversation and return its ID."""
    result = supabase.table("conversations").insert({
        "username": username,
        "assistant": clean_assistant_label(assistant_name),
        "title": conversation_title_from_text(first_message),
        "archived": False,
        "pinned": False,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }).execute()

    if not result.data:
        raise RuntimeError("Conversation was not created. Supabase returned no data.")

    return result.data[0]["id"]


def save_message(conversation_id, role, content):
    """Save one chat message into Supabase."""
    if not conversation_id:
        raise RuntimeError("Missing conversation_id. Message was not saved.")

    supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": now_iso()
    }).execute()

    supabase.table("conversations").update({
        "updated_at": now_iso()
    }).eq("id", conversation_id).execute()


def load_messages(conversation_id):
    """Load all messages for a selected conversation."""
    if not conversation_id:
        return []

    result = (
        supabase
        .table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    return [
        {"role": item.get("role", "assistant"), "content": item.get("content", "")}
        for item in (result.data or [])
    ]


def load_conversations(username, role=None):
    """
    Reliable history loader.

    Important: this intentionally does NOT filter by assistant.
    Earlier versions filtered by assistant label and username too strictly,
    which caused saved cases to disappear from the sidebar.
    """
    result = (
        supabase
        .table("conversations")
        .select("*")
        .order("updated_at", desc=True)
        .limit(100)
        .execute()
    )

    rows = result.data or []

    def is_active(row):
        value = row.get("archived")
        return not (value is True or str(value).lower() == "true")

    active_rows = [row for row in rows if is_active(row)]

    # Pinned conversations should stay at the top, similar to ChatGPT.
    active_rows = sorted(
        active_rows,
        key=lambda row: (
            not bool(row.get("pinned", False)),
            str(row.get("updated_at") or row.get("created_at") or "")
        ),
        reverse=False
    )

    # Admin can see all cases. Staff sees their own cases first.
    if str(role or "").lower() == "admin":
        return active_rows[:30]

    own_rows = [
        row for row in active_rows
        if str(row.get("username", "")).lower() == str(username or "").lower()
    ]

    # Fallback: if username changed during testing, show all active rows.
    return (own_rows or active_rows)[:30]


def archive_conversation(conversation_id):
    if conversation_id:
        supabase.table("conversations").update({
            "archived": True,
            "updated_at": now_iso()
        }).eq("id", conversation_id).execute()


def delete_conversation(conversation_id):
    """Permanently delete a conversation and its messages."""
    if not conversation_id:
        return

    # The messages table should also delete by cascade, but this makes it explicit.
    supabase.table("messages").delete().eq("conversation_id", conversation_id).execute()
    supabase.table("conversations").delete().eq("id", conversation_id).execute()


def toggle_pin_conversation(conversation_id, pinned):
    """Pin or unpin a conversation in the sidebar."""
    if not conversation_id:
        return

    supabase.table("conversations").update({
        "pinned": bool(pinned),
        "updated_at": now_iso()
    }).eq("id", conversation_id).execute()


def format_history_date(value):
    if not value:
        return ""

    text = str(value)[:10]
    try:
        dt = datetime.fromisoformat(text)
        return dt.strftime("%b %-d")
    except Exception:
        try:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%b %d").replace(" 0", " ")
        except Exception:
            return text


def get_current_conversation_title():
    cid = st.session_state.get("conversation_id")
    if not cid:
        return "New Case"
    try:
        result = (
            supabase
            .table("conversations")
            .select("title")
            .eq("id", cid)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("title") or "New Case"
    except Exception:
        pass
    return "New Case"


# ============================================================
# Chat History Sidebar
# ============================================================

if assistant != "⚙️ Admin Panel":
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="history-title">Chat History</div>', unsafe_allow_html=True)

    top_left, top_right = st.sidebar.columns([0.78, 0.22], gap="small")
    with top_left:
        st.caption("Saved cases")
    with top_right:
        if st.button("↻", key="refresh_history", help="Refresh history"):
            st.rerun()

    try:
        conversations = load_conversations(
            st.session_state.username,
            st.session_state.role
        )

        st.sidebar.markdown(
            f'<div class="history-count">{len(conversations)} conversation(s)</div>',
            unsafe_allow_html=True
        )

        if conversations:
            pinned_conversations = [c for c in conversations if c.get("pinned")]
            normal_conversations = [c for c in conversations if not c.get("pinned")]

            if pinned_conversations:
                st.sidebar.caption("Pinned")

            ordered_sections = []
            if pinned_conversations:
                ordered_sections.append(pinned_conversations)
            if normal_conversations:
                if pinned_conversations:
                    st.sidebar.caption("Recent")
                ordered_sections.append(normal_conversations)

            for section in ordered_sections:
                for convo in section:
                    convo_id = convo["id"]
                    title = convo.get("title") or "New Case"
                    assistant_label = clean_assistant_label(convo.get("assistant") or "")
                    updated_at = format_history_date(convo.get("updated_at") or convo.get("created_at"))
                    pinned = bool(convo.get("pinned", False))
                    is_current = st.session_state.conversation_id == convo_id

                    if len(title) > 32:
                        title = title[:32] + "..."

                    meta_parts = []
                    if assistant_label:
                        meta_parts.append(assistant_label)
                    if updated_at:
                        meta_parts.append(updated_at)
                    meta = " · ".join(meta_parts)

                    active_mark = "● " if is_current else ""
                    pin_icon = "📌" if pinned else "☆"
                    history_label = f"{active_mark}{title}"
                    if meta:
                        history_label += f"\n{meta}"

                    item_col, pin_col, delete_col = st.sidebar.columns([0.74, 0.13, 0.13], gap="small")

                    with item_col:
                        if st.button(history_label, key=f"open_{convo_id}", help="Open conversation"):
                            st.session_state.conversation_id = convo_id
                            st.session_state.messages = load_messages(convo_id)
                            st.rerun()

                    with pin_col:
                        if st.button(pin_icon, key=f"pin_{convo_id}", help="Pin / unpin"):
                            try:
                                toggle_pin_conversation(convo_id, not pinned)
                                st.rerun()
                            except Exception as e:
                                st.sidebar.error(f"Pin failed: {e}")

                    with delete_col:
                        if st.button("🗑", key=f"delete_{convo_id}", help="Delete conversation"):
                            try:
                                delete_conversation(convo_id)
                                if st.session_state.conversation_id == convo_id:
                                    st.session_state.conversation_id = None
                                    st.session_state.messages = []
                                st.rerun()
                            except Exception as e:
                                st.sidebar.error(f"Delete failed: {e}")
        else:
            st.sidebar.caption("No saved cases yet.")

        if st.session_state.conversation_id:
            current_title = get_current_conversation_title()
            st.sidebar.markdown(
                f'<div class="history-current-note">Current: {html.escape(current_title)}</div>',
                unsafe_allow_html=True
            )

            if st.sidebar.button("Archive current case", key="archive_current_case"):
                archive_conversation(st.session_state.conversation_id)
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.rerun()

    except Exception as e:
        st.sidebar.error(f"Chat history error: {e}")

# ============================================================
# Admin Panel
# ============================================================

if assistant == "⚙️ Admin Panel":

    st.markdown('<div class="workspace-card">', unsafe_allow_html=True)
    st.subheader("⚙️ Admin Panel")
    st.caption("Manage users and upload new documents into your AI knowledge base.")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["👥 Manage Users", "📚 Upload Knowledge"])

    with tab1:
        st.markdown("### Current Users")
        users = supabase.table("users").select("*").execute().data

        for user in users:
            st.write(f"**{user['username']}** | {user['role']} | Active: {user['active']}")

        st.markdown("---")
        st.markdown("### Add / Update User")

        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["staff", "admin"])
        new_active = st.checkbox("Active", value=True)

        if st.button("Save User"):
            if new_username and new_password:
                existing = (
                    supabase
                    .table("users")
                    .select("*")
                    .eq("username", new_username)
                    .execute()
                    .data
                )

                if existing:
                    supabase.table("users").update({
                        "password": new_password,
                        "role": new_role,
                        "active": new_active
                    }).eq("username", new_username).execute()
                    st.success("User updated successfully.")
                else:
                    supabase.table("users").insert({
                        "username": new_username,
                        "password": new_password,
                        "role": new_role,
                        "active": new_active
                    }).execute()
                    st.success("User added successfully.")

                st.rerun()
            else:
                st.warning("Please enter username and password.")

    with tab2:
        st.markdown("### Upload Documents to Knowledge Base")

        database_choice = st.selectbox(
            "Choose database",
            ["Technical Support Database", "Sales & Marketing Database"]
        )

        admin_files = st.file_uploader(
            "Upload documents",
            type=["pdf", "txt", "docx"],
            accept_multiple_files=True
        )

        if st.button("Upload to Knowledge Base"):
            if not admin_files:
                st.warning("Please upload at least one document.")
            else:
                if database_choice == "Technical Support Database":
                    selected_vector_store_id = TECHNICAL_VECTOR_STORE_ID
                else:
                    selected_vector_store_id = SALES_VECTOR_STORE_ID

                for admin_file in admin_files:
                    try:
                        file_id = upload_to_vector_store(admin_file, selected_vector_store_id)
                        st.success(f"Uploaded: {admin_file.name} | File ID: {file_id}")
                    except Exception as e:
                        st.error(f"Failed to upload {admin_file.name}: {e}")

# ============================================================
# Main Chat UI
# ============================================================

else:

    st.markdown(
        f"""
        <div class="assistant-section-card">
            <div class="assistant-section-title">{assistant}</div>
            <p class="assistant-section-subtitle">
                Upload photos, PDFs, or TXT files, then ask AutoTecPro AI for support.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploaded_files = st.file_uploader(
        "📎 Attach files or photos",
        type=["jpg", "jpeg", "png", "pdf", "txt"],
        accept_multiple_files=True,
        key="chat_file_uploader"
    )

    for msg in st.session_state.messages:
        render_chat_message(msg["role"], msg["content"])

    prompt = st.chat_input("Message AutoTecPro AI...")

    if prompt:
        user_display = prompt

        if uploaded_files:
            file_names = ", ".join([file.name for file in uploaded_files])
            user_display += f"\n\n📎 Attached: {file_names}"

        if st.session_state.conversation_id is None:
            try:
                st.session_state.conversation_id = create_conversation(
                    st.session_state.username,
                    assistant,
                    user_display
                )
            except Exception as e:
                st.error(f"Could not create chat history case: {e}")
                st.session_state.conversation_id = None

        st.session_state.messages.append({
            "role": "user",
            "content": user_display
        })

        try:
            save_message(st.session_state.conversation_id, "user", user_display)
        except Exception as e:
            st.warning(f"User message was not saved to history: {e}")

        render_chat_message("user", user_display)

        with st.spinner("Searching AutoTecPro knowledge base..."):
            answer = ask_ai(prompt, uploaded_files)

        render_chat_message("assistant", answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        try:
            save_message(st.session_state.conversation_id, "assistant", answer)
        except Exception as e:
            st.warning(f"AI answer was not saved to history: {e}")

        st.rerun()
