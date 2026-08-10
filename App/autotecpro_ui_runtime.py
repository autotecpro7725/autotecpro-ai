"""AutoTecPro AI UI runtime helpers.

Large CSS/JavaScript renderers are isolated from business logic without altering
their bodies, selectors, timing, or Streamlit behavior.
"""
import streamlit as st
import streamlit.components.v1 as components

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

        .stTextInput input {
            background-color: rgba(15, 23, 42, 0.96) !important;
            color: #ffffff !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
        }

        /*
         * Canonical textarea style.
         * The BaseWeb wrapper owns the only visible border. The editable
         * textarea is deliberately borderless so mobile Safari cannot draw a
         * second nested focus rectangle.
         */
        .stTextArea div[data-baseweb="textarea"] {
            background-color: rgba(15, 23, 42, 0.96) !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            outline: none !important;
            box-shadow: none !important;
            -webkit-box-shadow: none !important;
            overflow: hidden !important;
        }

        .stTextArea div[data-baseweb="textarea"]:focus-within {
            border-color: var(--atp-red) !important;
            outline: none !important;
            box-shadow: none !important;
            -webkit-box-shadow: none !important;
        }

        .stTextArea textarea,
        .stTextArea textarea:focus,
        .stTextArea textarea:focus-visible,
        .stTextArea textarea:active {
            background-color: transparent !important;
            color: #ffffff !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            -webkit-box-shadow: none !important;
            border-radius: 11px !important;
            background-image: none !important;
            -webkit-appearance: none !important;
            appearance: none !important;
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

        .stTextInput input:focus {
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

        div[data-testid="stSidebar"] hr {
        margin: 22px 0 0 0 !important;
        border-color: rgba(148, 163, 184, 0.13) !important;
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
            margin-block: 18px;
            color: #ffffff;
            line-height: 1.25;
        }

        .chat-bubble ul {
            margin-top: 6px;
            margin-bottom: 10px;
            padding-left: 22px;
        }

        .chat-bubble ol {
            margin-top: 6px;
            margin-bottom: 12px;
            padding-left: 24px;
        }

        .assistant-bubble .atp-chat-paragraph {
            margin: 0 0 13px 0;
            line-height: 1.72;
        }

        .assistant-bubble .atp-chat-paragraph:last-child {
            margin-bottom: 0;
        }

        .chat-bubble li {
            margin-bottom: 3px;
        }

        /* Copy-safe assistant lists: markers are literal text, not browser-only
           list decorations, so 1./2./3. and bullets survive clipboard paste. */
        .assistant-bubble .atp-copy-list-item {
            margin: 0 0 9px 0;
            padding-left: 1.65em;
            text-indent: -1.65em;
            line-height: 1.62;
            white-space: normal;
        }

        .assistant-bubble .atp-copy-list-item:last-child {
            margin-bottom: 10px;
        }

        .assistant-bubble .atp-copy-numbered {
            padding-left: 2.05em;
            text-indent: -2.05em;
        }

        .assistant-bubble .atp-customer-reply-line {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            margin: 0;
            padding: 0 0 12px 16px;
            border-left: 3px solid rgba(245, 158, 11, 0.72);
            background: rgba(245, 158, 11, 0.055);
            line-height: 1.72;
            white-space: normal;
        }

        .assistant-bubble .atp-customer-reply-line:first-of-type {
            padding-top: 12px;
            border-top-right-radius: 10px;
        }

        .assistant-bubble .atp-customer-reply-line:last-child {
            padding-bottom: 12px;
            border-bottom-right-radius: 10px;
        }

        .assistant-bubble .atp-section-list-item {
            margin: 0 0 10px 0;
            padding: 9px 12px 9px 38px;
            text-indent: -22px;
            line-height: 1.58;
            border-radius: 9px;
            background: rgba(148, 163, 184, 0.07);
            border: 1px solid rgba(148, 163, 184, 0.10);
        }

        .assistant-bubble .atp-required-item::first-letter,
        .assistant-bubble .atp-retained-item::first-letter,
        .assistant-bubble .atp-warning-item::first-letter,
        .assistant-bubble .atp-info-item::first-letter {
            font-weight: 800;
        }

        .assistant-bubble .atp-warning-item {
            background: rgba(245, 158, 11, 0.08);
            border-color: rgba(245, 158, 11, 0.18);
        }

        .assistant-bubble .atp-info-item {
            background: rgba(59, 130, 246, 0.07);
            border-color: rgba(59, 130, 246, 0.16);
        }

        .assistant-bubble .atp-customer-reply-box {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            margin: 0 0 14px 0;
            padding: 14px 16px;
            border-left: 4px solid rgba(245, 158, 11, 0.82);
            border-radius: 0 12px 12px 0;
            background: rgba(245, 158, 11, 0.07);
            box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.10);
            line-height: 1.72;
        }

        .assistant-bubble .atp-customer-reply-box .atp-customer-reply-line {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            margin: 0 0 18px 0;
            padding: 0;
            border: 0;
            background: transparent;
            line-height: 1.72;
        }

        .assistant-bubble .atp-customer-reply-box .atp-customer-reply-line:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
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

        .assistant-bubble h1,
        .assistant-bubble h2,
        .assistant-bubble h3 {
            margin-top: 24px !important;
            margin-bottom: 16px !important;
        }

        .assistant-bubble > h1:first-child,
        .assistant-bubble > h2:first-child,
        .assistant-bubble > h3:first-child {
            margin-top: 0 !important;
        }

        .assistant-bubble table th,
        .assistant-bubble table td {
            padding: 11px 13px;
        }

        .assistant-bubble table tbody tr:nth-child(even) td {
            background: rgba(148, 163, 184, 0.045);
        }

        /* ============================================================
           v68880 MOBILE RESPONSE TABLE FIT
           Keep AI-generated tables inside the mobile message boundary.
           Long cell text wraps vertically instead of forcing a desktop-width
           table beyond the viewport. Desktop table rendering is unchanged.
        ============================================================ */
        @media (max-width: 768px) {
            .chat-bubble,
            .assistant-bubble {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }

            .chat-bubble table,
            .assistant-bubble table {
                display: table !important;
                width: 100% !important;
                min-width: 0 !important;
                max-width: 100% !important;
                table-layout: fixed !important;
                overflow: visible !important;
                box-sizing: border-box !important;
                border-radius: 10px !important;
            }

            .chat-bubble table thead,
            .chat-bubble table tbody,
            .chat-bubble table tr,
            .assistant-bubble table thead,
            .assistant-bubble table tbody,
            .assistant-bubble table tr {
                width: 100% !important;
                max-width: 100% !important;
            }

            .chat-bubble table th,
            .chat-bubble table td,
            .assistant-bubble table th,
            .assistant-bubble table td {
                min-width: 0 !important;
                max-width: none !important;
                width: auto !important;
                white-space: normal !important;
                word-break: break-word !important;
                overflow-wrap: anywhere !important;
                hyphens: auto !important;
                line-height: 1.38 !important;
                padding: 9px 9px !important;
                vertical-align: top !important;
                box-sizing: border-box !important;
            }

            /* Two-column support/specification tables read best with a compact
               label column and a wider detail column. Multi-column tables still
               remain within the viewport because table-layout is fixed. */
            .chat-bubble table th:first-child,
            .chat-bubble table td:first-child,
            .assistant-bubble table th:first-child,
            .assistant-bubble table td:first-child {
                width: 38% !important;
            }

            /* Prevent a nested markdown/code/link node inside a cell from
               re-introducing horizontal overflow. */
            .chat-bubble table th *,
            .chat-bubble table td *,
            .assistant-bubble table th *,
            .assistant-bubble table td * {
                max-width: 100% !important;
                overflow-wrap: anywhere !important;
                word-break: break-word !important;
            }

            /* Leave enough space below long mobile answers so the fixed composer
               never covers the last rows of a table. */
            div[data-testid="stAppViewContainer"] main .block-container {
                padding-bottom: 10.5rem !important;
            }
        }

        .assistant-bubble .atp-compatibility-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 16px 0;
            padding: 8px 12px;
            border-radius: 999px;
            font-weight: 800;
            letter-spacing: 0.01em;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(148, 163, 184, 0.10);
        }

        .assistant-bubble .atp-status-compatible {
            color: #86efac;
            border-color: rgba(34, 197, 94, 0.38);
            background: rgba(34, 197, 94, 0.12);
        }

        .assistant-bubble .atp-status-conditional {
            color: #fde68a;
            border-color: rgba(245, 158, 11, 0.42);
            background: rgba(245, 158, 11, 0.12);
        }

        .assistant-bubble .atp-status-incompatible {
            color: #fca5a5;
            border-color: rgba(239, 68, 68, 0.42);
            background: rgba(239, 68, 68, 0.12);
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

        .chat-bubble ol {
            margin-top: 4px !important;
            margin-bottom: 10px !important;
            padding-left: 22px !important;
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

        .sidebar-newcase-placeholder {
            height: 66px !important;
            min-height: 66px !important;
            margin-top: 22px !important;
            margin-bottom: 8px !important;
            pointer-events: none !important;
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

        /* Generated artwork uses a large chat preview. Uploaded reference
           images keep their existing compact 260px preview. */
        .chat-generated-image-card {
            width: min(100%, 800px) !important;
            max-width: 800px !important;
        }

        .chat-generated-image-card img {
            width: 100% !important;
            max-width: 800px !important;
            height: auto !important;
            object-fit: contain !important;
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
            .chat-image-card,
            .chat-generated-image-card {
                max-width: 100% !important;
                width: 100% !important;
            }

            .chat-generated-image-card img {
                max-width: 100% !important;
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



        /* ============================================================
           MOBILE/DARK-MODE POLISH: uploader + bottom chat composer
           Final overrides placed last so they safely win over old rules.
        ============================================================ */

        /* File uploader: readable text and icon on the dark app background */
        div[data-testid="stFileUploader"] {
            background: rgba(15, 23, 42, 0.72) !important;
            border: 1px solid rgba(148, 163, 184, 0.24) !important;
            border-radius: 16px !important;
            padding: 12px !important;
        }

        div[data-testid="stFileUploader"] > label,
        div[data-testid="stFileUploader"] > label p {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            opacity: 1 !important;
        }

        div[data-testid="stFileUploader"] section,
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
            background: rgba(2, 6, 23, 0.52) !important;
            border: 1px dashed rgba(148, 163, 184, 0.42) !important;
            border-radius: 13px !important;
            min-height: 92px !important;
        }

        div[data-testid="stFileUploader"] section:hover,
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover {
            border-color: rgba(239, 68, 68, 0.72) !important;
            background: rgba(15, 23, 42, 0.82) !important;
        }

        div[data-testid="stFileUploader"] section *,
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] *,
        div[data-testid="stFileUploader"] small,
        div[data-testid="stFileUploader"] span,
        div[data-testid="stFileUploader"] p {
            color: #e5e7eb !important;
            -webkit-text-fill-color: #e5e7eb !important;
            opacity: 1 !important;
        }

        div[data-testid="stFileUploader"] svg {
            color: #f8fafc !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            opacity: 1 !important;
        }

        div[data-testid="stFileUploader"] button {
            min-height: 36px !important;
            height: 36px !important;
            width: auto !important;
            padding: 0 14px !important;
            border-radius: 10px !important;
            border: 1px solid rgba(148, 163, 184, 0.28) !important;
            background: rgba(30, 41, 59, 0.96) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: none !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            transform: none !important;
        }

        div[data-testid="stFileUploader"] button:hover {
            background: rgba(51, 65, 85, 1) !important;
            border-color: rgba(239, 68, 68, 0.58) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Clean ChatGPT-style bottom composer */
        div[data-testid="stChatInput"] {
            background: rgba(2, 6, 23, 0.88) !important;
            border: 1px solid rgba(148, 163, 184, 0.30) !important;
            border-radius: 18px !important;
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.30) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            overflow: hidden !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: rgba(239, 68, 68, 0.88) !important;
            box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.34), 0 14px 38px rgba(0, 0, 0, 0.34) !important;
        }

        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            background: transparent !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            caret-color: #ef4444 !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 15px !important;
            line-height: 1.45 !important;
            padding-top: 13px !important;
            padding-bottom: 13px !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] input::placeholder {
            color: #94a3b8 !important;
            -webkit-text-fill-color: #94a3b8 !important;
            opacity: 1 !important;
        }

        div[data-testid="stChatInput"] button {
            width: 38px !important;
            min-width: 38px !important;
            height: 38px !important;
            min-height: 38px !important;
            margin: 5px 7px 5px 4px !important;
            padding: 0 !important;
            border-radius: 12px !important;
            border: none !important;
            background: linear-gradient(135deg, #ff5a3d 0%, #ef4444 55%, #dc2626 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: 0 7px 18px rgba(239, 68, 68, 0.30) !important;
            transform: none !important;
        }

        div[data-testid="stChatInput"] button:hover {
            filter: brightness(1.08) !important;
            transform: none !important;
        }

        div[data-testid="stChatInput"] button svg {
            color: #ffffff !important;
            fill: currentColor !important;
            stroke: currentColor !important;
        }

        @media (max-width: 768px) {
            /* Override the older white mobile input rule */
            div[data-testid="stChatInput"],
            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                background: rgba(2, 6, 23, 0.96) !important;
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
            }

            div[data-testid="stChatInput"] {
                border-radius: 16px !important;
                margin-bottom: max(8px, env(safe-area-inset-bottom)) !important;
            }

            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                font-size: 16px !important; /* prevents iOS auto zoom */
                min-height: 48px !important;
            }

            div[data-testid="stChatInput"] textarea::placeholder,
            div[data-testid="stChatInput"] input::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
            }

            div[data-testid="stFileUploader"] {
                padding: 10px !important;
                border-radius: 14px !important;
            }

            div[data-testid="stFileUploader"] section,
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
                background: rgba(2, 6, 23, 0.72) !important;
                min-height: 86px !important;
            }

            div[data-testid="stFileUploader"] section *,
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] *,
            div[data-testid="stFileUploader"] small,
            div[data-testid="stFileUploader"] span,
            div[data-testid="stFileUploader"] p,
            div[data-testid="stFileUploader"] button,
            div[data-testid="stFileUploader"] button * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }
        }



        /* ============================================================
           FINAL MOBILE ALIGNMENT: centered upload icon + clean composer
        ============================================================ */

        /* Keep the upload button icon and label perfectly centered */
        div[data-testid="stFileUploader"] button,
        div[data-testid="stFileUploader"] button > div,
        div[data-testid="stFileUploader"] button > span,
        div[data-testid="stFileUploader"] button p {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
            line-height: 1 !important;
            vertical-align: middle !important;
        }

        div[data-testid="stFileUploader"] button svg {
            width: 18px !important;
            height: 18px !important;
            min-width: 18px !important;
            display: block !important;
            margin: 0 !important;
            position: static !important;
            transform: none !important;
        }

        /* Remove Streamlit's inner rectangle so the composer reads as one pill */
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] [data-baseweb="textarea"],
        div[data-testid="stChatInput"] [data-baseweb="base-input"],
        div[data-testid="stChatInput"] div[class*="st-emotion-cache"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatInput"] {
            min-height: 58px !important;
            display: flex !important;
            align-items: center !important;
            padding: 6px 8px 6px 16px !important;
            background: rgba(21, 27, 41, 0.96) !important;
            border: 1px solid rgba(148, 163, 184, 0.30) !important;
            border-radius: 22px !important;
            overflow: hidden !important;
        }

        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            min-height: 44px !important;
            height: 44px !important;
            padding: 11px 8px !important;
            margin: 0 !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            resize: none !important;
        }

        div[data-testid="stChatInput"] button {
            width: 42px !important;
            min-width: 42px !important;
            max-width: 42px !important;
            height: 42px !important;
            min-height: 42px !important;
            max-height: 42px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex: 0 0 42px !important;
        }

        div[data-testid="stChatInput"] button svg {
            width: 21px !important;
            height: 21px !important;
            margin: 0 !important;
            display: block !important;
            transform: none !important;
        }

        @media (max-width: 768px) {
            div[data-testid="stChatInput"] {
                min-height: 60px !important;
                padding: 7px 8px 7px 16px !important;
                border-radius: 22px !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                min-height: 44px !important;
                height: 44px !important;
                font-size: 16px !important;
                padding: 10px 6px !important;
            }

            div[data-testid="stFileUploader"] button {
                min-height: 42px !important;
                height: 42px !important;
                padding: 0 16px !important;
            }
        }


        /* ============================================================
           FINAL PHOTO-MATCH COMPOSER + SAFE BROWSER VOICE DICTATION
        ============================================================ */
        div[data-testid="stChatInput"] {
            position: relative !important;
            min-height: 66px !important;
            padding: 7px 9px 7px 68px !important;
            background: linear-gradient(90deg, rgba(28, 35, 50, 0.98), rgba(18, 25, 39, 0.98)) !important;
            border: 1px solid rgba(248, 113, 113, 0.46) !important;
            border-radius: 24px !important;
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.30) !important;
            overflow: visible !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: rgba(248, 113, 113, 0.78) !important;
            box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.18), 0 14px 36px rgba(0, 0, 0, 0.34) !important;
        }

        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] [data-baseweb="textarea"],
        div[data-testid="stChatInput"] [data-baseweb="base-input"],
        div[data-testid="stChatInput"] div[class*="st-emotion-cache"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            min-height: 50px !important;
            height: 50px !important;
            padding: 13px 8px !important;
            margin: 0 !important;
            background: transparent !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            border: 0 !important;
            box-shadow: none !important;
            font-size: 16px !important;
            line-height: 1.4 !important;
            resize: none !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] input::placeholder {
            color: #a8b1c1 !important;
            -webkit-text-fill-color: #a8b1c1 !important;
            opacity: 1 !important;
        }

        div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
            width: 48px !important;
            min-width: 48px !important;
            max-width: 48px !important;
            height: 48px !important;
            min-height: 48px !important;
            max-height: 48px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            border: none !important;
            background: linear-gradient(135deg, #ff5a4f 0%, #ff4141 58%, #ef3038 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 20px rgba(239, 68, 68, 0.30) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex: 0 0 48px !important;
        }

        div[data-testid="stChatInput"] button:not(.atp-voice-trigger) svg {
            width: 23px !important;
            height: 23px !important;
            margin: 0 !important;
        }

        .atp-voice-trigger {
            position: absolute !important;
            left: 13px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            z-index: 20 !important;
            width: 46px !important;
            min-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            padding: 0 !important;
            margin: 0 !important;
            border: 0 !important;
            border-radius: 50% !important;
            background: rgba(71, 82, 103, 0.42) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 31px !important;
            font-weight: 300 !important;
            line-height: 1 !important;
            cursor: pointer !important;
            user-select: none !important;
            -webkit-tap-highlight-color: transparent !important;
        }

        .atp-voice-trigger:hover {
            background: rgba(91, 103, 126, 0.58) !important;
        }

        .atp-voice-trigger.listening {
            background: rgba(239, 68, 68, 0.92) !important;
            box-shadow: 0 0 0 5px rgba(239, 68, 68, 0.14) !important;
            animation: atpVoicePulse 1.25s ease-in-out infinite !important;
        }

        .atp-voice-trigger.unsupported {
            opacity: 0.58 !important;
            cursor: not-allowed !important;
        }

        @keyframes atpVoicePulse {
            0%, 100% { transform: translateY(-50%) scale(1); }
            50% { transform: translateY(-50%) scale(1.07); }
        }

        @media (max-width: 768px) {
            div[data-testid="stChatInput"] {
                min-height: 66px !important;
                padding: 7px 8px 7px 68px !important;
                border-radius: 24px !important;
                margin-bottom: max(10px, env(safe-area-inset-bottom)) !important;
            }

            div[data-testid="stChatInput"] textarea,
            div[data-testid="stChatInput"] input {
                min-height: 50px !important;
                height: 50px !important;
                font-size: 16px !important;
                padding: 13px 6px !important;
            }

            .atp-voice-trigger {
                left: 12px !important;
                width: 46px !important;
                min-width: 46px !important;
                height: 46px !important;
                min-height: 46px !important;
            }
        }

        /* ============================================================
           FINAL CROSS-DEVICE UI FIX
           Desktop + mobile uploader and chat composer alignment.
        ============================================================ */

        /* Upload button: center icon and text vertically on all devices */
        html body div[data-testid="stFileUploader"] button,
        html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            display: inline-flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 9px !important;
            width: auto !important;
            min-width: 0 !important;
            min-height: 46px !important;
            height: 46px !important;
            max-height: 46px !important;
            padding: 0 18px !important;
            margin: 0 !important;
            line-height: 1 !important;
            box-sizing: border-box !important;
        }

        html body div[data-testid="stFileUploader"] button > div,
        html body div[data-testid="stFileUploader"] button > span,
        html body div[data-testid="stFileUploader"] button p {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }

        html body div[data-testid="stFileUploader"] button svg {
            display: block !important;
            flex: 0 0 19px !important;
            width: 19px !important;
            min-width: 19px !important;
            height: 19px !important;
            margin: 0 !important;
            position: static !important;
            transform: none !important;
            vertical-align: middle !important;
        }

        /* Compact one-row composer on both desktop and mobile */
        html body div[data-testid="stChatInput"] {
            position: relative !important;
            box-sizing: border-box !important;
            width: 100% !important;
            min-height: 64px !important;
            height: 64px !important;
            max-height: 64px !important;
            margin: 0 !important;
            padding: 7px 68px 7px 62px !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: visible !important;
            border-radius: 22px !important;
            background: linear-gradient(
                90deg,
                rgba(28, 35, 50, 0.98),
                rgba(18, 25, 39, 0.98)
            ) !important;
            border: 1px solid rgba(248, 113, 113, 0.52) !important;
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.30) !important;
        }

        /* Prevent Streamlit's nested wrappers from making the composer tall */
        html body div[data-testid="stChatInput"] > div:has(textarea),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            box-sizing: border-box !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 44px !important;
            height: 44px !important;
            max-height: 44px !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] textarea,
        html body div[data-testid="stChatInput"] input {
            box-sizing: border-box !important;
            display: block !important;
            width: 100% !important;
            min-width: 0 !important;
            min-height: 44px !important;
            height: 44px !important;
            max-height: 44px !important;
            margin: 0 !important;
            padding: 11px 6px !important;
            border: 0 !important;
            outline: 0 !important;
            resize: none !important;
            overflow: hidden !important;
            white-space: nowrap !important;
            line-height: 22px !important;
            font-size: 16px !important;
            text-align: left !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
        }

        html body div[data-testid="stChatInput"] textarea::placeholder,
        html body div[data-testid="stChatInput"] input::placeholder {
            color: #94a3b8 !important;
            -webkit-text-fill-color: #94a3b8 !important;
            opacity: 1 !important;
        }

        /* SVG voice button centered at left */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            position: absolute !important;
            left: 8px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            box-sizing: border-box !important;
            width: 46px !important;
            min-width: 46px !important;
            max-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 30 !important;
            color: #ffffff !important;
            background: linear-gradient(
                135deg,
                #ff5a3d 0%,
                #ef4444 55%,
                #dc2626 100%
            ) !important;
            border: 0 !important;
            box-shadow: 0 7px 18px rgba(239, 68, 68, 0.30) !important;
        }

        html body #atp-browser-voice-dictation svg,
        html body .atp-voice-trigger svg {
            display: block !important;
            width: 23px !important;
            height: 23px !important;
            margin: 0 !important;
            fill: none !important;
            stroke: currentColor !important;
            stroke-width: 1.9 !important;
            stroke-linecap: round !important;
            stroke-linejoin: round !important;
        }

        /* Native send button centered at right */
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
            position: absolute !important;
            right: 8px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            box-sizing: border-box !important;
            width: 46px !important;
            min-width: 46px !important;
            max-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 25 !important;
            background: linear-gradient(
                135deg,
                #ff5a3d 0%,
                #ef4444 55%,
                #dc2626 100%
            ) !important;
            border: 0 !important;
            box-shadow: 0 7px 18px rgba(239, 68, 68, 0.30) !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) svg {
            display: block !important;
            width: 22px !important;
            height: 22px !important;
            margin: 0 !important;
            color: #ffffff !important;
        }

        html body #atp-browser-voice-dictation.listening,
        html body .atp-voice-trigger.listening {
            animation: atpVoicePulse 1.15s ease-in-out infinite !important;
        }

        @keyframes atpVoicePulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.35);
            }
            50% {
                box-shadow: 0 0 0 8px rgba(239, 68, 68, 0.08);
            }
        }

        @media (min-width: 769px) {
            html body div[data-testid="stChatInput"] {
                max-width: 980px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                min-height: 62px !important;
                height: 62px !important;
                max-height: 62px !important;
                padding: 7px 66px 7px 60px !important;
                border-radius: 21px !important;
                margin-bottom: max(8px, env(safe-area-inset-bottom)) !important;
            }

            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger {
                left: 8px !important;
                width: 44px !important;
                min-width: 44px !important;
                max-width: 44px !important;
                height: 44px !important;
                min-height: 44px !important;
                max-height: 44px !important;
            }

            html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
                right: 8px !important;
                width: 44px !important;
                min-width: 44px !important;
                max-width: 44px !important;
                height: 44px !important;
                min-height: 44px !important;
                max-height: 44px !important;
            }
        }


        /* ============================================================
           FINAL V2 ALIGNMENT OVERRIDE
           Fixes send-button centering, uploader icon position, and composer width.
        ============================================================ */

        /* Wider composer on desktop, full-width on mobile */
        html body div[data-testid="stChatInput"] {
            width: calc(100% - 12px) !important;
            max-width: 1180px !important;
            min-height: 64px !important;
            height: 64px !important;
            max-height: 64px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding: 7px 70px 7px 62px !important;
            box-sizing: border-box !important;
        }

        /* Keep all nested Streamlit wrappers vertically centered */
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            height: 44px !important;
            min-height: 44px !important;
            max-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] textarea,
        html body div[data-testid="stChatInput"] input {
            height: 44px !important;
            min-height: 44px !important;
            max-height: 44px !important;
            line-height: 22px !important;
            padding: 11px 8px !important;
            margin: 0 !important;
            display: block !important;
            box-sizing: border-box !important;
        }

        /* Force the native Streamlit send button into the exact vertical center */
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
            position: absolute !important;
            top: 50% !important;
            right: 9px !important;
            bottom: auto !important;
            left: auto !important;
            transform: translate3d(0, -50%, 0) !important;
            width: 46px !important;
            min-width: 46px !important;
            max-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            align-self: center !important;
            line-height: 1 !important;
            box-sizing: border-box !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) > div,
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) > span,
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) p {
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1 !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) svg {
            width: 22px !important;
            height: 22px !important;
            margin: 0 !important;
            display: block !important;
            transform: translateY(0) !important;
        }

        /* Voice button centered to match send button */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            top: 50% !important;
            left: 9px !important;
            bottom: auto !important;
            transform: translate3d(0, -50%, 0) !important;
            width: 46px !important;
            min-width: 46px !important;
            max-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }

        /* Lower uploader icon slightly without moving the text */
        html body div[data-testid="stFileUploader"] button svg,
        html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] svg {
            transform: translateY(2px) !important;
        }

        html body div[data-testid="stFileUploader"] button,
        html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            min-height: 46px !important;
            height: 46px !important;
            max-height: 46px !important;
            align-items: center !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                width: calc(100% - 8px) !important;
                max-width: none !important;
                min-height: 62px !important;
                height: 62px !important;
                max-height: 62px !important;
                padding: 7px 66px 7px 60px !important;
            }

            html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger),
            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger {
                width: 44px !important;
                min-width: 44px !important;
                max-width: 44px !important;
                height: 44px !important;
                min-height: 44px !important;
                max-height: 44px !important;
            }

            html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
                right: 8px !important;
            }

            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger {
                left: 8px !important;
            }

            html body div[data-testid="stFileUploader"] button svg,
            html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] svg {
                transform: translateY(2px) !important;
            }
        }


        /* ============================================================
           FINAL V3 RESPONSIVE ALIGNMENT
           - uploader button vertically centered in dropzone
           - composer spans available width responsively
           - send button aligned to far-right edge
           - desktop/mobile auto-adjust
        ============================================================ */

        /* Make the uploader dropzone a true vertically-centered row */
        html body div[data-testid="stFileUploader"] section,
        html body div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            min-height: 112px !important;
            height: 112px !important;
            padding: 0 24px !important;
            box-sizing: border-box !important;
        }

        html body div[data-testid="stFileUploader"] section > div,
        html body div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            width: 100% !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            gap: 24px !important;
        }

        html body div[data-testid="stFileUploader"] button,
        html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            align-self: center !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            transform: translateY(4px) !important;
        }

        html body div[data-testid="stFileUploader"] button svg,
        html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] svg {
            transform: translateY(2px) !important;
        }

        /* Composer uses nearly all available horizontal space */
        html body div[data-testid="stChatInput"] {
            width: calc(100% - 4px) !important;
            max-width: none !important;
            min-width: 0 !important;
            margin-left: 2px !important;
            margin-right: 2px !important;
            box-sizing: border-box !important;
            padding-left: 64px !important;
            padding-right: 64px !important;
        }

        /* Keep message field flexible between mic and send controls */
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
        }

        /* Voice button aligned with left edge */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            left: 8px !important;
        }

        /* Send button flush to right edge and vertically centered */
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
            right: 6px !important;
            top: 50% !important;
            bottom: auto !important;
            transform: translate3d(0, -50%, 0) !important;
            margin: 0 !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) > div,
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) > span,
        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) p {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) svg {
            position: static !important;
            transform: none !important;
            margin: 0 !important;
        }

        /* Desktop layout */
        @media (min-width: 1200px) {
            html body div[data-testid="stChatInput"] {
                width: calc(100% - 8px) !important;
                margin-left: 4px !important;
                margin-right: 4px !important;
            }
        }

        /* Tablet */
        @media (min-width: 769px) and (max-width: 1199px) {
            html body div[data-testid="stChatInput"] {
                width: calc(100% - 6px) !important;
                margin-left: 3px !important;
                margin-right: 3px !important;
            }
        }

        /* Mobile */
        @media (max-width: 768px) {
            html body div[data-testid="stFileUploader"] section,
            html body div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
                min-height: 104px !important;
                height: 104px !important;
                padding: 0 18px !important;
            }

            html body div[data-testid="stFileUploader"] section > div,
            html body div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div {
                gap: 18px !important;
            }

            html body div[data-testid="stFileUploader"] button,
            html body div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
                transform: translateY(5px) !important;
            }

            html body div[data-testid="stChatInput"] {
                width: calc(100% - 4px) !important;
                margin-left: 2px !important;
                margin-right: 2px !important;
                padding-left: 60px !important;
                padding-right: 60px !important;
            }

            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger {
                left: 6px !important;
            }

            html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
                right: 4px !important;
            }
        }


        /* ============================================================
           LOGIN LAYOUT SAFETY
           Preserve the original login-page width and alignment.
        ============================================================ */
        body:has(.login-heading) .block-container,
        body:has(.login-logo) .block-container {
            max-width: 680px !important;
            padding-top: 64px !important;
            padding-bottom: 40px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }


        /* ============================================================
           FINAL V5 SEND POSITION
           Keep login untouched; only adjust the chat composer controls.
        ============================================================ */
        html body div[data-testid="stChatInput"] {
            padding-right: 60px !important;
        }

        html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
            right: 0px !important;
            top: 50% !important;
            bottom: auto !important;
            transform: translate3d(0, -50%, 0) !important;
            margin: 0 !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                padding-right: 58px !important;
            }

            html body div[data-testid="stChatInput"] button:not(.atp-voice-trigger) {
                right: 0px !important;
            }
        }


        /* ============================================================
           FINAL V6 SEND EDGE FIX
           Hide Streamlit's native send control and use a right-edge proxy.
        ============================================================ */

        /* Hide only Streamlit's native send button; JS proxy keeps behavior. */
        html body div[data-testid="stChatInput"]
        button:not(.atp-voice-trigger):not(.atp-send-proxy) {
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            width: 1px !important;
            min-width: 1px !important;
            max-width: 1px !important;
            height: 1px !important;
            min-height: 1px !important;
            max-height: 1px !important;
            right: 0 !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] {
            padding-right: 58px !important;
        }

        html body #atp-send-proxy,
        html body .atp-send-proxy {
            position: absolute !important;
            right: 4px !important;
            top: 50% !important;
            bottom: auto !important;
            left: auto !important;
            transform: translate3d(0, -50%, 0) !important;
            box-sizing: border-box !important;
            width: 46px !important;
            min-width: 46px !important;
            max-width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            border: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            z-index: 40 !important;
            color: #ffffff !important;
            background: linear-gradient(
                135deg,
                #ff5a3d 0%,
                #ef4444 55%,
                #dc2626 100%
            ) !important;
            box-shadow: 0 7px 18px rgba(239, 68, 68, 0.30) !important;
            cursor: pointer !important;
        }

        html body #atp-send-proxy svg,
        html body .atp-send-proxy svg {
            display: block !important;
            width: 23px !important;
            height: 23px !important;
            margin: 0 !important;
            fill: none !important;
            stroke: currentColor !important;
            stroke-width: 2.1 !important;
            stroke-linecap: round !important;
            stroke-linejoin: round !important;
        }

        html body #atp-send-proxy.disabled,
        html body .atp-send-proxy.disabled {
            opacity: 0.58 !important;
            cursor: default !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                padding-right: 56px !important;
            }

            html body #atp-send-proxy,
            html body .atp-send-proxy {
                right: 3px !important;
                width: 44px !important;
                min-width: 44px !important;
                max-width: 44px !important;
                height: 44px !important;
                min-height: 44px !important;
                max-height: 44px !important;
            }
        }


        /* ============================================================
           FINAL V7 COLOR CLARITY FIX
           - solid login button color
           - solid composer background
           - fully visible send button
        ============================================================ */

        /* Login button: remove gradient fade and keep a clear solid red-orange */
        body:has(.login-heading) .stFormSubmitButton > button,
        body:has(.login-logo) .stFormSubmitButton > button {
            background: #ff3b30 !important;
            background-image: none !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            filter: none !important;
            box-shadow: 0 10px 26px rgba(255, 59, 48, 0.34) !important;
        }

        body:has(.login-heading) .stFormSubmitButton > button:hover,
        body:has(.login-logo) .stFormSubmitButton > button:hover {
            background: #ff4a3f !important;
            background-image: none !important;
            opacity: 1 !important;
            filter: none !important;
        }

        /* Composer: remove left-to-right fade and use one solid dark tone */
        html body div[data-testid="stChatInput"] {
            background: #151b29 !important;
            background-image: none !important;
        }

        /* Voice button: solid and fully visible */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            background: #ff3b30 !important;
            background-image: none !important;
            opacity: 1 !important;
            filter: none !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: 0 7px 18px rgba(255, 59, 48, 0.34) !important;
        }

        /* Send button: solid and fully visible */
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            background: #ff3b30 !important;
            background-image: none !important;
            opacity: 1 !important;
            filter: none !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: 0 7px 18px rgba(255, 59, 48, 0.34) !important;
        }

        /* Keep the send icon visible even when the input is empty */
        html body #atp-send-proxy.disabled,
        html body .atp-send-proxy.disabled {
            opacity: 1 !important;
            filter: none !important;
            background: #ff3b30 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            cursor: default !important;
        }

        html body #atp-send-proxy svg,
        html body .atp-send-proxy svg,
        html body #atp-browser-voice-dictation svg,
        html body .atp-voice-trigger svg {
            color: #ffffff !important;
            stroke: #ffffff !important;
            opacity: 1 !important;
        }


        /* ============================================================
           FINAL V10 AUTO-GROW COMPOSER
           Expands for long typed/pasted text like ChatGPT.
        ============================================================ */
        html body div[data-testid="stChatInput"] {
            height: auto !important;
            min-height: 64px !important;
            max-height: 234px !important;
            align-items: flex-end !important;
            overflow: visible !important;
            padding-top: 7px !important;
            padding-bottom: 7px !important;
        }

        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            height: auto !important;
            min-height: 44px !important;
            max-height: 220px !important;
            align-items: flex-end !important;
            overflow: visible !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            height: auto !important;
            min-height: 44px !important;
            max-height: 220px !important;
            overflow-y: hidden !important;
            white-space: pre-wrap !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            resize: none !important;
            line-height: 22px !important;
            padding-top: 11px !important;
            padding-bottom: 11px !important;
        }

        /* Keep controls at the bottom as the composer expands. */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger,
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            top: auto !important;
            bottom: 9px !important;
            transform: none !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                min-height: 62px !important;
                max-height: 210px !important;
            }

            html body div[data-testid="stChatInput"] textarea {
                max-height: 196px !important;
            }

            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger,
            html body #atp-send-proxy,
            html body .atp-send-proxy {
                bottom: 9px !important;
            }
        }


        /* ============================================================
           FINAL V11 STABLE AUTO-GROW
           Prevent oversized composer while keeping ChatGPT-like growth.
        ============================================================ */
        html body div[data-testid="stChatInput"] {
            height: auto !important;
            min-height: 64px !important;
            max-height: 196px !important;
            align-items: flex-end !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            height: auto !important;
            min-height: 44px !important;
            max-height: 180px !important;
            overflow: visible !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            height: auto !important;
            min-height: 44px !important;
            max-height: 180px !important;
            overflow-y: hidden !important;
            white-space: pre-wrap !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            resize: none !important;
            line-height: 22px !important;
        }

        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger,
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            top: auto !important;
            bottom: 9px !important;
            transform: none !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                max-height: 170px !important;
            }

            html body div[data-testid="stChatInput"] textarea {
                max-height: 154px !important;
            }
        }


        /* ============================================================
           FINAL V12 TEXT WIDTH + AUTO-GROW FIX
           Prevents pasted text from collapsing into one character per line.
        ============================================================ */

        html body div[data-testid="stChatInput"] {
            display: flex !important;
            align-items: flex-end !important;
            width: calc(100% - 4px) !important;
            min-width: 0 !important;
            height: auto !important;
            min-height: 64px !important;
            max-height: 196px !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            display: flex !important;
            flex: 1 1 auto !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            height: auto !important;
            min-height: 44px !important;
            max-height: 180px !important;
            overflow: visible !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            display: block !important;
            flex: 1 1 auto !important;
            box-sizing: border-box !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            height: auto !important;
            min-height: 44px !important;
            max-height: 180px !important;
            overflow-y: hidden !important;
            overflow-x: hidden !important;
            white-space: pre-wrap !important;
            overflow-wrap: break-word !important;
            word-break: normal !important;
            writing-mode: horizontal-tb !important;
            resize: none !important;
            line-height: 22px !important;
            padding: 11px 8px !important;
        }

        html body div[data-testid="stChatInput"] textarea::placeholder {
            white-space: nowrap !important;
        }

        /* Keep voice and send controls fixed at the bottom corners. */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            left: 6px !important;
            top: auto !important;
            bottom: 9px !important;
            transform: none !important;
        }

        html body #atp-send-proxy,
        html body .atp-send-proxy {
            right: 3px !important;
            top: auto !important;
            bottom: 9px !important;
            transform: none !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                max-height: 170px !important;
            }

            html body div[data-testid="stChatInput"] textarea {
                max-height: 154px !important;
            }
        }


        /* ============================================================
           FINAL V13 FULL-WIDTH TEXT AREA
           Let pasted text use the full composer width up to the send button.
        ============================================================ */

        /* Reserve only the actual mic/send button space */
        html body div[data-testid="stChatInput"] {
            padding-left: 62px !important;
            padding-right: 54px !important;
        }

        /* Force the editable area to consume all remaining width */
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            flex: 1 1 0% !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            flex: 1 1 0% !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            padding-left: 8px !important;
            padding-right: 4px !important;
        }

        /* Keep the send button very close to the right edge */
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            right: 2px !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                padding-left: 58px !important;
                padding-right: 52px !important;
            }

            html body #atp-send-proxy,
            html body .atp-send-proxy {
                right: 2px !important;
            }
        }


        /* ============================================================
           FINAL V14 CHATGPT-STYLE FULL TEXT WIDTH
           Let text flow nearly all the way to the send button.
        ============================================================ */

        html body div[data-testid="stChatInput"] {
            display: grid !important;
            grid-template-columns: 54px minmax(0, 1fr) 50px !important;
            align-items: end !important;
            column-gap: 6px !important;
            padding: 7px 4px 7px 4px !important;
            width: calc(100% - 4px) !important;
            box-sizing: border-box !important;
        }

        /* Place the microphone in column 1 */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            position: static !important;
            grid-column: 1 !important;
            grid-row: 1 !important;
            align-self: end !important;
            justify-self: center !important;
            transform: none !important;
            margin: 0 !important;
        }

        /* Place all Streamlit input wrappers in column 2 */
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            grid-column: 2 !important;
            grid-row: 1 !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            flex: 1 1 auto !important;
            box-sizing: border-box !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            box-sizing: border-box !important;
            padding-left: 4px !important;
            padding-right: 2px !important;
            margin: 0 !important;
        }

        /* Place the visible send proxy in column 3 */
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            position: static !important;
            grid-column: 3 !important;
            grid-row: 1 !important;
            align-self: end !important;
            justify-self: end !important;
            transform: none !important;
            margin: 0 !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                grid-template-columns: 50px minmax(0, 1fr) 46px !important;
                column-gap: 4px !important;
                padding-left: 3px !important;
                padding-right: 3px !important;
            }

            html body div[data-testid="stChatInput"] textarea {
                padding-left: 3px !important;
                padding-right: 1px !important;
            }
        }


        /* ============================================================
           FINAL V15 MIC LEFT + FULL CONTENT WIDTH
           Keep the microphone in its original left position while
           allowing text to use the full space up to the send button.
        ============================================================ */

        /* Return composer to a normal flex layout */
        html body div[data-testid="stChatInput"] {
            display: flex !important;
            grid-template-columns: none !important;
            align-items: flex-end !important;
            width: calc(100% - 4px) !important;
            padding: 7px 54px 7px 62px !important;
            box-sizing: border-box !important;
        }

        /* Keep the microphone fixed at the original left position */
        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            position: absolute !important;
            left: 6px !important;
            bottom: 9px !important;
            top: auto !important;
            transform: none !important;
            margin: 0 !important;
            grid-column: auto !important;
            grid-row: auto !important;
            align-self: auto !important;
            justify-self: auto !important;
        }

        /* Let the text wrappers fill all remaining space */
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu),
        html body div[data-testid="stChatInput"] > div:not(.atp-plus-menu) > div,
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            display: flex !important;
            flex: 1 1 auto !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            grid-column: auto !important;
            grid-row: auto !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            flex: 1 1 auto !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            padding-left: 4px !important;
            padding-right: 2px !important;
            margin: 0 !important;
        }

        /* Keep send button at the far right edge */
        html body #atp-send-proxy,
        html body .atp-send-proxy {
            position: absolute !important;
            right: 2px !important;
            bottom: 9px !important;
            top: auto !important;
            transform: none !important;
            margin: 0 !important;
            grid-column: auto !important;
            grid-row: auto !important;
            align-self: auto !important;
            justify-self: auto !important;
        }

        @media (max-width: 768px) {
            html body div[data-testid="stChatInput"] {
                padding-left: 58px !important;
                padding-right: 52px !important;
            }

            html body #atp-browser-voice-dictation,
            html body .atp-voice-trigger {
                left: 6px !important;
            }

            html body #atp-send-proxy,
            html body .atp-send-proxy {
                right: 2px !important;
            }
        }


        /* ============================================================
           FINAL V17 FULL-WIDTH RUNTIME SUPPORT
        ============================================================ */
        html body div[data-testid="stChatInput"] {
            position: relative !important;
            display: block !important;
            width: calc(100% - 4px) !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            display: block !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
            white-space: pre-wrap !important;
            overflow-wrap: break-word !important;
            word-break: normal !important;
            writing-mode: horizontal-tb !important;
        }

        html body #atp-browser-voice-dictation,
        html body .atp-voice-trigger {
            position: absolute !important;
            left: 6px !important;
            bottom: 9px !important;
            top: auto !important;
            transform: none !important;
        }

        html body #atp-send-proxy,
        html body .atp-send-proxy {
            position: absolute !important;
            right: 2px !important;
            bottom: 9px !important;
            top: auto !important;
            transform: none !important;
        }


        /* ============================================================
           MOBILE DARK-MODE FORM TEXT FIX
           Scoped only to Admin user controls and Knowledge Submission.
           This overrides iOS Safari's native dark text inheritance.
        ============================================================ */
        @media (max-width: 768px) {
            /* Admin: Username and Password fields */
            div[class*="st-key-stable_admin_username"] input,
            div[class*="st-key-stable_admin_password"] input {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            div[class*="st-key-stable_admin_username"] input::placeholder,
            div[class*="st-key-stable_admin_password"] input::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /* Admin: selected Role value and opened dropdown options */
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] > div,
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] span,
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] input,
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] [role="combobox"],
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] [aria-selected="true"],
            div[class*="st-key-stable_admin_role"]
            div[data-baseweb="select"] div[class],
            div[data-baseweb="popover"] ul[role="listbox"] li,
            div[data-baseweb="popover"] ul[role="listbox"] li span {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* iOS Safari can render the closed BaseWeb Select value through
               an internal input/value node instead of the visible span. */
            div[class*="st-key-stable_admin_role"]
            [data-testid="stSelectbox"] input,
            div[class*="st-key-stable_admin_role"]
            [data-testid="stSelectbox"] [role="combobox"],
            div[class*="st-key-stable_admin_role"]
            [data-testid="stSelectbox"] div[data-baseweb="select"] * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Admin Upload Knowledge: Optional image-context textarea.
               Mobile-only. Keep one outer focus border and remove the
               overlapping inner textarea border/outline. */
            div[class*="st-key-stable_admin_upload_context"]
            div[data-baseweb="textarea"] {
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                box-shadow: none !important;
                outline: none !important;
                overflow: hidden !important;
            }

            div[class*="st-key-stable_admin_upload_context"]
            div[data-baseweb="textarea"]:focus-within {
                border-color: var(--atp-red) !important;
                box-shadow: none !important;
                outline: none !important;
            }

            div[class*="st-key-stable_admin_upload_context"]
            textarea,
            div[class*="st-key-stable_admin_upload_context"]
            textarea:focus,
            div[class*="st-key-stable_admin_upload_context"]
            textarea:focus-visible {
                border: none !important;
                box-shadow: none !important;
                outline: none !important;
            }

            /* Admin: Edit existing user selected value.
               Mobile-only and scoped to this exact keyed selectbox. */
            div[class*="st-key-stable_admin_edit_user"]
            div[data-baseweb="select"],
            div[class*="st-key-stable_admin_edit_user"]
            div[data-baseweb="select"] *,
            div[class*="st-key-stable_admin_edit_user"]
            [data-testid="stSelectbox"] input,
            div[class*="st-key-stable_admin_edit_user"]
            [data-testid="stSelectbox"] [role="combobox"],
            div[class*="st-key-stable_admin_edit_user"]
            [aria-selected="true"] {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Admin: Permanent Delete User selected value.
               Scoped to mobile only and to this exact keyed widget. */
            div[class*="st-key-stable_permanent_delete_user_select"]
            div[data-baseweb="select"],
            div[class*="st-key-stable_permanent_delete_user_select"]
            div[data-baseweb="select"] *,
            div[class*="st-key-stable_permanent_delete_user_select"]
            [role="combobox"],
            div[class*="st-key-stable_permanent_delete_user_select"]
            input {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Admin: Upload Knowledge database selected value */
            div[class*="st-key-stable_admin_database_choice"]
            [data-testid="stSelectbox"] div[data-baseweb="select"] *,
            div[class*="st-key-stable_admin_database_choice"]
            [data-testid="stSelectbox"] input,
            div[class*="st-key-stable_admin_database_choice"]
            [data-testid="stSelectbox"] [role="combobox"],
            div[class*="st-key-stable_admin_database_choice"]
            div[data-baseweb="select"] * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /* Admin: Permanent Delete username confirmation text.
               Mobile-only and scoped to this exact keyed input. */
            div[class*="st-key-stable_permanent_delete_username_confirm"]
            input {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            div[class*="st-key-stable_permanent_delete_username_confirm"]
            input::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /* Admin: Upload Knowledge optional image context text.
               Mobile-only and scoped to the existing stable textarea key. */
            div[class*="st-key-stable_admin_upload_context"]
            textarea {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            div[class*="st-key-stable_admin_upload_context"]
            textarea::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /* Knowledge Submission: Subject, Issue, and Solution */
            div[class*="st-key-knowledge_structured_fields"] input,
            div[class*="st-key-knowledge_structured_fields"] textarea {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            div[class*="st-key-knowledge_structured_fields"] input::placeholder,
            div[class*="st-key-knowledge_structured_fields"] textarea::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /* iOS Safari autofill can otherwise force dark text. */
            div[class*="st-key-stable_admin_username"]
            input:-webkit-autofill,
            div[class*="st-key-stable_admin_password"]
            input:-webkit-autofill,
            div[class*="st-key-knowledge_structured_fields"]
            input:-webkit-autofill {
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                transition: background-color 9999s ease-out 0s !important;
            }
        }


        /* Final guard: never show accidental code artifact boxes in assistant replies */
        .assistant-bubble pre,
        .assistant-bubble code {
            display: none !important;
        }


        /* ============================================================
           v68886 CLICK-TO-ENLARGE IMAGE LIGHTBOX
           Pure CSS: no JavaScript, no rerun, no pipeline/state changes.
        ============================================================ */
        .atp-enlarge-label {
            display: block;
            width: 100%;
            cursor: zoom-in;
            border-radius: inherit;
            position: relative;
        }

        .atp-enlarge-label::after {
            content: "Click to enlarge";
            position: absolute;
            right: 10px;
            bottom: 10px;
            z-index: 2;
            padding: 5px 8px;
            border-radius: 999px;
            background: rgba(2, 6, 23, 0.78);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            line-height: 1;
            opacity: 0;
            transform: translateY(3px);
            transition: opacity 0.16s ease, transform 0.16s ease;
            pointer-events: none;
            box-shadow: 0 5px 16px rgba(0,0,0,0.22);
        }

        .atp-enlarge-label:hover::after {
            opacity: 1;
            transform: translateY(0);
        }

        .atp-lightbox-toggle {
            position: fixed !important;
            left: -10000px !important;
            top: -10000px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        .atp-lightbox-overlay {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 2147483000;
            align-items: center;
            justify-content: center;
            padding: 24px;
            box-sizing: border-box;
            background: rgba(2, 6, 23, 0.94);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            cursor: zoom-out;
        }

        .atp-lightbox-toggle:checked + .atp-lightbox-overlay {
            display: flex !important;
        }

        .atp-lightbox-frame {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: min(96vw, 1600px);
            height: min(94vh, 1100px);
            padding: 18px;
            box-sizing: border-box;
            border-radius: 16px;
            background: rgba(15, 23, 42, 0.98);
            border: 1px solid rgba(255,255,255,0.16);
            box-shadow: 0 28px 90px rgba(0,0,0,0.58);
            cursor: default;
        }

        .atp-lightbox-frame img {
            display: block !important;
            width: auto !important;
            height: auto !important;
            max-width: 100% !important;
            max-height: 100% !important;
            object-fit: contain !important;
            border-radius: 8px !important;
            background: transparent !important;
        }

        .atp-lightbox-close {
            position: absolute;
            top: 10px;
            right: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border-radius: 999px;
            background: rgba(2, 6, 23, 0.84);
            border: 1px solid rgba(255,255,255,0.22);
            color: #ffffff;
            font-size: 26px;
            font-weight: 400;
            line-height: 1;
            pointer-events: none;
        }

        @media (max-width: 768px) {
            .atp-lightbox-overlay {
                padding: 8px;
            }

            .atp-lightbox-frame {
                width: 98vw;
                height: 92vh;
                padding: 10px;
                border-radius: 12px;
            }

            .atp-enlarge-label::after {
                content: "Tap to enlarge";
                opacity: 0.88;
                transform: none;
                right: 8px;
                bottom: 8px;
                font-size: 10px;
            }
        }

        /* ============================================================
           v68886 PRINT / SAVE-AS-PDF COLOR FIDELITY
           Browser print engines often drop transparent dark backgrounds.
           Use exact solid print colors and remove interactive chrome.
        ============================================================ */
        @media print {
            html,
            body,
            body *,
            [data-testid="stAppViewContainer"],
            [data-testid="stAppViewContainer"] * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }

            @page {
                margin: 12mm 10mm 14mm 10mm;
            }

            html,
            body,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            main,
            main .block-container {
                background: #07111f !important;
                color: #f8fafc !important;
            }

            /* Print the conversation/document body at full page width. */
            section[data-testid="stSidebar"],
            [data-testid="stSidebar"],
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"],
            [data-testid="stChatInput"],
            .atp-lightbox-overlay,
            .atp-lightbox-toggle,
            .atp-enlarge-label::after {
                display: none !important;
            }

            main,
            [data-testid="stMain"],
            main .block-container {
                width: 100% !important;
                max-width: none !important;
                min-width: 0 !important;
                margin: 0 !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
                padding-bottom: 0 !important;
            }

            /* Replace translucent screen colors with deterministic solids so
               PDF/printers do not composite them against white/gray. */
            .chat-row {
                width: 100% !important;
                break-inside: avoid-page;
                page-break-inside: avoid;
            }

            .chat-bubble {
                background: #172338 !important;
                border-color: #334155 !important;
                color: #f8fafc !important;
                box-shadow: none !important;
            }

            .user-bubble {
                background: #173a87 !important;
                border-color: #3565c7 !important;
            }

            .assistant-bubble {
                background: #0f1b2d !important;
                border-color: #6b4d1e !important;
            }

            .assistant-section-card,
            .workspace-card,
            .app-header {
                background: #101c2f !important;
                border-color: #334155 !important;
                box-shadow: none !important;
            }

            .chat-bubble h1,
            .chat-bubble h2,
            .chat-bubble h3,
            .chat-bubble strong,
            .assistant-bubble,
            .assistant-bubble *,
            .user-bubble,
            .user-bubble * {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            .chat-bubble table {
                width: 100% !important;
                max-width: 100% !important;
                table-layout: fixed !important;
                border-collapse: collapse !important;
                break-inside: auto;
                page-break-inside: auto;
            }

            .chat-bubble thead {
                display: table-header-group;
            }

            .chat-bubble tr {
                break-inside: avoid;
                page-break-inside: avoid;
            }

            .chat-bubble th {
                background: #29384f !important;
                border-color: #526176 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }

            .chat-bubble td {
                background: #101c2f !important;
                border-color: #3b4a60 !important;
                color: #e5e7eb !important;
                -webkit-text-fill-color: #e5e7eb !important;
                overflow-wrap: anywhere !important;
                word-break: break-word !important;
            }

            .chat-bubble tr:nth-child(even) td,
            .assistant-bubble table tbody tr:nth-child(even) td {
                background: #152238 !important;
            }

            .chat-image-grid,
            .chat-image-card,
            .atp-pl-image-card {
                break-inside: avoid;
                page-break-inside: avoid;
            }

            .chat-image-card,
            .atp-pl-image-card {
                background: #0f1b2d !important;
                border-color: #334155 !important;
                box-shadow: none !important;
            }

            .chat-image-card img,
            .atp-pl-image-card img,
            .atp-enlarge-label img {
                max-width: 100% !important;
                height: auto !important;
                object-fit: contain !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }

            /* Hide interactive actions but retain the actual image and caption. */
            .atp-pl-image-actions,
            .generated-image-actions,
            [class*="generated-image-actions"] {
                display: none !important;
            }

            a,
            a:visited {
                color: #93c5fd !important;
                -webkit-text-fill-color: #93c5fd !important;
                text-decoration: none !important;
            }
        }

</style>
        """,
        unsafe_allow_html=True
    )


def install_gpt_uploader_css():
    """Render isolated native-uploader and managed-preview styling."""
    st.markdown(
        """
        <style>
        html body div[class*="st-key-atp_upload_shell_"] {
            width: 100% !important;
            border: 1px dashed rgba(248, 113, 113, 0.72) !important;
            border-radius: 18px !important;
            background: rgba(2, 6, 23, 0.30) !important;
            padding: 10px 12px !important;
            box-sizing: border-box !important;
            overflow: visible !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        > div[data-testid="stVerticalBlock"] {
            gap: 7px !important;
        }

        .atp-upload-heading {
            color: #f8fafc;
            font-size: 13px;
            font-weight: 760;
            margin: 0;
            text-align: left;
        }

        .atp-add-file-label {
            width: 100%;
            margin: 2px 0 0;
            color: #cbd5e1;
            font-size: 12.5px;
            font-weight: 650;
            text-align: center;
        }

        /* Keep every managed upload-preview row centered as one compact group.
           Streamlit columns normally expand across the full container, which made
           two or three files appear widely separated. Shrink the row to its content
           width and give each card one fixed flex basis instead. This shared selector
           applies to every managed uploader in Technical, Sales, Marketing, Admin,
           Knowledge Submission, Product Library, and the main chat composer. */
        html body div[class*="st-key-atp_preview_grid_"] {
            width: fit-content !important;
            max-width: 100% !important;
            margin: 0 auto 7px !important;
            padding: 0 !important;
        }

        html body div[class*="st-key-atp_preview_grid_"]
        div[data-testid="stHorizontalBlock"] {
            width: fit-content !important;
            max-width: 100% !important;
            margin: 0 auto !important;
            padding: 0 !important;
            display: flex !important;
            align-items: flex-start !important;
            justify-content: center !important;
            column-gap: 9px !important;
            row-gap: 10px !important;
            flex-wrap: nowrap !important;
        }

        html body div[class*="st-key-atp_preview_grid_"]
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
        html body div[class*="st-key-atp_preview_grid_"]
        div[data-testid="column"] {
            flex: 0 0 178px !important;
            flex-grow: 0 !important;
            flex-shrink: 0 !important;
            width: 178px !important;
            min-width: 178px !important;
            max-width: 178px !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        html body div[class*="st-key-atp_upload_card_"] {
            position: relative !important;
            isolation: isolate !important;
            width: 100% !important;
            max-width: 178px !important;
            margin: 0 auto !important;
            padding: 0 !important;
            border: 1px solid rgba(148, 163, 184, 0.20) !important;
            border-radius: 14px !important;
            background: rgba(15, 23, 42, 0.84) !important;
            overflow: visible !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18) !important;
        }

        html body div[class*="st-key-atp_upload_card_"]
        > div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .atp-gpt-upload-media {
            width: 100%;
            height: 108px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 13px 13px 0 0;
            background: #020617;
        }

        .atp-gpt-upload-media img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            background: #020617;
        }

        .atp-gpt-file-icon {
            width: 41px;
            height: 41px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 41px;
            line-height: 1;
        }

        .atp-gpt-file-icon img {
            display: block;
            width: 41px;
            height: 41px;
            object-fit: contain;
            background: transparent;
        }

        /* ZIP preview only: 30% larger than the standard 41 px document icon. */
        .atp-gpt-file-icon.atp-gpt-file-icon-zip {
            width: 53px;
            height: 53px;
        }

        .atp-gpt-file-icon.atp-gpt-file-icon-zip img {
            width: 53px;
            height: 53px;
            min-width: 53px;
            max-width: 53px;
            min-height: 53px;
            max-height: 53px;
        }

        .atp-gpt-upload-meta {
            padding: 7px 8px 8px;
            text-align: center;
            border-top: 1px solid rgba(148, 163, 184, 0.12);
        }

        .atp-gpt-upload-name {
            color: #f8fafc;
            font-size: 11px;
            font-weight: 700;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }

        .atp-gpt-upload-size {
            margin-top: 2px;
            color: #94a3b8;
            font-size: 10px;
        }

        html body div[class*="st-key-atp_delete_btn_"] {
            position: absolute !important;
            top: 6px !important;
            right: 6px !important;
            z-index: 999 !important;
            width: 27px !important;
            height: 27px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        html body div[class*="st-key-atp_delete_btn_"] .stButton,
        html body div[class*="st-key-atp_delete_btn_"] div[data-testid="stButton"] {
            width: 27px !important;
            height: 27px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        html body div[class*="st-key-atp_delete_btn_"] button {
            width: 27px !important;
            min-width: 27px !important;
            max-width: 27px !important;
            height: 27px !important;
            min-height: 27px !important;
            max-height: 27px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 50% !important;
            border: 1px solid rgba(15, 23, 42, 0.16) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            color: #475569 !important;
            -webkit-text-fill-color: #475569 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28) !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 17px !important;
            line-height: 1 !important;
            transform: none !important;
        }

        html body div[class*="st-key-atp_delete_btn_"] button:hover {
            background: #ffffff !important;
            color: #dc2626 !important;
            -webkit-text-fill-color: #dc2626 !important;
            transform: none !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] {
            position: relative !important;
            width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            border: 0 !important;
            background: transparent !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
            min-height: 82px !important;
            height: auto !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex-direction: column !important;
            gap: 7px !important;
            padding: 8px 12px !important;
            border: 1px dashed rgba(148, 163, 184, 0.25) !important;
            border-radius: 13px !important;
            background: rgba(15, 23, 42, 0.28) !important;
            box-sizing: border-box !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section > div,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div {
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex-direction: column !important;
            gap: 6px !important;
            margin: 0 !important;
            padding: 0 !important;
            text-align: center !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            width: auto !important;
            min-width: 126px !important;
            height: 44px !important;
            min-height: 44px !important;
            margin: 0 auto !important;
            padding: 0 18px !important;
            border-radius: 12px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
            transform: none !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button svg {
            width: 21px !important;
            height: 21px !important;
        }

        /* Native temporary rows are replaced by managed Python previews. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] ul,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"] {
            display: none !important;
        }

        /* Streamlit's native helper may reflect a lower framework limit even
           though this application validates files at 20 MB. Hide it and render
           one consistent Product Library limit label. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] small,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploaderDropzoneInstructions"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none !important;
        }

        /* Hide only instruction-only wrappers. Never collapse a wrapper that
           contains the native Upload button; doing so also hides the clickable
           control in newer Streamlit DOM structures. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section > div:not(:has(button)) p,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section > div:not(:has(button)) span,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]
        > div:not(:has(button)) p,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]
        > div:not(:has(button)) span {
            display: none !important;
        }

        /* Explicitly preserve the native Upload control and all of its children. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button *,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] * {
            display: inline-flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            font-size: 14px !important;
            line-height: 1.2 !important;
            overflow: visible !important;
        }

        /* Final upload-button dimensions and visual vertical alignment.
           The native dropzone reserves more visual space below the button for
           the custom 20 MB helper line. Move only the button down slightly so
           the open space above and below it appears balanced, without changing
           the uploader height, helper text, or clickable area. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            width: auto !important;
            min-width: 126px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 18px !important;
            border-radius: 12px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
            position: relative !important;
            top: 6px !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section::after,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
            content: "20MB per file • JPG, JPEG, PNG, WEBP, PDF, DOCX, XLS, XLSX, XLSM, XLSB, CSV, PPT, PPTX, ZIP";
            display: block;
            width: 100%;
            margin: 2px 0 0;
            color: #94a3b8;
            font-size: 11.5px;
            line-height: 1.3;
            text-align: center;
            pointer-events: none;
        }

        /* Lightweight upload-processing state. Keep Streamlit's native preview
           thumbnail/file icon and file metadata, but hide its temporary action
           buttons. The spinner and indeterminate line are CSS-only, so they do
           not trigger Python loops, network calls, or extra Streamlit reruns. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderDeleteBtn"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button[aria-label*="remove" i],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button[title*="remove" i],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button[aria-label*="add" i],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] button[title*="add" i] {
            display: none !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"] {
            display: flex !important;
            width: min(100%, 220px) !important;
            min-height: 142px !important;
            margin: 4px auto 0 !important;
            padding: 10px 12px 12px !important;
            border: 1px solid rgba(148, 163, 184, 0.20) !important;
            border-radius: 14px !important;
            background: rgba(15, 23, 42, 0.74) !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16) !important;
            align-items: center !important;
            justify-content: center !important;
            flex-direction: column !important;
            gap: 5px !important;
            overflow: hidden !important;
            position: relative !important;
            box-sizing: border-box !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] img,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"] img,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"] img {
            width: 76px !important;
            height: 62px !important;
            max-width: 76px !important;
            max-height: 62px !important;
            object-fit: contain !important;
            border-radius: 9px !important;
            background: #020617 !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFileData"] {
            display: flex !important;
            width: 100% !important;
            align-items: center !important;
            justify-content: center !important;
            flex-direction: column !important;
            gap: 1px !important;
            text-align: center !important;
            color: #f8fafc !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {
            display: block !important;
            max-width: 190px !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            font-size: 11.5px !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            text-align: center !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFileSize"] {
            display: block !important;
            color: #94a3b8 !important;
            -webkit-text-fill-color: #94a3b8 !important;
            font-size: 10px !important;
            line-height: 1.2 !important;
            text-align: center !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]::after,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"]::after,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"]::after {
            content: "Processing image…";
            display: block;
            width: 100%;
            margin-top: 4px;
            padding-top: 15px;
            color: #cbd5e1;
            font-size: 11px;
            font-weight: 650;
            line-height: 1.2;
            text-align: center;
            background:
                radial-gradient(circle at 50% 5px, transparent 4px, #cbd5e1 4.5px, #cbd5e1 5.5px, transparent 6px),
                linear-gradient(90deg, transparent 0%, rgba(148,163,184,.25) 20%, rgba(226,232,240,.95) 50%, rgba(148,163,184,.25) 80%, transparent 100%)
                center bottom / 84% 2px no-repeat;
            animation: atpProcessingPulse 1.15s ease-in-out infinite;
            pointer-events: none;
        }

        @keyframes atpProcessingPulse {
            0%, 100% { opacity: .55; }
            50% { opacity: 1; }
        }

        @media (max-width: 768px) {
            html body div[class*="st-key-atp_upload_shell_"] {
                padding: 11px !important;
                border-radius: 15px !important;
            }

            html body div[class*="st-key-atp_preview_grid_"] {
                width: fit-content !important;
                max-width: 100% !important;
            }

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="stHorizontalBlock"] {
                width: fit-content !important;
                max-width: 100% !important;
                column-gap: 8px !important;
                row-gap: 9px !important;
                flex-wrap: wrap !important;
            }

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="column"] {
                flex: 0 0 154px !important;
                width: 154px !important;
                min-width: 154px !important;
                max-width: 154px !important;
            }

            html body div[class*="st-key-atp_upload_card_"] {
                max-width: 154px !important;
            }

            .atp-gpt-upload-media {
                height: 96px;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] section,
            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
                min-height: 76px !important;
                padding: 8px 10px !important;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] button,
            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
                min-width: 116px !important;
                height: 42px !important;
                min-height: 42px !important;
                padding: 0 16px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def install_global_chat_file_dropzone():
    """
    Reliably forward files dropped anywhere over the main chat, or pasted
    images, into the existing Streamlit chat file uploader.

    The browser listeners are replaced on every Streamlit rerun, and the
    current chat uploader input is located dynamically inside its keyed
    container. No separate backend upload path is introduced.
    """
    components.html(
        """
        <script>
        (() => {
            const parentWindow = window.parent;
            const doc = parentWindow.document;
            const CONTROLLER_KEY = "__atpGlobalChatDropzoneV3";
            const CHAT_SHELL_SELECTOR =
                'div[class*="st-key-atp_upload_shell_chat_files"]';
            const ACCEPTED_EXTENSIONS = [
                ".jpg", ".jpeg", ".png", ".pdf", ".txt",
                ".doc", ".docx", ".xls", ".xlsx", ".xlsm", ".xlsb", ".csv",
                ".ppt", ".pptx", ".zip"
            ];

            // Streamlit reruns can destroy the component iframe while leaving
            // listeners on the parent document. Always remove the previous
            // listener set before installing the current one.
            try {
                parentWindow[CONTROLLER_KEY]?.cleanup?.();
            } catch (error) {
                console.warn(
                    "AutoTecPro AI: previous dropzone cleanup failed.",
                    error
                );
            }

            let disposed = false;
            let dragActive = false;
            let hideTimer = null;
            let uploadInProgress = false;
            const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

            function ensureOverlay() {
                let overlay = doc.getElementById("atp-global-drop-overlay");

                if (!overlay) {
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
                            <div style="font-size:42px;line-height:1;margin-bottom:12px;">
                                📎
                            </div>
                            <div style="font-size:22px;font-weight:800;margin-bottom:7px;">
                                Drop files to attach
                            </div>
                            <div style="font-size:14px;color:#cbd5e1;">
                                JPG, PNG, PDF, TXT, Word, Excel, CSV, PowerPoint, or ZIP
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
                }

                return overlay;
            }

            const overlay = ensureOverlay();

            function showOverlay() {
                if (disposed) return;
                dragActive = true;
                if (hideTimer) {
                    parentWindow.clearTimeout(hideTimer);
                    hideTimer = null;
                }
                overlay.style.display = "flex";
            }

            function hideOverlay() {
                dragActive = false;
                if (hideTimer) {
                    parentWindow.clearTimeout(hideTimer);
                    hideTimer = null;
                }
                overlay.style.display = "none";
            }

            function scheduleOverlayHide() {
                if (hideTimer) {
                    parentWindow.clearTimeout(hideTimer);
                }

                hideTimer = parentWindow.setTimeout(() => {
                    if (!dragActive) {
                        overlay.style.display = "none";
                    }
                }, 90);
            }

            function eventContainsFiles(event) {
                const transfer = event.dataTransfer;
                if (!transfer) return false;

                const types = Array.from(transfer.types || []);
                if (types.includes("Files")) return true;

                return Array.from(transfer.items || []).some(
                    (item) => item.kind === "file"
                );
            }

            function getCurrentChatFileInput() {
                const shells = Array.from(
                    doc.querySelectorAll(CHAT_SHELL_SELECTOR)
                ).filter((shell) => shell.isConnected);

                // During a Streamlit rerun, an old shell can briefly coexist
                // with the newly mounted one. Prefer the newest connected shell.
                for (let index = shells.length - 1; index >= 0; index -= 1) {
                    const inputs = Array.from(
                        shells[index].querySelectorAll('input[type="file"]')
                    ).filter(
                        (input) =>
                            input.isConnected &&
                            !input.disabled
                    );

                    if (inputs.length) {
                        return inputs[inputs.length - 1];
                    }
                }

                return null;
            }

            const MIME_BY_EXTENSION = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".pdf": "application/pdf",
                ".txt": "text/plain",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xls": "application/vnd.ms-excel",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
                ".xlsb": "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
                ".csv": "text/csv",
                ".ppt": "application/vnd.ms-powerpoint",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".zip": "application/zip"
            };

            function fileExtension(file) {
                const name = String(file?.name || "").toLowerCase();
                return ACCEPTED_EXTENSIONS.find(
                    (extension) => name.endsWith(extension)
                ) || "";
            }

            function acceptedFiles(fileList) {
                // Keep the original browser File objects. Reconstructing an XLSX
                // File can corrupt Chromium's upload handoff for larger workbooks.
                const supported = [];
                const oversized = [];

                for (const file of Array.from(fileList || [])) {
                    if (!fileExtension(file)) continue;
                    if (Number(file.size || 0) > MAX_UPLOAD_BYTES) {
                        oversized.push(file.name || "Unnamed file");
                        continue;
                    }
                    supported.push(file);
                }

                if (oversized.length) {
                    parentWindow.alert(
                        `These files exceed the 20 MB limit: ${oversized.join(", ")}`
                    );
                }

                return supported;
            }

            function setInputFiles(input, files) {
                if (!input || !input.isConnected || uploadInProgress) return false;

                const transfer = new parentWindow.DataTransfer();
                const seen = new Set();

                // The managed uploader stores completed files in session state and
                // remounts a fresh native input after each upload. Assign only the
                // newly dropped files here; preserving a stale input.files list can
                // submit the same large workbook twice and leave Streamlit's upload
                // endpoint waiting indefinitely.
                for (const file of files) {
                    const signature = [
                        file.name,
                        file.size,
                        file.lastModified,
                        file.type
                    ].join("|");

                    if (!seen.has(signature)) {
                        seen.add(signature);
                        transfer.items.add(file);
                    }
                }

                if (!transfer.files.length) return false;

                const filesSetter = Object.getOwnPropertyDescriptor(
                    parentWindow.HTMLInputElement.prototype,
                    "files"
                )?.set;

                uploadInProgress = true;
                input.dataset.atpProgrammaticUpload = "1";

                if (filesSetter) {
                    filesSetter.call(input, transfer.files);
                } else {
                    input.files = transfer.files;
                }

                // A file input's native semantic event is "change". Dispatching
                // both input and change can trigger duplicate upload requests in
                // some Streamlit/React combinations, especially for large XLSX files.
                input.dispatchEvent(
                    new parentWindow.Event("change", {
                        bubbles: true,
                        composed: true
                    })
                );

                // Streamlit normally reruns and replaces the input after completion.
                // Release the guard as a fallback if the component remains mounted.
                parentWindow.setTimeout(() => {
                    uploadInProgress = false;
                    try {
                        delete input.dataset.atpProgrammaticUpload;
                    } catch (_) {}
                }, 2500);

                return true;
            }

            function attachFilesWithRetry(fileList, attempt = 0) {
                if (disposed) return;

                const files = acceptedFiles(fileList);
                if (!files.length) return;

                const input = getCurrentChatFileInput();

                if (!input) {
                    // Streamlit may be between unmounting the old uploader and
                    // mounting the new generation. Retry briefly instead of
                    // silently failing and requiring a browser refresh.
                    if (attempt < 20) {
                        parentWindow.setTimeout(
                            () => attachFilesWithRetry(files, attempt + 1),
                            75
                        );
                    } else {
                        console.warn(
                            "AutoTecPro AI: chat uploader was not available after retries."
                        );
                    }
                    return;
                }

                try {
                    if (!setInputFiles(input, files) && attempt < 20) {
                        parentWindow.setTimeout(
                            () => attachFilesWithRetry(files, attempt + 1),
                            125
                        );
                    }
                } catch (error) {
                    // A stale input can disappear between lookup and assignment.
                    // Retry against the newest mounted input.
                    if (attempt < 20) {
                        parentWindow.setTimeout(
                            () => attachFilesWithRetry(files, attempt + 1),
                            75
                        );
                    } else {
                        console.error(
                            "AutoTecPro AI: could not attach dropped files.",
                            error
                        );
                    }
                }
            }

            function onDragEnter(event) {
                if (!eventContainsFiles(event)) return;
                event.preventDefault();
                showOverlay();
            }

            function onDragOver(event) {
                if (!eventContainsFiles(event)) return;
                event.preventDefault();
                event.stopPropagation();

                if (event.dataTransfer) {
                    event.dataTransfer.dropEffect = "copy";
                }

                showOverlay();
            }

            function onDragLeave(event) {
                if (!eventContainsFiles(event)) return;
                event.preventDefault();

                // Avoid an error-prone drag-depth counter. Hide only after a
                // short delay; another dragover immediately cancels the hide.
                dragActive = false;
                scheduleOverlayHide();
            }

            function onDrop(event) {
                if (!eventContainsFiles(event)) return;

                event.preventDefault();
                event.stopPropagation();
                hideOverlay();

                const files = Array.from(event.dataTransfer?.files || []);
                attachFilesWithRetry(files);
            }

            function onPaste(event) {
                const clipboardFiles = Array.from(
                    event.clipboardData?.files || []
                );
                if (!clipboardFiles.length) return;

                const imageFiles = clipboardFiles.filter((file) =>
                    String(file.type || "").toLowerCase().startsWith("image/")
                );
                if (!imageFiles.length) return;

                event.preventDefault();
                attachFilesWithRetry(imageFiles);
            }

            function onWindowBlur() {
                hideOverlay();
            }

            function cleanup() {
                if (disposed) return;
                disposed = true;

                doc.removeEventListener("dragenter", onDragEnter, true);
                doc.removeEventListener("dragover", onDragOver, true);
                doc.removeEventListener("dragleave", onDragLeave, true);
                doc.removeEventListener("drop", onDrop, true);
                doc.removeEventListener("paste", onPaste, true);
                parentWindow.removeEventListener("blur", onWindowBlur);

                if (hideTimer) {
                    parentWindow.clearTimeout(hideTimer);
                    hideTimer = null;
                }

                overlay.style.display = "none";
            }

            doc.addEventListener("dragenter", onDragEnter, true);
            doc.addEventListener("dragover", onDragOver, true);
            doc.addEventListener("dragleave", onDragLeave, true);
            doc.addEventListener("drop", onDrop, true);
            doc.addEventListener("paste", onPaste, true);
            parentWindow.addEventListener("blur", onWindowBlur);

            parentWindow[CONTROLLER_KEY] = { cleanup };

            // Cleanup when this particular component iframe is destroyed.
            window.addEventListener("beforeunload", cleanup, { once: true });
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def install_browser_voice_dictation():
    """Install rerun-safe voice and send controls without stacking observers."""
    components.html(
        r"""
        <script>
        (() => {
          const root = window.parent;
          const doc = root.document;
          const GLOBAL_KEY = "__atpVoiceControllerV3";
          const VOICE_ID = "atp-browser-voice-dictation";
          const SEND_ID = "atp-send-proxy";
          const INSTANCE = `${Date.now()}-${Math.random()}`;

          // Streamlit reruns recreate this iframe. Always tear down the previous
          // controller first so observers/timers do not accumulate after uploads.
          try {
            root[GLOBAL_KEY]?.cleanup?.();
          } catch (error) {}

          let observer = null;
          let timer = null;
          let recognition = null;
          let listening = false;
          let scheduled = false;

          const MIC_ICON = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Z"
                    fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M19 11a7 7 0 0 1-14 0M12 18v4M8 22h8"
                    fill="none" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>`;

          const LISTENING_ICON = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="5" fill="currentColor"/>
            </svg>`;

          const SEND_ICON = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 19V5M5 12l7-7 7 7"
                    fill="none" stroke="currentColor" stroke-width="2.2"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>`;

          function composer() {
            return doc.querySelector('div[data-testid="stChatInput"]');
          }

          function nativeSend(container) {
            if (!container) return null;
            const buttons = [...container.querySelectorAll("button")];
            return buttons.find(
              (button) =>
                button.id !== VOICE_ID &&
                button.id !== SEND_ID &&
                !button.classList.contains("atp-voice-trigger") &&
                !button.classList.contains("atp-send-proxy")
            ) || null;
          }

          function inputElement(container) {
            return container?.querySelector("textarea, input") || null;
          }

          function setReactValue(input, value) {
            if (!input) return;
            const prototype = Object.getPrototypeOf(input);
            const setter = Object.getOwnPropertyDescriptor(
              prototype,
              "value"
            )?.set;
            if (setter) setter.call(input, value);
            else input.value = value;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }

          function updateSendState(container, proxy) {
            const input = inputElement(container);
            const active = Boolean(input?.value?.trim());
            proxy.disabled = !active;
            proxy.setAttribute("aria-disabled", active ? "false" : "true");
          }

          function removeStaleControls(container) {
            for (const id of [VOICE_ID, SEND_ID]) {
              const node = doc.getElementById(id);
              if (node && (!container || !container.contains(node))) node.remove();
            }
          }

          function makeSend(container) {
            doc.getElementById(SEND_ID)?.remove();

            const proxy = doc.createElement("button");
            proxy.id = SEND_ID;
            proxy.type = "button";
            proxy.className = "atp-send-proxy";
            proxy.dataset.atpInstance = INSTANCE;
            proxy.innerHTML = SEND_ICON;
            proxy.setAttribute("title", "Send message");
            proxy.setAttribute("aria-label", "Send message");

            proxy.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();

              const current = composer();
              const realButton = nativeSend(current);
              const input = inputElement(current);

              if (!input?.value?.trim()) return;

              if (realButton && !realButton.disabled) {
                realButton.click();
                return;
              }

              input.focus();
              input.dispatchEvent(
                new KeyboardEvent("keydown", {
                  key: "Enter",
                  code: "Enter",
                  keyCode: 13,
                  which: 13,
                  bubbles: true
                })
              );
            });

            container.appendChild(proxy);

            const input = inputElement(container);
            if (input) {
              const sync = () => updateSendState(container, proxy);
              input.addEventListener("input", sync);
              input.addEventListener("change", sync);
              sync();
            }
            return proxy;
          }

          function resetVoice(button) {
            listening = false;
            button?.classList.remove("listening");
            if (button) {
              button.innerHTML = MIC_ICON;
              button.setAttribute("title", "Voice dictation");
              button.setAttribute("aria-label", "Start voice dictation");
            }
          }

          function makeVoice(container) {
            doc.getElementById(VOICE_ID)?.remove();

            const button = doc.createElement("button");
            button.id = VOICE_ID;
            button.type = "button";
            button.className = "atp-voice-trigger";
            button.dataset.atpInstance = INSTANCE;
            button.innerHTML = MIC_ICON;
            button.setAttribute("title", "Voice dictation");
            button.setAttribute("aria-label", "Start voice dictation");
            container.appendChild(button);

            const SpeechRecognition =
              root.SpeechRecognition || root.webkitSpeechRecognition;

            if (!SpeechRecognition) {
              button.classList.add("unsupported");
              button.addEventListener("click", () => {
                root.alert(
                  "Voice dictation is not supported by this browser. You can still type normally."
                );
              });
              return button;
            }

            button.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();

              const current = composer();
              const input = inputElement(current);
              if (!input) return;

              if (listening && recognition) {
                try { recognition.stop(); } catch (error) {}
                return;
              }

              try {
                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.maxAlternatives = 1;
                recognition.lang =
                  doc.documentElement.lang ||
                  root.navigator.language ||
                  "en-US";

                let committed = input.value?.trim() || "";

                recognition.onstart = () => {
                  listening = true;
                  button.classList.add("listening");
                  button.innerHTML = LISTENING_ICON;
                  button.setAttribute("title", "Listening — tap to stop");
                };

                recognition.onresult = (resultEvent) => {
                  let interim = "";
                  let finalText = "";

                  for (
                    let i = resultEvent.resultIndex;
                    i < resultEvent.results.length;
                    i += 1
                  ) {
                    const transcript = resultEvent.results[i][0].transcript;
                    if (resultEvent.results[i].isFinal) finalText += transcript;
                    else interim += transcript;
                  }

                  const prefix = committed ? committed + " " : "";
                  setReactValue(input, (prefix + finalText + interim).trimStart());

                  const proxy = doc.getElementById(SEND_ID);
                  if (proxy && current) updateSendState(current, proxy);

                  if (finalText) committed = (prefix + finalText).trim();
                };

                recognition.onerror = (event) => {
                  if (!["aborted", "no-speech"].includes(event.error)) {
                    console.warn("Voice dictation error:", event.error);
                  }
                };
                recognition.onend = () => resetVoice(button);
                recognition.start();
              } catch (error) {
                resetVoice(button);
                console.warn("Could not start voice dictation:", error);
              }
            });

            return button;
          }

          function mountNow() {
            scheduled = false;
            const current = composer();
            removeStaleControls(current);
            if (!current) return;

            const voice = doc.getElementById(VOICE_ID);
            if (
              !voice ||
              voice.dataset.atpInstance !== INSTANCE ||
              !current.contains(voice)
            ) {
              makeVoice(current);
            }

            const send = doc.getElementById(SEND_ID);
            if (
              !send ||
              send.dataset.atpInstance !== INSTANCE ||
              !current.contains(send)
            ) {
              makeSend(current);
            } else {
              updateSendState(current, send);
            }
          }

          function scheduleMount() {
            if (scheduled) return;
            scheduled = true;
            root.requestAnimationFrame(mountNow);
          }

          const observeRoot =
            doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;

          observer = new MutationObserver(scheduleMount);
          if (observeRoot) {
            observer.observe(observeRoot, {
              childList: true,
              subtree: true
            });
          }

          // A slow fallback is enough; the observer handles normal rerenders.
          timer = root.setInterval(scheduleMount, 1800);
          scheduleMount();

          function cleanup() {
            try { observer?.disconnect(); } catch (error) {}
            try { root.clearInterval(timer); } catch (error) {}
            try {
              if (recognition && listening) recognition.stop();
            } catch (error) {}

            for (const id of [VOICE_ID, SEND_ID]) {
              const node = doc.getElementById(id);
              if (node?.dataset?.atpInstance === INSTANCE) node.remove();
            }
          }

          root[GLOBAL_KEY] = { cleanup };
          window.addEventListener("beforeunload", cleanup, { once: true });
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def install_knowledge_submission_css():
    """
    Match the app's modern navigation language without red containers.

    Selectors are fully scoped to this workspace so other buttons, uploaders,
    Admin pages, chat, and login remain unchanged.
    """
    st.markdown(
        """
        <style>
        /* Clean page width and spacing. */
        div[class*="st-key-knowledge_submission_page"] {
            width: 100% !important;
            max-width: 980px !important;
            margin: 0 auto !important;
        }

        div[class*="st-key-knowledge_submission_page"]
        > div[data-testid="stVerticalBlock"] {
            gap: 13px !important;
        }

        /* Knowledge Type buttons use the same quiet navigation treatment. */
        div[class*="st-key-knowledge_type_"] {
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[class*="st-key-knowledge_type_"] .stButton,
        div[class*="st-key-knowledge_type_"] div[data-testid="stButton"] {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        div[class*="st-key-knowledge_type_"] .stButton > button {
            width: 100% !important;
            min-height: 48px !important;
            height: 48px !important;
            margin: 0 !important;
            padding: 0 14px !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 11px !important;
            background: rgba(255, 255, 255, 0.025) !important;
            background-color: rgba(255, 255, 255, 0.025) !important;
            color: #d7dee8 !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
            text-align: left !important;
            font-size: 14px !important;
            font-weight: 650 !important;
            transform: none !important;
        }

        div[class*="st-key-knowledge_type_"] .stButton > button:hover {
            border-color: rgba(148, 163, 184, 0.30) !important;
            background: rgba(255, 255, 255, 0.060) !important;
            background-color: rgba(255, 255, 255, 0.060) !important;
            color: #ffffff !important;
            transform: none !important;
        }

        div[class*="st-key-knowledge_type_active_"] .stButton > button {
            border-color: rgba(96, 165, 250, 0.34) !important;
            background: rgba(59, 130, 246, 0.16) !important;
            background-color: rgba(59, 130, 246, 0.16) !important;
            color: #ffffff !important;
            font-weight: 750 !important;
            box-shadow: inset 3px 0 0 rgba(96, 165, 250, 0.88) !important;
        }

        div[class*="st-key-knowledge_type_"]
        .stButton > button div[data-testid="stMarkdownContainer"],
        div[class*="st-key-knowledge_type_"]
        .stButton > button div[data-testid="stMarkdownContainer"] p {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            text-align: left !important;
            color: inherit !important;
            white-space: nowrap !important;
        }

        /* Remove the red treatment only from the Knowledge Submission uploader. */
        html body div[class*="st-key-atp_upload_shell_knowledge_submission_files"] {
            border: 1px dashed rgba(148, 163, 184, 0.34) !important;
            background: rgba(15, 23, 42, 0.24) !important;
            box-shadow: none !important;
        }

        html body div[class*="st-key-atp_upload_shell_knowledge_submission_files"]
        div[data-testid="stFileUploader"] section,
        html body div[class*="st-key-atp_upload_shell_knowledge_submission_files"]
        div[data-testid="stFileUploader"]
        [data-testid="stFileUploaderDropzone"] {
            border: 1px dashed rgba(148, 163, 184, 0.28) !important;
            background: rgba(15, 23, 42, 0.22) !important;
            box-shadow: none !important;
        }

        /* Knowledge Submission action: centered at 50% width.
           The state-specific container key controls grey/blue styling without
           reintroducing the stale disabled-button bug. */
        div[class*="st-key-knowledge_submit_button_"] {
            width: 50% !important;
            max-width: 50% !important;
            margin: 7px auto 0 auto !important;
        }

        div[class*="st-key-knowledge_submit_button_"] .stButton,
        div[class*="st-key-knowledge_submit_button_"] .stButton > button {
            width: 100% !important;
        }

        div[class*="st-key-knowledge_submit_button_"] .stButton > button {
            min-height: 48px !important;
            border-radius: 11px !important;
            transform: none !important;
        }

        div[class*="st-key-knowledge_submit_button_ready"]
        .stButton > button {
            border: 1px solid rgba(96, 165, 250, 0.42) !important;
            background: linear-gradient(
                135deg,
                rgba(37, 99, 235, 0.96),
                rgba(59, 130, 246, 0.88)
            ) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: 0 8px 22px rgba(37, 99, 235, 0.22) !important;
        }

        div[class*="st-key-knowledge_submit_button_ready"]
        .stButton > button:hover {
            border-color: rgba(147, 197, 253, 0.62) !important;
            background: linear-gradient(
                135deg,
                rgba(29, 78, 216, 0.98),
                rgba(37, 99, 235, 0.94)
            ) !important;
        }

        div[class*="st-key-knowledge_submit_button_waiting"]
        .stButton > button,
        div[class*="st-key-knowledge_submit_button_waiting"]
        .stButton > button:hover {
            background: rgba(71, 85, 105, 0.58) !important;
            border: 1px solid rgba(148, 163, 184, 0.24) !important;
            color: rgba(226, 232, 240, 0.70) !important;
            -webkit-text-fill-color: rgba(226, 232, 240, 0.70) !important;
            box-shadow: none !important;
        }

        @media (max-width: 640px) {
            div[class*="st-key-knowledge_submit_button_"] {
                width: 100% !important;
                max-width: 100% !important;
            }
        }

        /* Structured Knowledge Submission fields only. */
        div[class*="st-key-knowledge_structured_fields"]
        > div[data-testid="stVerticalBlock"] {
            gap: 18px !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        div[data-testid="stTextInput"],
        div[class*="st-key-knowledge_structured_fields"]
        div[data-testid="stTextArea"] {
            margin-top: 2px !important;
            margin-bottom: 0 !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        label[data-testid="stWidgetLabel"] {
            display: block !important;
            margin: 0 0 8px 0 !important;
            padding: 0 !important;
            line-height: 1.35 !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        label[data-testid="stWidgetLabel"] p {
            margin: 0 !important;
            padding: 0 !important;
            font-weight: 700 !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        input,
        div[class*="st-key-knowledge_structured_fields"]
        textarea {
            width: 100% !important;
            border-radius: 11px !important;
            box-sizing: border-box !important;
        }

        /* Knowledge Submission textareas: one clean focus border only.
           The BaseWeb wrapper owns the border; the inner textarea stays
           borderless so the global textarea focus rule cannot create a
           second overlapping orange outline. */
        div[class*="st-key-knowledge_structured_fields"]
        div[data-baseweb="textarea"] {
            border: 1px solid #334155 !important;
            border-radius: 11px !important;
            box-shadow: none !important;
            outline: none !important;
            overflow: hidden !important;
            background-color: rgba(15, 23, 42, 0.96) !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        div[data-baseweb="textarea"]:focus-within {
            border-color: var(--atp-red) !important;
            box-shadow: none !important;
            outline: none !important;
        }

        div[class*="st-key-knowledge_structured_fields"]
        textarea,
        div[class*="st-key-knowledge_structured_fields"]
        textarea:focus,
        div[class*="st-key-knowledge_structured_fields"]
        textarea:focus-visible {
            min-height: 138px !important;
            max-height: 520px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            resize: vertical !important;
            border: none !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            outline: none !important;
            background-color: transparent !important;
        }

        /* Small visible diagonal resize grip in the bottom-right corner.
           Chromium/Safari render this pseudo-element while preserving the
           textarea's native vertical resize behavior and scrollbar. */
        div[class*="st-key-knowledge_structured_fields"]
        textarea::-webkit-resizer {
            background-color: transparent !important;
            background-image:
                linear-gradient(135deg, transparent 0 56%, #94a3b8 57% 64%, transparent 65%),
                linear-gradient(135deg, transparent 0 70%, #94a3b8 71% 78%, transparent 79%) !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-size: 12px 12px !important;
        }

        .knowledge-status-card {
            margin-top: 12px;
            padding: 14px 16px;
            border: 1px solid rgba(52, 211, 153, 0.28);
            border-radius: 13px;
            background: rgba(16, 185, 129, 0.09);
        }

        .knowledge-status-title {
            color: #d1fae5;
            font-size: 15px;
            font-weight: 780;
            margin-bottom: 8px;
        }

        .knowledge-status-row {
            color: #cbd5e1;
            font-size: 13px;
            line-height: 1.55;
            margin: 2px 0;
        }

        .knowledge-status-row strong {
            color: #f8fafc;
        }

        @media (max-width: 760px) {
            div[class*="st-key-knowledge_submission_page"] {
                max-width: 100% !important;
            }

            div[class*="st-key-knowledge_type_"] .stButton > button {
                min-height: 46px !important;
                height: 46px !important;
                font-size: 13px !important;
                padding: 0 11px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def install_chat_composer_autogrow():
    """
    Keep the editable text area exactly between the microphone and send icons.

    This controller also neutralizes older grid/flex rules that may remain in
    the page stylesheet, without changing the uploader, chat history, or any
    business logic.
    """
    components.html(
        r"""
        <script>
        (() => {
          const root = window.parent;
          const doc = root.document;
          const GLOBAL_KEY = "__atpComposerBetweenIconsV6";
          const MIN_HEIGHT = 44;
          const MAX_HEIGHT = 180;

          try { root[GLOBAL_KEY]?.cleanup?.(); } catch (error) {}

          let observer = null;
          let timer = null;
          let scheduled = false;
          let boundTextarea = null;
          let currentOwner = null;
          let inputHandler = null;
          let pasteHandler = null;
          let resizeHandler = null;

          function important(element, property, value) {
            if (element) {
              element.style.setProperty(property, value, "important");
            }
          }

          function getComposer() {
            return doc.querySelector('div[data-testid="stChatInput"]');
          }

          function getDirectOwner(textarea, container) {
            let node = textarea;
            while (node.parentElement && node.parentElement !== container) {
              node = node.parentElement;
            }
            return node;
          }

          function normalizeElement(element, displayValue = "block") {
            if (!element) return;

            important(element, "position", "static");
            important(element, "left", "auto");
            important(element, "right", "auto");
            important(element, "top", "auto");
            important(element, "bottom", "auto");
            important(element, "transform", "none");

            important(element, "display", displayValue);
            important(element, "grid-column", "auto");
            important(element, "grid-row", "auto");
            important(element, "grid-template-columns", "none");
            important(element, "grid-template-rows", "none");

            important(element, "flex", "1 1 auto");
            important(element, "flex-basis", "auto");
            important(element, "align-self", "stretch");
            important(element, "justify-self", "stretch");

            important(element, "width", "100%");
            important(element, "min-width", "0");
            important(element, "max-width", "none");
            important(element, "height", "auto");
            important(element, "min-height", "0");
            important(element, "max-height", "none");

            important(element, "margin", "0");
            important(element, "padding", "0");
            important(element, "box-sizing", "border-box");
            important(element, "overflow", "visible");
          }

          function normalizeInnerTree(textarea, owner) {
            let node = textarea.parentElement;
            while (node && node !== owner) {
              normalizeElement(node, "block");
              node = node.parentElement;
            }
          }

          function positionOwner(owner, left, right) {
            important(owner, "position", "absolute");
            important(owner, "left", `${left}px`);
            important(owner, "right", `${right}px`);
            important(owner, "top", "8px");
            important(owner, "bottom", "8px");
            important(owner, "transform", "none");

            important(owner, "display", "block");
            important(owner, "grid-column", "auto");
            important(owner, "grid-row", "auto");
            important(owner, "flex", "none");
            important(owner, "align-self", "auto");
            important(owner, "justify-self", "auto");

            important(owner, "width", "auto");
            important(owner, "min-width", "0");
            important(owner, "max-width", "none");
            important(owner, "height", "auto");
            important(owner, "min-height", "0");
            important(owner, "max-height", "none");

            important(owner, "margin", "0");
            important(owner, "padding", "0");
            important(owner, "box-sizing", "border-box");
            important(owner, "overflow", "visible");
          }

          function fixLayout() {
            scheduled = false;

            const container = getComposer();
            const textarea = container?.querySelector("textarea");
            const mic = doc.getElementById("atp-browser-voice-dictation");
            const send = doc.getElementById("atp-send-proxy");

            if (!container || !textarea || !mic || !send) return;

            const containerRect = container.getBoundingClientRect();
            const micRect = mic.getBoundingClientRect();
            const sendRect = send.getBoundingClientRect();

            if (
              containerRect.width <= 0 ||
              micRect.width <= 0 ||
              sendRect.width <= 0
            ) return;

            const owner = getDirectOwner(textarea, container);
            if (!owner) return;
            currentOwner = owner;

            const left = Math.max(
              0,
              Math.ceil(micRect.right - containerRect.left + 12)
            );
            const right = Math.max(
              0,
              Math.ceil(containerRect.right - sendRect.left + 12)
            );

            important(container, "position", "relative");
            important(container, "display", "block");
            important(container, "grid-template-columns", "none");
            important(container, "width", "calc(100% - 4px)");
            important(container, "min-width", "0");
            important(container, "box-sizing", "border-box");
            important(container, "padding-left", "0");
            important(container, "padding-right", "0");
            important(container, "overflow", "hidden");

            positionOwner(owner, left, right);
            normalizeInnerTree(textarea, owner);

            important(textarea, "position", "static");
            important(textarea, "display", "block");
            important(textarea, "grid-column", "auto");
            important(textarea, "grid-row", "auto");
            important(textarea, "flex", "1 1 auto");

            important(textarea, "width", "100%");
            important(textarea, "min-width", "0");
            important(textarea, "max-width", "none");
            important(textarea, "box-sizing", "border-box");

            important(textarea, "padding", "11px 4px");
            important(textarea, "margin", "0");
            important(textarea, "white-space", "pre-wrap");
            important(textarea, "overflow-wrap", "break-word");
            important(textarea, "word-break", "normal");
            important(textarea, "writing-mode", "horizontal-tb");
            important(textarea, "text-orientation", "mixed");
            important(textarea, "line-height", "22px");

            important(textarea, "height", "auto");
            important(textarea, "min-height", `${MIN_HEIGHT}px`);
            important(textarea, "max-height", `${MAX_HEIGHT}px`);

            const targetHeight = Math.min(
              Math.max(textarea.scrollHeight, MIN_HEIGHT),
              MAX_HEIGHT
            );

            important(textarea, "height", `${targetHeight}px`);
            important(
              textarea,
              "overflow-y",
              textarea.scrollHeight > MAX_HEIGHT ? "auto" : "hidden"
            );

            const composerHeight = Math.max(64, targetHeight + 16);
            important(container, "height", `${composerHeight}px`);
            important(container, "min-height", "64px");
            important(container, "max-height", "196px");
          }

          function scheduleFix() {
            if (scheduled) return;
            scheduled = true;
            root.requestAnimationFrame(fixLayout);
          }

          function unbind() {
            if (!boundTextarea) return;
            try {
              boundTextarea.removeEventListener("input", inputHandler);
              boundTextarea.removeEventListener("change", inputHandler);
              boundTextarea.removeEventListener("keyup", inputHandler);
              boundTextarea.removeEventListener("paste", pasteHandler);
            } catch (error) {}
            boundTextarea = null;
            currentOwner = null;
          }

          function bind() {
            const textarea =
              doc.querySelector('div[data-testid="stChatInput"] textarea');

            if (!textarea) return;

            if (boundTextarea !== textarea) {
              unbind();
              boundTextarea = textarea;

              inputHandler = scheduleFix;
              pasteHandler = () => {
                root.setTimeout(scheduleFix, 0);
                root.setTimeout(scheduleFix, 70);
                root.setTimeout(scheduleFix, 180);
              };

              textarea.addEventListener("input", inputHandler);
              textarea.addEventListener("change", inputHandler);
              textarea.addEventListener("keyup", inputHandler);
              textarea.addEventListener("paste", pasteHandler);
            }

            scheduleFix();
          }

          resizeHandler = scheduleFix;
          root.addEventListener("resize", resizeHandler);

          const observeRoot =
            doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;

          observer = new MutationObserver(bind);
          if (observeRoot) {
            observer.observe(observeRoot, {
              childList: true,
              subtree: true
            });
          }

          timer = root.setInterval(bind, 1200);
          bind();

          function cleanup() {
            try { observer?.disconnect(); } catch (error) {}
            try { root.clearInterval(timer); } catch (error) {}
            try {
              root.removeEventListener("resize", resizeHandler);
            } catch (error) {}
            unbind();
          }

          root[GLOBAL_KEY] = { cleanup };
          window.addEventListener("beforeunload", cleanup, { once: true });
        })();
        </script>
        """,
        height=0,
        width=0,
    )




def apply_graphic_designer_mobile_css():
    """Keep Advanced Image Designer controls readable on mobile dark mode."""
    st.markdown(
        """
        <style>
        @media screen and (max-width: 1600px) {
            input[aria-label="Graphic Marketing mode"],
            input[aria-label="Graphic Marketing mode"][value],
            input[aria-label="Design category"],
            input[aria-label="Design category"][value],
            input[aria-label="Design type"],
            input[aria-label="Design type"][value],
            input[aria-label="Design style"],
            input[aria-label="Design style"][value],
            input[aria-label="Background"],
            input[aria-label="Background"][value],
            input[aria-label="Color theme"],
            input[aria-label="Color theme"][value],
            input[aria-label="Marketing goal"],
            input[aria-label="Marketing goal"][value],
            input[aria-label="Output format"],
            input[aria-label="Output format"][value] {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                caret-color: #ffffff !important;
                opacity: 1 !important;
            }

            /*
             * Mobile Safari applies a separate text-fill color after an input
             * becomes populated or focused. Target every real control state
             * directly, using the same aria-label method that fixed the earlier
             * Marketing Mode issue.
             */
            input[aria-label="Product / model"],
            input[aria-label="Product / model"]:focus,
            input[aria-label="Product / model"]:active,
            input[aria-label="Product / model"][value],
            input[aria-label="Vehicle / compatibility"],
            input[aria-label="Vehicle / compatibility"]:focus,
            input[aria-label="Vehicle / compatibility"]:active,
            input[aria-label="Vehicle / compatibility"][value],
            input[aria-label="Target audience"],
            input[aria-label="Target audience"]:focus,
            input[aria-label="Target audience"]:active,
            input[aria-label="Target audience"][value],
            input[aria-label="Headline"],
            input[aria-label="Headline"]:focus,
            input[aria-label="Headline"]:active,
            input[aria-label="Headline"][value],
            input[aria-label="Call to action"],
            input[aria-label="Call to action"]:focus,
            input[aria-label="Call to action"]:active,
            input[aria-label="Call to action"][value],
            input[aria-label="Website or contact information"],
            input[aria-label="Website or contact information"]:focus,
            input[aria-label="Website or contact information"]:active,
            input[aria-label="Website or contact information"][value],
            textarea[aria-label="Describe your custom design"],
            textarea[aria-label="Describe your custom design"]:focus,
            textarea[aria-label="Describe your custom design"]:active,
            textarea[aria-label="Additional instructions"],
            textarea[aria-label="Additional instructions"]:focus,
            textarea[aria-label="Additional instructions"]:active {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            /*
             * Narrow fallback for Streamlit/BaseWeb builds that move the
             * visible value to an inner input node while retaining the form.
             * This is scoped only to the Advanced AI Image Designer form.
             */
            form[data-testid="stForm"] input[type="text"],
            form[data-testid="stForm"] input[type="text"]:focus,
            form[data-testid="stForm"] input[type="text"]:active,
            form[data-testid="stForm"] textarea,
            form[data-testid="stForm"] textarea:focus,
            form[data-testid="stForm"] textarea:active {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            input[aria-label="Product / model"]::placeholder,
            input[aria-label="Vehicle / compatibility"]::placeholder,
            input[aria-label="Target audience"]::placeholder,
            input[aria-label="Headline"]::placeholder,
            input[aria-label="Call to action"]::placeholder,
            input[aria-label="Website or contact information"]::placeholder,
            textarea[aria-label="Describe your custom design"]::placeholder,
            textarea[aria-label="Additional instructions"]::placeholder,
            form[data-testid="stForm"] input[type="text"]::placeholder,
            form[data-testid="stForm"] textarea::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /*
             * Advanced Image Designer: one clean focus outline only.
             *
             * The global app stylesheet styles the inner input/textarea on
             * focus, while Streamlit/BaseWeb also styles its outer wrapper.
             * That creates two nested red/orange rectangles. Keep the outer
             * BaseWeb wrapper as the single border owner and remove border,
             * outline, and shadow from the actual editable control.
             */
            input[aria-label="Product / model"],
            input[aria-label="Product / model"]:focus,
            input[aria-label="Product / model"]:focus-visible,
            input[aria-label="Product / model"]:active,
            input[aria-label="Vehicle / compatibility"],
            input[aria-label="Vehicle / compatibility"]:focus,
            input[aria-label="Vehicle / compatibility"]:focus-visible,
            input[aria-label="Vehicle / compatibility"]:active,
            input[aria-label="Target audience"],
            input[aria-label="Target audience"]:focus,
            input[aria-label="Target audience"]:focus-visible,
            input[aria-label="Target audience"]:active,
            input[aria-label="Headline"],
            input[aria-label="Headline"]:focus,
            input[aria-label="Headline"]:focus-visible,
            input[aria-label="Headline"]:active,
            input[aria-label="Call to action"],
            input[aria-label="Call to action"]:focus,
            input[aria-label="Call to action"]:focus-visible,
            input[aria-label="Call to action"]:active,
            input[aria-label="Website or contact information"],
            input[aria-label="Website or contact information"]:focus,
            input[aria-label="Website or contact information"]:focus-visible,
            input[aria-label="Website or contact information"]:active,
            textarea[aria-label="Describe your custom design"],
            textarea[aria-label="Describe your custom design"]:focus,
            textarea[aria-label="Describe your custom design"]:focus-visible,
            textarea[aria-label="Describe your custom design"]:active,
            textarea[aria-label="Additional instructions"],
            textarea[aria-label="Additional instructions"]:focus,
            textarea[aria-label="Additional instructions"]:focus-visible,
            textarea[aria-label="Additional instructions"]:active {
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
            }

            div[data-baseweb="input"]:has(
                input[aria-label="Product / model"]
            ),
            div[data-baseweb="input"]:has(
                input[aria-label="Vehicle / compatibility"]
            ),
            div[data-baseweb="input"]:has(
                input[aria-label="Target audience"]
            ),
            div[data-baseweb="input"]:has(
                input[aria-label="Headline"]
            ),
            div[data-baseweb="input"]:has(
                input[aria-label="Call to action"]
            ),
            div[data-baseweb="input"]:has(
                input[aria-label="Website or contact information"]
            ),
            div[data-baseweb="textarea"]:has(
                textarea[aria-label="Describe your custom design"]
            ),
            div[data-baseweb="textarea"]:has(
                textarea[aria-label="Additional instructions"]
            ) {
                border: 1px solid #334155 !important;
                outline: none !important;
                box-shadow: none !important;
                overflow: hidden !important;
            }

            div[data-baseweb="input"]:has(
                input[aria-label="Product / model"]
            ):focus-within,
            div[data-baseweb="input"]:has(
                input[aria-label="Vehicle / compatibility"]
            ):focus-within,
            div[data-baseweb="input"]:has(
                input[aria-label="Target audience"]
            ):focus-within,
            div[data-baseweb="input"]:has(
                input[aria-label="Headline"]
            ):focus-within,
            div[data-baseweb="input"]:has(
                input[aria-label="Call to action"]
            ):focus-within,
            div[data-baseweb="input"]:has(
                input[aria-label="Website or contact information"]
            ):focus-within,
            div[data-baseweb="textarea"]:has(
                textarea[aria-label="Describe your custom design"]
            ):focus-within,
            div[data-baseweb="textarea"]:has(
                textarea[aria-label="Additional instructions"]
            ):focus-within {
                border-color: var(--atp-red) !important;
                outline: none !important;
                box-shadow: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_marketing_tools_form_css():
    """Keep Marketing tool form text readable on narrow mobile screens."""
    st.markdown(
        """
        <style>
        /*
         * Mobile-only Marketing form compatibility fix.
         *
         * This stylesheet is injected only while the Marketing workspace is
         * rendered. Desktop styling and every non-Marketing workspace remain
         * unchanged.
         */
        @media screen and (max-width: 1600px) {
            /*
             * Exact mobile/tablet fix for the closed Marketing Mode value.
             * On the deployed Safari build, BaseWeb renders the visible selected
             * value through the labelled input itself. Target that stable
             * accessibility attribute directly instead of depending on wrapper
             * classes or nesting.
             */
            input[aria-label="Marketing mode"],
            input[aria-label="Marketing mode"]:focus,
            input[aria-label="Marketing mode"]:active,
            input[aria-label="Marketing mode"][value] {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                caret-color: #ffffff !important;
                opacity: 1 !important;
            }

            /*
             * Exact accessibility-attribute protection for the new Competitor
             * Analysis controls on mobile Safari. This follows the same method
             * that fixed the Marketing Mode selected-value issue.
             */
            input[aria-label="Competitor company"],
            input[aria-label="Target market / region"],
            input[aria-label="Competitor product / model"],
            input[aria-label="Competitor public product URL (optional)"],
            input[aria-label="AutoTecPro product / model"],
            textarea[aria-label="Competitor specifications or page content (optional)"],
            textarea[aria-label="Additional instructions (optional)"] {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            input[aria-label="Competitor company"]::placeholder,
            input[aria-label="Competitor product / model"]::placeholder,
            input[aria-label="Competitor public product URL (optional)"]::placeholder,
            input[aria-label="AutoTecPro product / model"]::placeholder,
            textarea[aria-label="Competitor specifications or page content (optional)"]::placeholder,
            textarea[aria-label="Additional instructions (optional)"]::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /*
             * Marketing mode selector outside the form, plus every selectbox
             * and multiselect inside the currently rendered Marketing form.
             * BaseWeb uses different nested nodes for the closed value on iOS
             * Safari, so cover the combobox, value container and descendants.
             */
            /*
             * Scope the closed Marketing Mode value through a dedicated keyed
             * container. This avoids relying on generated selectbox key classes,
             * which are not consistently exposed by mobile Safari/Streamlit.
             */
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"],
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"]
            [data-baseweb="select"] [role="combobox"],
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"] span,
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"] p,
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"]
            [data-baseweb="select"] *:not(svg):not(path),
            div[data-testid="stForm"] [data-baseweb="select"],
            div[data-testid="stForm"] [data-baseweb="select"] > div,
            div[data-testid="stForm"]
            [data-baseweb="select"] [role="combobox"],
            div[data-testid="stForm"] [data-baseweb="select"] span {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                opacity: 1 !important;
            }

            /*
             * Closed select values may be drawn through an input or a nested
             * div rather than a span, depending on the Streamlit/BaseWeb build.
             */
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"] input,
            div[class*="st-key-marketing_mode_control"]
            div[data-testid="stSelectbox"] [data-baseweb="select"] div,
            div[data-testid="stForm"] [data-baseweb="select"] input,
            div[data-testid="stForm"] [data-baseweb="select"] div {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            /* Typed values in Marketing text inputs and text areas. */
            div[data-testid="stForm"] [data-testid="stTextInput"] input,
            div[data-testid="stForm"]
            div[data-testid="stTextInputRootElement"] input,
            div[data-testid="stForm"] [data-testid="stTextArea"] textarea,
            div[data-testid="stForm"] input[type="text"],
            div[data-testid="stForm"] input[type="url"],
            div[data-testid="stForm"] textarea {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
            }

            /* Keep placeholder text readable but distinct from entered text. */
            div[data-testid="stForm"] [data-testid="stTextInput"] input::placeholder,
            div[data-testid="stForm"]
            div[data-testid="stTextInputRootElement"] input::placeholder,
            div[data-testid="stForm"]
            [data-testid="stTextArea"] textarea::placeholder,
            div[data-testid="stForm"] input[type="text"]::placeholder,
            div[data-testid="stForm"] input[type="url"]::placeholder,
            div[data-testid="stForm"] textarea::placeholder {
                color: #94a3b8 !important;
                -webkit-text-fill-color: #94a3b8 !important;
                opacity: 1 !important;
            }

            /*
             * Safari autofill and disabled/read-only states can otherwise
             * restore a black text fill after a rerun or field selection.
             */
            div[data-testid="stForm"] input:-webkit-autofill,
            div[data-testid="stForm"] input:-webkit-autofill:hover,
            div[data-testid="stForm"] input:-webkit-autofill:focus,
            div[data-testid="stForm"] input:disabled,
            div[data-testid="stForm"] textarea:disabled {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f87171 !important;
                opacity: 1 !important;
                transition: background-color 9999s ease-out 0s !important;
            }

            /*
             * Shared Marketing form focus styling.
             *
             * Streamlit/BaseWeb draws the outer input/textarea wrapper border.
             * The global app stylesheet can also draw a border or glow on the
             * editable element itself, producing two nested red rectangles on
             * mobile Safari. Keep the BaseWeb wrapper as the only border owner.
             */
            div[data-testid="stForm"] [data-baseweb="input"],
            div[data-testid="stForm"] [data-baseweb="textarea"] {
                border: 1px solid #334155 !important;
                border-radius: 11px !important;
                outline: none !important;
                box-shadow: none !important;
                overflow: hidden !important;
            }

            div[data-testid="stForm"] [data-baseweb="input"]:focus-within,
            div[data-testid="stForm"] [data-baseweb="textarea"]:focus-within {
                border-color: var(--atp-red) !important;
                outline: none !important;
                box-shadow: none !important;
            }

            div[data-testid="stForm"] [data-baseweb="input"] input,
            div[data-testid="stForm"] [data-baseweb="input"] input:focus,
            div[data-testid="stForm"] [data-baseweb="input"] input:focus-visible,
            div[data-testid="stForm"] [data-baseweb="input"] input:active,
            div[data-testid="stForm"] [data-baseweb="textarea"] textarea,
            div[data-testid="stForm"] [data-baseweb="textarea"] textarea:focus,
            div[data-testid="stForm"] [data-baseweb="textarea"] textarea:focus-visible,
            div[data-testid="stForm"] [data-baseweb="textarea"] textarea:active {
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
                background-color: transparent !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
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

        /* Login page only: solid, high-contrast button with no fade */
        .stFormSubmitButton > button {
            background: #ff3b30 !important;
            background-color: #ff3b30 !important;
            background-image: none !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            filter: none !important;
            border: 1px solid #ff5a50 !important;
            box-shadow: 0 8px 20px rgba(255, 59, 48, 0.28) !important;
        }

        .stFormSubmitButton > button:hover,
        .stFormSubmitButton > button:focus,
        .stFormSubmitButton > button:active {
            background: #ff3b30 !important;
            background-color: #ff3b30 !important;
            background-image: none !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            filter: none !important;
            border-color: #ff6b63 !important;
            box-shadow: 0 9px 22px rgba(255, 59, 48, 0.34) !important;
            transform: none !important;
        }

        .stFormSubmitButton > button *,
        .stFormSubmitButton > button p,
        .stFormSubmitButton > button span {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
        }

        /* Login inputs: high contrast on iPhone/Safari and desktop */
        div[data-testid="stForm"] .stTextInput label,
        div[data-testid="stForm"] .stTextInput label p {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] .stTextInput input {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ff4b43 !important;
            opacity: 1 !important;
            font-weight: 500 !important;
        }

        div[data-testid="stForm"] .stTextInput input::placeholder {
            color: #aeb7c6 !important;
            -webkit-text-fill-color: #aeb7c6 !important;
            opacity: 1 !important;
        }

        /* Prevent iOS/Safari autofill from fading the username/password text */
        div[data-testid="stForm"] .stTextInput input:-webkit-autofill,
        div[data-testid="stForm"] .stTextInput input:-webkit-autofill:hover,
        div[data-testid="stForm"] .stTextInput input:-webkit-autofill:focus,
        div[data-testid="stForm"] .stTextInput input:-webkit-autofill:active {
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ff4b43 !important;
            -webkit-box-shadow: 0 0 0 1000px #0f172a inset !important;
            box-shadow: 0 0 0 1000px #0f172a inset !important;
            transition: background-color 9999s ease-out 0s !important;
            opacity: 1 !important;
        }

        /* Streamlit's mobile form hint was too dark on the login screen */
        div[data-testid="stForm"] [data-testid="InputInstructions"],
        div[data-testid="stForm"] [data-testid="stInputInstructions"],
        div[data-testid="stForm"] small {
            color: #cbd5e1 !important;
            -webkit-text-fill-color: #cbd5e1 !important;
            opacity: 1 !important;
        }

        @media (max-width: 700px) {
            div[data-testid="stForm"] .stTextInput input {
                font-size: 17px !important;
            }

            div[data-testid="stForm"] [data-testid="InputInstructions"],
            div[data-testid="stForm"] [data-testid="stInputInstructions"] {
                font-size: 12px !important;
                color: #d5dbe5 !important;
                -webkit-text-fill-color: #d5dbe5 !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def install_login_autofill_support():
    """
    Disable competing browser autofill behavior.

    The login fields are prefilled by Python from the saved cookie, so no
    browser-side redirect, auto-login, st.stop(), or checkbox manipulation is
    needed.
    """
    components.html(
        """
        <script>
        (() => {
          const root = window.parent;
          const doc = root.document;
          const KEY = "__atpManualCredentialLoginV1";

          try { root[KEY]?.cleanup?.(); } catch (error) {}

          let stopped = false;
          let timerId = null;
          let attempts = 0;

          function configure() {
            if (stopped) return;

            const forms = Array.from(
              doc.querySelectorAll(
                'form[data-testid="stForm"], div[data-testid="stForm"]'
              )
            );

            for (const form of forms) {
              const inputs = Array.from(form.querySelectorAll("input"));
              const usernameInput = inputs.find(
                (input) => input.type === "text"
              );
              const passwordInput = inputs.find(
                (input) => input.type === "password"
              );

              if (usernameInput && passwordInput) {
                form.setAttribute("autocomplete", "off");
                usernameInput.setAttribute("autocomplete", "off");
                usernameInput.setAttribute("autocapitalize", "none");
                usernameInput.setAttribute("spellcheck", "false");
                passwordInput.setAttribute(
                  "autocomplete",
                  "new-password"
                );
                return;
              }
            }

            attempts += 1;
            if (attempts < 50) {
              timerId = root.setTimeout(configure, 100);
            }
          }

          configure();

          function cleanup() {
            stopped = true;
            if (timerId) {
              try { root.clearTimeout(timerId); } catch (error) {}
            }
          }

          root[KEY] = { cleanup };
          window.addEventListener(
            "beforeunload",
            cleanup,
            { once: true }
          );
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def install_composer_width_safety_css():
    """
    Final inner-element safety rules.

    These rules do not position the textarea owner; JavaScript places that
    owner precisely between the microphone and send controls.
    """
    st.markdown(
        """
        <style>
        html body div[data-testid="stChatInput"] [data-baseweb="textarea"],
        html body div[data-testid="stChatInput"] [data-baseweb="base-input"] {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            box-sizing: border-box !important;
        }

        html body div[data-testid="stChatInput"] textarea {
            display: block !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            box-sizing: border-box !important;
            writing-mode: horizontal-tb !important;
            text-orientation: mixed !important;
            white-space: pre-wrap !important;
            overflow-wrap: break-word !important;
            word-break: normal !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
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
