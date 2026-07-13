import streamlit as st
import streamlit.components.v1 as components
from streamlit_cookies_controller import CookieController
from openai import OpenAI
from pathlib import Path
try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
import base64
import html
import hashlib
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import tempfile
import os
import re
import json
import time
import io
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from difflib import SequenceMatcher
from config import supabase
try:
    from supabase import create_client as create_supabase_client
except Exception:
    create_supabase_client = None

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


# Hide zero-height custom-component containers before the cookie controller
# mounts. This prevents the temporary grey bars/empty overlay blocks that can
# appear above the login logo while cookies are loading.
st.markdown(
    """
    <style>
    .element-container:has(iframe[height="0"]),
    div[data-testid="stElementContainer"]:has(iframe[height="0"]),
    div[data-testid="stCustomComponentV1"]:has(iframe[height="0"]) {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# One browser-cookie controller for saved login credentials.
auth_cookie_controller = CookieController(
    key="atp_auth_cookie_controller"
)


# ============================================================
# Optional Live Integrations
# ============================================================

def get_optional_secret(name, default=""):
    """Read an optional Streamlit secret without crashing the app."""
    try:
        value = st.secrets.get(name, default)
        return str(value).strip() if value is not None else str(default)
    except Exception:
        return str(default)



UPS_CLIENT_ID = get_optional_secret("UPS_CLIENT_ID")
UPS_CLIENT_SECRET = get_optional_secret("UPS_CLIENT_SECRET")



CANADA_POST_USERNAME = get_optional_secret("CANADA_POST_USERNAME")
CANADA_POST_PASSWORD = get_optional_secret("CANADA_POST_PASSWORD")

LIVE_HTTP_TIMEOUT = 15


def safe_json_response(response):
    """Return JSON or a readable error without exposing credentials."""
    try:
        payload = response.json()
    except Exception:
        payload = {"message": response.text[:500]}

    if response.ok:
        return payload

    message = (
        payload.get("message")
        or payload.get("error_description")
        or payload.get("error")
        or payload.get("errors")
        or f"HTTP {response.status_code}"
    )
    raise RuntimeError(str(message))



def geocode_open_meteo(location):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=LIVE_HTTP_TIMEOUT,
    )
    data = safe_json_response(response)
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"Location not found: {location}")
    return results[0]


def get_live_weather(location):
    place = geocode_open_meteo(location)
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": (
                "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": 5,
        },
        timeout=LIVE_HTTP_TIMEOUT,
    )
    data = safe_json_response(response)

    return {
        "source": "Open-Meteo",
        "location": {
            "name": place.get("name"),
            "admin1": place.get("admin1"),
            "country": place.get("country"),
            "timezone": data.get("timezone"),
        },
        "current": data.get("current", {}),
        "current_units": data.get("current_units", {}),
        "daily": data.get("daily", {}),
        "daily_units": data.get("daily_units", {}),
    }





def get_live_exchange_rate(base_currency, quote_currency):
    """Fetch the latest available reference exchange rate without an API key."""
    base = str(base_currency or "").strip().upper()
    quote_currency = str(quote_currency or "").strip().upper()

    if not re.fullmatch(r"[A-Z]{3}", base):
        raise RuntimeError("Invalid base currency code.")
    if not re.fullmatch(r"[A-Z]{3}", quote_currency):
        raise RuntimeError("Invalid quote currency code.")
    if base == quote_currency:
        return {
            "source": "Frankfurter",
            "base": base,
            "quote": quote_currency,
            "rate": 1.0,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "note": "The currencies are identical.",
        }

    response = requests.get(
        f"https://api.frankfurter.dev/v2/rate/{base}/{quote_currency}",
        timeout=LIVE_HTTP_TIMEOUT,
    )
    data = safe_json_response(response)

    rate = data.get("rate")
    if rate is None:
        raise RuntimeError(
            f"No exchange rate was returned for {base}/{quote_currency}."
        )

    return {
        "source": "Frankfurter",
        "base": data.get("base", base),
        "quote": data.get("quote", quote_currency),
        "rate": rate,
        "date": data.get("date"),
        "provider": data.get("provider"),
        "note": (
            "Latest available central-bank reference rate. "
            "This may not equal a bank, card, or cash-conversion rate."
        ),
    }



def cached_oauth_token(cache_key, token_url, client_id, client_secret, *,
                       data=None, headers=None, auth=None):
    if not client_id or not client_secret:
        raise RuntimeError("API credentials are not configured.")

    token_record = st.session_state.get(cache_key) or {}
    if (
        token_record.get("access_token")
        and float(token_record.get("expires_at", 0)) > time.time() + 60
    ):
        return token_record["access_token"]

    request_data = dict(data or {})
    request_headers = dict(headers or {})

    response = requests.post(
        token_url,
        data=request_data,
        headers=request_headers,
        auth=auth,
        timeout=LIVE_HTTP_TIMEOUT,
    )
    payload = safe_json_response(response)
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("OAuth response did not include an access token.")

    expires_in = int(payload.get("expires_in", 3300))
    st.session_state[cache_key] = {
        "access_token": token,
        "expires_at": time.time() + max(expires_in, 300),
    }
    return token


def get_ups_access_token():
    print("[UPS OAUTH] Requesting or reusing UPS OAuth token.", flush=True)
    token = cached_oauth_token(
        "ups_oauth_token",
        "https://onlinetools.ups.com/security/v1/oauth/token",
        UPS_CLIENT_ID,
        UPS_CLIENT_SECRET,
        data={"grant_type": "client_credentials"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        auth=(UPS_CLIENT_ID, UPS_CLIENT_SECRET),
    )
    print("[UPS OAUTH] Token available.", flush=True)
    return token


def track_ups(tracking_number):
    if not UPS_CLIENT_ID or not UPS_CLIENT_SECRET:
        return {
            "configured": False,
            "carrier": "UPS",
            "message": "UPS credentials are not configured."
        }

    # Never send surrounding words or punctuation to UPS.
    normalized_tracking = re.sub(
        r"[^A-Z0-9]",
        "",
        str(tracking_number or "").upper(),
    )

    if not re.fullmatch(r"1Z[A-Z0-9]{16}", normalized_tracking):
        raise RuntimeError(
            "Invalid UPS tracking-number format. "
            "A standard UPS 1Z tracking number must contain exactly 18 characters."
        )

    print(
        f"[UPS ROUTER] Calling UPS Tracking API for {normalized_tracking}.",
        flush=True,
    )
    token = get_ups_access_token()
    response = requests.get(
        (
            "https://onlinetools.ups.com/api/track/v1/details/"
            f"{quote(normalized_tracking, safe='')}"
        ),
        params={
            "locale": "en_US",
            "returnSignature": "false",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "transId": f"atp-{int(time.time() * 1000)}",
            "transactionSrc": "AutoTecProAI",
            "Accept": "application/json",
        },
        timeout=LIVE_HTTP_TIMEOUT,
    )

    print(
        f"[UPS TRACKING] HTTP {response.status_code} for {normalized_tracking}.",
        flush=True,
    )

    try:
        data = safe_json_response(response)
    except Exception as error:
        # Log only non-secret diagnostic information to Streamlit Cloud logs.
        safe_body = response.text[:1000].replace("\n", " ").replace("\r", " ")
        print(
            "[UPS TRACKING ERROR] "
            f"status={response.status_code} "
            f"tracking={normalized_tracking} "
            f"response={safe_body}",
            flush=True,
        )
        raise RuntimeError(f"UPS Tracking API error: {error}") from error

    return {
        "configured": True,
        "carrier": "UPS",
        "tracking_number": normalized_tracking,
        "source": "UPS Tracking API",
        "data": data,
    }






def xml_to_dict(element):
    result = {}
    for child in list(element):
        tag = child.tag.split("}")[-1]
        value = xml_to_dict(child) if list(child) else (child.text or "").strip()
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value
    return result


def track_canada_post(tracking_number):
    if not CANADA_POST_USERNAME or not CANADA_POST_PASSWORD:
        return {
            "configured": False,
            "carrier": "Canada Post",
            "message": "Canada Post credentials are not configured."
        }

    response = requests.get(
        (
            "https://soa-gw.canadapost.ca/vis/track/pin/"
            f"{quote(tracking_number.strip())}/detail"
        ),
        auth=(CANADA_POST_USERNAME, CANADA_POST_PASSWORD),
        headers={
            "Accept": "application/vnd.cpc.track+xml",
            "Accept-language": "en-CA",
        },
        timeout=LIVE_HTTP_TIMEOUT,
    )
    if not response.ok:
        safe_json_response(response)

    root = ET.fromstring(response.content)
    return {
        "configured": True,
        "carrier": "Canada Post",
        "tracking_number": tracking_number,
        "source": "Canada Post Tracking Web Service",
        "data": xml_to_dict(root),
    }


def extract_tracking_number(prompt):
    """
    Extract a carrier tracking number without accidentally appending words
    such as UPS, tracking, package, or shipment.

    UPS 1Z numbers are always exactly 18 characters:
    "1Z" + 16 letters/digits.
    """
    value = str(prompt or "").upper()

    # UPS standard tracking number: exactly 18 alphanumeric characters.
    ups_match = re.search(r"(?<![A-Z0-9])(1Z[A-Z0-9]{16})(?![A-Z0-9])", value)
    if ups_match:
        return ups_match.group(1)

    # Canada Post domestic tracking numbers are commonly 16 digits.
    canada_post_numeric = re.search(r"(?<!\d)(\d{16})(?!\d)", value)
    if canada_post_numeric:
        return canada_post_numeric.group(1)

    # Canada Post international format, for example AB123456789CA.
    canada_post_international = re.search(
        r"(?<![A-Z0-9])([A-Z]{2}\d{9}CA)(?![A-Z0-9])",
        value,
    )
    if canada_post_international:
        return canada_post_international.group(1)

    # Conservative fallback for other explicitly labelled tracking requests.
    labelled_match = re.search(
        r"(?:TRACK(?:ING)?(?:\s+NUMBER)?|PACKAGE|PARCEL|SHIPMENT)"
        r"\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{7,33})",
        value,
    )
    if labelled_match:
        compact = re.sub(r"[^A-Z0-9]", "", labelled_match.group(1))
        if 8 <= len(compact) <= 34 and any(char.isdigit() for char in compact):
            return compact

    return ""


def detect_live_request(prompt):
    value = str(prompt or "").strip()
    lower = value.lower()

    if not value:
        return {"type": "none"}

    tracking_number = extract_tracking_number(value)

    # Route a valid UPS 1Z number directly to UPS even when the user only types:
    # "1Zxxxxxxxxxxxxxxxx UPS" or just the tracking number by itself.
    if tracking_number and tracking_number.startswith("1Z"):
        return {
            "type": "tracking",
            "carrier": "ups",
            "tracking_number": tracking_number,
        }

    # Route Canada Post when the carrier is named, even without the word "track".
    if tracking_number and (
        "canada post" in lower or "canadapost" in lower
    ):
        return {
            "type": "tracking",
            "carrier": "canada_post",
            "tracking_number": tracking_number,
        }

    # For other tracking formats, require tracking-related language.
    if tracking_number and any(
        word in lower
        for word in ["track", "tracking", "shipment", "package", "parcel"]
    ):
        return {
            "type": "tracking_unknown",
            "tracking_number": tracking_number,
        }

    weather_match = re.search(
        r"(?:weather|temperature|forecast|rain|snow)"
        r"\s+(?:in|for|at)\s+([A-Za-z .,'-]{2,80})",
        value,
        flags=re.IGNORECASE,
    )
    if weather_match:
        location = re.split(
            r"\b(?:today|tomorrow|now|right now|this week|next week)\b",
            weather_match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" ,.?")

        if location:
            return {"type": "weather", "location": location}

    fx_match = re.search(
        r"\b([A-Z]{3})\s*(?:/|to|into|-)\s*([A-Z]{3})\b",
        value.upper(),
    )
    if fx_match and any(
        word in lower
        for word in [
            "rate", "exchange", "convert", "currency", "fx",
            "worth", "how much"
        ]
    ):
        return {
            "type": "fx",
            "base": fx_match.group(1),
            "quote": fx_match.group(2),
        }

    if any(
        phrase in lower
        for phrase in [
            "search the internet",
            "browse the web",
            "look online",
            "latest news",
            "latest update",
            "current news",
            "what happened today",
            "search online",
        ]
    ):
        return {"type": "web", "query": value}

    return {"type": "none"}



def get_live_data_for_prompt(prompt):
    request_type = detect_live_request(prompt)
    kind = request_type.get("type")

    try:
        if kind == "weather":
            return get_live_weather(request_type["location"])

        if kind == "fx":
            return get_live_exchange_rate(
                request_type["base"],
                request_type["quote"],
            )

        if kind == "tracking":
            carrier = request_type["carrier"]
            tracking_number = request_type["tracking_number"]

            if carrier == "ups":
                return track_ups(tracking_number)

            if carrier == "canada_post":
                return track_canada_post(tracking_number)

        if kind == "tracking_unknown":
            return {
                "source": "Live tracking router",
                "tracking_number": request_type.get("tracking_number"),
                "message": (
                    "A tracking number was detected, but the carrier is unclear. "
                    "Ask the user to specify UPS or Canada Post."
                ),
            }

        # OpenAI web_search handles public internet browsing.
        if kind == "web":
            return None

    except requests.Timeout:
        return {
            "source": "Live integration",
            "error": "The live service timed out. Please try again.",
        }
    except requests.RequestException as error:
        return {
            "source": "Live integration",
            "error": f"Network error: {error}",
        }
    except Exception as error:
        return {
            "source": "Live integration",
            "error": str(error),
        }

    return None




def live_integration_statuses():
    return [
        (
            "OpenAI web search / internet browsing",
            True,
            "Uses the existing OPENAI_API_KEY",
        ),
        (
            "Open-Meteo live weather",
            True,
            "No additional API key required",
        ),
        (
            "Frankfurter exchange rates",
            True,
            "No additional API key required",
        ),
        (
            "UPS tracking",
            bool(UPS_CLIENT_ID and UPS_CLIENT_SECRET),
            "UPS_CLIENT_ID + UPS_CLIENT_SECRET",
        ),
        (
            "Canada Post tracking",
            bool(CANADA_POST_USERNAME and CANADA_POST_PASSWORD),
            "CANADA_POST_USERNAME + CANADA_POST_PASSWORD",
        ),
    ]




# ============================================================
# Stable GPT-style upload manager
# ============================================================

MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


class ManagedUploadedFile(io.BytesIO):
    """In-memory upload compatible with the app's existing file handlers."""

    def __init__(self, data, name, mime_type="application/octet-stream"):
        super().__init__(data)
        self.name = str(name or "upload")
        self.type = str(mime_type or "application/octet-stream")
        self.size = len(data)

    def getvalue(self):
        position = self.tell()
        try:
            self.seek(0)
            return super().getvalue()
        finally:
            self.seek(position)


def _managed_upload_record(uploaded_file):
    data = uploaded_file.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    return {
        "id": digest,
        "name": str(getattr(uploaded_file, "name", "upload")),
        "type": str(
            getattr(uploaded_file, "type", "application/octet-stream")
            or "application/octet-stream"
        ),
        "size": len(data),
        "data": data,
    }


def _managed_upload_objects(records):
    return [
        ManagedUploadedFile(
            record["data"],
            record["name"],
            record.get("type") or "application/octet-stream",
        )
        for record in (records or [])
    ]


def clear_managed_uploads(storage_key, generation_key):
    st.session_state[storage_key] = []
    st.session_state[generation_key] = (
        int(st.session_state.get(generation_key, 0)) + 1
    )


def install_gpt_uploader_css():
    """
    Final, isolated uploader styling.

    No Streamlit DOM nodes are cloned or moved. Preview cards and delete
    controls are rendered by Python inside one keyed Streamlit container.
    """
    st.markdown(
        """
        <style>
        /* One professional upload box containing everything. */
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

        /* Preview card stays centered inside the upload box. */
        html body div[class*="st-key-atp_upload_card_"] {
            position: relative !important;
            width: min(100%, 196px) !important;
            margin: 0 auto !important;
            padding: 0 !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-radius: 15px !important;
            background: rgba(15, 23, 42, 0.82) !important;
            overflow: visible !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.18) !important;
        }

        html body div[class*="st-key-atp_upload_card_"]
        > div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        .atp-upload-preview-media {
            width: 100%;
            height: 105px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background: #020617;
            border-radius: 14px 14px 0 0;
            overflow: hidden;
        }

        .atp-upload-preview-media img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            background: #020617;
        }

        .atp-upload-file-icon {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            background: rgba(30, 41, 59, 0.74);
        }

        .atp-upload-meta {
            padding: 7px 32px 7px 8px;
            text-align: center;
            border-top: 1px solid rgba(148, 163, 184, 0.13);
        }

        .atp-upload-name {
            color: #f8fafc;
            font-size: 11px;
            font-weight: 700;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }

        .atp-upload-size {
            color: #94a3b8;
            font-size: 10px;
            margin-top: 2px;
        }

        /* Small ChatGPT-style delete icon over each image. */
        html body div[class*="st-key-atp_upload_card_"] {
            position: relative !important;
            isolation: isolate !important;
        }

        html body div[class*="st-key-atp_upload_card_"] .stButton,
        html body div[class*="st-key-atp_upload_card_"] div[data-testid="stButton"],
        html body div[class*="st-key-atp_upload_card_"] div[data-testid="stElementContainer"]:has(button[aria-label="Remove file"]) {
            position: absolute !important;
            top: 0 !important;
            right: 0 !important;
            transform: translate(34%, -34%) !important;
            left: auto !important;
            bottom: auto !important;
            z-index: 999 !important;
            width: 27px !important;
            min-width: 27px !important;
            max-width: 27px !important;
            height: 27px !important;
            min-height: 27px !important;
            max-height: 27px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        html body div[class*="st-key-atp_upload_card_"] button[aria-label="Remove file"],
        html body div[class*="st-key-atp_upload_card_"] .stButton > button,
        html body div[class*="st-key-atp_upload_card_"] div[data-testid="stButton"] > button {
            width: 27px !important;
            min-width: 27px !important;
            max-width: 27px !important;
            height: 27px !important;
            min-height: 27px !important;
            max-height: 27px !important;
            margin: 0 !important;
            padding: 0 !important;
            border-radius: 999px !important;
            border: 1px solid rgba(15, 23, 42, 0.16) !important;
            background: rgba(255, 255, 255, 0.94) !important;
            color: #475569 !important;
            -webkit-text-fill-color: #475569 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28) !important;
            font-size: 17px !important;
            font-weight: 400 !important;
            line-height: 1 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transform: none !important;
        }

        html body div[class*="st-key-atp_upload_card_"] .stButton > button:hover {
            background: #ffffff !important;
            border-color: rgba(239, 68, 68, 0.24) !important;
            color: #dc2626 !important;
            -webkit-text-fill-color: #dc2626 !important;
            transform: none !important;
        }

        html body div[class*="st-key-atp_upload_card_"] .stButton > button p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }

        /* Horizontal preview row on desktop; Streamlit stacks columns on mobile. */
        html body div[class*="st-key-atp_preview_grid_"] {
            width: 100% !important;
            margin: 0 auto 7px auto !important;
            display: block !important;
        }

        html body div[class*="st-key-atp_preview_grid_"]
        div[data-testid="stHorizontalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 auto !important;
            display: flex !important;
            align-items: flex-start !important;
            justify-content: center !important;
            gap: 7px !important;
            flex-wrap: nowrap !important;
        }

        html body div[class*="st-key-atp_preview_grid_"]
        div[data-testid="column"] {
            flex: 0 0 184px !important;
            width: 184px !important;
            min-width: 184px !important;
            max-width: 184px !important;
            padding: 0 !important;
        }

        .atp-add-file-label {
            width: 100%;
            text-align: center;
            color: #cbd5e1;
            font-size: 12.5px;
            font-weight: 650;
            margin: 2px 0 0 0;
        }
        /* Native chooser is centered and remains inside the same box. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] {
            background: transparent !important;
            border: 0 !important;
            padding: 0 !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid="stFileUploaderDropzone"] {
            min-height: 100px !important;
            height: auto !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex-direction: column !important;
            gap: 7px !important;
            padding: 12px !important;
            border: 1px dashed rgba(148, 163, 184, 0.25) !important;
            border-radius: 13px !important;
            background: rgba(15, 23, 42, 0.28) !important;
            box-sizing: border-box !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section > div,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid="stFileUploaderDropzone"] > div {
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
        div[data-testid="stFileUploader"]
        [data-testid="stBaseButton-secondary"] {
            width: auto !important;
            min-width: 126px !important;
            height: 50px !important;
            min-height: 50px !important;
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
            width: 25px !important;
            height: 25px !important;
        }

        




        /* Additional safe fallback for temporary icon-only controls.
           This does not affect the real Upload/Browse button. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        button[aria-label="Remove file"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        button[aria-label="Add file"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        button[title="Remove file"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        button[title="Add file"] {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        /* Safely hide only temporary row controls.
           The main Upload/Browse button remains clickable. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid="stFileUploaderFile"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid*="UploadedFile"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid*="FileUploaderFile"] button {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

/* Keep Streamlit's native size/type helper visible.
           The server upload limit is set to 10 MB in .streamlit/config.toml.
           Native uploaded rows remain hidden because Python renders previews. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] ul,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] section > div:has([data-testid="stFileUploaderFile"]) {
            display: none !important;
        }

        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] small {
            display: block !important;
            width: 100% !important;
            margin: 4px 0 0 0 !important;
            color: #94a3b8 !important;
            -webkit-text-fill-color: #94a3b8 !important;
            font-size: 11.5px !important;
            line-height: 1.35 !important;
            text-align: center !important;
            opacity: 1 !important;
        }




        /* Compact preview cards. */
        html body div[class*="st-key-atp_upload_card_"] {
            position: relative !important;
            width: 100% !important;
            max-width: 178px !important;
            margin: 0 auto !important;
            padding: 0 !important;
            border: 1px solid rgba(148, 163, 184, 0.20) !important;
            border-radius: 14px !important;
            background: rgba(15, 23, 42, 0.84) !important;
            overflow: visible !important;
            box-shadow: 0 6px 18px rgba(0,0,0,0.18) !important;
            isolation: isolate !important;
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
            font-size: 34px;
        }

        .atp-gpt-upload-meta {
            padding: 7px 8px 8px 8px;
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
            color: #94a3b8;
            font-size: 10px;
            margin-top: 2px;
        }

        /* Real Streamlit delete button pinned to upper-right of each image. */
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
            box-shadow: 0 2px 8px rgba(0,0,0,0.28) !important;
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


        /* Immediate CSS fallback for Streamlit's transient add/remove controls. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid="stFileUploaderFile"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid*="UploadedFile"] button,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"]
        [data-testid*="FileUploaderFile"] button {
            display: none !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        /* Hide every native temporary uploaded-file row/control. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] ul,
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] [data-testid*="UploadedFile"] {
            display: none !important;
        }
        @media (max-width: 768px) {

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="stHorizontalBlock"] {
                gap: 5px !important;
                flex-wrap: wrap !important;
            }

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="column"] {
                flex: 0 0 154px !important;
                width: 154px !important;
                min-width: 154px !important;
                max-width: 154px !important;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stHorizontalBlock"] {
                gap: 5px !important;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stHorizontalBlock"]
            > div[data-testid="column"] {
                flex: 0 0 154px !important;
                width: 154px !important;
                min-width: 154px !important;
                max-width: 154px !important;
            }

            html body div[class*="st-key-atp_upload_shell_"] {
                padding: 11px !important;
                border-radius: 15px !important;
            }

            html body div[class*="st-key-atp_upload_card_"] {
                width: min(100%, 168px) !important;
            }

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="stHorizontalBlock"] {
                gap: 7px !important;
            }

            html body div[class*="st-key-atp_preview_grid_"]
            div[data-testid="column"] {
                flex: 0 0 168px !important;
                width: 168px !important;
                min-width: 168px !important;
                max-width: 168px !important;
            }

            .atp-upload-preview-media {
                height: 100px;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] section,
            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"]
            [data-testid="stFileUploaderDropzone"] {
                min-height: 92px !important;
                padding: 10px !important;
                background: rgba(15, 23, 42, 0.34) !important;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] button,
            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"]
            [data-testid="stBaseButton-secondary"] {
                min-width: 116px !important;
                height: 47px !important;
                min-height: 47px !important;
                padding: 0 16px !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }

            html body div[class*="st-key-atp_upload_shell_"]
            div[data-testid="stFileUploader"] button * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }
        }
        
        /* FINAL RELIABLE APPROACH:
           Hide Streamlit's native uploader UI completely. The actual file
           input remains mounted and is opened by our custom Upload button. */
        html body div[class*="st-key-atp_upload_shell_"]
        div[data-testid="stFileUploader"] {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            min-width: 1px !important;
            min-height: 1px !important;
            max-width: 1px !important;
            max-height: 1px !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            border: 0 !important;
        }

        .atp-custom-upload-controls {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 7px;
            margin: 2px 0 0 0;
        }

        .atp-custom-upload-trigger {
            min-width: 126px;
            height: 50px;
            padding: 0 18px;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.32);
            background: rgba(51, 65, 85, 0.78);
            color: #ffffff;
            font-size: 15px;
            font-weight: 750;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            cursor: pointer;
            box-shadow: none;
            transition: background 0.16s ease, border-color 0.16s ease;
        }

        .atp-custom-upload-trigger:hover {
            background: rgba(71, 85, 105, 0.92);
            border-color: rgba(148, 163, 184, 0.46);
            transform: none;
        }

        .atp-custom-upload-trigger:active {
            transform: scale(0.98);
        }

        .atp-custom-upload-icon {
            width: 22px;
            height: 22px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }

        .atp-custom-upload-icon svg {
            width: 22px;
            height: 22px;
            display: block;
        }

        .atp-custom-upload-helper {
            color: #94a3b8;
            font-size: 11.5px;
            line-height: 1.35;
            text-align: center;
        }

        @media (max-width: 768px) {
            .atp-custom-upload-trigger {
                min-width: 116px;
                height: 47px;
                padding: 0 16px;
            }
        }
</style>
        """,
        unsafe_allow_html=True,
    )


    components.html(
        """
        <script>
        (() => {
          const root = window.parent;
          const doc = root.document;
          const KEY = "__atpCustomUploaderTriggerV1";

          try { root[KEY]?.cleanup?.(); } catch (error) {}

          function onClick(event) {
            const trigger = event.target.closest(".atp-custom-upload-trigger");
            if (!trigger) return;

            event.preventDefault();
            event.stopPropagation();

            const shell = trigger.closest(
              'div[class*="st-key-atp_upload_shell_"]'
            );
            if (!shell) return;

            const input = shell.querySelector(
              'div[data-testid="stFileUploader"] input[type="file"]'
            );
            if (!input) return;

            input.click();
          }

          doc.addEventListener("click", onClick, true);

          function cleanup() {
            doc.removeEventListener("click", onClick, true);
          }

          root[KEY] = { cleanup };
          window.addEventListener("beforeunload", cleanup, { once: true });
        })();
        </script>
        """,
        height=0,
        width=0,
    )











def render_managed_upload_preview(record, delete_key, on_delete):
    """Render one preview card with a real Streamlit delete button."""
    file_type = str(record.get("type") or "")
    file_name = html.escape(str(record.get("name") or "upload"))
    file_size = float(record.get("size") or 0) / (1024 * 1024)
    card_key = f"atp_upload_card_{record['id'][:16]}"

    with st.container(key=card_key):
        if file_type.startswith("image/"):
            encoded = base64.b64encode(record["data"]).decode()
            media_html = (
                '<div class="atp-gpt-upload-media">'
                f'<img src="data:{html.escape(file_type)};base64,{encoded}" '
                f'alt="{file_name}">'
                "</div>"
            )
        else:
            extension = Path(record.get("name") or "").suffix.lower()
            icon = "📄" if extension in {".pdf", ".txt", ".docx"} else "📎"
            media_html = (
                '<div class="atp-gpt-upload-media">'
                f'<div class="atp-gpt-file-icon">{icon}</div>'
                "</div>"
            )

        st.markdown(
            f"""
            {media_html}
            <div class="atp-gpt-upload-meta">
                <div class="atp-gpt-upload-name">{file_name}</div>
                <div class="atp-gpt-upload-size">{file_size:.1f} MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "×",
            key=delete_key,
            help="Remove file",
        ):
            on_delete()


def managed_file_uploader(
    *,
    storage_key,
    generation_key,
    widget_prefix,
    accepted_types,
    heading,
):
    """
    Stable GPT-style upload manager.

    A short rerun is intentionally used after selection so Streamlit's native
    temporary file row disappears completely. This is more reliable than
    trying to hide every temporary control with browser-side JavaScript.
    """
    install_gpt_uploader_css()

    if storage_key not in st.session_state:
        st.session_state[storage_key] = []
    if generation_key not in st.session_state:
        st.session_state[generation_key] = 0

    records = list(st.session_state.get(storage_key) or [])
    shell_key = f"atp_upload_shell_{widget_prefix}"

    with st.container(key=shell_key):
        st.markdown(
            f'<div class="atp-upload-heading">{html.escape(heading)}</div>',
            unsafe_allow_html=True,
        )

        if records:
            # Render previews row-by-row instead of cycling items down fixed
            # columns. This keeps every row aligned horizontally and centers
            # the final incomplete row.
            cards_per_row = 5

            for row_start in range(0, len(records), cards_per_row):
                row_records = records[row_start:row_start + cards_per_row]

                with st.container(
                    key=f"atp_preview_grid_{widget_prefix}_{row_start}"
                ):
                    preview_columns = st.columns(
                        len(row_records),
                        gap="small",
                        vertical_alignment="top",
                    )

                    for column, record in zip(preview_columns, row_records):
                        record_id = record["id"]

                        def delete_record(record_id=record_id):
                            st.session_state[storage_key] = [
                                item
                                for item in st.session_state.get(storage_key, [])
                                if item.get("id") != record_id
                            ]
                            st.session_state[generation_key] += 1
                            st.rerun()

                        with column:
                            render_managed_upload_preview(
                                record,
                                delete_key=(
                                    f"atp_delete_btn_{widget_prefix}_"
                                    f"{record_id[:16]}"
                                ),
                                on_delete=delete_record,
                            )

            st.markdown(
                '<div class="atp-add-file-label">＋ Add another file</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="atp-custom-upload-controls">
                <button
                    type="button"
                    class="atp-custom-upload-trigger"
                    data-uploader-prefix="{html.escape(widget_prefix)}"
                >
                    <span class="atp-custom-upload-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="none"
                             stroke="currentColor" stroke-width="2"
                             stroke-linecap="round" stroke-linejoin="round"
                             aria-hidden="true">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="17 8 12 3 7 8"></polyline>
                            <line x1="12" y1="3" x2="12" y2="15"></line>
                        </svg>
                    </span>
                    <span>Upload</span>
                </button>
                <div class="atp-custom-upload-helper">
                    10MB per file · JPG, JPEG, PNG, PDF, TXT
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        incoming_files = st.file_uploader(
            "Upload files",
            type=accepted_types,
            accept_multiple_files=True,
            key=f"{widget_prefix}_{st.session_state[generation_key]}",
            label_visibility="collapsed",
        )

    if incoming_files:
        existing_ids = {item["id"] for item in records}
        oversized_names = []

        for uploaded_file in incoming_files:
            record = _managed_upload_record(uploaded_file)

            if record["size"] > MAX_UPLOAD_BYTES:
                oversized_names.append(record["name"])
                continue

            if record["id"] not in existing_ids:
                records.append(record)
                existing_ids.add(record["id"])

        st.session_state[storage_key] = records
        st.session_state[generation_key] += 1

        if oversized_names:
            st.session_state[f"{storage_key}_size_error"] = (
                "These files exceed the 10 MB limit: "
                + ", ".join(oversized_names)
            )

        # Intentional single rerun after selection: refreshes the custom
        # preview cards and resets the hidden native uploader input.
        st.rerun()

    size_error = st.session_state.pop(f"{storage_key}_size_error", None)
    if size_error:
        st.error(size_error)

    return _managed_upload_objects(st.session_state.get(storage_key) or [])



# ============================================================
# Styling
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


        /* Final guard: never show accidental code artifact boxes in assistant replies */
        .assistant-bubble pre,
        .assistant-bubble code {
            display: none !important;
        }

</style>
        """,
        unsafe_allow_html=True
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


# Final isolated history-row presentation.
# The title and action menu are siblings; no Streamlit columns are used.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"] {
        position: relative !important;
        width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        margin: 0 0 4px 0 !important;
        padding: 0 3px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    > div[data-testid="stVerticalBlock"] {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        overflow: visible !important;
    }

    /* The title control occupies the complete row width. */
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] .stButton,
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] div[data-testid="stButton"] {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        height: 38px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] button {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        margin: 0 !important;
        padding: 0 34px 0 5px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        text-align: left !important;
        white-space: nowrap !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] button
    div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] button
    div[data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] button span {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        text-align: left !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        word-break: normal !important;
        overflow-wrap: normal !important;
        line-height: 1.2 !important;
    }

    /* Anchor the popover itself at the far-right center.
       This selector works across the current Streamlit DOM structure. */
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] {
        position: absolute !important;
        top: 50% !important;
        right: 3px !important;
        transform: translateY(-50%) !important;
        z-index: 80 !important;
        display: block !important;
        width: 28px !important;
        min-width: 28px !important;
        max-width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        max-height: 28px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        opacity: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
        transition: opacity 0.12s ease !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]:hover
    [data-testid="stPopover"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]:focus-within
    [data-testid="stPopover"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"]:has(button[aria-expanded="true"]) {
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }

    /* Prevent the popover's Streamlit wrapper from hiding or clipping it. */
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[data-testid="stElementContainer"]:has([data-testid="stPopover"]) {
        position: static !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: none !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]:hover
    div[data-testid="stElementContainer"]:has([data-testid="stPopover"]),
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]:focus-within
    div[data-testid="stElementContainer"]:has([data-testid="stPopover"]) {
        pointer-events: auto !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] > button {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 28px !important;
        min-width: 28px !important;
        max-width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        max-height: 28px !important;
        margin: 0 !important;
        padding: 0 !important;
        border-radius: 7px !important;
        line-height: 1 !important;
    }

    /* Pinned and Recent titles share the exact same left edge. */
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_pinned_"]::before,
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_active_pinned_"]::before {
        display: none !important;
        content: none !important;
        width: 0 !important;
    }

    section[data-testid="stSidebar"] .history-row-meta {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



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


def get_supabase_admin_client():
    """
    Create the privileged Supabase client only when permanent deletion is used.

    This keeps the stable app and Admin Panel load path unchanged. Missing or
    invalid privileged credentials produce an inline error during deletion
    instead of crashing the application at startup.
    """
    if create_supabase_client is None:
        raise RuntimeError(
            "The Supabase client package could not create an admin connection."
        )

    supabase_url = st.secrets.get("SUPABASE_URL")
    admin_key = (
        st.secrets.get("SUPABASE_SECRET_KEY")
        or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is missing from Streamlit Secrets.")

    if not admin_key:
        raise RuntimeError(
            "SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is missing "
            "from Streamlit Secrets."
        )

    return create_supabase_client(
        str(supabase_url),
        str(admin_key),
    )


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


def render_chat_message(
    role,
    content,
    images=None,
    message_index=None,
    show_generated_actions=True,
):
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

    if (
        role != "user"
        and show_generated_actions
        and final_images
    ):
        render_generated_image_actions(
            final_images,
            message_index=message_index,
        )

REMEMBER_CREDENTIAL_COOKIE = "atp_saved_login_v1"
REMEMBER_CREDENTIAL_DAYS = 30


def get_saved_login_credentials():
    """
    Read manually remembered login credentials from this browser.

    Returns:
        {"remember": bool, "username": str, "password": str}

    No authentication occurs here. The user must still click Login.
    """
    try:
        # CookieController already reads the browser cookies when the Streamlit
        # session starts. Avoid calling refresh() here because it mounts a
        # second temporary component and delays the login form rendering.
        raw_value = auth_cookie_controller.get(
            REMEMBER_CREDENTIAL_COOKIE
        )

        if not raw_value:
            return {
                "remember": False,
                "username": "",
                "password": "",
            }

        if isinstance(raw_value, dict):
            profile = raw_value
        else:
            profile = json.loads(str(raw_value))

        if (
            not isinstance(profile, dict)
            or profile.get("version") != 1
            or profile.get("remember") is not True
            or not isinstance(profile.get("username"), str)
            or not isinstance(profile.get("password"), str)
        ):
            remove_saved_login_credentials()
            return {
                "remember": False,
                "username": "",
                "password": "",
            }

        return {
            "remember": True,
            "username": profile.get("username", ""),
            "password": profile.get("password", ""),
        }

    except Exception:
        return {
            "remember": False,
            "username": "",
            "password": "",
        }


def save_login_credentials(username, password):
    """
    Save credentials only after a successful login with Remember me checked.

    The saved values are used only to prefill the next login page. They never
    authenticate the user automatically.
    """
    profile = {
        "version": 1,
        "remember": True,
        "username": str(username or "").strip(),
        "password": str(password or ""),
        "saved_at": now_iso(),
    }

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=REMEMBER_CREDENTIAL_DAYS
    )

    auth_cookie_controller.set(
        REMEMBER_CREDENTIAL_COOKIE,
        json.dumps(profile),
        path="/",
        expires=expires_at,
        max_age=REMEMBER_CREDENTIAL_DAYS * 24 * 60 * 60,
        secure=True,
        same_site="strict",
    )


def remove_saved_login_credentials():
    """Remove all app-saved login credentials from this browser."""
    try:
        auth_cookie_controller.remove(
            REMEMBER_CREDENTIAL_COOKIE,
            path="/",
            secure=True,
            same_site="strict",
        )
    except Exception:
        pass


def clear_legacy_browser_login_data():
    """
    Remove storage values left by earlier experimental Remember Me versions.
    """
    components.html(
        """
        <script>
        (() => {
          try {
            const storage = window.parent.localStorage;
            storage.removeItem("atp_remembered_credentials_v1");
            storage.removeItem("atp_login_profile");
            storage.removeItem("atp_remember_session");
            storage.removeItem("atp_remember_username");
            storage.removeItem("atp_remember_enabled");
          } catch (error) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def clear_browser_login_profile():
    """
    Clear credentials only when Remember me is unchecked or login is invalid.
    """
    remove_saved_login_credentials()
    clear_legacy_browser_login_data()


def queue_login_cookie_action(action, username="", password=""):
    """
    Queue a browser-cookie change for the next authenticated render.

    Supported actions:
    - "save": save username/password/checked state
    - "clear": remove saved login credentials
    """
    st.session_state["_atp_pending_login_cookie_action"] = {
        "action": str(action or "").strip().lower(),
        "username": str(username or "").strip(),
        "password": str(password or ""),
    }


def process_pending_login_cookie_action():
    """
    Execute a queued cookie action without immediately rerunning.

    This lets the CookieController frontend component finish writing/removing
    the cookie before the page is closed or refreshed.
    """
    pending = st.session_state.pop(
        "_atp_pending_login_cookie_action",
        None,
    )

    if not isinstance(pending, dict):
        return

    action = str(pending.get("action") or "").strip().lower()

    if action == "save":
        username = str(pending.get("username") or "").strip()
        password = str(pending.get("password") or "")

        if username and password:
            save_login_credentials(username, password)
            clear_legacy_browser_login_data()

    elif action == "clear":
        clear_browser_login_profile()


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


def restore_login_session():
    """
    Auto-login is intentionally disabled.

    Remember me now only prefills the login form. The user must always press
    the Login button.
    """
    return


def logout_user():
    """
    Log out of the current Streamlit session.

    Saved credentials are intentionally kept so a user who previously checked
    Remember me can return to a prefilled login page and manually sign in.
    """
    try:
        st.query_params.clear()
    except Exception:
        pass

    st.session_state.logged_in = False
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()


# ============================================================
# Login Screen
# ============================================================

def show_login_loading_message(placeholder):
    """
    Replace the complete login page with a small text-only loading state.

    Rendering inside the same placeholder guarantees the login logo and form
    are removed before the authenticated page appears.
    """
    placeholder.markdown(
        """
        <style>
        .atp-inline-login-loading {
            width: 100%;
            min-height: 220px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .atp-inline-login-loading-content {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            color: #f8fafc;
            font-size: 16px;
            font-weight: 750;
        }

        .atp-inline-login-spinner {
            width: 21px;
            height: 21px;
            border: 2px solid rgba(255,255,255,0.22);
            border-top-color: #ff4d3d;
            border-radius: 50%;
            animation: atpInlineLoginSpin 0.72s linear infinite;
        }

        @keyframes atpInlineLoginSpin {
            to { transform: rotate(360deg); }
        }
        </style>

        <div class="atp-inline-login-loading">
            <div class="atp-inline-login-loading-content">
                <div class="atp-inline-login-spinner"></div>
                <div>Loading AutoTecPro AI System...</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login_screen():
    apply_login_layout_css()

    # Keep the complete login page in one placeholder so every login element
    # (logo, heading, form) disappears together after authentication.
    login_page_placeholder = st.empty()

    # Read saved credentials only to prefill the form. This never logs the
    # user in automatically.
    saved_login = get_saved_login_credentials()
    remember_default = bool(saved_login.get("remember"))
    saved_username = str(saved_login.get("username") or "")
    saved_password = str(saved_login.get("password") or "")

    with login_page_placeholder.container():
        logo_base64 = get_logo_base64()

        if logo_base64:
            st.markdown(
                f"""
                <div class="login-logo">
                    <img src="data:image/png;base64,{logo_base64}">
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="login-logo">
                    <h1 style="font-size:48px;margin:0;color:white;">
                        AutoTecPro
                    </h1>
                    <p style="color:#94a3b8;margin-top:6px;">
                        Driven by Innovation
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="login-heading">
                <div class="login-heading-main">AutoTecPro AI Login</div>
                <div class="login-heading-sub">Internal AI Assistant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        install_login_autofill_support()

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                value=saved_username,
                placeholder="Enter your username",
            )
            password = st.text_input(
                "Password",
                value=saved_password,
                placeholder="Enter your password",
                type="password",
            )
            remember_me = st.checkbox(
                "Remember me",
                value=remember_default,
                help="Save my username and password on this browser for 30 days.",
            )
            login_submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

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

                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.role = user["role"]
                st.session_state.messages = []
                st.session_state.conversation_id = None

                # Replace the complete login page (logo, heading, and form)
                # with the requested text-only loading message.
                login_page_placeholder.empty()
                show_login_loading_message(login_page_placeholder)

                if remember_me:
                    queue_login_cookie_action(
                        "save",
                        user["username"],
                        password,
                    )
                else:
                    queue_login_cookie_action("clear")

                try:
                    st.query_params.clear()
                except Exception:
                    pass

                st.rerun()
            else:
                clear_browser_login_profile()
                try:
                    st.query_params.clear()
                except Exception:
                    pass
                st.error("Invalid username or password.")

        except Exception as e:
            st.error(f"Login failed: {e}")


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_screen()
    st.stop()

# Complete any Remember Me cookie write/removal on a stable authenticated
# render. Do not rerun immediately after this call.
process_pending_login_cookie_action()

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

st.markdown(
    """
    <style>
    /* Stable AutoTecPro AI sidebar upgrade — native Streamlit only. */

    div[data-testid="stSidebar"] {
        border-right: 1px solid rgba(148, 163, 184, 0.12);
    }

    div[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.70rem;
        padding-left: 0.72rem;
        padding-right: 0.72rem;
    }

    .sidebar-profile {
        padding: 12px 13px !important;
        margin: 0 0 14px 0 !important;
        border-radius: 15px !important;
        border: 1px solid rgba(148, 163, 184, 0.14) !important;
        background: linear-gradient(
            145deg,
            rgba(30, 64, 175, 0.17),
            rgba(15, 23, 42, 0.58)
        ) !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 5px !important;
        width: 100% !important;
        margin: 7px 0 0 0 !important;
    }

    div[data-testid="stSidebar"] label[data-baseweb="radio"] {
        position: relative !important;
        width: 100% !important;
        min-height: 45px !important;
        margin: 0 !important;
        padding: 10px 12px !important;
        border: 0 !important;
        border-radius: 9px !important;
        background: transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        box-sizing: border-box !important;
        cursor: pointer !important;
        transition: background 100ms ease, color 100ms ease !important;
    }

    div[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
        background: rgba(255, 255, 255, 0.06) !important;
    }

    div[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(255, 255, 255, 0.09) !important;
        box-shadow: inset 3px 0 0 #ef4444 !important;
    }

    div[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
        position: absolute !important;
        width: 1px !important;
        min-width: 1px !important;
        height: 1px !important;
        min-height: 1px !important;
        margin: 0 !important;
        opacity: 0 !important;
        overflow: hidden !important;
        pointer-events: none !important;
    }

    div[data-testid="stSidebar"] label[data-baseweb="radio"] p {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 0 0 2px !important;
        color: #d4dbe5 !important;
        font-size: 15px !important;
        font-weight: 640 !important;
        line-height: 1.22 !important;
        text-align: left !important;
        white-space: nowrap !important;
    }

    div[data-testid="stSidebar"]
    label[data-baseweb="radio"]:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 760 !important;
    }

    .sidebar-action-area {
        margin: 23px 0 21px 0 !important;
        padding: 0 !important;
    }

    .sidebar-newcase-btn {
        width: 100% !important;
        margin: 0 !important;
    }

    .sidebar-newcase-btn .stButton > button {
        width: 100% !important;
        min-height: 50px !important;
        border-radius: 11px !important;
        justify-content: center !important;
        text-align: center !important;
        padding: 0 15px !important;
        background: linear-gradient(
            135deg,
            #ff4b2b 0%,
            #ef233c 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        color: #ffffff !important;
        font-size: 15.5px !important;
        font-weight: 800 !important;
        box-shadow: 0 10px 22px rgba(239, 35, 60, 0.18) !important;
    }

    .sidebar-newcase-btn .stButton > button p {
        margin: 0 !important;
        color: #ffffff !important;
        font-size: 15.5px !important;
        font-weight: 800 !important;
        text-align: center !important;
    }

    .sidebar-newcase-btn .stButton > button:hover {
        filter: brightness(1.05) !important;
        transform: none !important;
    }

    .history-title {
        margin: 17px 0 8px 1px !important;
        color: #f8fafc !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        text-align: left !important;
    }

    .history-count {
        display: none !important;
    }

    .history-storage-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        width: 100%;
        margin: 1px 0 15px 0;
        padding: 10px 11px;
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 11px;
        background: rgba(15, 23, 42, 0.22);
        box-sizing: border-box;
    }

    .history-storage-label {
        color: #94a3b8;
        font-size: 11px;
        font-weight: 650;
    }

    .history-storage-value {
        color: #f8fafc;
        font-size: 12px;
        font-weight: 760;
        white-space: nowrap;
    }

    .history-section-label {
        margin: 15px 0 7px 2px !important;
        color: #a8b3c2 !important;
        font-size: 12px !important;
        font-weight: 760 !important;
        letter-spacing: 0 !important;
        text-transform: none !important;
        text-align: left !important;
    }

    .history-empty-state {
        padding: 7px 3px 11px 3px !important;
        color: #748298 !important;
        font-size: 11.5px !important;
        text-align: left !important;
        border: 0 !important;
        background: transparent !important;
    }

    div[data-testid="stSidebar"] [data-testid="stTextInput"] {
        margin: 0 0 17px 0 !important;
    }

    div[data-testid="stSidebar"] [data-testid="stTextInput"] input {
        min-height: 41px !important;
        border-radius: 10px !important;
        padding-left: 11px !important;
        background: rgba(15, 23, 42, 0.40) !important;
        border-color: rgba(148, 163, 184, 0.16) !important;
        color: #eef2f7 !important;
        font-size: 12.5px !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
        color: #8492a6 !important;
        opacity: 1 !important;
    }

    .history-row-meta {
        display: none !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_"] {
        position: relative !important;
        width: 100% !important;
        margin: 0 0 6px 0 !important;
        padding: 0 !important;
        border: 1px solid rgba(148, 163, 184, 0.22) !important;
        border-radius: 9px !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_"] > div,
    div[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="stHorizontalBlock"],
    div[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="column"] {
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        background: transparent !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_"] .stButton {
        width: 100% !important;
        margin: 0 !important;
        background: transparent !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button {
        width: 100% !important;
        min-height: 36px !important;
        height: 36px !important;
        margin: 0 !important;
        padding: 0 4px 0 8px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: #d7e0eb !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 12.5px !important;
        font-weight: 540 !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button p,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button span,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button div {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover {
        background: rgba(255, 255, 255, 0.055) !important;
        border-color: rgba(148, 163, 184, 0.32) !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_active_"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(239, 68, 68, 0.28) !important;
        box-shadow: inset 2px 0 0 #ef4444 !important;
    }

    div[data-testid="stSidebar"] [class*="st-key-history_row_pinned_"]::before,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_active_pinned_"]::before {
        content: "📌";
        position: absolute;
        left: 7px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 10px;
        z-index: 2;
        pointer-events: none;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_pinned_"] .stButton > button,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_active_pinned_"] .stButton > button {
        padding-left: 22px !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] [data-testid="stPopover"] {
        opacity: 0 !important;
        pointer-events: none !important;
        transition: opacity 90ms ease !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"]:hover [data-testid="stPopover"],
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_active_"] [data-testid="stPopover"] {
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] [data-testid="stPopover"] button {
        width: 30px !important;
        min-width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        border-radius: 7px !important;
        background: transparent !important;
        color: #93a1b3 !important;
        box-shadow: none !important;
        justify-content: center !important;
        font-size: 17px !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] [data-testid="stPopover"] button:hover {
        background: rgba(71, 85, 105, 0.46) !important;
        color: #ffffff !important;
    }

    div[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        scrollbar-width: thin;
        scrollbar-color: rgba(71, 85, 105, 0.58) transparent;
    }

    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar {
        width: 4px;
    }

    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-track {
        background: transparent;
    }

    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb {
        background: rgba(71, 85, 105, 0.58);
        border-radius: 999px;
    }

    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb:hover {
        background: rgba(239, 68, 68, 0.82);
    }

    .sidebar-logout-divider {
        height: 1px !important;
        margin: 16px 0 10px 0 !important;
        background: rgba(148, 163, 184, 0.14) !important;
    }

    .sidebar-logout-btn {
        width: 100% !important;
        margin: 0 0 6px 0 !important;
    }

    .sidebar-logout-btn .stButton > button {
        width: 100% !important;
        min-height: 40px !important;
        border-radius: 9px !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 0 11px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        color: #9ba8b9 !important;
        font-size: 12.5px !important;
        font-weight: 560 !important;
        box-shadow: none !important;
    }

    .sidebar-logout-btn .stButton > button:hover {
        background: rgba(51, 65, 85, 0.30) !important;
        color: #ffffff !important;
    }

    @media (max-width: 768px) {
        div[data-testid="stSidebar"] {
            width: min(90vw, 340px) !important;
            min-width: min(90vw, 340px) !important;
            max-width: min(90vw, 340px) !important;
        }

        div[data-testid="stSidebar"] > div:first-child {
            padding:
                calc(env(safe-area-inset-top, 0px) + 0.5rem)
                0.65rem
                calc(env(safe-area-inset-bottom, 0px) + 0.8rem)
                0.65rem !important;
        }

        div[data-testid="stSidebar"] label[data-baseweb="radio"] {
            min-height: 50px !important;
            padding: 12px 13px !important;
        }

        div[data-testid="stSidebar"] label[data-baseweb="radio"] p {
            font-size: 15px !important;
        }

        .sidebar-newcase-btn .stButton > button {
            min-height: 51px !important;
            font-size: 15.5px !important;
        }

        div[data-testid="stSidebar"]
        [data-testid="stTextInput"] input {
            min-height: 46px !important;
            font-size: 13px !important;
        }

        div[data-testid="stSidebar"] [class*="st-key-history_row_"] {
            margin-bottom: 8px !important;
        }

        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] .stButton > button {
            min-height: 44px !important;
            height: 44px !important;
            padding-left: 9px !important;
            font-size: 13px !important;
        }

        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] [data-testid="stPopover"] {
            opacity: 1 !important;
            pointer-events: auto !important;
        }

        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] [data-testid="stPopover"] button {
            width: 40px !important;
            min-width: 40px !important;
            height: 40px !important;
            min-height: 40px !important;
            font-size: 20px !important;
        }
    }

    @media (max-width: 420px) {
        div[data-testid="stSidebar"] {
            width: 92vw !important;
            min-width: 92vw !important;
            max-width: 92vw !important;
        }
    }
    /* ============================================================
       Final alignment and navigation override
    ============================================================ */

    .workspace-title {
        margin: 4px 0 8px 2px !important;
        color: #f8fafc !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        text-align: left !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] {
        width: 100% !important;
        margin: 0 0 3px 0 !important;
        padding: 0 !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] .stButton {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] .stButton > button {
        width: 100% !important;
        min-height: 43px !important;
        height: 43px !important;
        margin: 0 !important;
        padding: 0 11px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: #d5dde8 !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 640 !important;
        line-height: 1.2 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] .stButton > button p {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        color: inherit !important;
        font-size: 15px !important;
        font-weight: inherit !important;
        text-align: left !important;
        white-space: nowrap !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_idle_"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.055) !important;
        color: #ffffff !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_active_"] {
        background: rgba(255, 255, 255, 0.085) !important;
        box-shadow: inset 3px 0 0 #ef4444 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_active_"] .stButton > button {
        background: transparent !important;
        color: #ffffff !important;
        font-weight: 760 !important;
    }

    /* Section headings must occupy their own row and never be covered. */
    div[data-testid="stSidebar"] .history-section-label {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        height: auto !important;
        min-height: 18px !important;
        margin: 15px 0 8px 2px !important;
        padding: 0 !important;
        color: #b7c1cf !important;
        font-size: 12px !important;
        font-weight: 780 !important;
        line-height: 18px !important;
        text-align: left !important;
        overflow: visible !important;
        z-index: 5 !important;
        clear: both !important;
    }

    div[data-testid="stSidebar"] .history-empty-state {
        position: relative !important;
        display: block !important;
        min-height: 18px !important;
        margin: 0 0 8px 3px !important;
        padding: 0 !important;
        line-height: 18px !important;
        z-index: 4 !important;
    }

    /* Remove legacy vertical inflation and force a compact row. */
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        margin: 0 0 7px 0 !important;
        padding: 0 !important;
        border: 1px solid rgba(148, 163, 184, 0.24) !important;
        border-radius: 9px !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow: hidden !important;
        z-index: 1 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] > div,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"]
    div[data-testid="stHorizontalBlock"] {
        width: 100% !important;
        min-width: 0 !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        align-items: center !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"]
    div[data-testid="column"] {
        min-width: 0 !important;
        height: 38px !important;
        min-height: 38px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button {
        width: 100% !important;
        min-width: 0 !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        margin: 0 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button {
        padding: 0 5px 0 9px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 12.5px !important;
        font-weight: 560 !important;
        line-height: 1 !important;
        box-shadow: none !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button p,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button span,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] .stButton > button div {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Keep the three-dot control centered in the same 40px row. */
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] [data-testid="stPopover"] {
        height: 38px !important;
        min-height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stSidebar"]
    [class*="st-key-history_row_"] [data-testid="stPopover"] button {
        width: 30px !important;
        min-width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Align the pin marker vertically inside the compact row. */
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_pinned_"]::before,
    div[data-testid="stSidebar"]
    [class*="st-key-history_row_active_pinned_"]::before {
        top: 20px !important;
        transform: translateY(-50%) !important;
        line-height: 1 !important;
    }

    /* Prevent horizontal history scrolling caused by legacy widths. */
    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        overflow-x: hidden !important;
    }

    div[data-testid="stSidebar"]
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        overflow-x: hidden !important;
    }

    @media (max-width: 768px) {
        div[data-testid="stSidebar"]
        [class*="st-key-workspace_nav_"] .stButton > button {
            min-height: 48px !important;
            height: 48px !important;
            font-size: 15px !important;
        }

        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] {
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
        }

        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] > div,
        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"]
        div[data-testid="stHorizontalBlock"],
        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"]
        div[data-testid="column"],
        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] .stButton,
        div[data-testid="stSidebar"]
        [class*="st-key-history_row_"] .stButton > button {
            height: 44px !important;
            min-height: 44px !important;
            max-height: 44px !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


st.sidebar.markdown(
    f"""
    <div class="sidebar-profile">
        <div style="
            display:flex;
            align-items:center;
            gap:10px;
        ">
            <div style="
                width:36px;
                height:36px;
                border-radius:12px;
                display:flex;
                align-items:center;
                justify-content:center;
                background:rgba(248,80,58,.16);
                border:1px solid rgba(248,113,113,.22);
                font-size:18px;
            ">👤</div>
            <div style="min-width:0;">
                <div style="
                    color:#f8fafc;
                    font-size:16px;
                    font-weight:800;
                    line-height:1.15;
                    overflow:hidden;
                    text-overflow:ellipsis;
                    white-space:nowrap;
                ">{html.escape(str(st.session_state.username))}</div>
                <div style="
                    color:#94a3b8;
                    font-size:11.5px;
                    margin-top:3px;
                ">{html.escape(str(st.session_state.role).title())}</div>
            </div>
            <div style="
                margin-left:auto;
                width:8px;
                height:8px;
                border-radius:999px;
                background:#34d399;
                box-shadow:0 0 0 3px rgba(52,211,153,.10);
            "></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

workspace_items = [
    ("technical", "🔧", "Technical Support"),
    ("sales", "📈", "Sales & Marketing"),
    ("graphic", "🎨", "Graphic Marketing"),
]

if st.session_state.role == "admin":
    workspace_items.append(
        ("admin", "⚙️", "Admin Panel")
    )

valid_assistants = [
    f"{icon} {label}"
    for _, icon, label in workspace_items
]

if (
    "current_assistant" not in st.session_state
    or st.session_state.current_assistant not in valid_assistants
):
    st.session_state.current_assistant = valid_assistants[0]

st.sidebar.markdown(
    '<div class="workspace-title">AutoTecPro AI</div>',
    unsafe_allow_html=True,
)

for slug, icon, label in workspace_items:
    assistant_name = f"{icon} {label}"
    is_selected = (
        st.session_state.current_assistant
        == assistant_name
    )

    nav_state = "active" if is_selected else "idle"

    with st.sidebar.container(
        key=f"workspace_nav_{nav_state}_{slug}"
    ):
        if st.button(
            label,
            key=f"workspace_button_{slug}",
            use_container_width=True,
        ):
            if not is_selected:
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.session_state.current_assistant = (
                    assistant_name
                )
                st.session_state.chat_file_uploader_generation += 1
                clear_managed_uploads(
                    "chat_managed_uploads",
                    "chat_managed_upload_generation",
                )
                st.rerun()

assistant = st.session_state.current_assistant

# Final sidebar-only visual override.
# Kept separate so legacy/global button rules cannot recolor navigation.
st.markdown(
    """
    <style>
    /* ============================================================
       GPT-style workspace navigation: no red/orange backgrounds
    ============================================================ */

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"],
    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"] > div,
    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"] .stButton {
        background: transparent !important;
        background-color: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"]
    .stButton > button {
        width: 100% !important;
        min-height: 43px !important;
        height: 43px !important;
        margin: 0 !important;
        padding: 0 10px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: #d7dee8 !important;
        box-shadow: none !important;
        filter: none !important;
        transform: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 620 !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"]
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.055) !important;
        background-color: rgba(255, 255, 255, 0.055) !important;
        color: #ffffff !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_active_"],
    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_active_"] > div {
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_active_"]
    .stButton > button {
        background: rgba(255, 255, 255, 0.085) !important;
        background-color: rgba(255, 255, 255, 0.085) !important;
        background-image: none !important;
        color: #ffffff !important;
        font-weight: 740 !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stSidebar"]
    div[class*="st-key-workspace_nav_"]
    .stButton > button p {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        color: inherit !important;
        font-size: 15px !important;
        white-space: nowrap !important;
    }

    /* ============================================================
       Pinned / Recents alignment
    ============================================================ */

    div[data-testid="stSidebar"] .history-section-label {
        display: block !important;
        position: relative !important;
        width: 100% !important;
        min-height: 20px !important;
        height: 20px !important;
        margin: 16px 0 0 2px !important;
        padding: 0 !important;
        color: #b8c2cf !important;
        font-size: 12px !important;
        font-weight: 780 !important;
        line-height: 20px !important;
        text-align: left !important;
        overflow: visible !important;
        z-index: 10 !important;
    }

    div[data-testid="stSidebar"] .history-section-spacer {
        display: block !important;
        width: 100% !important;
        height: 8px !important;
        min-height: 8px !important;
        margin: 0 !important;
        padding: 0 !important;
        clear: both !important;
    }

    /* ============================================================
       Compact chat rows and exact icon/text alignment
    ============================================================ */

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"] {
        width: 100% !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        margin: 0 0 7px 0 !important;
        padding: 0 !important;
        border: 1px solid rgba(148, 163, 184, 0.24) !important;
        border-radius: 9px !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        width: 100% !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        gap: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[data-testid="column"]:first-child {
        flex: 1 1 auto !important;
        width: calc(100% - 38px) !important;
        min-width: 0 !important;
        max-width: calc(100% - 38px) !important;
        height: 40px !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[data-testid="column"]:last-child {
        flex: 0 0 38px !important;
        width: 38px !important;
        min-width: 38px !important;
        max-width: 38px !important;
        height: 40px !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    .stButton,
    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    .stButton > button {
        width: 100% !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        margin: 0 !important;
        padding: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    .stButton > button {
        padding: 0 6px 0 10px !important;
        border: 0 !important;
        border-radius: 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
        color: #dbe3ed !important;
        font-size: 12.5px !important;
        font-weight: 560 !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    .stButton > button p {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] {
        width: 38px !important;
        height: 40px !important;
        min-height: 40px !important;
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] > button,
    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] button {
        width: 32px !important;
        min-width: 32px !important;
        max-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        max-height: 32px !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    [data-testid="stPopover"] svg {
        display: none !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_pinned_"]::before,
    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_active_pinned_"]::before {
        top: 21px !important;
        left: 7px !important;
        transform: translateY(-50%) !important;
        line-height: 1 !important;
    }

    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_pinned_"]
    .stButton > button,
    div[data-testid="stSidebar"]
    div[class*="st-key-history_row_active_pinned_"]
    .stButton > button {
        padding-left: 23px !important;
    }

    /* Keep desktop three dots hidden until hover. */
    @media (hover: hover) and (pointer: fine) {
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            opacity: 0 !important;
            pointer-events: none !important;
        }

        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]:hover
        [data-testid="stPopover"],
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_active_"]
        [data-testid="stPopover"] {
            opacity: 1 !important;
            pointer-events: auto !important;
        }
    }

    @media (max-width: 768px) {
        div[data-testid="stSidebar"]
        div[class*="st-key-workspace_nav_"]
        .stButton > button {
            min-height: 48px !important;
            height: 48px !important;
        }

        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"] {
            height: 48px !important;
            min-height: 48px !important;
            max-height: 48px !important;
        }

        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        div[data-testid="stHorizontalBlock"],
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        div[data-testid="column"],
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        .stButton,
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        .stButton > button,
        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            height: 46px !important;
            min-height: 46px !important;
            max-height: 46px !important;
        }

        div[data-testid="stSidebar"]
        div[class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            opacity: 1 !important;
            pointer-events: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Definitive sidebar fix: target Streamlit widget key classes directly.
st.markdown(
    """
    <style>
    /* Workspace navigation — key-level selectors override global red buttons. */
    section[data-testid="stSidebar"] [class*="st-key-workspace_button_"] .stButton > button,
    section[data-testid="stSidebar"] [class*="st-key-workspace_button_"] button {
        width: 100% !important;
        min-height: 42px !important;
        height: 42px !important;
        margin: 0 !important;
        padding: 0 10px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: #d7dee8 !important;
        box-shadow: none !important;
        filter: none !important;
        transform: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 15px !important;
        font-weight: 620 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-workspace_button_"] .stButton > button:hover,
    section[data-testid="stSidebar"] [class*="st-key-workspace_button_"] button:hover {
        background: rgba(255,255,255,0.055) !important;
        background-color: rgba(255,255,255,0.055) !important;
        color: #ffffff !important;
        box-shadow: none !important;
        transform: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-workspace_nav_active_"]
    [class*="st-key-workspace_button_"] .stButton > button {
        background: rgba(255,255,255,0.085) !important;
        background-color: rgba(255,255,255,0.085) !important;
        color: #ffffff !important;
        font-weight: 740 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-workspace_nav_"] {
        margin: 0 0 3px 0 !important;
        padding: 0 !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    /* History headings always sit on their own line. */
    section[data-testid="stSidebar"] .history-section-label {
        display: block !important;
        position: relative !important;
        width: 100% !important;
        height: auto !important;
        min-height: 20px !important;
        margin: 16px 0 8px 2px !important;
        padding: 0 !important;
        color: #b8c2cf !important;
        font-size: 12px !important;
        font-weight: 780 !important;
        line-height: 20px !important;
        text-align: left !important;
        clear: both !important;
        z-index: 3 !important;
    }

    /* One-row history card. Popover is absolutely positioned, so it cannot wrap. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"] {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        min-height: 40px !important;
        height: 40px !important;
        max-height: 40px !important;
        margin: 0 0 7px 0 !important;
        padding: 0 !important;
        border: 1px solid rgba(148,163,184,0.24) !important;
        border-radius: 9px !important;
        background: transparent !important;
        overflow: hidden !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"] > div,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"] > div > div {
        position: static !important;
        width: 100% !important;
        min-height: 38px !important;
        height: 38px !important;
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        background: transparent !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton,
    section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton > button {
        width: 100% !important;
        min-height: 38px !important;
        height: 38px !important;
        max-height: 38px !important;
        margin: 0 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton > button {
        padding: 0 42px 0 10px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        color: #dbe3ed !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
        font-size: 12.5px !important;
        font-weight: 560 !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton > button p,
    section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton > button div {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"] [data-testid="stPopover"] {
        position: absolute !important;
        top: 4px !important;
        right: 4px !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        min-height: 32px !important;
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 8 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"] [data-testid="stPopover"] button {
        width: 32px !important;
        min-width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        border-radius: 7px !important;
        background: transparent !important;
        color: #93a1b3 !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"] [data-testid="stPopover"] svg {
        display: none !important;
    }

    @media (hover:hover) and (pointer:fine) {
        section[data-testid="stSidebar"] [class*="st-key-history_row_"] [data-testid="stPopover"] {
            opacity: 0 !important;
            pointer-events: none !important;
        }
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover [data-testid="stPopover"],
        section[data-testid="stSidebar"] [class*="st-key-history_row_active_"] [data-testid="stPopover"] {
            opacity: 1 !important;
            pointer-events: auto !important;
        }
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_pinned_"]::before,
    section[data-testid="stSidebar"] [class*="st-key-history_row_active_pinned_"]::before {
        top: 20px !important;
        left: 7px !important;
        transform: translateY(-50%) !important;
        line-height: 1 !important;
        z-index: 7 !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_pinned_"] [class*="st-key-open_"] .stButton > button,
    section[data-testid="stSidebar"] [class*="st-key-history_row_active_pinned_"] [class*="st-key-open_"] .stButton > button {
        padding-left: 23px !important;
    }

    @media (max-width:768px) {
        section[data-testid="stSidebar"] [class*="st-key-workspace_button_"] .stButton > button {
            min-height: 48px !important;
            height: 48px !important;
        }
        section[data-testid="stSidebar"] [class*="st-key-history_row_"] {
            min-height: 46px !important;
            height: 46px !important;
            max-height: 46px !important;
        }
        section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton,
        section[data-testid="stSidebar"] [class*="st-key-open_"] .stButton > button {
            min-height: 44px !important;
            height: 44px !important;
            max-height: 44px !important;
        }
        section[data-testid="stSidebar"] [class*="st-key-history_row_"] [data-testid="stPopover"] {
            top: 6px !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final alignment-only sidebar override.
# This block is intentionally last so it wins over older global button rules.
st.markdown(
    """
    <style>
    /* ------------------------------------------------------------
       AutoTecPro AI navigation: one consistent left edge
    ------------------------------------------------------------ */

    section[data-testid="stSidebar"] .workspace-title {
        width: 100% !important;
        margin: 5px 0 8px 0 !important;
        padding: 0 !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] {
        width: 100% !important;
        margin: 0 0 3px 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"],
    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"] .stButton {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button {
        width: 100% !important;
        min-height: 42px !important;
        height: 42px !important;
        margin: 0 !important;
        padding: 0 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] p {
        display: block !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        white-space: nowrap !important;
    }

    /* ------------------------------------------------------------
       History section spacing
    ------------------------------------------------------------ */

    section[data-testid="stSidebar"] .history-title {
        margin: 20px 0 12px 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
    }

    section[data-testid="stSidebar"] .history-storage-card {
        margin: 0 0 18px 0 !important;
    }

    section[data-testid="stSidebar"] .history-section-label {
        display: block !important;
        width: 100% !important;
        min-height: 20px !important;
        height: auto !important;
        margin: 20px 0 12px 0 !important;
        padding: 0 !important;
        line-height: 20px !important;
        text-align: left !important;
        clear: both !important;
        overflow: visible !important;
    }

    section[data-testid="stSidebar"] .history-section-spacer {
        display: block !important;
        width: 100% !important;
        height: 6px !important;
        min-height: 6px !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"] .history-empty-state {
        margin: 0 0 12px 0 !important;
    }

    /* Guarantee a visible gap between a section heading and its first row. */
    section[data-testid="stSidebar"]
    .history-section-label
    + div {
        margin-top: 6px !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"]
        [class*="st-key-workspace_button_"]
        .stButton > button {
            padding-left: 10px !important;
        }

        section[data-testid="stSidebar"] .history-title {
            margin-top: 22px !important;
            margin-bottom: 14px !important;
        }

        section[data-testid="stSidebar"] .history-section-label {
            margin-top: 22px !important;
            margin-bottom: 14px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final workspace spacing and left-alignment override.
st.markdown(
    """
    <style>
    /* ------------------------------------------------------------
       Prevent AutoTecPro AI heading from touching/overlapping first item
    ------------------------------------------------------------ */
    section[data-testid="stSidebar"] .workspace-title {
        display: block !important;
        width: 100% !important;
        margin: 8px 0 14px 0 !important;
        padding: 0 !important;
        line-height: 1.25 !important;
        text-align: left !important;
        clear: both !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"]:first-of-type {
        margin-top: 0 !important;
    }

    /* ------------------------------------------------------------
       Force every workspace row to align to the same far-left edge
    ------------------------------------------------------------ */
    section[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] {
        width: 100% !important;
        margin: 0 0 5px 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"],
    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"] .stButton {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button {
        width: 100% !important;
        min-height: 44px !important;
        height: 44px !important;
        margin: 0 !important;
        padding: 0 10px !important;
        justify-content: flex-start !important;
        text-align: left !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] p {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Extra breathing room before New Case after the last workspace item. */
    .sidebar-action-area {
        margin-top: 26px !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] .workspace-title {
            margin-top: 10px !important;
            margin-bottom: 16px !important;
        }

        section[data-testid="stSidebar"]
        [class*="st-key-workspace_button_"]
        .stButton > button {
            min-height: 48px !important;
            height: 48px !important;
            padding-left: 11px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final fixed-column workspace alignment and heading spacing override.
st.markdown(
    """
    <style>
    /* ============================================================
       Workspace navigation — fixed icon column + aligned wording
    ============================================================ */

    section[data-testid="stSidebar"] .workspace-title {
        display: block !important;
        width: 100% !important;
        margin: 7px 0 13px 0 !important;
        padding: 0 !important;
        color: #f8fafc !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        text-align: left !important;
        clear: both !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_nav_"] {
        width: 100% !important;
        margin: 0 0 5px 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"],
    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"] .stButton {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button {
        display: flex !important;
        width: 100% !important;
        min-height: 44px !important;
        height: 44px !important;
        margin: 0 !important;
        padding: 0 10px !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        gap: 0 !important;
        overflow: hidden !important;
    }

    /* Every icon occupies exactly the same 34px column. */
    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button::before {
        display: inline-flex !important;
        flex: 0 0 34px !important;
        width: 34px !important;
        min-width: 34px !important;
        max-width: 34px !important;
        height: 22px !important;
        margin: 0 !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: flex-start !important;
        font-size: 19px !important;
        line-height: 22px !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_technical"]
    .stButton > button::before {
        content: "🔧";
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_sales"]
    .stButton > button::before {
        content: "📈";
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_graphic"]
    .stButton > button::before {
        content: "🎨";
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_admin"]
    .stButton > button::before {
        content: "⚙️";
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    [class*="st-key-workspace_button_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] p {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        color: inherit !important;
        font-size: 15px !important;
        font-weight: inherit !important;
        line-height: 1.2 !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* ============================================================
       History / Pinned / Recents heading hierarchy and spacing
    ============================================================ */

    section[data-testid="stSidebar"] .history-title {
        display: block !important;
        width: 100% !important;
        margin: 8px 0 12px 0 !important;
        padding: 0 !important;
        color: #f8fafc !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        line-height: 20px !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"] .history-storage-card {
        display: flex !important;
        width: 100% !important;
        margin: 0 0 18px 0 !important;
        padding: 10px 12px !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
    }

    section[data-testid="stSidebar"] .history-storage-label {
        margin: 0 !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"] .history-storage-value {
        margin: 0 0 0 auto !important;
        text-align: right !important;
        white-space: nowrap !important;
    }

    section[data-testid="stSidebar"] .history-section-label {
        display: block !important;
        position: relative !important;
        width: 100% !important;
        min-height: 20px !important;
        height: auto !important;
        margin: 20px 0 12px 0 !important;
        padding: 0 !important;
        color: #f8fafc !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        line-height: 20px !important;
        text-align: left !important;
        clear: both !important;
        overflow: visible !important;
        z-index: 8 !important;
    }

    section[data-testid="stSidebar"] .history-section-spacer {
        display: block !important;
        width: 100% !important;
        height: 6px !important;
        min-height: 6px !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"]
        [class*="st-key-workspace_button_"]
        .stButton > button {
            min-height: 48px !important;
            height: 48px !important;
            padding-left: 11px !important;
        }

        section[data-testid="stSidebar"]
        [class*="st-key-workspace_button_"]
        .stButton > button::before {
            flex-basis: 36px !important;
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
        }

        section[data-testid="stSidebar"] .history-title,
        section[data-testid="stSidebar"] .history-section-label {
            font-size: 14px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Final Pinned / Recent History visual-only cleanup.
# This override intentionally changes styling only; all existing history,
# pin, rename, delete, open, and popover functionality remains unchanged.
st.markdown(
    """
    <style>
    /* Match the clean AI Workspace navigation: no grey boxed cards. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"] {
        border: 0 !important;
        outline: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        box-shadow: none !important;
        filter: none !important;
        margin-bottom: 4px !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"] > div,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"] > div > div,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="stHorizontalBlock"],
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="column"] {
        border: 0 !important;
        outline: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    [class*="st-key-open_"] .stButton > button {
        border: 0 !important;
        outline: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        box-shadow: none !important;
        filter: none !important;
        transform: none !important;
    }

    /* Same subtle hover treatment used by AI Workspace navigation. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover
    [class*="st-key-open_"] .stButton > button {
        background: rgba(255, 255, 255, 0.055) !important;
        background-color: rgba(255, 255, 255, 0.055) !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }

    /* Current conversation follows the AI Workspace active-row treatment. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_active_"] {
        border: 0 !important;
        background: rgba(255, 255, 255, 0.085) !important;
        background-color: rgba(255, 255, 255, 0.085) !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_active_"]
    [class*="st-key-open_"] .stButton > button {
        background: transparent !important;
        background-color: transparent !important;
        color: #ffffff !important;
        font-weight: 650 !important;
    }

    /* Preserve the three-dot menu, but reveal it only on row hover. */
    @media (hover: hover) and (pointer: fine) {
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
            transition: opacity 0.14s ease !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover
        [data-testid="stPopover"],
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]
        [data-testid="stPopover"]:has([aria-expanded="true"]) {
            opacity: 1 !important;
            visibility: visible !important;
            pointer-events: auto !important;
        }
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        box-shadow: none !important;
        transform: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="sidebar-action-area">',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="sidebar-newcase-btn">',
    unsafe_allow_html=True,
)

if st.sidebar.button(
    "＋  New Case",
    key="new_case_button",
    use_container_width=True,
):
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.chat_file_uploader_generation += 1
    clear_managed_uploads(
        "chat_managed_uploads",
        "chat_managed_upload_generation",
    )
    st.rerun()

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

    EXIF orientation is applied before the preview is encoded. The preview schema
    intentionally remains {"name", "data_url"} because the existing history
    parser and renderer expect those exact keys.
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

            encoded = base64.b64encode(normalized_bytes).decode()
            previews.append({
                "name": file_name,
                "data_url": f"data:{normalized_mime};base64,{encoded}",
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
        if not isinstance(image, dict) or not image.get("data_url"):
            continue

        clean_image = {
            "name": str(image.get("name") or "uploaded image"),
            "data_url": str(image.get("data_url")),
        }

        # Preserve optional generated-image metadata while remaining fully
        # backward compatible with older uploaded-image history records.
        for key in (
            "generated",
            "prompt",
            "created_at",
            "model",
            "size",
            "resolution",
            "mime_type",
            "filename",
        ):
            if key in image:
                clean_image[key] = image.get(key)

        clean_images.append(clean_image)

    return visible_text, clean_images


def render_image_previews(images):
    """
    Render uploaded chat images as compact, unindented HTML.

    Keeping the generated HTML on one continuous line prevents Streamlit
    Markdown from interpreting the second image card as a code block.
    """
    if not images:
        return ""

    cards = []

    for image in images:
        name = html.escape(
            str(image.get("name") or "uploaded image"),
            quote=True,
        )
        data_url = str(image.get("data_url") or "").strip()

        if not data_url.startswith("data:image/"):
            continue

        safe_data_url = html.escape(data_url, quote=True)

        caption_icon = "🖼️" if image.get("generated") else "📎"
        card_class = (
            "chat-image-card chat-generated-image-card"
            if image.get("generated")
            else "chat-image-card"
        )
        cards.append(
            f'<div class="{card_class}">'
            f'<img src="{safe_data_url}" alt="{name}">'
            f'<div class="chat-image-caption">{caption_icon} {name}</div>'
            f'</div>'
        )

    if not cards:
        return ""

    return '<div class="chat-image-grid">' + "".join(cards) + '</div>'


GRAPHIC_IMAGE_COUNT = 1
GRAPHIC_IMAGE_MODEL = "gpt-image-1"
GRAPHIC_IMAGE_TIMEOUT_SECONDS = 180.0
GRAPHIC_IMAGE_MAX_RETRIES = 0


def is_graphic_image_generation_request(prompt_text, uploaded_files=None):
    """
    Detect an explicit request to create or edit an image.

    Graphic Marketing can still answer ordinary text questions. Image
    generation activates only when the prompt clearly asks for visual output.
    """
    text = str(prompt_text or "").strip().lower()
    if not text:
        return False

    visual_nouns = (
        "image", "photo", "picture", "graphic", "artwork", "banner",
        "thumbnail", "poster", "flyer", "ad", "advertisement", "logo",
        "background", "social media post", "instagram post",
        "facebook post", "facebook cover", "youtube cover",
        "product shot", "product photography", "render",
    )
    action_words = (
        "create", "generate", "make", "design", "draw", "render",
        "produce", "edit", "modify", "change", "replace", "remove",
        "add", "transform", "recreate", "enhance", "retouch",
    )

    has_visual_noun = any(term in text for term in visual_nouns)
    has_action_word = any(term in text for term in action_words)

    # Common direct commands that may omit the word "image."
    direct_phrases = (
        "turn this into", "use this photo", "use this image",
        "change the background", "remove the background",
        "make it look", "make this look", "create a 16:9",
        "create a 1:1", "create a 9:16",
    )

    return (
        (has_visual_noun and has_action_word)
        or any(phrase in text for phrase in direct_phrases)
    )


def choose_graphic_image_size(prompt_text):
    """
    Use the supported high-resolution landscape output for every
    Graphic Marketing image generation.
    """
    return "1536x1024"


def graphic_image_filename(prompt_text, created_at=None):
    """Create a readable, filesystem-safe PNG filename."""
    timestamp = created_at or datetime.now(timezone.utc)
    words = re.findall(r"[A-Za-z0-9]+", str(prompt_text or ""))[:6]
    stem = "_".join(words).strip("_") or "AutoTecPro_Generated_Image"
    stem = stem[:72]
    return f"{stem}_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.png"


def data_url_to_bytes(data_url):
    """Decode an image data URL into raw bytes and its MIME type."""
    value = str(data_url or "")
    match = re.match(
        r"^data:(image/[A-Za-z0-9.+-]+);base64,(.+)$",
        value,
        flags=re.DOTALL,
    )
    if not match:
        return b"", "image/png"

    try:
        return base64.b64decode(match.group(2)), match.group(1)
    except Exception:
        return b"", match.group(1)


def image_bytes_to_png(image_bytes):
    """
    Normalize generated output to PNG without changing its resolution.

    The API currently returns base64 image data. This helper guarantees the
    Download PNG button always serves PNG, even if a future model returns a
    different raster format.
    """
    raw = bytes(image_bytes or b"")
    if not raw or Image is None:
        return raw

    try:
        with Image.open(io.BytesIO(raw)) as generated_image:
            output = io.BytesIO()
            if generated_image.mode not in ("RGB", "RGBA"):
                generated_image = generated_image.convert("RGBA")
            generated_image.save(output, format="PNG", optimize=True)
            return output.getvalue()
    except Exception:
        return raw


def prepare_graphic_reference_images(uploaded_files):
    """Convert uploaded reference images into SDK-compatible in-memory files."""
    references = []

    for index, uploaded_file in enumerate(uploaded_files or []):
        mime_type = str(getattr(uploaded_file, "type", "") or "").lower()
        if not mime_type.startswith("image/"):
            continue

        normalized_bytes, normalized_mime = normalize_uploaded_image_bytes(
            uploaded_file
        )
        if not normalized_bytes:
            continue

        extension = ".png" if normalized_mime == "image/png" else ".jpg"
        reference = io.BytesIO(normalized_bytes)
        reference.name = (
            Path(str(getattr(uploaded_file, "name", "") or "")).name
            or f"reference_{index + 1}{extension}"
        )
        if not Path(reference.name).suffix:
            reference.name += extension
        reference.seek(0)
        references.append(reference)

    return references


def generate_graphic_marketing_images(prompt_text, uploaded_files=None):
    """
    Generate or reference-edit Graphic Marketing images through the Image API.

    Image calls use one supported model, no automatic retries, and a bounded
    timeout so Streamlit cannot remain in a loading state indefinitely.
    """
    prompt_text = str(prompt_text or "").strip()
    if not prompt_text:
        raise ValueError("Please enter an image-generation command.")

    output_size = choose_graphic_image_size(prompt_text)
    reference_images = prepare_graphic_reference_images(uploaded_files)

    # Apply reliability settings only to image requests. The shared client and
    # every other OpenAI feature in the application remain unchanged.
    image_client = client.with_options(
        timeout=GRAPHIC_IMAGE_TIMEOUT_SECONDS,
        max_retries=GRAPHIC_IMAGE_MAX_RETRIES,
    )

    try:
        if reference_images:
            for reference in reference_images:
                reference.seek(0)

            image_input = (
                reference_images
                if len(reference_images) > 1
                else reference_images[0]
            )
            result = image_client.images.edit(
                model=GRAPHIC_IMAGE_MODEL,
                image=image_input,
                prompt=prompt_text,
                n=GRAPHIC_IMAGE_COUNT,
                size=output_size,
            )
        else:
            result = image_client.images.generate(
                model=GRAPHIC_IMAGE_MODEL,
                prompt=prompt_text,
                n=GRAPHIC_IMAGE_COUNT,
                size=output_size,
            )
    except Exception as error:
        error_name = type(error).__name__
        safe_error = str(error).strip() or "No additional details were returned."
        print(
            "[GRAPHIC IMAGE ERROR] "
            f"type={error_name} model={GRAPHIC_IMAGE_MODEL} "
            f"details={safe_error}",
            flush=True,
        )

        if error_name == "APITimeoutError":
            raise RuntimeError(
                "Image generation timed out after 3 minutes. "
                "Please try again with one clear prompt or a smaller number "
                "of reference images."
            ) from error

        raise RuntimeError(
            f"Image generation failed: {safe_error}"
        ) from error

    result_items = list(getattr(result, "data", None) or [])
    generated_images = []

    for item in result_items:
        encoded = (
            getattr(item, "b64_json", None)
            or (
                item.get("b64_json")
                if isinstance(item, dict)
                else None
            )
        )
        if not encoded:
            continue

        try:
            raw_bytes = base64.b64decode(encoded)
        except Exception:
            continue

        png_bytes = image_bytes_to_png(raw_bytes)
        if not png_bytes:
            continue

        created_at = datetime.now(timezone.utc)
        filename = graphic_image_filename(prompt_text, created_at)
        data_url = (
            "data:image/png;base64,"
            + base64.b64encode(png_bytes).decode()
        )

        generated_images.append({
            "name": filename,
            "filename": filename,
            "data_url": data_url,
            "generated": True,
            "prompt": prompt_text,
            "created_at": created_at.isoformat(),
            "model": GRAPHIC_IMAGE_MODEL,
            "size": output_size,
            "resolution": output_size,
            "mime_type": "image/png",
        })

    if not generated_images:
        raise RuntimeError(
            "OpenAI completed the request but did not return usable image data."
        )

    return generated_images


def generated_image_answer_text(images, regenerated=False):
    """Create the concise assistant text stored beside generated artwork."""
    if not images:
        return "The image could not be generated."

    image = images[0]
    action = "Generated another version" if regenerated else "Created your image"
    details = [
        f"{action}.",
        f"Resolution: {image.get('resolution') or image.get('size') or 'Original'}",
        f"Format: PNG",
    ]
    return "\n".join(details)


def show_generated_image_full_size(image):
    """
    Display the original generated image in a Streamlit dialog.

    This avoids opening a large base64 data URL in a browser tab, which can
    produce a blank page in some browsers.
    """
    data_url = str((image or {}).get("data_url") or "")
    image_bytes, _ = data_url_to_bytes(data_url)

    if not image_bytes:
        st.error("The full-size image data is unavailable.")
        return

    filename = str(
        (image or {}).get("filename")
        or (image or {}).get("name")
        or "Generated Image"
    )

    dialog_factory = getattr(st, "dialog", None)
    if callable(dialog_factory):
        @dialog_factory(filename)
        def _generated_image_dialog():
            st.image(image_bytes, use_container_width=True)

        _generated_image_dialog()
    else:
        # Compatibility fallback for older Streamlit versions.
        st.image(
            image_bytes,
            caption=filename,
            use_container_width=True,
        )


def generated_image_action_key(image, message_index, image_index, action):
    seed = (
        str(image.get("data_url") or "")
        + str(image.get("prompt") or "")
        + str(message_index)
        + str(image_index)
        + action
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
    return f"graphic_{action}_{digest}"


def render_generated_image_actions(images, message_index=None):
    """
    Render equal-size Full Size, Download, and Regenerate controls.

    The displayed image remains a standard HTML image, so desktop users can
    still right-click and use Save Image As or Copy Image.
    """
    generated_images = [
        image
        for image in (images or [])
        if isinstance(image, dict)
        and image.get("generated")
        and str(image.get("data_url") or "").startswith("data:image/")
    ]
    if not generated_images:
        return

    for image_index, image in enumerate(generated_images):
        image_bytes, _ = data_url_to_bytes(image.get("data_url"))
        if not image_bytes:
            continue

        filename = str(
            image.get("filename")
            or image.get("name")
            or "AutoTecPro_Generated_Image.png"
        )
        if not filename.lower().endswith(".png"):
            filename = f"{Path(filename).stem}.png"

        open_key = generated_image_action_key(
            image,
            message_index,
            image_index,
            "open",
        )
        download_key = generated_image_action_key(
            image,
            message_index,
            image_index,
            "download",
        )
        regenerate_key = generated_image_action_key(
            image,
            message_index,
            image_index,
            "regenerate",
        )

        container_key = f"generated_image_actions_{open_key}"

        with st.container(key=container_key):
            st.markdown(
                """
                <style>
                /* Force three genuinely equal columns. */
                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stHorizontalBlock"] {
                    width: 100% !important;
                    display: flex !important;
                    align-items: stretch !important;
                    gap: 10px !important;
                }

                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stHorizontalBlock"]
                > div[data-testid="column"] {
                    flex: 1 1 0 !important;
                    width: 0 !important;
                    min-width: 0 !important;
                    max-width: none !important;
                    padding: 0 !important;
                }

                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stHorizontalBlock"]
                > div[data-testid="column"]
                > div[data-testid="stVerticalBlock"] {
                    width: 100% !important;
                    height: 100% !important;
                    gap: 0 !important;
                }

                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stElementContainer"],
                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stButton"],
                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stDownloadButton"],
                div[class*="st-key-generated_image_actions_"]
                .stButton,
                div[class*="st-key-generated_image_actions_"]
                .stDownloadButton {
                    width: 100% !important;
                    height: 44px !important;
                    min-height: 44px !important;
                    max-height: 44px !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }

                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stButton"] > button,
                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stDownloadButton"] > button,
                div[class*="st-key-generated_image_actions_"]
                .stButton > button,
                div[class*="st-key-generated_image_actions_"]
                .stDownloadButton > button {
                    box-sizing: border-box !important;
                    width: 100% !important;
                    min-width: 100% !important;
                    max-width: 100% !important;
                    height: 44px !important;
                    min-height: 44px !important;
                    max-height: 44px !important;
                    margin: 0 !important;
                    padding: 0 14px !important;
                    border-radius: 9px !important;
                    border: 1px solid rgba(148, 163, 184, 0.30) !important;
                    background: rgba(30, 41, 59, 0.72) !important;
                    background-image: none !important;
                    color: #f8fafc !important;
                    -webkit-text-fill-color: #f8fafc !important;
                    font-family: inherit !important;
                    font-size: 14px !important;
                    font-weight: 650 !important;
                    line-height: 1 !important;
                    box-shadow: none !important;
                    transform: none !important;
                    display: inline-flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    text-align: center !important;
                    white-space: nowrap !important;
                }

                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stButton"] > button:hover,
                div[class*="st-key-generated_image_actions_"]
                div[data-testid="stDownloadButton"] > button:hover,
                div[class*="st-key-generated_image_actions_"]
                .stButton > button:hover,
                div[class*="st-key-generated_image_actions_"]
                .stDownloadButton > button:hover {
                    background: rgba(51, 65, 85, 0.92) !important;
                    background-image: none !important;
                    border-color: rgba(148, 163, 184, 0.48) !important;
                    color: #ffffff !important;
                    -webkit-text-fill-color: #ffffff !important;
                    box-shadow: none !important;
                    transform: none !important;
                }

                div[class*="st-key-generated_image_actions_"] button p {
                    width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    color: inherit !important;
                    -webkit-text-fill-color: inherit !important;
                    font: inherit !important;
                    line-height: 1 !important;
                    text-align: center !important;
                    white-space: nowrap !important;
                }

                @media (max-width: 768px) {
                    div[class*="st-key-generated_image_actions_"]
                    div[data-testid="stHorizontalBlock"] {
                        gap: 6px !important;
                    }

                    div[class*="st-key-generated_image_actions_"]
                    div[data-testid="stButton"] > button,
                    div[class*="st-key-generated_image_actions_"]
                    div[data-testid="stDownloadButton"] > button,
                    div[class*="st-key-generated_image_actions_"]
                    .stButton > button,
                    div[class*="st-key-generated_image_actions_"]
                    .stDownloadButton > button {
                        padding: 0 6px !important;
                        font-size: 12px !important;
                    }
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            open_column, download_column, regenerate_column = st.columns(
                3,
                gap="small",
                vertical_alignment="center",
            )

            with open_column:
                if st.button(
                    "Open Full Size",
                    key=open_key,
                    use_container_width=True,
                    type="secondary",
                ):
                    show_generated_image_full_size(image)

            with download_column:
                st.download_button(
                    "Download PNG",
                    data=image_bytes,
                    file_name=filename,
                    mime="image/png",
                    key=download_key,
                    use_container_width=True,
                    type="secondary",
                )

            with regenerate_column:
                if st.button(
                    "Regenerate",
                    key=regenerate_key,
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state.pending_graphic_regeneration = {
                        "prompt": str(image.get("prompt") or "").strip(),
                    }
                    st.rerun()


def process_pending_graphic_regeneration():
    """Generate another version from a saved image's original prompt."""
    pending = st.session_state.pop(
        "pending_graphic_regeneration",
        None,
    )
    if not pending:
        return False

    prompt_text = str(pending.get("prompt") or "").strip()
    if not prompt_text:
        st.warning("The original generation prompt is unavailable.")
        return False

    try:
        with st.spinner("Creating another image version..."):
            images = generate_graphic_marketing_images(prompt_text, [])
            answer_text = generated_image_answer_text(
                images,
                regenerated=True,
            )
            stored_content = answer_text + serialize_images_marker(images)

            st.session_state.messages.append({
                "role": "assistant",
                "content": stored_content,
            })

            try:
                save_message(
                    st.session_state.conversation_id,
                    "assistant",
                    stored_content,
                )
            except Exception as error:
                st.warning(
                    f"Generated image was not saved to history: {error}"
                )
    except Exception as error:
        st.error(str(error))
        return False

    st.session_state.scroll_to_bottom = True
    st.rerun()
    return True


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



def get_live_context():
    """Return current live application context for every AI request."""
    try:
        toronto_tz = ZoneInfo("America/Toronto")
        now_toronto = datetime.now(toronto_tz)

        return {
            "current_date": now_toronto.strftime("%A, %B %d, %Y"),
            "current_time": now_toronto.strftime("%I:%M:%S %p"),
            "timezone": "America/Toronto",
            "utc_offset": now_toronto.strftime("%z"),
            "iso_datetime": now_toronto.isoformat(),
        }
    except Exception:
        now_utc = datetime.now(timezone.utc)
        return {
            "current_date": now_utc.strftime("%A, %B %d, %Y"),
            "current_time": now_utc.strftime("%I:%M:%S %p"),
            "timezone": "UTC",
            "utc_offset": "+0000",
            "iso_datetime": now_utc.isoformat(),
        }


def build_live_context_text():
    """Create a concise system-supplied live context block."""
    context = get_live_context()

    return (
        "LIVE APPLICATION CONTEXT — supplied by the AutoTecPro app:\n"
        f"- Current date: {context['current_date']}\n"
        f"- Current time: {context['current_time']}\n"
        f"- Time zone: {context['timezone']}\n"
        f"- UTC offset: {context['utc_offset']}\n"
        f"- ISO date/time: {context['iso_datetime']}\n\n"
        "Use this context whenever the user asks for the current date, "
        "current time, today, tomorrow, yesterday, or another relative date. "
        "Do not claim that you cannot access the current time because the app "
        "has supplied it above. For other live information such as weather, "
        "inventory, order status, prices, tracking, or internet news, clearly "
        "state that a separate live API or web-search connection is required "
        "unless that information is included elsewhere in the request."
    )



def build_user_input(prompt_text, uploaded_files):
    content = [
        {
            "type": "input_text",
            "text": build_live_context_text()
        }
    ]

    live_data = get_live_data_for_prompt(prompt_text)
    if live_data is not None:
        content.append({
            "type": "input_text",
            "text": (
                "LIVE DATA RESULT — retrieved by the AutoTecPro application:\n"
                + json.dumps(live_data, ensure_ascii=False, default=str)
                + "\n\nUse this live result exactly as supplied. Mention its source. "
                  "Do not invent any missing fields, status, price, rate, date, "
                  "delivery estimate, or tracking event."
            )
        })

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
    instructions = (
        get_instructions(assistant)
        + "\n\nThe AutoTecPro application may supply LIVE APPLICATION CONTEXT "
          "and LIVE DATA RESULT blocks. Treat those application-supplied blocks "
          "as authoritative. Use web search for current public information, "
          "recent news, recalls, software updates, laws, specifications, or facts "
          "that may have changed. Use file_search first for AutoTecPro internal "
          "technical and sales knowledge. Always name the source of live data. "
          "Never invent a tracking event, exchange rate, weather condition, "
          "or delivery estimate."
    )

    tools = [{"type": "web_search"}]

    if assistant == "🔧 Technical Support":
        tools.insert(
            0,
            {
                "type": "file_search",
                "vector_store_ids": [TECHNICAL_VECTOR_STORE_ID]
            }
        )
    elif assistant == "📈 Sales & Marketing":
        tools.insert(
            0,
            {
                "type": "file_search",
                "vector_store_ids": [SALES_VECTOR_STORE_ID]
            }
        )

    response = client.responses.create(
        model="gpt-5.5",
        instructions=instructions,
        tools=tools,
        input=user_input
    )

    return response.output_text



def is_admin_image_file(uploaded_file):
    mime_type = str(getattr(uploaded_file, "type", "") or "").lower()
    suffix = Path(str(getattr(uploaded_file, "name", "") or "")).suffix.lower()
    return mime_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png"}


def convert_admin_image_to_knowledge_file(uploaded_file, database_choice, admin_context=""):
    """
    Convert an uploaded JPG/PNG reference image into a searchable TXT document.

    OpenAI vector stores are optimized for text-based retrieval. This function
    uses vision once during admin upload to extract visible text, model numbers,
    vehicle/product relationships, and reusable rules. The generated TXT file is
    then uploaded to the selected vector store.

    Returns:
        (file_like_object, extracted_text)
    """
    image_url = normalized_image_data_url(uploaded_file)
    original_name = str(getattr(uploaded_file, "name", "reference_image"))
    database_label = str(database_choice or "Knowledge Base")
    extra_context = str(admin_context or "").strip()

    extraction_instructions = """
You are AutoTecPro's internal knowledge extraction specialist.

Analyze the uploaded reference image carefully and convert it into accurate,
searchable internal knowledge.

Extract only information that is actually visible or strongly supported by the
image. Do not invent missing vehicle years, part numbers, prices, compatibility,
or technical specifications.

Prioritize:
- Document/reference title
- Vehicle make, model, generation, and year range
- Factory radio/SYNC/Uconnect/RPO system
- Screen size and climate-control type
- KVN/factory code/model number
- AutoTecPro part number, SKU, product name, and screen size
- Compatibility rules and visual identification rules
- Troubleshooting steps, labels, warnings, and notes
- Any visible table, comparison, legend, or mapping

Write clean plain text with clear headings and bullet points.
Include the original filename and selected database.
If text is unclear, mark it as uncertain instead of guessing.
Do not output HTML, markdown code fences, or JSON.
"""

    prompt_text = (
        f"Original filename: {original_name}\n"
        f"Selected database: {database_label}\n"
    )
    if extra_context:
        prompt_text += f"Admin context: {extra_context}\n"
    prompt_text += "\nExtract this image into reusable AutoTecPro knowledge."

    response = client.responses.create(
        model="gpt-5.5",
        instructions=extraction_instructions,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
    )

    extracted_text = clean_visible_chat_text(response.output_text)
    if not extracted_text:
        raise ValueError("The image could not be converted into searchable knowledge.")

    final_text = (
        f"AutoTecPro Image Knowledge Record\n"
        f"Original file: {original_name}\n"
        f"Database: {database_label}\n"
        f"Created at: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"{extracted_text}\n"
    )

    output = io.BytesIO(final_text.encode("utf-8"))
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original_name).stem).strip("_")
    output.name = f"{safe_stem or 'image'}_knowledge.txt"
    output.seek(0)

    return output, final_text


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
    """Fast fallback title used before the AI-generated title is available."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    clean = re.sub(r"📎\s*Attached:.*$", "", clean, flags=re.IGNORECASE).strip()
    if not clean:
        return "New Case"

    words = clean.split()
    fallback = " ".join(words[:7]).strip(" .,:;!?-")
    if not fallback:
        return "New Case"
    return fallback[:48]


def history_display_title(title):
    """
    Return a clean sidebar title.

    New chats use their saved AI-generated title. Older raw-message titles are
    compacted for display until they receive an AI-generated title.
    """
    clean = re.sub(r"\s+", " ", str(title or "")).strip()
    clean = re.sub(
        r"📎\s*Attached:.*$",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    if not clean:
        return "New Case"

    lower = clean.lower()

    common_titles = [
        (r"which model supports?.*2013.*(?:dodge|ram)", "2013 RAM Compatibility"),
        (r"which model is it", "Vehicle Model Identification"),
        (r"france.*spain.*world cup", "France vs Spain Odds"),
        (r"what is this", "Image Identification"),
        (r"what are these", "Part Identification"),
        (r"this is the document", "Document Review"),
        (r"extract|extrac", "Document Data Extraction"),
    ]
    for pattern, replacement in common_titles:
        if re.search(pattern, lower):
            return replacement

    if re.fullmatch(r"1Z[A-Z0-9]{16}", clean.upper()):
        return "UPS Package Tracking"

    # Already-clean AI/manual titles remain as saved.
    if len(clean.split()) <= 5 and len(clean) <= 36:
        return clean

    compact = conversation_title_from_text(clean)
    words = compact.split()[:5]
    return " ".join(words)[:36].rstrip(" .,:;!?-") or "New Case"


def generate_ai_conversation_title(first_message, assistant_answer=""):
    """
    Generate a concise ChatGPT-style conversation title.

    Failure is non-fatal: the existing fallback title remains unchanged.
    """
    user_text = re.sub(r"\s+", " ", str(first_message or "")).strip()
    answer_text = re.sub(r"\s+", " ", str(assistant_answer or "")).strip()

    if not user_text:
        return "New Case"

    try:
        response = client.responses.create(
            model="gpt-5.5",
            instructions=(
                "Create a clean professional title for a chat-history sidebar. "
                "Return only the title. Use 2 to 5 words. Do not use emoji. "
                "Do not use quotation marks, markdown, a prefix, or ending "
                "punctuation. Do not repeat the user's full sentence. Summarize "
                "the actual topic or task. Keep it under 36 characters. Preserve "
                "important vehicle models, product names, document types, or "
                "tracking context when useful."
            ),
            input=(
                f"User message: {user_text[:1200]}\n"
                f"Assistant response context: {answer_text[:800]}"
            ),
        )
        title = re.sub(r"\s+", " ", str(response.output_text or "")).strip()
        title = title.strip(" \"'`“”‘’")
        title = re.sub(r"[.!?:;,-]+$", "", title).strip()

        # Safety cleanup: no emoji/symbol decorations and no oversized titles.
        title = re.sub(
            r"[^A-Za-z0-9&/+\- ]+",
            "",
            title,
        )
        title = re.sub(r"\s+", " ", title).strip()

        if title:
            words = title.split()[:5]
            return " ".join(words)[:36].rstrip()
    except Exception:
        pass

    return conversation_title_from_text(user_text)


def update_conversation_ai_title(conversation_id, first_message, assistant_answer=""):
    """Generate and store an AI title once the first answer is complete."""
    if not conversation_id:
        return

    try:
        current = (
            supabase
            .table("conversations")
            .select("title")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        current_title = ""
        if current.data:
            current_title = str(current.data[0].get("title") or "").strip()

        fallback_title = conversation_title_from_text(first_message)
        normalized_message = re.sub(
            r"\s+",
            " ",
            str(first_message or ""),
        ).strip()

        # Recognize both the current fallback and the older raw-message title
        # formats as automatic titles. Manually renamed titles stay untouched.
        legacy_titles = {
            "New Case",
            fallback_title,
            normalized_message[:55].strip(),
            normalized_message[:48].strip(),
            normalized_message[:40].strip(),
        }
        if current_title and current_title not in legacy_titles:
            return

        ai_title = generate_ai_conversation_title(
            first_message,
            assistant_answer,
        )
        if not ai_title:
            return

        supabase.table("conversations").update({
            "title": ai_title,
            "updated_at": now_iso(),
        }).eq("id", conversation_id).execute()
    except Exception:
        # Title generation must never interrupt the conversation.
        pass


def get_conversation_storage_count(username, role=None):
    """
    Count active saved conversations for the signed-in user only.

    Every account has an independent history, including admin accounts.
    Pinned and unpinned active conversations are both included in the
    displayed storage count.
    """
    username = str(username or "").strip()
    if not username:
        return 0

    try:
        result = (
            supabase
            .table("conversations")
            .select("id", count="exact")
            .eq("username", username)
            .or_("archived.is.null,archived.eq.false")
            .execute()
        )
        if result.count is not None:
            return int(result.count)
    except Exception:
        pass

    try:
        rows = safe_select_rows(
            "conversations",
            order_columns=["updated_at", "created_at"],
            limit=5000,
        )
        return len([
            row
            for row in rows
            if str(row.get("username", "")).lower() == username.lower()
            and not (
                row.get("archived") is True
                or str(row.get("archived")).lower() == "true"
            )
        ])
    except Exception:
        return 0


MAX_UNPINNED_CONVERSATIONS_PER_USER = 100


def _detach_learning_reference_before_history_delete(conversation_id):
    """
    Preserve learned knowledge before deleting old chat history.

    Only the optional source_conversation_id link is cleared. The learned
    record, uploaded knowledge file, OpenAI file, and vector-store content
    remain untouched.
    """
    if not conversation_id:
        return

    columns = set(get_table_columns("learned_knowledge"))
    if "source_conversation_id" not in columns:
        return

    try:
        (
            supabase
            .table("learned_knowledge")
            .update({"source_conversation_id": None})
            .eq("source_conversation_id", conversation_id)
            .execute()
        )
    except Exception as error:
        raise RuntimeError(
            "Could not safely preserve learned knowledge before deleting "
            "the oldest conversation. No automatic deletion was performed."
        ) from error


def _delete_old_unpinned_conversation(username, conversation_id):
    """
    Delete one old unpinned conversation belonging to one user account.

    Pinned conversations are protected. Only that conversation and its
    message rows are deleted.
    """
    username = str(username or "").strip()
    if not username or not conversation_id:
        return False

    check = (
        supabase
        .table("conversations")
        .select("id, username, pinned")
        .eq("id", conversation_id)
        .eq("username", username)
        .limit(1)
        .execute()
    )
    rows = list(check.data or [])
    if not rows or bool(rows[0].get("pinned", False)):
        return False

    _detach_learning_reference_before_history_delete(conversation_id)

    (
        supabase
        .table("messages")
        .delete()
        .eq("conversation_id", conversation_id)
        .execute()
    )
    (
        supabase
        .table("conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("username", username)
        .eq("pinned", False)
        .execute()
    )
    return True


def make_room_for_new_conversation(
    username,
    max_unpinned=MAX_UNPINNED_CONVERSATIONS_PER_USER,
):
    """
    Keep at most 100 unpinned conversations for one user.

    Pinned conversations are unlimited, do not count toward the 100 limit,
    and are never automatically deleted. Before a new unpinned conversation
    is created, the oldest unpinned conversation is removed when necessary.
    """
    username = str(username or "").strip()
    if not username:
        raise RuntimeError("A valid username is required to save chat history.")

    try:
        max_unpinned = max(1, int(max_unpinned))
    except (TypeError, ValueError):
        max_unpinned = MAX_UNPINNED_CONVERSATIONS_PER_USER

    result = (
        supabase
        .table("conversations")
        .select("id, username, pinned, created_at, updated_at")
        .eq("username", username)
        .eq("pinned", False)
        .order("created_at", desc=False)
        .execute()
    )

    unpinned_rows = list(result.data or [])
    delete_count = max(0, len(unpinned_rows) - max_unpinned + 1)

    for conversation in unpinned_rows[:delete_count]:
        _delete_old_unpinned_conversation(
            username,
            conversation.get("id"),
        )


def create_conversation(username, assistant_name, first_message=None):
    """Create a new conversation and return its ID."""
    # History is isolated by username. Pinned chats are unlimited; only
    # unpinned chats are limited to the newest 100 for this account.
    make_room_for_new_conversation(username)
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
    Load active conversation history for the signed-in user only.

    Pinned conversations are unlimited and shown first. The newest 100
    unpinned conversations are shown below them. Assistant type does not
    restrict history visibility.
    """
    username = str(username or "").strip()
    if not username:
        return []

    result = (
        supabase
        .table("conversations")
        .select("*")
        .eq("username", username)
        .order("updated_at", desc=True)
        .limit(1000)
        .execute()
    )

    rows = list(result.data or [])

    def is_active(row):
        value = row.get("archived")
        return not (value is True or str(value).lower() == "true")

    active_rows = [row for row in rows if is_active(row)]

    pinned_rows = sorted(
        [
            row
            for row in active_rows
            if bool(row.get("pinned", False))
        ],
        key=lambda row: str(
            row.get("updated_at")
            or row.get("created_at")
            or ""
        ),
        reverse=True,
    )

    normal_rows = sorted(
        [
            row
            for row in active_rows
            if not bool(row.get("pinned", False))
        ],
        key=lambda row: str(
            row.get("updated_at")
            or row.get("created_at")
            or ""
        ),
        reverse=True,
    )[:MAX_UNPINNED_CONVERSATIONS_PER_USER]

    return pinned_rows + normal_rows


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


def _history_datetime(conversation):
    """Return the best available timezone-aware datetime for history grouping."""
    raw_value = (
        conversation.get("updated_at")
        or conversation.get("created_at")
        or ""
    )

    if not raw_value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(raw_value).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _history_group_name(conversation):
    """Group conversations into familiar, mobile-friendly date sections."""
    conversation_time = _history_datetime(conversation)
    if conversation_time is None:
        return "Older"

    now = datetime.now(timezone.utc)
    today = now.date()
    conversation_date = conversation_time.date()
    days_old = (today - conversation_date).days

    if days_old <= 0:
        return "Today"
    if days_old == 1:
        return "Yesterday"
    if days_old <= 7:
        return "Last 7 Days"
    return "Older"


def _history_time_label(conversation):
    """Small secondary label shown beside each saved conversation."""
    conversation_time = _history_datetime(conversation)
    if conversation_time is None:
        return ""

    group_name = _history_group_name(conversation)

    if group_name == "Today":
        return conversation_time.strftime("%I:%M %p").lstrip("0")
    if group_name == "Yesterday":
        return "Yesterday"
    if group_name == "Last 7 Days":
        return conversation_time.strftime("%a")
    return conversation_time.strftime("%b %d")


def render_history_cards(conversations):
    """
    Responsive Streamlit-native conversation history.

    Stability:
    - Keeps existing open, rename, pin, archive, and delete functions.
    - Uses only native Streamlit widgets plus scoped CSS.
    - Does not introduce JavaScript or a second state-management system.
    """
    search_value = str(
        st.session_state.get("history_search_query", "")
    ).strip().lower()

    visible_conversations = []

    for conversation in conversations:
        title = str(conversation.get("title") or "New Case")
        assistant_name = str(conversation.get("assistant") or "")

        if (
            not search_value
            or search_value in title.lower()
            or search_value in assistant_name.lower()
        ):
            visible_conversations.append(conversation)

    pinned_conversations = [
        conversation
        for conversation in visible_conversations
        if conversation.get("pinned")
    ]

    normal_conversations = [
        conversation
        for conversation in visible_conversations
        if not conversation.get("pinned")
    ]

    grouped = {
        "Today": [],
        "Yesterday": [],
        "Last 7 Days": [],
        "Older": [],
    }

    for conversation in normal_conversations:
        grouped[_history_group_name(conversation)].append(conversation)

    recent_conversations = []
    for group_name in ("Today", "Yesterday", "Last 7 Days", "Older"):
        recent_conversations.extend(grouped[group_name])

    sections = [
        ("Pinned", pinned_conversations),
        ("Recents", recent_conversations),
    ]

    if not pinned_conversations and not recent_conversations:
        empty_text = (
            "No matching conversations."
            if search_value
            else "No saved conversations yet."
        )
        st.markdown(
            f'<div class="history-empty-state">{html.escape(empty_text)}</div>',
            unsafe_allow_html=True,
        )
        return

    history_box = st.sidebar.container(
        height=460,
        border=False,
    )

    with history_box:
        for section_name, section_conversations in sections:
            st.markdown(
                (
                    '<div class="history-section-label">'
                    f'{html.escape(section_name)}'
                    '</div>'
                    '<div class="history-section-heading-gap" '
                    'aria-hidden="true"></div>'
                ),
                unsafe_allow_html=True,
            )
            if not section_conversations:
                empty_label = (
                    "No pinned conversations"
                    if section_name == "Pinned"
                    else "No recent conversations"
                )
                st.markdown(
                    (
                        '<div class="history-empty-state">'
                        f'{html.escape(empty_label)}'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )
                continue

            for conversation in section_conversations:
                conversation_id = conversation["id"]
                title = str(
                    conversation.get("title")
                    or "New Case"
                )
                pinned = bool(
                    conversation.get("pinned", False)
                )
                is_current = (
                    str(
                        st.session_state.get(
                            "conversation_id"
                        )
                    )
                    == str(conversation_id)
                )

                # Display the complete saved AI title. CSS keeps it on one
                # line and adds an ellipsis only at the actual row boundary.
                title_short = history_display_title(title)
                time_label = _history_time_label(
                    conversation
                )

                history_label = title_short

                row_state = []
                if is_current:
                    row_state.append("active")
                if pinned:
                    row_state.append("pinned")

                row_suffix = "_".join(row_state) or "normal"

                row = st.container(
                    key=(
                        f"history_row_{row_suffix}_"
                        f"{conversation_id}"
                    )
                )

                with row:
                    if st.button(
                        history_label,
                        key=f"open_{conversation_id}",
                        help=title,
                        use_container_width=True,
                    ):
                        st.session_state.conversation_id = conversation_id
                        st.session_state.messages = load_messages(
                            conversation_id
                        )
                        st.session_state.rename_conversation_id = None
                        st.session_state.scroll_to_bottom = True
                        st.rerun()

                    if time_label:
                        st.markdown(
                            (
                                '<div class="history-row-meta">'
                                f'{html.escape(time_label)}'
                                '</div>'
                            ),
                            unsafe_allow_html=True,
                        )

                    with st.popover(
                        "⋯",
                        help="Conversation actions",
                    ):
                        st.markdown(
                            (
                                '<div class="history-menu-title">'
                                f'{html.escape(title_short)}'
                                '</div>'
                            ),
                            unsafe_allow_html=True,
                        )

                        if st.button(
                            "Rename",
                            key=f"rename_{conversation_id}",
                            use_container_width=True,
                        ):
                            st.session_state.rename_conversation_id = str(
                                conversation_id
                            )
                            st.session_state.rename_conversation_value = title
                            st.rerun()

                        pin_label = (
                            "Unpin chat"
                            if pinned
                            else "Pin chat"
                        )

                        if st.button(
                            pin_label,
                            key=f"pin_{conversation_id}",
                            use_container_width=True,
                        ):
                            try:
                                toggle_pin_conversation(
                                    conversation_id,
                                    not pinned,
                                )
                                st.rerun()
                            except Exception:
                                st.toast(
                                    "Pin needs the pinned column in Supabase."
                                )

                        if st.button(
                            "Archive",
                            key=f"archive_{conversation_id}",
                            use_container_width=True,
                        ):
                            archive_conversation(conversation_id)
                            if (
                                st.session_state.conversation_id
                                == conversation_id
                            ):
                                st.session_state.conversation_id = None
                                st.session_state.messages = []
                            st.rerun()

                        if st.button(
                            "Delete",
                            key=f"delete_{conversation_id}",
                            use_container_width=True,
                        ):
                            delete_conversation(conversation_id)
                            if (
                                st.session_state.conversation_id
                                == conversation_id
                            ):
                                st.session_state.conversation_id = None
                                st.session_state.messages = []
                            st.rerun()


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
            const CONTROLLER_KEY = "__atpGlobalChatDropzoneV2";
            const CHAT_SHELL_SELECTOR =
                'div[class*="st-key-atp_upload_shell_chat_files"]';
            const ACCEPTED_EXTENSIONS =
                [".jpg", ".jpeg", ".png", ".pdf", ".txt"];

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

            function acceptedFiles(fileList) {
                return Array.from(fileList || []).filter((file) => {
                    const name = String(file?.name || "").toLowerCase();
                    return ACCEPTED_EXTENSIONS.some(
                        (extension) => name.endsWith(extension)
                    );
                });
            }

            function setInputFiles(input, files) {
                const transfer = new DataTransfer();
                const seen = new Set();

                // Preserve files already present in the current uploader.
                for (const file of Array.from(input.files || [])) {
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

                const filesSetter = Object.getOwnPropertyDescriptor(
                    parentWindow.HTMLInputElement.prototype,
                    "files"
                )?.set;

                if (filesSetter) {
                    filesSetter.call(input, transfer.files);
                } else {
                    input.files = transfer.files;
                }

                // Dispatch both events because Streamlit/React versions can
                // listen to either one.
                input.dispatchEvent(
                    new parentWindow.Event("input", {
                        bubbles: true,
                        composed: true
                    })
                );
                input.dispatchEvent(
                    new parentWindow.Event("change", {
                        bubbles: true,
                        composed: true
                    })
                );
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
                    setInputFiles(input, files);
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
    st.sidebar.markdown(
        (
            '<div class="history-title">History</div>'
            '<div class="history-heading-gap" aria-hidden="true"></div>'
        ),
        unsafe_allow_html=True,
    )

    try:
        conversations = load_conversations(
            st.session_state.username,
            st.session_state.role
        )

        storage_count = get_conversation_storage_count(
            st.session_state.username,
            st.session_state.role,
        )
        st.sidebar.markdown(
            (
                '<div class="history-storage-card">'
                '<div class="history-storage-label">Storage</div>'
                f'<div class="history-storage-value">'
                f'{storage_count} saved case'
                f'{"s" if storage_count != 1 else ""}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        refresh_col, search_col = st.sidebar.columns(
            [0.17, 0.83],
            gap="medium",
        )

        with refresh_col:
            if st.button(
                "↻",
                key="refresh_history",
                help="Refresh conversations",
                use_container_width=True,
            ):
                st.rerun()

        with search_col:
            st.text_input(
                "Search conversations",
                key="history_search_query",
                placeholder="Search conversations…",
                label_visibility="collapsed",
            )

        # Final history-row color override loaded immediately before the
        # rows are rendered. This prevents older sidebar button CSS from
        # restoring grey backgrounds while the AI is processing.
        st.sidebar.markdown(
            """
            <style>
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"],
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"] > div,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"] div[data-testid="stElementContainer"],
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"] div[data-testid="stButton"],
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"] .stButton {
                background: transparent !important;
                background-color: transparent !important;
                background-image: none !important;
                border-color: transparent !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]
            div[class*="st-key-open_"] button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]
            div[data-testid="stButton"] > button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]
            .stButton > button {
                background: transparent !important;
                background-color: transparent !important;
                background-image: none !important;
                border-color: transparent !important;
                box-shadow: none !important;
                filter: none !important;
            }

            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]:hover
            div[class*="st-key-open_"] button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]:hover
            div[data-testid="stButton"] > button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_"]:hover
            .stButton > button {
                background: rgba(148, 163, 184, 0.10) !important;
                background-color: rgba(148, 163, 184, 0.10) !important;
            }

            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_active_"]
            div[class*="st-key-open_"] button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_active_"]
            div[data-testid="stButton"] > button,
            section[data-testid="stSidebar"]
            div[class*="st-key-history_row_active_"]
            .stButton > button {
                background: rgba(100, 116, 139, 0.34) !important;
                background-color: rgba(100, 116, 139, 0.34) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        render_history_cards(conversations)

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

    st.sidebar.markdown(
        '<div class="sidebar-logout-divider"></div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="sidebar-logout-btn">',
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "↪  Log out",
        key="logout_button",
        use_container_width=True,
    ):
        logout_user()

    st.sidebar.markdown('</div>', unsafe_allow_html=True)


def _admin_upload_fragment_decorator(function):
    """
    Use a fragment when supported so database selection reruns only the
    Upload Knowledge section. Older Streamlit versions safely fall back to
    the original full-page behavior without changing the interface.
    """
    fragment = getattr(st, "fragment", None)
    if callable(fragment):
        return fragment(function)
    return function


@_admin_upload_fragment_decorator
def render_admin_upload_knowledge_tab():
    st.markdown("### Upload Documents to Knowledge Base")
    st.caption(
        "Choose the target database, add optional image context, then upload. "
        "Changing the database no longer reruns the entire Admin Panel."
    )

    database_choice = st.selectbox(
        "Choose database",
        [
            "Technical Support Database",
            "Sales & Marketing Database"
        ],
        key="stable_admin_database_choice"
    )

    admin_context = st.text_area(
        "Optional context for uploaded images",
        placeholder=(
            "Example: This chart is for Ford F-150 2015–2021 and should be "
            "used to identify SYNC version and climate-control type."
        ),
        help=(
            "Optional. This helps the AI interpret reference images accurately. "
            "It is not required for PDF, TXT, or DOCX files."
        ),
        key="stable_admin_upload_context"
    )

    admin_files = managed_file_uploader(
        storage_key="admin_managed_uploads",
        generation_key="admin_managed_upload_generation",
        widget_prefix="admin_knowledge",
        accepted_types=["pdf", "txt", "docx", "jpg", "jpeg", "png"],
        heading="Upload documents or reference images",
    )

    st.caption(
        "Reference images are converted into searchable text before being "
        "added to the knowledge base."
    )

    _admin_upload_left, _admin_upload_center, _admin_upload_right = st.columns(
        [3, 4, 3],
        gap="small",
    )
    with _admin_upload_center:
        admin_upload_submitted = st.button(
            "Upload to Knowledge Base",
            key="stable_admin_knowledge_upload_submit",
            use_container_width=True,
        )

    if admin_upload_submitted:
        if not admin_files:
            st.warning("Please upload at least one document or image.")
        else:
            selected_vector_store_id = (
                TECHNICAL_VECTOR_STORE_ID
                if database_choice == "Technical Support Database"
                else SALES_VECTOR_STORE_ID
            )

            progress = st.progress(0)
            total_files = len(admin_files)

            for index, admin_file in enumerate(admin_files, start=1):
                try:
                    if is_admin_image_file(admin_file):
                        with st.spinner(
                            f"Analyzing image: {admin_file.name}"
                        ):
                            (
                                searchable_file,
                                extracted_text
                            ) = convert_admin_image_to_knowledge_file(
                                admin_file,
                                database_choice,
                                admin_context
                            )

                            file_id = upload_to_vector_store(
                                searchable_file,
                                selected_vector_store_id
                            )

                        st.success(
                            f"Image converted and uploaded: {admin_file.name} "
                            f"| Search file: {searchable_file.name} "
                            f"| File ID: {file_id}"
                        )

                        with st.expander(
                            f"Extracted knowledge — {admin_file.name}"
                        ):
                            st.text(extracted_text)
                    else:
                        file_id = upload_to_vector_store(
                            admin_file,
                            selected_vector_store_id
                        )
                        st.success(
                            f"Uploaded: {admin_file.name} "
                            f"| File ID: {file_id}"
                        )

                except Exception as error:
                    st.error(
                        f"Failed to upload {admin_file.name}: {error}"
                    )

                progress.progress(index / total_files)

            st.info(
                "Upload completed. OpenAI may take a short time to finish "
                "indexing new knowledge before it appears in search results."
            )
            clear_managed_uploads(
                "admin_managed_uploads",
                "admin_managed_upload_generation",
            )


# ============================================================
# Admin Panel
# ============================================================

if assistant == "⚙️ Admin Panel":

    st.subheader("⚙️ Admin Panel")
    st.caption(
        "Manage users, knowledge uploads, AI learning, analytics, "
        "and continuous improvement."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "👥 Users",
        "📚 Upload Knowledge",
        "🧠 AI Learning",
        "🚗 Vehicle Analytics",
        "📦 Product Analytics",
        "🔧 Technical Analytics",
        "📊 AI Analytics",
        "📈 Learning Analytics",
        "🔌 Live Integrations"
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

        delete_success = st.session_state.pop(
            "permanent_delete_success_message",
            None
        )
        if delete_success:
            st.success(delete_success)

        try:
            users = (
                supabase
                .table("users")
                .select("*")
                .order("username")
                .execute()
                .data
            ) or []
        except Exception as error:
            users = []
            st.error(f"Unable to load users: {error}")

        for user in users:
            username_value = str(user.get("username") or "")
            role_value = str(user.get("role") or "staff")
            active_value = bool(user.get("active"))
            current_note = (
                " | Current User"
                if username_value == st.session_state.username
                else ""
            )
            st.write(
                f"**{username_value}** | {role_value} | "
                f"Active: {active_value}{current_note}"
            )

        st.markdown("---")
        st.markdown("### Add / Update User")

        new_username = st.text_input(
            "Username",
            key="stable_admin_username"
        )
        new_password = st.text_input(
            "Password",
            type="password",
            key="stable_admin_password"
        )
        new_role = st.selectbox(
            "Role",
            ["staff", "admin"],
            key="stable_admin_role"
        )
        new_active = st.checkbox(
            "Active",
            value=True,
            key="stable_admin_active"
        )

        if st.button("Save User", key="stable_admin_save_user"):
            if new_username and new_password:
                try:
                    clean_username = new_username.strip()
                    existing = (
                        supabase
                        .table("users")
                        .select("*")
                        .eq("username", clean_username)
                        .execute()
                        .data
                    )

                    if existing:
                        (
                            supabase
                            .table("users")
                            .update({
                                "password": new_password,
                                "role": new_role,
                                "active": new_active
                            })
                            .eq("username", clean_username)
                            .execute()
                        )
                        st.success("User updated successfully.")
                    else:
                        (
                            supabase
                            .table("users")
                            .insert({
                                "username": clean_username,
                                "password": new_password,
                                "role": new_role,
                                "active": new_active
                            })
                            .execute()
                        )
                        st.success("User added successfully.")

                    time.sleep(0.4)
                    st.rerun()

                except Exception as error:
                    st.error(f"Unable to save user: {error}")
            else:
                st.warning("Please enter username and password.")

        st.markdown("---")
        st.markdown("### Permanently Delete User")
        st.caption(
            "This uses the database function delete_user_permanently and "
            "removes the selected account and all associated records."
        )

        deletable_usernames = [
            str(user.get("username"))
            for user in users
            if user.get("username")
            and str(user.get("username")) != st.session_state.username
        ]

        if not deletable_usernames:
            st.info("There are no other users available to delete.")
        else:
            with st.form(
                "stable_permanent_delete_user_form",
                clear_on_submit=True
            ):
                selected_delete_username = st.selectbox(
                    "Select user",
                    ["— Select a user —"] + deletable_usernames
                )

                typed_delete_username = st.text_input(
                    "Type the username exactly to confirm"
                )

                confirm_permanent_delete = st.checkbox(
                    "I understand this deletion is permanent and cannot be undone."
                )

                permanent_delete_submitted = st.form_submit_button(
                    "Permanently Delete User"
                )

            if permanent_delete_submitted:
                if selected_delete_username == "— Select a user —":
                    st.warning("Please select a user to delete.")

                elif typed_delete_username.strip() != selected_delete_username:
                    st.warning(
                        "The confirmation username does not match "
                        "the selected user."
                    )

                elif not confirm_permanent_delete:
                    st.warning(
                        "Please confirm that you understand this action "
                        "is permanent."
                    )

                else:
                    selected_rows = [
                        user
                        for user in users
                        if str(user.get("username"))
                        == selected_delete_username
                    ]
                    selected_user = selected_rows[0] if selected_rows else {}

                    active_admins = [
                        user
                        for user in users
                        if str(user.get("role") or "").lower() == "admin"
                        and bool(user.get("active"))
                    ]

                    if (
                        str(selected_user.get("role") or "").lower() == "admin"
                        and bool(selected_user.get("active"))
                        and len(active_admins) <= 1
                    ):
                        st.error(
                            "The final active administrator account "
                            "cannot be deleted."
                        )
                    else:
                        try:
                            admin_supabase = get_supabase_admin_client()

                            result = (
                                admin_supabase
                                .rpc(
                                    "delete_user_permanently",
                                    {
                                        "p_requesting_username":
                                            st.session_state.username,
                                        "p_target_username":
                                            selected_delete_username,
                                    },
                                )
                                .execute()
                            )

                            result_data = result.data
                            deletion_confirmed = True

                            if isinstance(result_data, dict):
                                deletion_confirmed = bool(
                                    result_data.get("success", True)
                                )
                            elif (
                                isinstance(result_data, list)
                                and result_data
                                and isinstance(result_data[0], dict)
                            ):
                                deletion_confirmed = bool(
                                    result_data[0].get("success", True)
                                )

                            if not deletion_confirmed:
                                raise RuntimeError(
                                    "The database did not confirm "
                                    "successful deletion."
                                )

                            st.session_state[
                                "permanent_delete_success_message"
                            ] = (
                                f"User '{selected_delete_username}' and "
                                "all associated records were permanently deleted."
                            )
                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Permanent deletion failed: {error}"
                            )

    with tab2:
        render_admin_upload_knowledge_tab()

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



    with tab9:
        st.markdown("### 🔌 Live Integrations")
        st.caption(
            "Connection status only. Secret values are never displayed. "
            "Missing credentials do not crash the app."
        )

        for service_name, connected, requirement in live_integration_statuses():
            status_text = "✅ Connected / Available" if connected else "❌ Not configured"
            st.write(f"**{service_name}** — {status_text}")
            st.caption(f"Configuration: {requirement}")

        st.markdown("---")
        st.markdown("#### Required Streamlit secret names")
        st.code(
            """UPS_CLIENT_ID = ""
UPS_CLIENT_SECRET = ""

CANADA_POST_USERNAME = ""
CANADA_POST_PASSWORD = """"",
            language="toml",
        )

        st.info(
            "OpenAI web search, Open-Meteo weather, and Frankfurter exchange "
            "rates are available without additional secrets. UPS and Canada "
            "Post tracking become active after their credentials are added."
        )



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

    uploaded_files = managed_file_uploader(
        storage_key="chat_managed_uploads",
        generation_key="chat_managed_upload_generation",
        widget_prefix="chat_files",
        accepted_types=["jpg", "jpeg", "png", "pdf", "txt"],
        heading="📎 Attach files or photos",
    )

    st.caption("Drag and drop files anywhere in the chat, or paste a screenshot with Ctrl+V.")
    install_global_chat_file_dropzone()

    for message_index, msg in enumerate(st.session_state.messages):
        render_chat_message(
            msg["role"],
            msg["content"],
            message_index=message_index,
        )

    # Regenerate is processed after existing messages render, preserving the
    # current conversation and adding a new assistant image message.
    if assistant == "🎨 Graphic Marketing":
        process_pending_graphic_regeneration()

    st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)
    if st.session_state.get("scroll_to_bottom"):
        auto_scroll_to_latest()
        st.session_state.scroll_to_bottom = False

    install_browser_voice_dictation()
    install_chat_composer_autogrow()
    install_composer_width_safety_css()
    prompt = st.chat_input("Message AutoTecPro AI...")

    if prompt:
        user_display = clean_visible_chat_text(prompt)

        # Managed uploads are SHA-256 deduplicated and are cleared
        # immediately after this message is completed.
        effective_uploaded_files = list(uploaded_files or [])

        uploaded_image_previews = get_uploaded_image_previews(
            effective_uploaded_files
        )

        if effective_uploaded_files:
            file_names = ", ".join(
                [file.name for file in effective_uploaded_files]
            )
            user_display += f"\n\n📎 Attached: {file_names}"


        user_content_to_save = (
            user_display
            + serialize_images_marker(uploaded_image_previews)
        )

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

        generated_images = []
        is_graphic_generation = (
            assistant == "🎨 Graphic Marketing"
            and is_graphic_image_generation_request(
                prompt,
                effective_uploaded_files,
            )
        )

        if is_graphic_generation:
            response_start_time = time.time()
            try:
                with st.spinner("Creating your image..."):
                    generated_images = generate_graphic_marketing_images(
                        prompt,
                        effective_uploaded_files,
                    )
                answer = generated_image_answer_text(generated_images)
            except Exception as error:
                generated_images = []
                answer = (
                    "Image generation was not completed.\n\n"
                    + str(error)
                )
                st.error(str(error))

            response_time = round(time.time() - response_start_time, 2)
            tokens_used = None
        else:
            with st.spinner("Searching AutoTecPro knowledge base..."):
                response_start_time = time.time()
                answer = ask_ai(prompt, effective_uploaded_files)
                answer = clean_visible_chat_text(answer)
                response_time = round(time.time() - response_start_time, 2)
                tokens_used = None

        assistant_content_to_save = (
            answer
            + serialize_images_marker(generated_images)
        )

        render_chat_message(
            "assistant",
            answer,
            generated_images,
            message_index=len(st.session_state.messages),
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_content_to_save
        })

        try:
            save_message(
                st.session_state.conversation_id,
                "assistant",
                assistant_content_to_save,
            )
        except Exception as e:
            st.warning(f"AI answer was not saved to history: {e}")

        # Generate a concise ChatGPT-style title after the first completed answer.
        if len([
            item for item in st.session_state.messages
            if item.get("role") == "user"
        ]) == 1:
            update_conversation_ai_title(
                st.session_state.conversation_id,
                prompt,
                answer,
            )

        # Continuous Learning:
        # Automatically extracts reusable knowledge, detects duplicates,
        # improves existing records, and syncs final knowledge to OpenAI Vector Store.
        learning_result = None
        if not is_graphic_generation:
            try:
                learning_result = auto_learn_from_latest_answer(
                    prompt,
                    answer,
                    assistant,
                )
                if learning_result and learning_result.get("learned"):
                    mode = learning_result.get("mode", "saved")
                    st.toast(
                        f"AI learned from this case ({mode}).",
                        icon="🧠",
                    )
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
        clear_managed_uploads(
            "chat_managed_uploads",
            "chat_managed_upload_generation",
        )

        st.session_state.scroll_to_bottom = True
        st.rerun()

# ============================================================
# FINAL HISTORY NAVIGATION OVERRIDE
# Matches the AI Workspace navigation style without changing logic.
# ============================================================
st.markdown(
    """
    <style>
    /* The history list should behave like the workspace navigation:
       transparent by default, one subtle hover/active surface only. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"] {
        position: relative !important;
        width: 100% !important;
        min-height: 42px !important;
        margin: 0 0 5px 0 !important;
        padding: 0 !important;
        border: 0 !important;
        outline: 0 !important;
        border-radius: 11px !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow: visible !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    > div[data-testid="stVerticalBlock"],
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    > div[data-testid="stVerticalBlock"] > div,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="stElementContainer"],
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    div[data-testid="stButton"],
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton {
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    /* Conversation title — same clean row treatment as workspace items. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton > button,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    button[kind="secondary"] {
        display: flex !important;
        width: 100% !important;
        min-height: 42px !important;
        height: 42px !important;
        margin: 0 !important;
        padding: 0 42px 0 12px !important;
        align-items: center !important;
        justify-content: flex-start !important;
        border: 0 !important;
        outline: 0 !important;
        border-radius: 11px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: #e8edf5 !important;
        -webkit-text-fill-color: #e8edf5 !important;
        box-shadow: none !important;
        filter: none !important;
        transform: none !important;
        text-align: left !important;
        font-size: 14px !important;
        font-weight: 560 !important;
        line-height: 1.2 !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton > button::before,
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton > button::after {
        content: none !important;
        display: none !important;
        background: none !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton > button div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .stButton > button div[data-testid="stMarkdownContainer"] p {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Only hover or the currently opened conversation receives a surface. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover
    .stButton > button {
        background: rgba(148, 163, 184, 0.10) !important;
        background-color: rgba(148, 163, 184, 0.10) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_active_"]
    .stButton > button {
        background: rgba(100, 116, 139, 0.34) !important;
        background-color: rgba(100, 116, 139, 0.34) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Keep metadata visually light and inside the clean row. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    .history-row-meta {
        position: absolute !important;
        left: 12px !important;
        bottom: 3px !important;
        margin: 0 !important;
        padding: 0 !important;
        color: #7f8b9d !important;
        font-size: 9.5px !important;
        line-height: 1 !important;
        pointer-events: none !important;
        display: none !important;
    }

    /* Three-dot action remains overlaid, never creates a second grey box. */
    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    [data-testid="stPopover"] {
        position: absolute !important;
        top: 50% !important;
        right: 7px !important;
        z-index: 20 !important;
        width: 28px !important;
        height: 28px !important;
        margin: 0 !important;
        padding: 0 !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    [data-testid="stPopover"] button {
        width: 28px !important;
        min-width: 28px !important;
        max-width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        max-height: 28px !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        background-color: transparent !important;
        background-image: none !important;
        color: #cbd5e1 !important;
        -webkit-text-fill-color: #cbd5e1 !important;
        box-shadow: none !important;
        transform: none !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }

    section[data-testid="stSidebar"] [class*="st-key-history_row_"]
    [data-testid="stPopover"] button:hover {
        background: rgba(148, 163, 184, 0.16) !important;
        background-color: rgba(148, 163, 184, 0.16) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    @media (hover: hover) and (pointer: fine) {
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
            transition: opacity 0.14s ease !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-history_row_"]:hover
        [data-testid="stPopover"],
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]
        [data-testid="stPopover"]:has([aria-expanded="true"]) {
            opacity: 1 !important;
            visibility: visible !important;
            pointer-events: auto !important;
        }
    }

    /* Touch devices need the action control available because hover is absent. */
    @media (hover: none), (pointer: coarse) {
        section[data-testid="stSidebar"] [class*="st-key-history_row_"]
        [data-testid="stPopover"] {
            opacity: 1 !important;
            visibility: visible !important;
            pointer-events: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final isolated AutoTecPro AI heading spacing override.
# This changes only the heading size and the space above/below it.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] .workspace-title {
        display: block !important;
        width: 100% !important;
        margin-top: 18px !important;
        margin-right: 0 !important;
        margin-bottom: 18px !important;
        margin-left: 0 !important;
        padding: 0 !important;
        color: #f8fafc !important;
        font-size: 21px !important;
        font-weight: 850 !important;
        line-height: 1.2 !important;
        letter-spacing: -0.2px !important;
        text-align: left !important;
        clear: both !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] .workspace-title {
            margin-top: 16px !important;
            margin-bottom: 16px !important;
            font-size: 20px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Structural spacing below History / Pinned / Recents headings.
# The spacing is created by real rendered spacer elements, not collapsing margins.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] .history-heading-gap {
        display: block !important;
        width: 100% !important;
        height: 14px !important;
        min-height: 14px !important;
        margin: 0 !important;
        padding: 0 !important;
        flex: 0 0 14px !important;
        pointer-events: none !important;
    }

    section[data-testid="stSidebar"] .history-section-heading-gap {
        display: block !important;
        width: 100% !important;
        height: 12px !important;
        min-height: 12px !important;
        margin: 0 !important;
        padding: 0 !important;
        flex: 0 0 12px !important;
        pointer-events: none !important;
    }

    /* Remove competing bottom margins; the real spacers control the gap. */
    section[data-testid="stSidebar"] .history-title,
    section[data-testid="stSidebar"] .history-section-label {
        margin-bottom: 0 !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] .history-heading-gap {
            height: 13px !important;
            min-height: 13px !important;
            flex-basis: 13px !important;
        }

        section[data-testid="stSidebar"] .history-section-heading-gap {
            height: 11px !important;
            min-height: 11px !important;
            flex-basis: 11px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final authenticated main-page spacing cleanup.
# Collapses invisible style-only Streamlit wrappers that otherwise create
# large blank gaps between the AutoTecPro AI header and each page body.
st.markdown(
    """
    <style>
    /* Style-only markdown elements do not need layout height.
       Use selectors compatible with current and older Streamlit DOM versions. */
    [data-testid="stMainBlockContainer"]
    div[data-testid="stElementContainer"]:has(style),
    [data-testid="stAppViewContainer"]
    div[data-testid="stElementContainer"]:has(style),
    .block-container
    div[data-testid="stElementContainer"]:has(style) {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        flex: 0 0 0 !important;
    }

    /* Keep a clean, modest gap below the main AutoTecPro AI header. */
    [data-testid="stMainBlockContainer"] .app-header,
    [data-testid="stAppViewContainer"] .app-header,
    .block-container .app-header {
        margin-bottom: 14px !important;
    }

    /* Prevent the first page card from adding another large top gap. */
    [data-testid="stMainBlockContainer"] .assistant-section-card,
    [data-testid="stAppViewContainer"] .assistant-section-card,
    .block-container .assistant-section-card {
        margin-top: 0 !important;
    }

    /* Admin heading begins directly below the main header. */
    [data-testid="stMainBlockContainer"] h2:first-of-type,
    [data-testid="stAppViewContainer"] h2:first-of-type,
    .block-container h2:first-of-type {
        margin-top: 0 !important;
    }

    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] .app-header,
        [data-testid="stAppViewContainer"] .app-header,
        .block-container .app-header {
            margin-bottom: 12px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final isolated Pinned / Recents text alignment.
# This affects only history-row titles and does not change row actions or colors.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"] {
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"] .stButton {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"]
    .stButton > button {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        min-width: 0 !important;
        padding-right: 42px !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"]
    div[class*="st-key-open_"]
    .stButton > button
    div[data-testid="stMarkdownContainer"] p {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Final Pinned / Recents left-alignment and single-line title display.
# This targets the actual keyed Streamlit title buttons at the end of the file.
st.markdown(
    """
    <style>
    /* Remove the old pin-icon indentation so both sections share one left edge. */
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_pinned_"]::before,
    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_active_pinned_"]::before {
        display: none !important;
        content: none !important;
        width: 0 !important;
    }

    /* Actual keyed title-button wrapper. */
    section[data-testid="stSidebar"]
    div[class*="st-key-open_"],
    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] .stButton,
    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] div[data-testid="stButton"] {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] .stButton > button,
    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] div[data-testid="stButton"] > button {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        height: 36px !important;
        min-height: 36px !important;
        margin: 0 !important;
        padding: 0 40px 0 8px !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] .stButton > button *,
    section[data-testid="stSidebar"]
    div[class*="st-key-open_"] div[data-testid="stButton"] > button * {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    section[data-testid="stSidebar"]
    div[class*="st-key-history_row_"] {
        text-align: left !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


