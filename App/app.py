import streamlit as st
from openai import OpenAI
from pathlib import Path
import base64
from datetime import datetime, timezone
from config import supabase

# ============================================================
# App Paths / API
# ============================================================

BASE_DIR = Path(__file__).parent.parent
APP_DIR = Path(__file__).parent
LOGO_FILE = APP_DIR / "logo.png"

api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

TECHNICAL_VECTOR_STORE_ID = "vs_6a4e9facdf2c8191b6c712329e398490"
SALES_VECTOR_STORE_ID = "vs_6a4eaf5d33a081919722e8628a1c5e71"

st.set_page_config(
    page_title="AutoTecPro AI",
    page_icon="🤖",
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

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border: 1px solid var(--atp-red) !important;
            box-shadow: 0 0 0 1px var(--atp-red) !important;
        }

        .stButton > button {
            width: 100%;
            height: 46px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(90deg, var(--atp-red), var(--atp-red-dark));
            color: white;
            font-weight: 750;
            font-size: 15px;
            transition: 0.2s ease;
        }

        .stButton > button:hover {
            background: linear-gradient(90deg, #f87171, var(--atp-red));
            color: white;
            border: 1px solid rgba(255,255,255,0.18);
            transform: translateY(-1px);
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

        [data-testid="stChatMessage"] {
            background: rgba(15, 23, 42, 0.40);
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 18px;
            padding: 12px;
            margin-bottom: 12px;
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

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", placeholder="Enter your password", type="password")

    if st.button("Login", use_container_width=True):
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
    st.session_state.logged_in = False
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()

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
# Optional Supabase Chat History Helpers
# ============================================================

def create_conversation(username, assistant_name, first_message=None):
    title = "New Case"

    if first_message:
        clean = first_message.replace("\n", " ").strip()
        title = clean[:48] if clean else "New Case"

    result = supabase.table("conversations").insert({
        "username": username,
        "assistant": assistant_name,
        "title": title,
        "archived": False,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }).execute()

    return result.data[0]["id"]


def save_message(conversation_id, role, content):
    if not conversation_id:
        return

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
    result = (
        supabase
        .table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    return [{"role": item["role"], "content": item["content"]} for item in result.data]


def load_conversations(username, assistant_name):
    result = (
        supabase
        .table("conversations")
        .select("*")
        .eq("username", username)
        .eq("assistant", assistant_name)
        .eq("archived", False)
        .order("updated_at", desc=True)
        .limit(12)
        .execute()
    )

    return result.data


def archive_conversation(conversation_id):
    if conversation_id:
        supabase.table("conversations").update({
            "archived": True,
            "updated_at": now_iso()
        }).eq("id", conversation_id).execute()


# ============================================================
# Chat History Sidebar
# ============================================================

if assistant != "⚙️ Admin Panel":
    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="history-title">Chat History</div>', unsafe_allow_html=True)

    try:
        conversations = load_conversations(st.session_state.username, assistant)

        if conversations:
            for convo in conversations:
                title = convo.get("title") or "New Case"
                if len(title) > 34:
                    title = title[:34] + "..."

                if st.sidebar.button(f"💬 {title}", key=f"convo_{convo['id']}"):
                    st.session_state.conversation_id = convo["id"]
                    st.session_state.messages = load_messages(convo["id"])
                    st.rerun()
        else:
            st.sidebar.caption("No saved cases yet.")

        if st.session_state.conversation_id:
            if st.sidebar.button("🗄️ Archive Current Case"):
                archive_conversation(st.session_state.conversation_id)
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.rerun()

    except Exception:
        st.sidebar.caption("Chat history unavailable. Create Supabase conversations/messages tables to enable it.")

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

    st.markdown('<div class="workspace-card">', unsafe_allow_html=True)
    st.subheader(assistant)
    st.caption("Upload photos, PDFs, or TXT files, then ask AutoTecPro AI for support.")
    st.markdown('</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "📎 Attach files or photos",
        type=["jpg", "jpeg", "png", "pdf", "txt"],
        accept_multiple_files=True,
        key="chat_file_uploader"
    )

    for msg in st.session_state.messages:
        avatar = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    prompt = st.chat_input("Message AutoTecPro AI...")
    send_button = st.button("Ask AI", use_container_width=True)

    if prompt or send_button:
        if not prompt and not uploaded_files:
            st.warning("Please type a message or upload a file.")
        else:
            user_display = prompt if prompt else "[Uploaded file only]"

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
                except Exception:
                    st.session_state.conversation_id = None

            st.session_state.messages.append({"role": "user", "content": user_display})

            try:
                save_message(st.session_state.conversation_id, "user", user_display)
            except Exception:
                pass

            with st.chat_message("user", avatar="👤"):
                st.markdown(user_display)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Searching AutoTecPro knowledge base..."):
                    answer = ask_ai(prompt, uploaded_files)
                    st.markdown(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})

            try:
                save_message(st.session_state.conversation_id, "assistant", answer)
            except Exception:
                pass
