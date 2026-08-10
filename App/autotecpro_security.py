"""AutoTecPro AI security primitives.

Pure-Python, dependency-free helpers kept outside the Streamlit app so password
storage/verification can be tested independently from UI, Supabase, OpenAI, and
other production integrations.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass

PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 310_000
PASSWORD_SALT_BYTES = 16
MIN_PASSWORD_HASH_ITERATIONS = 210_000
MAX_PASSWORD_HASH_ITERATIONS = 5_000_000


@dataclass(frozen=True)
class PasswordVerification:
    valid: bool
    legacy_plaintext: bool = False


def _decode_b64(value: str) -> bytes:
    value = str(value or "")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def parse_password_hash(stored_value: str):
    """Return (rounds, salt, digest) for a valid app hash, else None."""
    value = str(stored_value or "")
    parts = value.split("$")
    if len(parts) != 4 or parts[0] != PASSWORD_HASH_SCHEME:
        return None
    try:
        rounds = int(parts[1])
        if not (MIN_PASSWORD_HASH_ITERATIONS <= rounds <= MAX_PASSWORD_HASH_ITERATIONS):
            return None
        salt = _decode_b64(parts[2])
        digest = _decode_b64(parts[3])
    except Exception:
        return None
    if len(salt) < 12 or len(digest) != 32:
        return None
    return rounds, salt, digest


def is_password_hash(stored_value: str) -> bool:
    return parse_password_hash(stored_value) is not None


def hash_password(password: str, *, iterations: int = PASSWORD_HASH_ITERATIONS) -> str:
    password_text = str(password or "")
    if not password_text:
        raise ValueError("Password cannot be empty.")
    rounds = max(MIN_PASSWORD_HASH_ITERATIONS, int(iterations or PASSWORD_HASH_ITERATIONS))
    if rounds > MAX_PASSWORD_HASH_ITERATIONS:
        raise ValueError("Password hash iteration count is too high.")
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password_text.encode("utf-8"), salt, rounds
    )
    return "$".join((
        PASSWORD_HASH_SCHEME,
        str(rounds),
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    ))


def verify_password(password: str, stored_value: str) -> PasswordVerification:
    """Verify PBKDF2 hashes and support one-time migration from legacy plaintext."""
    password_text = str(password or "")
    parsed = parse_password_hash(stored_value)
    if parsed is None:
        return PasswordVerification(
            valid=hmac.compare_digest(password_text, str(stored_value or "")),
            legacy_plaintext=True,
        )
    rounds, salt, expected = parsed
    actual = hashlib.pbkdf2_hmac(
        "sha256", password_text.encode("utf-8"), salt, rounds
    )
    return PasswordVerification(valid=hmac.compare_digest(actual, expected))


# Process-wide failed-login throttle. This supplements (not replaces) any reverse
# proxy/WAF rate limiting and requires no database schema change.
_LOGIN_LOCK = threading.Lock()
_LOGIN_FAILURES = {}
_LOGIN_WINDOW_SECONDS = 600
_LOGIN_MAX_FAILURES = 5
_LOGIN_MAX_BACKOFF_SECONDS = 60


def _login_key(username: str) -> str:
    return str(username or "").strip().casefold()[:160]


def _prune_login_failures(now: float) -> None:
    cutoff = now - _LOGIN_WINDOW_SECONDS
    stale = []
    for key, values in list(_LOGIN_FAILURES.items()):
        recent = [float(ts) for ts in values if float(ts) >= cutoff]
        if recent:
            _LOGIN_FAILURES[key] = recent
        else:
            stale.append(key)
    for key in stale:
        _LOGIN_FAILURES.pop(key, None)


def login_rate_limit_status(username: str, *, now: float | None = None):
    """Return (allowed, retry_after_seconds) for a username.

    After five failures within ten minutes, exponential backoff is enforced.
    State is process-wide so separate browser sessions cannot trivially bypass it.
    """
    key = _login_key(username)
    current = float(time.monotonic() if now is None else now)
    if not key:
        return True, 0.0
    with _LOGIN_LOCK:
        _prune_login_failures(current)
        failures = list(_LOGIN_FAILURES.get(key) or [])
        if len(failures) < _LOGIN_MAX_FAILURES:
            return True, 0.0
        exponent = min(6, len(failures) - _LOGIN_MAX_FAILURES)
        backoff = min(_LOGIN_MAX_BACKOFF_SECONDS, 2 ** exponent)
        retry_at = failures[-1] + float(backoff)
        remaining = retry_at - current
        return (remaining <= 0.0), max(0.0, remaining)


def record_login_failure(username: str, *, now: float | None = None) -> None:
    key = _login_key(username)
    if not key:
        return
    current = float(time.monotonic() if now is None else now)
    with _LOGIN_LOCK:
        _prune_login_failures(current)
        values = list(_LOGIN_FAILURES.get(key) or [])
        values.append(current)
        _LOGIN_FAILURES[key] = values[-32:]


def clear_login_failures(username: str) -> None:
    key = _login_key(username)
    if not key:
        return
    with _LOGIN_LOCK:
        _LOGIN_FAILURES.pop(key, None)
