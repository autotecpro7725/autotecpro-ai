import streamlit as st
from openai import OpenAI
from pathlib import Path
import base64
from config import supabase

BASE_DIR = Path(__file__).parent.parent
APP_DIR = Path(__file__).parent
LOGO_FILE = APP_DIR / "logo.png"

# OpenAI API Key - Streamlit Cloud
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

TECHNICAL_VECTOR_STORE_ID = "vs_6a4e9facdf2c8191b6c712329e398490"
SALES_VECTOR_STORE_ID = "vs_6a4eaf5d33a081919722e8628a1c5e71"

st.set_page_config(
    page_title="AutoTecPro AI",
    layout="wide"
)

def login_screen():
    st.title("AutoTecPro AI Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
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
            st.rerun()
        else:
            st.error("Invalid username or password.")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_screen()
    st.stop()

with open(LOGO_FILE, "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:18px; margin-bottom:25px;">
        <img src="data:image/png;base64,{logo_base64}"
             style="width:75px; height:75px; border-radius:14px; object-fit:contain;">
        <div>
            <h1 style="margin:0; padding:0; font-size:46px; font-weight:700;">
                AutoTecPro AI
            </h1>
            <p style="margin:0; color:#9CA3AF; font-size:18px;">
                Internal AI Assistant for AutoTecPro
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
st.sidebar.write(f"Role: **{st.session_state.role}**")

menu_items = [
    "🔧 Technical Support",
    "📈 Sales & Marketing",
    "🎨 Graphic Marketing"
]

if st.session_state.role == "admin":
    menu_items.append("⚙️ Admin Panel")

assistant = st.sidebar.radio("Choose AI Assistant", menu_items)

if st.sidebar.button("🧹 New Case / Clear Chat"):
    st.session_state.messages = []
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.messages = []
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_assistant" not in st.session_state:
    st.session_state.current_assistant = assistant

if st.session_state.current_assistant != assistant:
    st.session_state.messages = []
    st.session_state.current_assistant = assistant
    st.rerun()

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

        content.append({
            "type": "input_text",
            "text": memory_text
        })

    if prompt_text:
        content.append({
            "type": "input_text",
            "text": prompt_text
        })

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

    return [
        {
            "role": "user",
            "content": content
        }
    ]

def ask_ai(prompt_text, uploaded_files):
    user_input = build_user_input(prompt_text, uploaded_files)
    instructions = get_instructions(assistant)

    if assistant == "🔧 Technical Support":
        response = client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [TECHNICAL_VECTOR_STORE_ID]
                }
            ],
            input=user_input
        )

    elif assistant == "📈 Sales & Marketing":
        response = client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [SALES_VECTOR_STORE_ID]
                }
            ],
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
    openai_file = client.files.create(
        file=uploaded_file,
        purpose="assistants"
    )

    client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=openai_file.id
    )

    return openai_file.id

if assistant == "⚙️ Admin Panel":

    st.subheader("⚙️ Admin Panel")

    tab1, tab2 = st.tabs(["👥 Manage Users", "📚 Upload Knowledge"])

    with tab1:
        st.markdown("### Current Users")

        users = supabase.table("users").select("*").execute().data

        for user in users:
            st.write(
                f"**{user['username']}** | {user['role']} | Active: {user['active']}"
            )

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
            [
                "Technical Support Database",
                "Sales & Marketing Database"
            ]
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
                        file_id = upload_to_vector_store(
                            admin_file,
                            selected_vector_store_id
                        )
                        st.success(f"Uploaded: {admin_file.name} | File ID: {file_id}")
                    except Exception as e:
                        st.error(f"Failed to upload {admin_file.name}: {e}")

else:

    st.subheader(assistant)

    uploaded_files = st.file_uploader(
        "Attach files or photos",
        type=["jpg", "jpeg", "png", "pdf", "txt"],
        accept_multiple_files=True,
        key="chat_file_uploader"
    )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Message AutoTecPro AI...")

    send_button = st.button("Ask AI")

    if prompt or send_button:

        if not prompt and not uploaded_files:
            st.warning("Please type a message or upload a file.")

        else:
            user_display = prompt if prompt else "[Uploaded file only]"

            if uploaded_files:
                file_names = ", ".join([file.name for file in uploaded_files])
                user_display += f"\n\n📎 Attached: {file_names}"

            st.session_state.messages.append({
                "role": "user",
                "content": user_display
            })

            with st.chat_message("user"):
                st.markdown(user_display)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = ask_ai(prompt, uploaded_files)
                    st.markdown(answer)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })