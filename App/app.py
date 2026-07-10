import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from pathlib import Path
try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
import base64
import html
from datetime import datetime, timezone
import tempfile
import os
import re
import json
import time
import io
from difflib import SequenceMatcher
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
        

        /* ============================================================
           Final ChatGPT-style compact history sidebar
        ============================================================ */
        section[data-testid="stSidebar"] {
            width: 292px !important;
            min-width: 292px !important;
        }

        .history-title {
            font-size: 13px !important;
            font-weight: 700 !important;
            color: #d7dde7 !important;
            margin: 12px 0 4px 0 !important;
        }

        .history-count, .history-current-note {
            font-size: 11px !important;
            color: #8d98a8 !important;
            margin: 4px 0 !important;
            line-height: 1.25 !important;
        }

        .history-section-label {
            font-size: 11px !important;
            color: #8d98a8 !important;
            font-weight: 700 !important;
            margin: 10px 0 3px 2px !important;
            line-height: 1.2 !important;
        }

        .history-menu-title {
            font-size: 12px;
            color: #cbd5e1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 4px 8px 6px 8px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            margin-bottom: 4px;
        }

        /* Reduce vertical space in sidebar columns */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 2px !important;
        }

        /* Compact history row button */
        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
            min-height: 30px !important;
            height: 30px !important;
            padding: 4px 8px !important;
            margin: 0 !important;
            border-radius: 8px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #dbe7f5 !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            line-height: 1.15 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            align-items: center !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button p,
        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button div {
            text-align: left !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.15 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            display: block !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button:hover {
            background: rgba(148, 163, 184, 0.11) !important;
            color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Small three-dot popover trigger only, no arrow */
        section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
            width: 28px !important;
            min-width: 28px !important;
            max-width: 28px !important;
            height: 30px !important;
            min-height: 30px !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 8px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #aeb9c8 !important;
            font-size: 18px !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {
            background: rgba(148, 163, 184, 0.12) !important;
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button svg {
            display: none !important;
            width: 0 !important;
        }

        /* ChatGPT-style small floating menu */
        div[data-testid="stPopoverBody"],
        div[data-baseweb="popover"] div[role="dialog"] {
            width: 176px !important;
            min-width: 176px !important;
            max-width: 176px !important;
            padding: 6px !important;
            border-radius: 14px !important;
            background: rgba(32, 33, 35, 0.98) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            box-shadow: 0 12px 32px rgba(0,0,0,0.38) !important;
            backdrop-filter: blur(12px) !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button {
            height: 32px !important;
            min-height: 32px !important;
            padding: 6px 8px !important;
            border-radius: 8px !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #e5e7eb !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            transform: none !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button:hover {
            background: rgba(255,255,255,0.08) !important;
            color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button[kind="secondary"] {
            color: #e5e7eb !important;
        }


        /* ============================================================
           FINAL SIDEBAR POLISH - action buttons + history compactness
           This section intentionally overrides earlier sidebar button CSS.
        ============================================================ */

        section[data-testid="stSidebar"] {
            min-width: 292px !important;
            max-width: 292px !important;
        }

        /* General sidebar spacing */
        div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 0.20rem !important;
        }

        div[data-testid="stSidebar"] div[data-testid="column"] {
            padding: 0 !important;
        }

        div[data-testid="stSidebar"] hr {
            margin: 18px 0 16px 0 !important;
            border-color: rgba(148, 163, 184, 0.14) !important;
        }

        /* Profile and workspace compact */
        .sidebar-profile {
            padding: 10px 10px !important;
            border-radius: 13px !important;
            margin-bottom: 10px !important;
            box-shadow: none !important;
        }

        div[data-testid="stSidebar"] label[data-baseweb="radio"] {
            min-height: 28px !important;
            padding: 2px 4px !important;
            margin: 0 !important;
        }

        div[data-testid="stSidebar"] label[data-baseweb="radio"] p {
            font-size: 12.5px !important;
            line-height: 1.15 !important;
        }

        /* New Case + Logout area: lower, smaller, cleaner */
        .sidebar-action-area {
            margin-top: 22px !important;
            margin-bottom: 24px !important;
            padding-top: 4px !important;
        }

        .sidebar-action-area .stButton {
            margin: 0 !important;
            padding: 0 !important;
        }

        .sidebar-action-area .stButton > button {
            box-shadow: none !important;
            transform: none !important;
            border-radius: 9px !important;
            border: 1px solid rgba(148, 163, 184, 0.16) !important;
            font-size: 12.5px !important;
            font-weight: 650 !important;
            line-height: 1.1 !important;
        }

        .sidebar-newcase-btn {
            width: 142px !important;
            margin-bottom: 8px !important;
        }

        .sidebar-newcase-btn .stButton > button {
            width: 142px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 6px 10px !important;
            background: rgba(239, 68, 68, 0.90) !important;
            color: #ffffff !important;
        }

        .sidebar-newcase-btn .stButton > button:hover {
            background: rgba(248, 80, 58, 0.98) !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
        }

        .sidebar-logout-btn {
            width: 82px !important;
        }

        .sidebar-logout-btn .stButton > button {
            width: 82px !important;
            height: 30px !important;
            min-height: 30px !important;
            padding: 5px 9px !important;
            background: rgba(239, 68, 68, 0.78) !important;
            color: #ffffff !important;
        }

        .sidebar-logout-btn .stButton > button:hover {
            background: rgba(239, 68, 68, 0.94) !important;
        }

        /* History headings */
        .history-title {
            font-size: 13px !important;
            font-weight: 700 !important;
            color: #f1f5f9 !important;
            margin: 14px 0 0 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
        }

        .history-count,
        .history-current-note {
            font-size: 11px !important;
            color: #94a3b8 !important;
            margin: 4px 0 !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        .history-section-label {
            font-size: 11px !important;
            color: #94a3b8 !important;
            font-weight: 700 !important;
            margin: 8px 0 3px 2px !important;
            line-height: 1.2 !important;
        }

        /* Compact history rows */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton {
            margin: 0 !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
            min-height: 28px !important;
            height: 28px !important;
            padding: 3px 8px !important;
            margin: 0 !important;
            border-radius: 7px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #dbe7f5 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            line-height: 1 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            align-items: center !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            transform: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button:hover {
            background: rgba(148, 163, 184, 0.11) !important;
            color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Hide popover arrow icon and make three dot button align */
        section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
            width: 26px !important;
            min-width: 26px !important;
            max-width: 26px !important;
            height: 28px !important;
            min-height: 28px !important;
            max-height: 28px !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 7px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #aeb9c8 !important;
            font-size: 16px !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transform: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button svg {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {
            background: rgba(148, 163, 184, 0.13) !important;
            color: #ffffff !important;
        }

        /* Compact floating menu */
        div[data-testid="stPopoverBody"],
        div[data-baseweb="popover"] div[role="dialog"] {
            width: 172px !important;
            min-width: 172px !important;
            max-width: 172px !important;
            padding: 6px !important;
            border-radius: 12px !important;
            background: rgba(32, 33, 35, 0.98) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            box-shadow: 0 12px 32px rgba(0,0,0,0.38) !important;
            backdrop-filter: blur(12px) !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button {
            height: 30px !important;
            min-height: 30px !important;
            padding: 5px 8px !important;
            border-radius: 8px !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #e5e7eb !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            transform: none !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button:hover {
            background: rgba(255,255,255,0.08) !important;
            color: #ffffff !important;
        }

        .history-menu-title {
            font-size: 11.5px !important;
            color: #cbd5e1 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            padding: 3px 6px 5px 6px !important;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14) !important;
            margin-bottom: 4px !important;
        }

        .rename-box-title {
            font-size: 11px !important;
            color: #94a3b8 !important;
            margin: 6px 0 4px 0 !important;
        }

        div[data-testid="stSidebar"] div[data-testid="stForm"] {
            padding: 8px !important;
            border-radius: 10px !important;
            margin: 4px 0 6px 0 !important;
            background: rgba(15, 23, 42, 0.38) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            box-shadow: none !important;
        }

        div[data-testid="stSidebar"] input {
            height: 32px !important;
            min-height: 32px !important;
            font-size: 12px !important;
            border-radius: 8px !important;
        }

        /* ============================================================
           AI Learning Engine UI
        ============================================================ */
        .learning-card {
            background: rgba(15, 23, 42, 0.58);
            border: 1px solid rgba(34, 197, 94, 0.22);
            border-radius: 16px;
            padding: 14px 16px;
            margin: 14px 0 18px 50px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.14);
        }

        .learning-title {
            font-size: 14px;
            font-weight: 800;
            color: #dcfce7;
            margin-bottom: 4px;
        }

        .learning-subtitle {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 10px;
        }


        /* ============================================================
           FIX: Scrollable chat history list
        ============================================================ */
        div[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
            background: transparent !important;
        }

        .history-scroll-note {
            font-size: 10.5px;
            color: #64748b;
            margin-top: 2px;
            margin-bottom: 4px;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(.history-section-label) {
            gap: 1px !important;
        }


        /* ============================================================
           PRODUCTION FIX: Scrollable history area shows many cases
        ============================================================ */
        .history-scroll-container {
            max-height: 360px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            padding-right: 4px !important;
            margin-top: 2px !important;
            margin-bottom: 6px !important;
        }

        .history-scroll-container::-webkit-scrollbar {
            width: 5px !important;
        }

        .history-scroll-container::-webkit-scrollbar-track {
            background: transparent !important;
        }

        .history-scroll-container::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.35) !important;
            border-radius: 999px !important;
        }

        .history-scroll-container::-webkit-scrollbar-thumb:hover {
            background: rgba(148, 163, 184, 0.55) !important;
        }


        /* ============================================================
           FINAL OVERRIDE: More history rows visible + aligned menu
        ============================================================ */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
            max-height: 460px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar {
            width: 5px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.35) !important;
            border-radius: 999px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
            gap: 3px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
            height: 26px !important;
            min-height: 26px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
            height: 26px !important;
            min-height: 26px !important;
            width: 24px !important;
            min-width: 24px !important;
            max-width: 24px !important;
        }


        /* ============================================================
           MOBILE FIX: readable sidebar/history text on phones
           Desktop is not affected because this only applies <= 768px
        ============================================================ */
        @media (max-width: 768px) {
            /* Main mobile form/input readability */
            input,
            textarea,
            div[data-testid="stTextInputRootElement"] input,
            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
                caret-color: #ef4444 !important;
            }

            input::placeholder,
            textarea::placeholder,
            div[data-testid="stChatInput"] textarea::placeholder,
            div[data-testid="stChatInput"] input::placeholder {
                color: #6b7280 !important;
                -webkit-text-fill-color: #6b7280 !important;
                opacity: 1 !important;
            }

            div[data-testid="stChatInput"],
            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                background: #ffffff !important;
                border-color: rgba(239, 68, 68, 0.85) !important;
            }

            /* Upload widget readability on iPhone Safari */
            div[data-testid="stFileUploader"] section {
                background: #f8fafc !important;
            }

            div[data-testid="stFileUploader"] button,
            div[data-testid="stFileUploader"] button *,
            div[data-testid="stFileUploader"] small,
            div[data-testid="stFileUploader"] span,
            div[data-testid="stFileUploader"] p {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
                opacity: 1 !important;
            }

            /* Sidebar background and general sidebar text */
            section[data-testid="stSidebar"] {
                background: #0b1220 !important;
            }

            section[data-testid="stSidebar"],
            section[data-testid="stSidebar"] * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* History headings */
            .history-title,
            .history-section-label {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            .history-count,
            .history-current-note,
            .history-scroll-note {
                color: #cbd5e1 !important;
                -webkit-text-fill-color: #cbd5e1 !important;
                opacity: 1 !important;
            }

            /* History row buttons */
            section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button,
            section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button *,
            section[data-testid="stSidebar"] .stButton > button,
            section[data-testid="stSidebar"] .stButton > button * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Three-dot menu button */
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button,
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Floating popover menu */
            div[data-testid="stPopoverBody"],
            div[data-baseweb="popover"] div[role="dialog"] {
                background: rgba(32, 33, 35, 0.98) !important;
            }

            div[data-testid="stPopoverBody"],
            div[data-testid="stPopoverBody"] *,
            div[data-baseweb="popover"] div[role="dialog"],
            div[data-baseweb="popover"] div[role="dialog"] * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            .history-menu-title {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
            }

            /* Sidebar radio/workspace text */
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] label *,
            section[data-testid="stSidebar"] p,
            section[data-testid="stSidebar"] span {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Keep red action buttons readable */
            .sidebar-newcase-btn .stButton > button,
            .sidebar-newcase-btn .stButton > button *,
            .sidebar-logout-btn .stButton > button,
            .sidebar-logout-btn .stButton > button * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }
        }


        /* ============================================================
           Chat uploaded image previews
        ============================================================ */
        .chat-image-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 12px;
        }

        .chat-image-card {
            max-width: 260px;
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.40);
            box-shadow: 0 10px 26px rgba(0,0,0,0.18);
        }

        .chat-image-card img {
            width: 100%;
            height: auto;
            display: block;
            object-fit: contain;
        }

        .chat-image-caption {
            padding: 7px 9px;
            font-size: 11px !important;
            color: #cbd5e1 !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border-top: 1px solid rgba(148, 163, 184, 0.14);
        }

        @media (max-width: 768px) {
            .chat-image-card {
                max-width: 100% !important;
                width: 100% !important;
            }
        }


        /* Final safety: hide empty HTML-artifact code boxes in chat */
        .chat-bubble pre,
        .chat-bubble code {
            white-space: pre-wrap !important;
        }

        .chat-bubble pre:has(code:empty),
        .chat-bubble code:empty {
            display: none !important;
        }


        /* ============================================================
           ChatGPT 2026 custom history cards
           Replaces Streamlit history buttons with real HTML cards.
        ============================================================ */
        .history-shell {
            max-height: 460px;
            overflow-y: auto;
            overflow-x: visible;
            padding: 2px 4px 8px 0;
            margin-top: 4px;
        }

        .history-shell::-webkit-scrollbar {
            width: 5px;
        }

        .history-shell::-webkit-scrollbar-track {
            background: transparent;
        }

        .history-shell::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.28);
            border-radius: 999px;
        }

        .history-list {
            display: flex;
            flex-direction: column;
            gap: 2px;
            margin: 2px 0 8px 0;
        }

        .history-row-html {
            position: relative;
            display: flex;
            align-items: center;
            min-height: 32px;
            padding: 0 4px 0 0;
            border-radius: 9px;
            transition: background 140ms ease, color 140ms ease;
        }

        .history-row-html:hover {
            background: rgba(148, 163, 184, 0.11);
        }

        .history-row-html.active {
            background: rgba(148, 163, 184, 0.14);
        }

        .history-row-html.active::before {
            content: "";
            position: absolute;
            left: 0;
            top: 7px;
            bottom: 7px;
            width: 3px;
            border-radius: 99px;
            background: #ef4444;
        }

        .history-open {
            flex: 1;
            min-width: 0;
            height: 32px;
            display: flex;
            align-items: center;
            padding: 0 8px 0 10px;
            color: #dbe7f5 !important;
            -webkit-text-fill-color: #dbe7f5 !important;
            text-decoration: none !important;
            font-size: 12.5px;
            font-weight: 500;
            line-height: 1.15;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border-radius: 9px;
        }

        .history-row-html.active .history-open {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: 650;
            padding-left: 13px;
        }

        .history-menu {
            width: 28px;
            min-width: 28px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 140ms ease;
        }

        .history-row-html:hover .history-menu,
        .history-menu:has(details[open]),
        .history-row-html.active .history-menu {
            opacity: 1;
        }

        .history-menu details {
            position: relative;
            width: 28px;
            height: 28px;
        }

        .history-menu summary {
            list-style: none;
            cursor: pointer;
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #aeb9c8 !important;
            -webkit-text-fill-color: #aeb9c8 !important;
            font-size: 18px;
            line-height: 1;
            user-select: none;
        }

        .history-menu summary::-webkit-details-marker {
            display: none;
        }

        .history-menu summary:hover {
            background: rgba(148, 163, 184, 0.13);
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .history-menu-panel {
            position: absolute;
            z-index: 999999;
            top: 30px;
            right: 0;
            width: 178px;
            padding: 6px;
            border-radius: 14px;
            background: rgba(32, 33, 35, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.10);
            box-shadow: 0 12px 32px rgba(0,0,0,0.38);
            backdrop-filter: blur(12px);
        }

        .history-menu-panel .menu-title {
            color: #cbd5e1;
            -webkit-text-fill-color: #cbd5e1;
            font-size: 11.5px;
            padding: 4px 7px 7px 7px;
            margin-bottom: 4px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .history-menu-panel a {
            display: block;
            height: 31px;
            line-height: 31px;
            padding: 0 8px;
            border-radius: 8px;
            color: #e5e7eb !important;
            -webkit-text-fill-color: #e5e7eb !important;
            text-decoration: none !important;
            font-size: 12.5px;
            font-weight: 500;
        }

        .history-menu-panel a:hover {
            background: rgba(255,255,255,0.08);
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .history-menu-panel a.delete-link {
            color: #fca5a5 !important;
            -webkit-text-fill-color: #fca5a5 !important;
        }

        .history-menu-panel a.delete-link:hover {
            background: rgba(239,68,68,0.15);
            color: #fecaca !important;
            -webkit-text-fill-color: #fecaca !important;
        }

        @media (max-width: 768px) {
            .history-menu {
                opacity: 1 !important;
            }

            .history-open {
                font-size: 13px !important;
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
            }

            .history-row-html {
                background: rgba(31, 41, 55, 0.92);
                border: 1px solid rgba(148, 163, 184, 0.18);
                margin-bottom: 5px;
            }
        }

        #chat-bottom-anchor {
            width: 1px;
            height: 1px;
        }


        /* ============================================================
           Stable native ChatGPT-style history rows
           This avoids raw HTML being printed in Streamlit sidebar.
        ============================================================ */
        .history-shell,
        .history-row-html,
        .history-open,
        .history-menu,
        .history-menu-panel {
            display: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
            max-height: 460px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            border: none !important;
            background: transparent !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar {
            width: 5px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.35) !important;
            border-radius: 999px !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
            gap: 3px !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
            min-height: 28px !important;
            height: 28px !important;
            padding: 3px 8px !important;
            margin: 0 !important;
            border-radius: 7px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #dbe7f5 !important;
            -webkit-text-fill-color: #dbe7f5 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            line-height: 1 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            align-items: center !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            transform: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button:hover {
            background: rgba(148, 163, 184, 0.11) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
            height: 28px !important;
            min-height: 28px !important;
            width: 26px !important;
            min-width: 26px !important;
            max-width: 26px !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 7px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #aeb9c8 !important;
            -webkit-text-fill-color: #aeb9c8 !important;
            font-size: 16px !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transform: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button svg {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {
            background: rgba(148, 163, 184, 0.13) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        div[data-testid="stPopoverBody"],
        div[data-baseweb="popover"] div[role="dialog"] {
            width: 172px !important;
            min-width: 172px !important;
            max-width: 172px !important;
            padding: 6px !important;
            border-radius: 12px !important;
            background: rgba(32, 33, 35, 0.98) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            box-shadow: 0 12px 32px rgba(0,0,0,0.38) !important;
            backdrop-filter: blur(12px) !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button {
            height: 30px !important;
            min-height: 30px !important;
            padding: 5px 8px !important;
            border-radius: 8px !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #e5e7eb !important;
            -webkit-text-fill-color: #e5e7eb !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            transform: none !important;
        }

        div[data-testid="stPopoverBody"] .stButton > button:hover {
            background: rgba(255,255,255,0.08) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        @media (max-width: 768px) {
            section[data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
                background: rgba(31, 41, 55, 0.92) !important;
                border: 1px solid rgba(148, 163, 184, 0.18) !important;
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
            }
        }


        /* Final guard: never show accidental code artifact boxes in assistant replies */
        .assistant-bubble pre,
        .assistant-bubble code {
            display: none !important;
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
# Supabase Schema Safety Helpers
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def get_table_columns(table_name):
    """
    Return actual Supabase table columns.

    IMPORTANT:
    Do not guess columns from fallback when a table is empty. That causes PGRST204
    missing-column errors. The RPC below reads information_schema directly.
    """
    try:
        result = supabase.rpc("get_table_columns", {"input_table_name": table_name}).execute()
        if result.data:
            return [row["column_name"] for row in result.data if row.get("column_name")]
    except Exception:
        pass

    # Safe minimum fallback only. These are columns used by the original app and are
    # usually present even in older schemas. Optional learning fields are filtered out
    # unless Supabase confirms they exist.
    fallback = {
        "learned_knowledge": [
            "id", "question", "approved_answer", "keywords",
            "source_conversation_id", "openai_file_id", "vector_store_id",
            "synced", "created_at"
        ],
        "ai_analytics": [
            "id", "username", "assistant", "vehicle", "issue", "product",
            "keywords", "question", "answer", "created_at"
        ],
        "conversations": [
            "id", "username", "assistant", "title", "archived", "pinned",
            "created_at", "updated_at"
        ],
        "messages": [
            "id", "conversation_id", "role", "content", "created_at"
        ],
        "login_sessions": [
            "id", "username", "role", "active", "created_at"
        ],
        "users": [
            "id", "username", "password", "role", "active"
        ]
    }
    return fallback.get(table_name, [])


def refresh_schema_cache():
    """Clear cached schema after SQL migration or Streamlit reboot."""
    try:
        get_table_columns.clear()
    except Exception:
        pass


def filter_payload_for_table(table_name, payload):
    """Remove fields that do not exist in Supabase table to prevent PGRST204 errors."""
    columns = set(get_table_columns(table_name))
    if not columns:
        return payload
    return {k: v for k, v in payload.items() if k in columns}


def safe_select_rows(table_name, order_columns=None, limit=500):
    """Select rows with fallback ordering for mixed database versions."""
    order_columns = order_columns or ["updated_at", "created_at"]
    last_error = None
    for order_col in order_columns:
        try:
            return (
                supabase
                .table(table_name)
                .select("*")
                .order(order_col, desc=True)
                .limit(limit)
                .execute()
                .data
            ) or []
        except Exception as e:
            last_error = e
    try:
        return (
            supabase
            .table(table_name)
            .select("*")
            .limit(limit)
            .execute()
            .data
        ) or []
    except Exception:
        if last_error:
            raise last_error
        raise


def safe_insert_row(table_name, payload):
    clean_payload = filter_payload_for_table(table_name, payload)
    return supabase.table(table_name).insert(clean_payload).execute()


def safe_update_row(table_name, payload, row_id):
    clean_payload = filter_payload_for_table(table_name, payload)
    return supabase.table(table_name).update(clean_payload).eq("id", row_id).execute()

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

    text = clean_visible_chat_text(text)
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
        stripped = line.strip()

        # Final defensive cleanup: never render HTML artifact lines.
        # This catches old saved messages and AI replies that include raw/escaped tags.
        artifact_check = stripped.replace("`", "").strip()
        artifact_check = re.sub(r"&lt;/?\s*(div|p|span|section|article|main|body|html)\b[^&]*&gt;", "", artifact_check, flags=re.IGNORECASE)
        artifact_check = re.sub(r"</?\s*(div|p|span|section|article|main|body|html)\b[^>]*>", "", artifact_check, flags=re.IGNORECASE).strip()

        if stripped in ("```", "```html", "```HTML"):
            i += 1
            continue

        if not artifact_check and (
            "<" in stripped or ">" in stripped or "&lt;" in stripped.lower() or "&gt;" in stripped.lower()
        ):
            i += 1
            continue

        # Remove inline HTML tags from otherwise valid lines.
        line = re.sub(r"&lt;/?\s*(div|p|span|section|article|main|body|html)\b[^&]*&gt;", "", line, flags=re.IGNORECASE)
        line = re.sub(r"</?\s*(div|p|span|section|article|main|body|html)\b[^>]*>", "", line, flags=re.IGNORECASE)
        stripped = line.strip()

        if not stripped:
            close_ul()
            html_lines.append("<br>")
            i += 1
            continue

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
    rendered = "\n".join(html_lines)

    # Final safety sweep after rendering.
    rendered = re.sub(r"&lt;/?\s*(div|p|span|section|article|main|body|html)\b[^&]*&gt;", "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"</?\s*(div|p|span|section|article|main|body|html)\b[^>]*>", "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"<div>\s*</div>", "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"(?:<br>\s*)+$", "", rendered, flags=re.IGNORECASE)
    return rendered


def render_chat_message(role, content, images=None):
    visible_content, stored_images = extract_images_from_message_content(content)
    visible_content = clean_visible_chat_text(visible_content)
    final_images = images if images is not None else stored_images

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

    # IMPORTANT:
    # Keep this HTML compact and unindented. Indented closing tags can be parsed
    # by Markdown as a code block, which is what caused visible </div> bars.
    chat_html = (
        f'<div class="chat-row">'
        f'<div class="chat-icon {icon_class}">{icon_html}</div>'
        f'<div class="chat-bubble {bubble_class}">'
        f'{html_from_text(visible_content)}'
        f'{render_image_previews(final_images)}'
        f'</div>'
        f'</div>'
    )

    st.markdown(chat_html, unsafe_allow_html=True)

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

# Incrementing this value gives the file uploader a fresh widget key.
# That clears previously uploaded files after each sent message so images
# are attached only to the message where they were actually uploaded.
if "chat_file_uploader_generation" not in st.session_state:
    st.session_state.chat_file_uploader_generation = 0

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
    st.session_state.chat_file_uploader_generation += 1
    st.rerun()

st.sidebar.markdown('<div class="sidebar-action-area">', unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-newcase-btn">', unsafe_allow_html=True)
if st.sidebar.button("＋ New Case", key="new_case_button"):
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.chat_file_uploader_generation += 1
    st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-logout-btn">', unsafe_allow_html=True)
if st.sidebar.button("Logout", key="logout_button"):
    logout_user()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# AI Helper Functions
# ============================================================


def normalize_uploaded_image_bytes(uploaded_file, max_dimension=2200, quality=90):
    """
    Normalize uploaded JPG/PNG images so EXIF orientation is applied consistently.

    Returns:
        normalized_bytes, mime_type

    Notes:
    - Applies ImageOps.exif_transpose() to physically rotate pixels.
    - Converts images to RGB for JPEG output.
    - Resizes very large images to reduce upload and preview size.
    - Falls back to the original bytes if normalization fails.
    """
    try:
        raw = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        width, height = image.size
        largest = max(width, height)
        if largest > max_dimension:
            scale = max_dimension / float(largest)
            new_size = (
                max(1, int(width * scale)),
                max(1, int(height * scale)),
            )
            image = image.resize(new_size, Image.LANCZOS)

        output = io.BytesIO()

        # Preserve transparency for PNG; otherwise use JPEG.
        if image.mode == "RGBA":
            image.save(output, format="PNG", optimize=True)
            mime_type = "image/png"
        else:
            image = image.convert("RGB")
            image.save(output, format="JPEG", quality=quality, optimize=True)
            mime_type = "image/jpeg"

        return output.getvalue(), mime_type
    except Exception:
        try:
            return uploaded_file.getvalue(), getattr(uploaded_file, "type", "image/jpeg")
        except Exception:
            return b"", "image/jpeg"


def normalized_image_data_url(uploaded_file):
    normalized_bytes, mime_type = normalize_uploaded_image_bytes(uploaded_file)
    encoded = base64.b64encode(normalized_bytes).decode()
    return f"data:{mime_type};base64,{encoded}"


def image_to_data_url(uploaded_file):
    return normalized_image_data_url(uploaded_file)


IMAGE_MARKER_PREFIX = "[[ATP_IMAGES_JSON:"
IMAGE_MARKER_SUFFIX = "]]"


def clean_visible_chat_text(text):
    """
    Remove raw/escaped HTML artifacts from model output and old saved messages.
    """
    value = str(text or "")

    try:
        marker_pattern = re.escape(IMAGE_MARKER_PREFIX) + r".*?" + re.escape(IMAGE_MARKER_SUFFIX)
        value = re.sub(marker_pattern, "", value, flags=re.DOTALL)
    except Exception:
        pass

    value = (
        value.replace("&lt;", "<")
             .replace("&gt;", ">")
             .replace("&#60;", "<")
             .replace("&#62;", ">")
    )

    tag_names = r"(div|p|span|section|article|main|body|html|details|summary|button|script|svg|path|rect|style|code|pre)"

    # Remove fenced blocks containing HTML fragments.
    value = re.sub(
        r"```(?:html|HTML|text)?[\s\S]*?(?:</?\s*" + tag_names + r"\b)[\s\S]*?```",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove raw tags anywhere.
    value = re.sub(r"</?\s*" + tag_names + r"\b[^>]*>", "", value, flags=re.IGNORECASE)

    cleaned = []
    for line in value.splitlines():
        stripped = line.strip()
        compact = stripped.replace("`", "").replace(" ", "").lower()

        if compact in {
            "```", "```html", "```text",
            "</div>", "<div>", "</p>", "<p>", "</span>", "<span>",
            "</details>", "<details>", "</summary>", "<summary>",
            "</button>", "<button>", "</script>", "<script>",
            "</svg>", "<svg>", "</path>", "<path>", "</rect>", "<rect>",
            "</pre>", "<pre>", "</code>", "<code>"
        }:
            continue

        if re.fullmatch(r"[</>\s`]+", stripped):
            continue

        cleaned.append(line)

    value = "\n".join(cleaned)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def make_image_preview_data_url(uploaded_file, max_size=(1200, 1200), quality=76):
    raw = uploaded_file.getvalue()
    mime_type = getattr(uploaded_file, "type", "") or "image/jpeg"

    if Image is not None:
        try:
            img = Image.open(io.BytesIO(raw))
            img.thumbnail(max_size)
            output = io.BytesIO()

            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                img.save(output, format="PNG", optimize=True)
                mime_type = "image/png"
            else:
                img = img.convert("RGB")
                img.save(output, format="JPEG", quality=quality, optimize=True)
                mime_type = "image/jpeg"

            raw = output.getvalue()
        except Exception:
            pass

    encoded = base64.b64encode(raw).decode()
    return f"data:{mime_type};base64,{encoded}"


def get_uploaded_image_previews(uploaded_files):
    """
    Build normalized image previews for chat history.

    EXIF orientation is applied before the preview is encoded, so portrait and
    landscape photos display correctly and consistently across browsers.
    """
    previews = []

    for uploaded_file in uploaded_files or []:
        mime_type = str(getattr(uploaded_file, "type", "") or "").lower()
        file_name = str(getattr(uploaded_file, "name", "image"))

        if not mime_type.startswith("image/"):
            continue

        try:
            normalized_bytes, normalized_mime = normalize_uploaded_image_bytes(uploaded_file)
            if not normalized_bytes:
                continue

            previews.append({
                "name": file_name,
                "mime_type": normalized_mime,
                "data_base64": base64.b64encode(normalized_bytes).decode(),
            })
        except Exception:
            continue

    return previews


def serialize_images_marker(images):
    if not images:
        return ""
    try:
        return "\n\n" + IMAGE_MARKER_PREFIX + json.dumps(images, ensure_ascii=False) + IMAGE_MARKER_SUFFIX
    except Exception:
        return ""


def extract_images_from_message_content(content):
    text = str(content or "")
    pattern = re.escape(IMAGE_MARKER_PREFIX) + r"(.*?)" + re.escape(IMAGE_MARKER_SUFFIX) + r"\s*$"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return text, []

    visible_text = text[:match.start()].rstrip()

    try:
        images = json.loads(match.group(1))
        if not isinstance(images, list):
            images = []
    except Exception:
        images = []

    clean_images = []
    for image in images:
        if isinstance(image, dict) and image.get("data_url"):
            clean_images.append({
                "name": str(image.get("name") or "uploaded image"),
                "data_url": str(image.get("data_url"))
            })

    return visible_text, clean_images


def render_image_previews(images):
    if not images:
        return ""

    cards = []
    for image in images:
        name = html.escape(str(image.get("name") or "uploaded image"))
        data_url = html.escape(str(image.get("data_url") or ""))
        if not data_url:
            continue

        cards.append(
            f"""
            <div class="chat-image-card">
                <img src="{data_url}" alt="{name}">
                <div class="chat-image-caption">📎 {name}</div>
            </div>
            """
        )

    if not cards:
        return ""

    return f'<div class="chat-image-grid">{"".join(cards)}</div>'


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
Do not output HTML or code-fence formatting.
"""

    if selected_assistant == "📈 Sales & Marketing":
        return """
You are AutoTecPro Sales & Marketing AI.

Always search the Sales & Marketing Vector Store before answering.

Help with product recommendations, compatibility, specifications,
dealer messages, customer replies, Amazon listings, website copy,
social media, promotions, warranty, and return policy.

Never invent pricing or compatibility.
Do not output HTML or code-fence formatting.
"""

    return """
You are AutoTecPro Graphic Marketing AI.

Analyze uploaded images when provided.

Help create ads, banners, YouTube thumbnails, product photography ideas,
social media posts, marketing campaigns, and image prompts.
Do not output HTML or code-fence formatting.
"""


def build_user_input(prompt_text, uploaded_files):
    content = []

    if st.session_state.messages:
        memory_text = "Previous conversation in this case:\n\n"

        for msg in st.session_state.messages[-10:]:
            clean_content, _ = extract_images_from_message_content(msg.get("content", ""))
            clean_content = clean_visible_chat_text(clean_content)
            memory_text += f"{msg['role'].upper()}: {clean_content}\n\n"

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
# Automatic AI Learning Engine
# Duplicate detection + continuous learning + self-improving knowledge
# ============================================================

def get_learning_vector_store_id(selected_assistant):
    if selected_assistant == "📈 Sales & Marketing":
        return SALES_VECTOR_STORE_ID
    return TECHNICAL_VECTOR_STORE_ID


def normalize_text_for_match(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def text_similarity(a, b):
    return SequenceMatcher(None, normalize_text_for_match(a), normalize_text_for_match(b)).ratio()


def extract_json_object(raw_text):
    if not raw_text:
        return {}
    text = str(raw_text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
    return {}


def detect_vehicle_basic(text):
    value = str(text or "").lower()
    years = re.findall(r"\b(20[0-2][0-9]|19[8-9][0-9])\b", value)
    vehicles = [
        "silverado", "sierra", "tahoe", "suburban", "yukon",
        "f150", "f-150", "f250", "f-250", "f350", "f-350",
        "ram", "tundra", "durango", "q50", "q60",
        "a4", "a5", "glc", "mercedes", "audi", "ford",
        "chevy", "gmc", "toyota", "dodge", "infiniti"
    ]
    found = ""
    for vehicle in vehicles:
        if vehicle in value:
            found = vehicle.upper()
            break
    if years and found:
        return f"{years[0]} {found}"
    if found:
        return found
    if years:
        return years[0]
    return ""


def extract_learning_candidate(question, answer, selected_assistant):
    extraction_prompt = f"""
You are AutoTecPro's internal knowledge engineer.

Convert this latest support conversation into a clean reusable knowledge record.

Return ONLY valid JSON with this exact schema:
{{
  "should_learn": true/false,
  "vehicle": "vehicle/product/year if known",
  "issue": "short reusable issue title",
  "solution": "clean final solution that future staff can reuse",
  "keywords": "comma-separated keywords",
  "confidence_score": 0-100,
  "reason": "short reason"
}}

Rules:
- should_learn should be true only if the answer contains a reusable solution, compatibility fact, troubleshooting step, product fact, warranty/sales policy, or customer reply that can help future cases.
- should_learn should be false for greetings, vague chats, uncertain answers, purely emotional messages, or cases where the answer says documentation is unavailable without useful next steps.
- Keep the solution accurate and concise.
- Never invent details not supported by the Q&A.

Assistant: {clean_assistant_label(selected_assistant)}

Question:
{question}

Answer:
{answer}
"""
    try:
        response = client.responses.create(
            model="gpt-5.5",
            instructions="Return only valid JSON. No markdown.",
            input=extraction_prompt
        )
        data = extract_json_object(response.output_text)
    except Exception:
        data = {}

    should_learn = bool(data.get("should_learn", False))
    vehicle = str(data.get("vehicle") or "").strip() or detect_vehicle_basic(question + " " + answer)
    issue = str(data.get("issue") or conversation_title_from_text(question)).strip()
    solution = str(data.get("solution") or answer).strip()
    keywords = str(data.get("keywords") or "").strip()

    try:
        confidence_score = int(data.get("confidence_score", 70))
    except Exception:
        confidence_score = 70

    confidence_score = max(0, min(100, confidence_score))

    if len(solution) < 80:
        should_learn = False
    if len(str(question).strip()) < 5:
        should_learn = False

    return {
        "should_learn": should_learn,
        "vehicle": vehicle,
        "issue": issue[:180],
        "solution": solution,
        "keywords": keywords,
        "confidence_score": confidence_score,
        "reason": str(data.get("reason") or "").strip()
    }


def make_learned_knowledge_document(record):
    return f"""AutoTecPro Self-Learned Knowledge

Assistant:
{record.get("assistant", "")}

Vehicle / Product:
{record.get("vehicle", "") or "Not specified"}

Issue:
{record.get("issue", "")}

Solution:
{record.get("solution", "")}

Keywords:
{record.get("keywords", "")}

Confidence Score:
{record.get("confidence_score", "")}

Times Seen:
{record.get("times_seen", "")}

Source Question:
{record.get("source_question", "")}

Source Answer:
{record.get("source_answer", "")}

Usage Instruction:
Use this learned case when a future AutoTecPro support, sales, or compatibility question is similar. Verify vehicle year, trim, factory radio, audio system, camera system, and firmware when relevant.
"""


def upload_learned_record_to_vector_store(record, vector_store_id):
    doc_text = make_learned_knowledge_document(record)
    safe_name = normalize_text_for_match(record.get("issue") or "learned_case")[:50].replace(" ", "_") or "learned_case"
    filename = f"autotecpro_learned_{safe_name}.txt"

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(doc_text)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            openai_file = client.files.create(file=(filename, f), purpose="assistants")

        client.vector_stores.files.create(vector_store_id=vector_store_id, file_id=openai_file.id)
        return openai_file.id
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def find_duplicate_learned_knowledge(candidate, selected_assistant):
    try:
        all_rows = safe_select_rows("learned_knowledge", order_columns=["updated_at", "created_at"], limit=200)
        rows = [
            row for row in all_rows
            if str(row.get("assistant") or "").strip().lower() == clean_assistant_label(selected_assistant).lower()
        ] or all_rows
    except Exception:
        return None, 0

    best_row = None
    best_score = 0

    candidate_text = " ".join([
        candidate.get("vehicle", ""),
        candidate.get("issue", ""),
        candidate.get("keywords", ""),
        candidate.get("solution", "")[:600]
    ])

    for row in rows:
        row_text = " ".join([
            row.get("vehicle", ""),
            row.get("issue", ""),
            row.get("keywords", ""),
            str(row.get("solution") or row.get("approved_answer") or "")[:600],
            row.get("source_question", "") or row.get("question", "")
        ])

        score = text_similarity(candidate_text, row_text)
        issue_score = text_similarity(candidate.get("issue", ""), row.get("issue", ""))

        vehicle_match = (
            candidate.get("vehicle")
            and row.get("vehicle")
            and normalize_text_for_match(candidate.get("vehicle")) in normalize_text_for_match(row.get("vehicle"))
        )

        if vehicle_match:
            score += 0.08
        if issue_score > 0.72:
            score += 0.10

        score = min(score, 1.0)

        if score > best_score:
            best_score = score
            best_row = row

    if best_score >= 0.82:
        return best_row, best_score

    return None, best_score


def improve_existing_solution(existing_row, candidate):
    prompt = f"""
You are AutoTecPro's internal knowledge base editor.

Merge the existing knowledge and the new case into one improved, accurate, reusable solution.

Return ONLY valid JSON:
{{
  "issue": "best short issue title",
  "vehicle": "best vehicle/product",
  "solution": "improved final solution",
  "keywords": "comma-separated keywords",
  "confidence_score": 0-100
}}

Do not invent facts. Preserve exact compatibility and troubleshooting details.

Existing Knowledge:
Vehicle: {existing_row.get("vehicle", "")}
Issue: {existing_row.get("issue", "")}
Solution: {existing_row.get("solution", "")}
Keywords: {existing_row.get("keywords", "")}
Confidence: {existing_row.get("confidence_score", 70)}
Times Seen: {existing_row.get("times_seen", 1)}

New Case:
Vehicle: {candidate.get("vehicle", "")}
Issue: {candidate.get("issue", "")}
Solution: {candidate.get("solution", "")}
Keywords: {candidate.get("keywords", "")}
Confidence: {candidate.get("confidence_score", 70)}
"""
    try:
        response = client.responses.create(
            model="gpt-5.5",
            instructions="Return only valid JSON. No markdown.",
            input=prompt
        )
        data = extract_json_object(response.output_text)
    except Exception:
        data = {}

    old_times_seen = int(existing_row.get("times_seen") or 1)
    old_confidence = int(existing_row.get("confidence_score") or 70)
    new_confidence = int(candidate.get("confidence_score") or 70)
    merged_confidence = max(old_confidence, min(98, round((old_confidence + new_confidence) / 2 + min(old_times_seen, 10))))

    return {
        "vehicle": str(data.get("vehicle") or candidate.get("vehicle") or existing_row.get("vehicle") or "").strip(),
        "issue": str(data.get("issue") or candidate.get("issue") or existing_row.get("issue") or "").strip()[:180],
        "solution": str(data.get("solution") or candidate.get("solution") or existing_row.get("solution") or "").strip(),
        "keywords": str(data.get("keywords") or candidate.get("keywords") or existing_row.get("keywords") or "").strip(),
        "confidence_score": int(data.get("confidence_score") or merged_confidence),
        "times_seen": old_times_seen + 1
    }


def auto_learn_from_latest_answer(question, answer, selected_assistant):
    if selected_assistant == "⚙️ Admin Panel":
        return None

    candidate = extract_learning_candidate(question, answer, selected_assistant)

    if not candidate.get("should_learn"):
        return {"learned": False, "reason": candidate.get("reason") or "Not reusable enough to learn."}

    vector_store_id = get_learning_vector_store_id(selected_assistant)
    duplicate_row, duplicate_score = find_duplicate_learned_knowledge(candidate, selected_assistant)

    if duplicate_row:
        improved = improve_existing_solution(duplicate_row, candidate)

        record_for_file = {
            "assistant": clean_assistant_label(selected_assistant),
            "vehicle": improved["vehicle"],
            "issue": improved["issue"],
            "solution": improved["solution"],
            "keywords": improved["keywords"],
            "confidence_score": improved["confidence_score"],
            "times_seen": improved["times_seen"],
            "source_question": question,
            "source_answer": answer
        }

        openai_file_id = upload_learned_record_to_vector_store(record_for_file, vector_store_id)

        update_payload = {
            "assistant": clean_assistant_label(selected_assistant),
            "vehicle": improved["vehicle"],
            "issue": improved["issue"],
            "solution": improved["solution"],
            "approved_answer": improved["solution"],
            "question": question,
            "keywords": improved["keywords"],
            "source_question": question,
            "source_answer": answer,
            "source_conversation_id": st.session_state.get("conversation_id"),
            "confidence_score": improved["confidence_score"],
            "times_seen": improved["times_seen"],
            "openai_file_id": openai_file_id,
            "vector_store_id": vector_store_id,
            "synced": True,
            "embedding_status": "synced",
            "updated_at": now_iso()
        }

        safe_update_row("learned_knowledge", update_payload, duplicate_row["id"])

        return {
            "learned": True,
            "mode": "updated",
            "duplicate_score": round(duplicate_score, 3),
            "record_id": duplicate_row["id"],
            "duplicate_of": duplicate_row["id"],
            "file_id": openai_file_id
        }

    new_record = {
        "username": st.session_state.get("username"),
        "assistant": clean_assistant_label(selected_assistant),
        "vehicle": candidate["vehicle"],
        "issue": candidate["issue"],
        "solution": candidate["solution"],
        "approved_answer": candidate["solution"],
        "question": question,
        "keywords": candidate["keywords"],
        "source_question": question,
        "source_answer": answer,
        "source_conversation_id": st.session_state.get("conversation_id"),
        "confidence_score": candidate["confidence_score"],
        "times_seen": 1,
        "times_used": 0,
        "search_count": 0,
        "vector_store_id": vector_store_id,
        "synced": False,
        "embedding_status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    openai_file_id = upload_learned_record_to_vector_store(new_record, vector_store_id)
    new_record["openai_file_id"] = openai_file_id
    new_record["synced"] = True

    result = safe_insert_row("learned_knowledge", new_record)
    if not result.data:
        raise RuntimeError("Learning record was not saved.")

    return {
        "learned": True,
        "mode": "created",
        "record_id": result.data[0]["id"],
        "file_id": openai_file_id
    }


# ============================================================
# AI Analytics Engine
# ============================================================

def extract_analytics_from_question(question, answer, selected_assistant):
    """Extract structured analytics signals from each AI interaction."""
    prompt = f"""
You are AutoTecPro's internal analytics engine.

Extract analytics from this AI interaction.

Return ONLY valid JSON:
{{
  "vehicle": "full vehicle if mentioned, else empty",
  "year": "year if mentioned, else empty",
  "make": "make/brand if mentioned, else empty",
  "model": "model if mentioned, else empty",
  "issue": "short issue/search topic",
  "product": "product/model/category searched, else empty",
  "solution": "short reusable solution summary, else empty",
  "keywords": "comma-separated keywords",
  "was_unanswered": true/false,
  "resolved": true/false,
  "confidence_score": 0-100
}}

Rules:
- was_unanswered is true if the AI could not answer, lacked documentation, asked for escalation, or only requested more info without a usable answer.
- resolved is true if the answer gives a clear useful solution, next step, compatibility fact, or customer-ready response.
- confidence_score should reflect how confident the AI answer appears based on the answer wording.
- Do not invent details.

Assistant:
{clean_assistant_label(selected_assistant)}

Question:
{question}

Answer:
{answer}
"""
    try:
        response = client.responses.create(
            model="gpt-5.5",
            instructions="Return only valid JSON. No markdown.",
            input=prompt
        )
        data = extract_json_object(response.output_text)
    except Exception:
        data = {}

    combined_text = str(question) + " " + str(answer)
    fallback_vehicle = detect_vehicle_basic(combined_text)
    fallback_year_match = re.search(r"\b(20[0-2][0-9]|19[8-9][0-9])\b", combined_text)

    try:
        confidence = int(data.get("confidence_score", 70))
    except Exception:
        confidence = 70

    vehicle = str(data.get("vehicle") or fallback_vehicle or "").strip()
    year = str(data.get("year") or (fallback_year_match.group(1) if fallback_year_match else "")).strip()
    make = str(data.get("make") or "").strip()
    model = str(data.get("model") or "").strip()

    # Lightweight fallback make/model split when AI extraction is empty.
    if vehicle and not make:
        vehicle_low = vehicle.lower()
        for brand in ["chevrolet", "chevy", "gmc", "ford", "toyota", "dodge", "ram", "infiniti", "audi", "mercedes"]:
            if brand in vehicle_low:
                make = brand.title()
                break

    if vehicle and not model:
        for possible_model in ["silverado", "sierra", "tahoe", "suburban", "yukon", "f150", "f-150", "f250", "f-250", "f350", "f-350", "tundra", "ram", "durango", "q50", "q60", "a4", "a5", "glc"]:
            if possible_model in vehicle.lower():
                model = possible_model.upper()
                break

    return {
        "username": st.session_state.get("username"),
        "assistant": clean_assistant_label(selected_assistant),
        "vehicle": vehicle,
        "year": year,
        "make": make,
        "model": model,
        "issue": str(data.get("issue") or conversation_title_from_text(question) or "").strip()[:180],
        "product": str(data.get("product") or "").strip()[:180],
        "solution": str(data.get("solution") or "").strip(),
        "keywords": str(data.get("keywords") or "").strip(),
        "question": str(question or ""),
        "answer": str(answer or ""),
        "was_unanswered": bool(data.get("was_unanswered", False)),
        "resolved": bool(data.get("resolved", False)),
        "confidence_score": max(0, min(100, confidence)),
        "conversation_id": st.session_state.get("conversation_id"),
        "created_at": now_iso()
    }

def log_ai_analytics(question, answer, selected_assistant, learning_result=None, response_time=None, tokens_used=None):
    """Save one analytics event for Admin dashboard."""
    try:
        payload = extract_analytics_from_question(question, answer, selected_assistant)

        if learning_result:
            payload["learned"] = bool(learning_result.get("learned"))
            payload["learning_mode"] = learning_result.get("mode")
            payload["learned_record_id"] = learning_result.get("record_id")
            payload["duplicate_of"] = learning_result.get("duplicate_of")
        else:
            payload["learned"] = False
            payload["learning_mode"] = None
            payload["learned_record_id"] = None
            payload["duplicate_of"] = None

        payload["response_time"] = response_time
        payload["tokens_used"] = tokens_used
        payload["learning_source"] = "automatic"

        safe_insert_row("ai_analytics", payload)
        return True

    except Exception:
        # Analytics should never break the main chat.
        return False

def top_counts(rows, field, limit=10):
    counts = {}
    for row in rows:
        value = str(row.get(field) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1

    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


def keyword_counts(rows, limit=10):
    counts = {}
    for row in rows:
        keywords = str(row.get("keywords") or "")
        for kw in keywords.split(","):
            key = kw.strip().lower()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


def render_count_table(title, data, col_name):
    st.markdown(f"#### {title}")
    if not data:
        st.info("No data yet.")
        return

    st.table([
        {col_name: item[0], "Count": item[1]}
        for item in data
    ])




def daily_question_counts(rows, limit=14):
    counts = {}
    for row in rows:
        day = str(row.get("created_at") or "")[:10]
        if not day:
            continue
        counts[day] = counts.get(day, 0) + 1

    items = sorted(counts.items())[-limit:]
    return [{"Date": k, "Questions": v} for k, v in items]


def assistant_counts(rows, limit=10):
    return top_counts(rows, "assistant", limit)


def user_counts(rows, limit=10):
    return top_counts(rows, "username", limit)


def learning_success_rate(rows):
    if not rows:
        return 0
    learned = len([r for r in rows if r.get("learned")])
    return round((learned / max(len(rows), 1)) * 100)




def count_today(rows, date_field="created_at"):
    today = datetime.now(timezone.utc).date().isoformat()
    return len([r for r in rows if str(r.get(date_field) or "").startswith(today)])


def safe_avg(rows, field):
    values = []
    for row in rows:
        try:
            if row.get(field) is not None:
                values.append(float(row.get(field)))
        except Exception:
            pass
    if not values:
        return 0
    return round(sum(values) / len(values), 2)


def duplicate_detection_rate(rows):
    if not rows:
        return 0
    dupes = len([r for r in rows if r.get("duplicate_of") or str(r.get("learning_mode") or "").lower() == "updated"])
    return round((dupes / max(len(rows), 1)) * 100)


def resolved_rate(rows):
    if not rows:
        return 0
    resolved = len([r for r in rows if r.get("resolved")])
    return round((resolved / max(len(rows), 1)) * 100)


def total_numeric(rows, field):
    total = 0
    for row in rows:
        try:
            total += int(row.get(field) or 0)
        except Exception:
            pass
    return total


def growth_counts(rows, field="created_at", limit=30, label="New Knowledge"):
    counts = {}
    for row in rows:
        day = str(row.get(field) or "")[:10]
        if not day:
            continue
        counts[day] = counts.get(day, 0) + 1
    items = sorted(counts.items())[-limit:]
    return [{"Date": k, label: v} for k, v in items]


def render_metric_row(metrics):
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        label, value = metric[0], metric[1]
        delta = metric[2] if len(metric) > 2 else None
        col.metric(label, value, delta=delta)



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
    payload = {
        "username": username,
        "assistant": clean_assistant_label(assistant_name),
        "title": conversation_title_from_text(first_message),
        "archived": False,
        "pinned": False,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }

    try:
        result = supabase.table("conversations").insert(payload).execute()
    except Exception as e:
        # Backward compatible if the pinned column has not been added yet.
        if "pinned" in str(e).lower():
            payload.pop("pinned", None)
            result = supabase.table("conversations").insert(payload).execute()
        else:
            raise

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

    # Pinned conversations stay at the top; newest first inside each group.
    active_rows = sorted(
        active_rows,
        key=lambda row: (
            0 if bool(row.get("pinned", False)) else 1,
            str(row.get("updated_at") or row.get("created_at") or "")
        ),
        reverse=False
    )
    pinned_rows = [r for r in active_rows if bool(r.get("pinned", False))]
    normal_rows = [r for r in active_rows if not bool(r.get("pinned", False))]
    pinned_rows = sorted(pinned_rows, key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
    normal_rows = sorted(normal_rows, key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
    active_rows = pinned_rows + normal_rows

    # Admin can see all cases. Staff sees their own cases first.
    if str(role or "").lower() == "admin":
        return active_rows[:50]

    own_rows = [
        row for row in active_rows
        if str(row.get("username", "")).lower() == str(username or "").lower()
    ]

    # Fallback: if username changed during testing, show all active rows.
    return (own_rows or active_rows)[:50]


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


def render_rename_form(conversations):
    """Inline rename form shown below the history list."""
    rename_id = st.session_state.get("rename_conversation_id")
    if not rename_id:
        return

    target = None
    for convo in conversations:
        if str(convo.get("id")) == str(rename_id):
            target = convo
            break

    if not target:
        st.session_state.rename_conversation_id = None
        return

    st.sidebar.markdown('<div class="rename-box-title">Rename conversation</div>', unsafe_allow_html=True)

    with st.sidebar.form(f"rename_form_{rename_id}", clear_on_submit=False):
        new_title = st.text_input(
            "Title",
            value=st.session_state.get("rename_conversation_value", target.get("title") or "New Case"),
            label_visibility="collapsed"
        )

        save_col, cancel_col = st.columns([0.58, 0.42], gap="small")

        with save_col:
            save_clicked = st.form_submit_button("Save", use_container_width=True)

        with cancel_col:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

    if save_clicked:
        cleaned = new_title.strip() or "New Case"
        supabase.table("conversations").update({
            "title": cleaned,
            "updated_at": now_iso()
        }).eq("id", rename_id).execute()

        st.session_state.rename_conversation_id = None
        st.session_state.rename_conversation_value = ""
        st.rerun()

    if cancel_clicked:
        st.session_state.rename_conversation_id = None
        st.session_state.rename_conversation_value = ""
        st.rerun()



# ============================================================
# ChatGPT-style HTML History Actions
# ============================================================

def app_action_url(action, conversation_id):
    """Build query-string URL for custom HTML history actions."""
    session_token = st.query_params.get("session")
    parts = []
    if session_token:
        parts.append(f"session={html.escape(str(session_token), quote=True)}")
    parts.append(f"hist_action={html.escape(str(action), quote=True)}")
    parts.append(f"cid={html.escape(str(conversation_id), quote=True)}")
    return "?" + "&".join(parts)


def clear_history_action_params():
    """Clear one-time history action query params while preserving login session."""
    session_token = st.query_params.get("session")
    st.query_params.clear()
    if session_token:
        st.query_params["session"] = session_token


def process_history_action():
    """Process open / rename / pin / archive / delete from custom HTML history links."""
    action = st.query_params.get("hist_action")
    cid = st.query_params.get("cid")

    if not action or not cid:
        return

    if "rename_conversation_id" not in st.session_state:
        st.session_state.rename_conversation_id = None
    if "rename_conversation_value" not in st.session_state:
        st.session_state.rename_conversation_value = ""

    try:
        if action == "open":
            st.session_state.conversation_id = cid
            st.session_state.messages = load_messages(cid)
            st.session_state.rename_conversation_id = None
            st.session_state.scroll_to_bottom = True

        elif action == "rename":
            st.session_state.rename_conversation_id = str(cid)
            st.session_state.rename_conversation_value = get_conversation_title_by_id(cid)

        elif action == "pin":
            current = (
                supabase.table("conversations")
                .select("pinned")
                .eq("id", cid)
                .limit(1)
                .execute()
            )
            pinned = False
            if current.data:
                pinned = bool(current.data[0].get("pinned", False))
            toggle_pin_conversation(cid, not pinned)

        elif action == "archive":
            archive_conversation(cid)
            if st.session_state.conversation_id == cid:
                st.session_state.conversation_id = None
                st.session_state.messages = []

        elif action == "delete":
            delete_conversation(cid)
            if st.session_state.conversation_id == cid:
                st.session_state.conversation_id = None
                st.session_state.messages = []

    except Exception as e:
        st.session_state.history_action_error = str(e)

    clear_history_action_params()
    st.rerun()


def get_conversation_title_by_id(conversation_id):
    try:
        result = (
            supabase
            .table("conversations")
            .select("title")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("title") or "New Case"
    except Exception:
        pass
    return "New Case"


def render_history_cards(conversations):
    """
    Streamlit-native ChatGPT-style history cards.

    Important:
    We intentionally do NOT render conversation rows as raw HTML.
    Streamlit can escape/sanitize complex sidebar HTML and print it as text.
    This native implementation keeps Rename / Pin / Archive / Delete working
    and avoids the raw <div> sidebar issue.
    """
    pinned_conversations = [c for c in conversations if c.get("pinned")]
    normal_conversations = [c for c in conversations if not c.get("pinned")]

    sections = []
    if pinned_conversations:
        sections.append(("Pinned", pinned_conversations))
    if normal_conversations:
        sections.append(("Recent", normal_conversations))

    history_box = st.sidebar.container(height=460, border=False)

    with history_box:
        for section_name, section_convos in sections:
            st.markdown(
                f'<div class="history-section-label">{html.escape(section_name)}</div>',
                unsafe_allow_html=True
            )

            for convo in section_convos:
                convo_id = convo["id"]
                title = convo.get("title") or "New Case"
                pinned = bool(convo.get("pinned", False))
                is_current = str(st.session_state.get("conversation_id")) == str(convo_id)

                title_short = title[:36] + "..." if len(title) > 36 else title
                active_prefix = "• " if is_current else ""
                pin_prefix = "📌 " if pinned else ""
                history_label = f"{active_prefix}{pin_prefix}{title_short}"

                item_col, menu_col = st.columns([0.86, 0.14], gap="small")

                with item_col:
                    if st.button(
                        history_label,
                        key=f"open_{convo_id}",
                        help="Open conversation",
                        use_container_width=True
                    ):
                        st.session_state.conversation_id = convo_id
                        st.session_state.messages = load_messages(convo_id)
                        st.session_state.rename_conversation_id = None
                        st.session_state.scroll_to_bottom = True
                        st.rerun()

                with menu_col:
                    with st.popover("⋯"):
                        st.markdown(
                            f'<div class="history-menu-title">{html.escape(title_short)}</div>',
                            unsafe_allow_html=True
                        )

                        if st.button("Rename", key=f"rename_{convo_id}", use_container_width=True):
                            st.session_state.rename_conversation_id = str(convo_id)
                            st.session_state.rename_conversation_value = title
                            st.rerun()

                        pin_label = "Unpin chat" if pinned else "Pin chat"
                        if st.button(pin_label, key=f"pin_{convo_id}", use_container_width=True):
                            try:
                                toggle_pin_conversation(convo_id, not pinned)
                                st.rerun()
                            except Exception:
                                st.toast("Pin needs the pinned column in Supabase.")

                        if st.button("Archive", key=f"archive_{convo_id}", use_container_width=True):
                            archive_conversation(convo_id)
                            if st.session_state.conversation_id == convo_id:
                                st.session_state.conversation_id = None
                                st.session_state.messages = []
                            st.rerun()

                        if st.button("Delete", key=f"delete_{convo_id}", use_container_width=True):
                            delete_conversation(convo_id)
                            if st.session_state.conversation_id == convo_id:
                                st.session_state.conversation_id = None
                                st.session_state.messages = []
                            st.rerun()


def install_global_chat_file_dropzone():
    """
    Allow users to drag files anywhere over the main app, or paste an image
    from the clipboard, and forward those files into the existing Streamlit
    chat file uploader.

    Stability notes:
    - Uses the existing st.file_uploader; no new backend upload path.
    - Ignores ordinary text paste.
    - Installs only one set of parent-document event listeners.
    - Locates the current visible uploader dynamically after Streamlit reruns.
    """
    components.html(
        """
        <script>
        (function () {
            const parentWindow = window.parent;
            const doc = parentWindow.document;

            function getVisibleChatFileInput() {
                const inputs = Array.from(doc.querySelectorAll('input[type="file"]'));
                const visible = inputs.filter((input) => {
                    const rect = input.getBoundingClientRect();
                    const style = parentWindow.getComputedStyle(input);
                    return (
                        rect.width >= 0 &&
                        rect.height >= 0 &&
                        style.display !== "none" &&
                        style.visibility !== "hidden"
                    );
                });

                // On the normal chat page, the chat uploader is the last/current
                // visible file input. Admin uploaders are not present on this page.
                return visible.length ? visible[visible.length - 1] : inputs[inputs.length - 1];
            }

            function ensureOverlay() {
                let overlay = doc.getElementById("atp-global-drop-overlay");
                if (overlay) return overlay;

                overlay = doc.createElement("div");
                overlay.id = "atp-global-drop-overlay";
                overlay.innerHTML = `
                    <div style="
                        width:min(520px,82vw);
                        padding:34px 28px;
                        border-radius:22px;
                        border:2px dashed rgba(255,255,255,.78);
                        background:rgba(15,23,42,.92);
                        box-shadow:0 24px 70px rgba(0,0,0,.42);
                        color:#fff;
                        text-align:center;
                        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                    ">
                        <div style="font-size:42px;line-height:1;margin-bottom:12px;">📎</div>
                        <div style="font-size:22px;font-weight:800;margin-bottom:7px;">
                            Drop files to attach
                        </div>
                        <div style="font-size:14px;color:#cbd5e1;">
                            JPG, PNG, PDF, or TXT
                        </div>
                    </div>
                `;
                Object.assign(overlay.style, {
                    position: "fixed",
                    inset: "0",
                    zIndex: "2147483646",
                    display: "none",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "rgba(2,6,23,.68)",
                    backdropFilter: "blur(6px)",
                    WebkitBackdropFilter: "blur(6px)",
                    pointerEvents: "none"
                });
                doc.body.appendChild(overlay);
                return overlay;
            }

            function hasFiles(event) {
                const types = Array.from(event.dataTransfer?.types || []);
                return types.includes("Files");
            }

            function attachFiles(fileList) {
                if (!fileList || !fileList.length) return false;

                const input = getVisibleChatFileInput();
                if (!input) {
                    console.warn("AutoTecPro AI: chat file uploader was not found.");
                    return false;
                }

                const acceptedExtensions = [".jpg", ".jpeg", ".png", ".pdf", ".txt"];
                const acceptedFiles = Array.from(fileList).filter((file) => {
                    const name = (file.name || "").toLowerCase();
                    return acceptedExtensions.some((ext) => name.endsWith(ext));
                });

                if (!acceptedFiles.length) return false;

                const transfer = new DataTransfer();

                // Preserve files already selected in the uploader, then append new ones.
                Array.from(input.files || []).forEach((file) => transfer.items.add(file));
                acceptedFiles.forEach((file) => transfer.items.add(file));

                input.files = transfer.files;
                input.dispatchEvent(new Event("change", { bubbles: true }));
                return true;
            }

            const overlay = ensureOverlay();

            if (!parentWindow.__atpGlobalDropzoneInstalled) {
                parentWindow.__atpGlobalDropzoneInstalled = true;
                let dragDepth = 0;

                doc.addEventListener("dragenter", function (event) {
                    if (!hasFiles(event)) return;
                    event.preventDefault();
                    dragDepth += 1;
                    overlay.style.display = "flex";
                }, true);

                doc.addEventListener("dragover", function (event) {
                    if (!hasFiles(event)) return;
                    event.preventDefault();
                    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
                    overlay.style.display = "flex";
                }, true);

                doc.addEventListener("dragleave", function (event) {
                    if (!hasFiles(event)) return;
                    event.preventDefault();
                    dragDepth = Math.max(0, dragDepth - 1);
                    if (dragDepth === 0) overlay.style.display = "none";
                }, true);

                doc.addEventListener("drop", function (event) {
                    if (!hasFiles(event)) return;
                    event.preventDefault();
                    event.stopPropagation();
                    dragDepth = 0;
                    overlay.style.display = "none";
                    attachFiles(event.dataTransfer.files);
                }, true);

                doc.addEventListener("paste", function (event) {
                    const clipboardFiles = Array.from(event.clipboardData?.files || []);
                    if (!clipboardFiles.length) return;

                    const imageFiles = clipboardFiles.filter((file) =>
                        (file.type || "").toLowerCase().startsWith("image/")
                    );
                    if (!imageFiles.length) return;

                    // Only intercept paste when there is an actual image in clipboard.
                    event.preventDefault();
                    attachFiles(imageFiles);
                }, true);

                parentWindow.addEventListener("blur", function () {
                    dragDepth = 0;
                    overlay.style.display = "none";
                });
            }
        })();
        </script>
        """,
        height=0,
    )


def auto_scroll_to_latest():
    """Scroll browser to the latest chat reply after a rerun."""
    components.html(
        """
        <script>
        const scrollToBottom = () => {
            const doc = window.parent.document;
            const anchor = doc.getElementById("chat-bottom-anchor");
            if (anchor) {
                anchor.scrollIntoView({behavior: "smooth", block: "end"});
            } else {
                window.parent.scrollTo({top: doc.body.scrollHeight, behavior: "smooth"});
            }
        };
        setTimeout(scrollToBottom, 120);
        setTimeout(scrollToBottom, 500);
        </script>
        """,
        height=0,
    )


# ============================================================
# Chat History Sidebar
# ============================================================

if assistant != "⚙️ Admin Panel":
    if "rename_conversation_id" not in st.session_state:
        st.session_state.rename_conversation_id = None
    if "rename_conversation_value" not in st.session_state:
        st.session_state.rename_conversation_value = ""

    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="history-title">Chat History</div>', unsafe_allow_html=True)

    header_left, header_right = st.sidebar.columns([0.84, 0.16], gap="small")
    with header_left:
        st.markdown('<div class="history-count">Saved cases</div>', unsafe_allow_html=True)
    with header_right:
        if st.button("↻", key="refresh_history", help="Refresh history"):
            st.rerun()

    try:
        conversations = load_conversations(
            st.session_state.username,
            st.session_state.role
        )

        if conversations:
            render_history_cards(conversations)
        else:
            st.sidebar.caption("No saved cases yet.")

        st.sidebar.markdown(
            f'<div class="history-count">{len(conversations)} conversation(s)</div>',
            unsafe_allow_html=True
        )

        render_rename_form(conversations)

        if st.session_state.conversation_id:
            current_title = get_current_conversation_title()
            st.sidebar.markdown(
                f'<div class="history-current-note">Current: {html.escape(current_title)}</div>',
                unsafe_allow_html=True
            )

        if st.session_state.get("history_action_error"):
            st.sidebar.warning(st.session_state.history_action_error)
            st.session_state.history_action_error = ""

    except Exception as e:
        st.sidebar.error(f"Chat history error: {e}")


# ============================================================
# Admin Panel
# ============================================================

if assistant == "⚙️ Admin Panel":

    st.markdown('<div class="workspace-card">', unsafe_allow_html=True)
    st.subheader("⚙️ Admin Panel")
    st.caption("Manage users, knowledge uploads, AI learning, analytics, and continuous improvement.")
    st.markdown('</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "👥 Users",
        "📚 Upload Knowledge",
        "🧠 AI Learning",
        "🚗 Vehicle Analytics",
        "📦 Product Analytics",
        "🔧 Technical Analytics",
        "📊 AI Analytics",
        "📈 Learning Analytics"
    ])

    # Shared analytics data for all admin dashboards.
    try:
        analytics_rows = safe_select_rows("ai_analytics", order_columns=["created_at"], limit=2000)
    except Exception:
        analytics_rows = []

    try:
        learned_rows_for_analytics = safe_select_rows("learned_knowledge", order_columns=["updated_at", "created_at"], limit=2000)
    except Exception:
        learned_rows_for_analytics = []

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

    with tab3:
        st.markdown("### 🧠 AI Learning")
        st.caption("Automatic knowledge extraction, duplicate detection, self-improving records, confidence score, and vector sync.")

        total_learned = len(learned_rows_for_analytics)
        new_today = count_today(learned_rows_for_analytics, "created_at")
        avg_conf = round(safe_avg(learned_rows_for_analytics, "confidence_score"))
        synced_cases = len([r for r in learned_rows_for_analytics if r.get("synced")])
        duplicate_rate = duplicate_detection_rate(analytics_rows)
        total_vectors = len([r for r in learned_rows_for_analytics if r.get("openai_file_id")])

        render_metric_row([
            ("Total Learned Cases", total_learned),
            ("New Knowledge Today", new_today),
            ("Duplicate Detection Rate", f"{duplicate_rate}%"),
            ("Confidence Average", f"{avg_conf}%"),
            ("Synced Cases", synced_cases),
            ("New Vectors Created", total_vectors),
        ])

        st.markdown("#### Knowledge Growth Chart")
        growth_data = growth_counts(learned_rows_for_analytics, "created_at", limit=30, label="Learned Cases")
        if growth_data:
            st.bar_chart(growth_data, x="Date", y="Learned Cases")
        else:
            st.info("No learned knowledge yet.")

        st.markdown("#### Latest Learned Knowledge")
        if learned_rows_for_analytics:
            for row in learned_rows_for_analytics[:80]:
                issue = row.get("issue") or row.get("question") or "Learned Knowledge"
                vehicle = row.get("vehicle") or "Vehicle not specified"
                confidence = row.get("confidence_score") or 0
                times_seen = row.get("times_seen") or 1
                with st.expander(f"{vehicle} | {issue[:90]} | Confidence {confidence}% | Seen {times_seen}x"):
                    st.write(f"**Assistant:** {row.get('assistant') or ''}")
                    st.write(f"**Product:** {row.get('product') or ''}")
                    st.write(f"**Keywords:** {row.get('keywords') or ''}")
                    st.write(f"**Synced:** {row.get('synced')}")
                    st.write(f"**Vector Store:** {row.get('vector_store_id') or ''}")
                    st.markdown("**Solution**")
                    st.write(row.get("solution") or row.get("approved_answer") or "")
                    st.markdown("**Source Question**")
                    st.write(row.get("source_question") or row.get("question") or "")
                    st.caption(f"OpenAI File ID: {row.get('openai_file_id') or 'N/A'}")

                    if st.button("Delete learned record", key=f"delete_learned_{row.get('id')}"):
                        supabase.table("learned_knowledge").delete().eq("id", row.get("id")).execute()
                        st.rerun()
        else:
            st.info("No learned knowledge saved yet.")

    with tab4:
        st.markdown("### 🚗 Vehicle Analytics")
        st.caption("Most common makes, models, years, and vehicle-related questions.")

        combined_rows = analytics_rows + learned_rows_for_analytics

        render_metric_row([
            ("Vehicle Mentions", len([r for r in combined_rows if r.get("vehicle")])),
            ("Unique Makes", len(set([str(r.get("make") or "").strip() for r in combined_rows if r.get("make")]))),
            ("Unique Models", len(set([str(r.get("model") or "").strip() for r in combined_rows if r.get("model")]))),
            ("Unique Years", len(set([str(r.get("year") or "").strip() for r in combined_rows if r.get("year")]))),
        ])

        c1, c2, c3 = st.columns(3)
        with c1:
            render_count_table("Most Common Makes", top_counts(combined_rows, "make", 15), "Make")
        with c2:
            render_count_table("Most Common Models", top_counts(combined_rows, "model", 15), "Model")
        with c3:
            render_count_table("Most Common Years", top_counts(combined_rows, "year", 15), "Year")

        st.markdown("#### Most Common Vehicle Strings")
        render_count_table("Vehicle Models / Platforms", top_counts(combined_rows, "vehicle", 20), "Vehicle")

    with tab5:
        st.markdown("### 📦 Product Analytics")
        st.caption("Products staff search most often, and products associated with the most issues.")

        render_metric_row([
            ("Product Searches", len([r for r in analytics_rows if r.get("product")])),
            ("Unique Products", len(set([str(r.get("product") or "").strip() for r in analytics_rows if r.get("product")]))),
            ("Product-Related Issues", len([r for r in analytics_rows if r.get("product") and r.get("issue")])),
        ])

        c1, c2 = st.columns(2)
        with c1:
            render_count_table("Most Searched Products", top_counts(analytics_rows, "product", 20), "Product")
        with c2:
            product_issue_rows = [r for r in analytics_rows if r.get("product") and r.get("issue")]
            render_count_table("Products With Most Issues", top_counts(product_issue_rows, "product", 20), "Product")

        st.markdown("#### Product Issue Details")
        product_issue_rows = [r for r in analytics_rows if r.get("product") and r.get("issue")][:50]
        if product_issue_rows:
            for row in product_issue_rows:
                st.write(f"**{row.get('product')}** — {row.get('issue')} | {row.get('vehicle') or 'No vehicle'}")
        else:
            st.info("No product issue data yet.")

    with tab6:
        st.markdown("### 🔧 Technical Analytics")
        st.caption("Recurring technical issues, successful solutions, unanswered questions, and resolution tracking.")

        unanswered_rows = [r for r in analytics_rows if r.get("was_unanswered")]
        resolved_rows = [r for r in analytics_rows if r.get("resolved")]
        avg_response = safe_avg(analytics_rows, "response_time")

        render_metric_row([
            ("Top Questions Logged", len(analytics_rows)),
            ("Resolved Rate", f"{resolved_rate(analytics_rows)}%"),
            ("Unanswered Questions", len(unanswered_rows)),
            ("Avg Response Time", f"{avg_response}s" if avg_response else "N/A"),
        ])

        c1, c2 = st.columns(2)
        with c1:
            render_count_table("Top Recurring Issues", top_counts(analytics_rows + learned_rows_for_analytics, "issue", 20), "Issue")
        with c2:
            frequent_solutions = sorted(
                [r for r in learned_rows_for_analytics if r.get("solution") or r.get("approved_answer")],
                key=lambda r: int(r.get("times_seen") or 1),
                reverse=True
            )[:15]

            st.markdown("#### Most Successful / Reused Solutions")
            if frequent_solutions:
                for row in frequent_solutions:
                    st.write(
                        f"**{row.get('vehicle') or 'N/A'}** — {row.get('issue') or 'Issue'} "
                        f"| Seen: {row.get('times_seen') or 1}x | Confidence: {row.get('confidence_score') or 0}%"
                    )
            else:
                st.info("No reusable solutions yet.")

        st.markdown("#### Unanswered Questions")
        if unanswered_rows:
            for row in unanswered_rows[:40]:
                with st.expander(f"{(row.get('vehicle') or 'Unknown')} | {(row.get('issue') or 'Unanswered')[:90]}"):
                    st.write(f"**Assistant:** {row.get('assistant') or ''}")
                    st.write(f"**User:** {row.get('username') or ''}")
                    st.write(f"**Product:** {row.get('product') or ''}")
                    st.write(f"**Confidence:** {row.get('confidence_score') or 0}%")
                    st.write(f"**Keywords:** {row.get('keywords') or ''}")
                    st.markdown("**Question**")
                    st.write(row.get("question") or "")
                    st.markdown("**AI Answer**")
                    st.write(row.get("answer") or "")
        else:
            st.success("No unanswered questions logged yet.")

    with tab7:
        st.markdown("### 📊 AI Analytics")
        st.caption("Confidence trend, token usage, response time, assistant usage, and duplicate questions.")

        total_tokens = total_numeric(analytics_rows, "tokens_used")
        duplicate_questions = len([r for r in analytics_rows if r.get("duplicate_of") or str(r.get("learning_mode") or "").lower() == "updated"])
        avg_response = safe_avg(analytics_rows, "response_time")
        avg_confidence = round(safe_avg(analytics_rows, "confidence_score"))

        render_metric_row([
            ("Total AI Questions", len(analytics_rows)),
            ("Avg Confidence", f"{avg_confidence}%"),
            ("OpenAI Token Usage", total_tokens if total_tokens else "N/A"),
            ("Avg Response Time", f"{avg_response}s" if avg_response else "N/A"),
            ("Duplicate Questions", duplicate_questions),
        ])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Confidence Trend")
            trend_rows = list(reversed(analytics_rows[:80]))
            if trend_rows:
                chart_data = [{"Case": idx + 1, "Confidence": int(row.get("confidence_score") or 0)} for idx, row in enumerate(trend_rows)]
                st.line_chart(chart_data, x="Case", y="Confidence")
            else:
                st.info("No confidence trend data yet.")

            st.markdown("#### Daily Question Volume")
            daily_data = daily_question_counts(analytics_rows, limit=30)
            if daily_data:
                st.bar_chart(daily_data, x="Date", y="Questions")
            else:
                st.info("No volume data yet.")

        with c2:
            render_count_table("Assistant Usage", assistant_counts(analytics_rows, 15), "Assistant")
            render_count_table("Most Active Users", user_counts(analytics_rows, 15), "User")

        st.markdown("#### Most Reused Knowledge")
        reused = sorted(
            [r for r in learned_rows_for_analytics if r.get("times_seen")],
            key=lambda r: int(r.get("times_seen") or 0),
            reverse=True
        )[:20]
        if reused:
            for row in reused:
                st.write(
                    f"**{row.get('issue') or 'Issue'}** | {row.get('vehicle') or 'N/A'} | "
                    f"Used/Seen: {row.get('times_seen') or 0} | Confidence: {row.get('confidence_score') or 0}%"
                )
        else:
            st.info("No reused knowledge yet.")

    with tab8:
        st.markdown("### 📈 Learning Analytics")
        st.caption("Auto-extracted knowledge, new vectors, search success, learning accuracy, and continuous improvement metrics.")

        auto_extracted = len(learned_rows_for_analytics)
        new_vectors = len([r for r in learned_rows_for_analytics if r.get("openai_file_id")])
        search_success_rate = resolved_rate(analytics_rows)
        learning_accuracy = round(safe_avg(learned_rows_for_analytics, "confidence_score"))
        continuous_updates = len([r for r in analytics_rows if str(r.get("learning_mode") or "").lower() == "updated"])

        render_metric_row([
            ("Auto-Extracted Knowledge", auto_extracted),
            ("New Vectors Created", new_vectors),
            ("Search Success Rate", f"{search_success_rate}%"),
            ("Learning Accuracy", f"{learning_accuracy}%"),
            ("Continuous Improvements", continuous_updates),
        ])

        st.markdown("#### Continuous Improvement Trend")
        updated_rows = [r for r in analytics_rows if str(r.get("learning_mode") or "").lower() == "updated"]
        improvement_chart = growth_counts(updated_rows, "created_at", limit=30, label="Improved Records")
        if improvement_chart:
            st.bar_chart(improvement_chart, x="Date", y="Improved Records")
        else:
            st.info("No duplicate/improvement events yet.")

        st.markdown("#### Learning Quality")
        quality_rows = sorted(
            learned_rows_for_analytics,
            key=lambda r: int(r.get("confidence_score") or 0),
            reverse=True
        )[:30]
        if quality_rows:
            for row in quality_rows:
                st.write(
                    f"**{row.get('confidence_score') or 0}%** — {row.get('vehicle') or 'N/A'} | "
                    f"{row.get('issue') or row.get('question') or 'Knowledge'}"
                )
        else:
            st.info("No quality data yet.")



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
        key=f"chat_file_uploader_{st.session_state.chat_file_uploader_generation}"
    )

    st.caption("Drag and drop files anywhere in the chat, or paste a screenshot with Ctrl+V.")
    install_global_chat_file_dropzone()

    for msg in st.session_state.messages:
        render_chat_message(msg["role"], msg["content"])

    st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)
    if st.session_state.get("scroll_to_bottom"):
        auto_scroll_to_latest()
        st.session_state.scroll_to_bottom = False

    prompt = st.chat_input("Message AutoTecPro AI...")

    if prompt:
        user_display = clean_visible_chat_text(prompt)
        uploaded_image_previews = get_uploaded_image_previews(uploaded_files)

        if uploaded_files:
            file_names = ", ".join([file.name for file in uploaded_files])
            user_display += f"\n\n📎 Attached: {file_names}"

        user_content_to_save = user_display + serialize_images_marker(uploaded_image_previews)

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
            "content": user_content_to_save
        })

        try:
            save_message(st.session_state.conversation_id, "user", user_content_to_save)
        except Exception as e:
            st.warning(f"User message was not saved to history: {e}")

        render_chat_message("user", user_display, uploaded_image_previews)

        with st.spinner("Searching AutoTecPro knowledge base..."):
            response_start_time = time.time()
            answer = ask_ai(prompt, uploaded_files)
            answer = clean_visible_chat_text(answer)
            response_time = round(time.time() - response_start_time, 2)
            tokens_used = None

        render_chat_message("assistant", answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        try:
            save_message(st.session_state.conversation_id, "assistant", answer)
        except Exception as e:
            st.warning(f"AI answer was not saved to history: {e}")

        # Continuous Learning:
        # Automatically extracts reusable knowledge, detects duplicates,
        # improves existing records, and syncs final knowledge to OpenAI Vector Store.
        learning_result = None
        try:
            learning_result = auto_learn_from_latest_answer(prompt, answer, assistant)
            if learning_result and learning_result.get("learned"):
                mode = learning_result.get("mode", "saved")
                st.toast(f"AI learned from this case ({mode}).", icon="🧠")
        except Exception as e:
            st.caption(f"AI learning skipped: {e}")

        # Analytics:
        # Tracks most common vehicles, recurring issues, searched products,
        # unanswered questions, confidence trend, and learning performance.
        try:
            log_ai_analytics(prompt, answer, assistant, learning_result, response_time=response_time, tokens_used=tokens_used)
        except Exception:
            pass

        # Clear uploaded files after this message is completed.
        # The image remains saved inside this specific user message/history item,
        # but it will not be automatically reused in the next conversation turn.
        st.session_state.chat_file_uploader_generation += 1

        st.session_state.scroll_to_bottom = True
        st.rerun()
