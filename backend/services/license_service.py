# -*- coding: utf-8 -*-
"""
DocClean License Key System
============================
License key verification for overseas distribution.

License tiers:
  free       — Basic features (upload/convert/download/edit), no key needed
  pro        — Advanced features (RAG knowledge base, AI Q&A, batch processing)
  enterprise — All features (including book compiler), no limits

Key format: DOCLEAN-<payload_b64>-<signature_b64>
  payload  = base64url(json)  e.g. {"t":"pro","e":"2026-12-31","c":"user@example.com"}
  signature = base64url(HMAC-SHA256(payload, SECRET))

License file: backend/license.json (auto-generated after API activation)
"""
import os
import json
import hmac
import hashlib
import base64
import time
from datetime import datetime
from config import BASE_DIR

# ========== SECRET KEY ==========
# Set via DOCLEAN_LICENSE_SECRET environment variable.
# Generate one: python -c "import secrets; print(secrets.token_hex(32))"
_SECRET = os.environ.get("DOCLEAN_LICENSE_SECRET", "").encode("utf-8")
if not _SECRET:
    raise RuntimeError(
        "DOCLEAN_LICENSE_SECRET environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

# ========== License file path ==========
LICENSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "license.json")

# ========== Feature tier definitions ==========
FEATURE_TIERS = {
    # Basic — always free
    "upload": "free",
    "convert": "free",
    "download": "free",
    "editor": "free",
    "pdf_export": "free",
    "tree_view": "free",
    # Advanced — Pro
    "knowledge_base": "pro",
    "rag_search": "pro",
    "ai_qa": "pro",
    "batch_process": "pro",
    # Enterprise
    "book_compiler": "enterprise",
    "api_access": "enterprise",
}


def _b64url_encode(data: bytes) -> str:
    """Base64URL encode (strip padding, replace +/ with -_)"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64URL decode (restore padding)"""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def generate_license_key(license_type: str, expiry_date: str, customer_email: str) -> str:
    """
    Generate a license key (used by seller only).

    Args:
        license_type: "pro" or "enterprise"
        expiry_date: expiry date, e.g. "2026-12-31"
        customer_email: customer email address

    Returns:
        License key string, e.g. "DOCLEAN-eyJ0IjoicHJvIi..."
    """
    payload = {
        "t": license_type,
        "e": expiry_date,
        "c": customer_email,
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))

    sig = hmac.new(_SECRET, payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"DOCLEAN-{payload_b64}.{sig_b64}"


def verify_license_key(key: str) -> dict | None:
    """
    Verify a license key's validity.

    Args:
        key: License key string (format: DOCLEAN-<payload_b64>.<sig_b64>)

    Returns:
        Valid → {"type": "pro", "expiry": "2026-12-31", "customer": "user@example.com"}
        Invalid → None
    """
    if not key or not key.startswith("DOCLEAN-"):
        return None

    try:
        after_prefix = key[len("DOCLEAN-"):]
        parts = after_prefix.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_part, sig_part = parts
    except Exception:
        return None

    expected_sig = hmac.new(_SECRET, payload_part.encode("ascii"), hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if expected_sig_b64 != sig_part:
        return None

    try:
        payload_json = _b64url_decode(payload_part).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        return None

    expiry_str = payload.get("e", "")
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            if expiry_date < datetime.now():
                return None
        except ValueError:
            return None

    return {
        "type": payload.get("t", "free"),
        "expiry": expiry_str,
        "customer": payload.get("c", "unknown"),
    }


def load_license() -> dict:
    """
    Load activated license info from local file.

    Returns:
        {
            "activated": True/False,
            "type": "free" / "pro" / "enterprise",
            "expiry": "2026-12-31",
            "customer": "user@example.com",
            "activated_at": 1715000000.0,
        }
    """
    default = {
        "activated": False,
        "type": "free",
        "expiry": "",
        "customer": "",
        "activated_at": 0,
    }

    if not os.path.exists(LICENSE_FILE):
        return default

    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        type_ = data.get("type", "free")
        if type_ != "free":
            expiry = data.get("expiry", "")
            if expiry:
                try:
                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
                    if expiry_date < datetime.now():
                        save_license({"activated": False, "type": "free", "expiry": "", "customer": "", "activated_at": 0})
                        return default
                except ValueError:
                    pass
        return {
            "activated": data.get("activated", False),
            "type": type_,
            "expiry": data.get("expiry", ""),
            "customer": data.get("customer", ""),
            "activated_at": data.get("activated_at", 0),
        }
    except Exception:
        return default


def save_license(info: dict):
    """Save license info to local file."""
    try:
        file_path = os.path.abspath(LICENSE_FILE)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[License] Failed to save license: {e}")


def activate_license(key: str) -> tuple[bool, str]:
    """
    Activate a license key.

    Returns:
        (success, message)
    """
    license_info = verify_license_key(key)
    if not license_info:
        return False, "Invalid license key. Please check and try again."

    save_data = {
        "activated": True,
        "type": license_info["type"],
        "expiry": license_info["expiry"],
        "customer": license_info["customer"],
        "activated_at": time.time(),
    }
    save_license(save_data)
    return True, f"License activated successfully — {license_info['type'].upper()} tier"


def check_feature(feature_name: str) -> bool:
    """
    Check if a feature is available under the current license.

    Args:
        feature_name: feature name (e.g. "rag_search", "book_compiler")

    Returns:
        True = available, False = upgrade required
    """
    required_tier = FEATURE_TIERS.get(feature_name, "free")
    if required_tier == "free":
        return True

    license_info = load_license()
    current_tier = license_info.get("type", "free") if license_info.get("activated") else "free"

    tier_levels = {"free": 0, "pro": 1, "enterprise": 2}
    return tier_levels.get(current_tier, 0) >= tier_levels.get(required_tier, 0)


def get_license_status() -> dict:
    """Get current license status for frontend display."""
    info = load_license()
    return {
        "activated": info["activated"],
        "type": info["type"],
        "expiry": info["expiry"],
        "customer": info["customer"],
        "features": {
            name: check_feature(name)
            for name in FEATURE_TIERS
        },
    }
