# -*- coding: utf-8 -*-
"""
Lemon Squeezy Webhook Integration
==================================
Handles incoming webhook events from Lemon Squeezy for automated license key management.

Events:
  - order_created          -> Generate a license key and store it
  - subscription_cancelled -> Revoke the customer's license key
  - order_refunded         -> Revoke the customer's license key

License keys use the same format as license_service.py:
  DOCLEAN-<payload_b64>.<signature_b64>

Storage: backend/data/licenses.json  (JSON keyed by customer email)
"""

import os
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from config import BASE_DIR
from services.license_service import generate_license_key, verify_license_key

# ── Blueprint ──────────────────────────────────────────────────────────
lemon_bp = Blueprint("lemon", __name__)

# ── Configuration ──────────────────────────────────────────────────────
LEMON_SECRET = os.environ.get("LEMON_SQUEEZY_SECRET", "")

LICENSES_FILE = os.path.join(BASE_DIR, "backend", "data", "licenses.json")


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

def _load_licenses():
    """
    Load all stored licenses from the JSON file.
    Returns an empty dict if the file does not exist or is corrupted.
    """
    directory = os.path.dirname(LICENSES_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(LICENSES_FILE):
        return {}
    try:
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {}


def _save_licenses(licenses):
    """
    Persist the licenses dict to the JSON file.
    Creates the parent directory if needed.
    """
    directory = os.path.dirname(LICENSES_FILE)
    os.makedirs(directory, exist_ok=True)
    with open(LICENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, ensure_ascii=False, indent=2)


def _verify_webhook_signature(raw_body, signature_header):
    """
    Verify the Lemon Squeezy webhook signature.

    Lemon Squeezy signs the raw request body with HMAC-SHA256 using your
    webhook signing secret.  The result is sent in the X-Signature header
    as a lowercase hex string.

    Returns:
        True  — signature matches (or verification is disabled)
        False — signature is missing or does not match
    """
    if not LEMON_SECRET:
        # Development / testing mode — skip verification when secret is not configured
        return True

    if not signature_header:
        return False

    computed = hmac.new(
        LEMON_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed, signature_header)


def _determine_tier(variant_name, product_name):
    """
    Map a Lemon Squeezy product / variant name to a DocClean license tier.

    Matching is case-insensitive keyword-based:
      "enterprise"  -> enterprise
      "pro"          -> pro  (or "professional")
      everything else -> pro  (safe default)
    """
    combined = f"{variant_name or ''} {product_name or ''}".lower()
    if "enterprise" in combined:
        return "enterprise"
    # 'pro' also catches 'professional' because it contains the substring
    return "pro"


def _calculate_expiry(attributes):
    """
    Determine the license expiry date from webhook order data.

    Priority:
      1. Subscription renewal date  (renews_at)
      2. 1 year from now             (safe default for one-time / annual)
    """
    # If Lemon Squeezy provides a subscription renewal date, use it
    renews_at = attributes.get("renews_at")
    if renews_at:
        try:
            # Parses ISO-8601 date string, e.g. "2027-05-13T00:00:00Z"
            dt = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    # Fallback: 1 year from now
    return (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")


def _extract_customer_email(attributes):
    """
    Extract the customer email from webhook attributes.

    Tries multiple field names used by Lemon Squeezy:
      user_email, email, customer_email
    """
    for field in ("user_email", "email", "customer_email"):
        value = attributes.get(field, "").strip()
        if value:
            return value
    return ""


def _extract_variant_and_product(attributes):
    """
    Extract variant name and product name from webhook order data.
    """
    variant_name = ""
    product_name = ""

    # Lemon Squeezy typically nests variant/product inside first_order_item
    first_item = attributes.get("first_order_item") or {}
    variant_name = (first_item.get("variant_name") or "").strip()
    product_name = (first_item.get("product_name") or "").strip()

    # Fallback: try top-level attributes (depends on LS version)
    if not variant_name:
        variant_name = (attributes.get("variant_name") or "").strip()
    if not product_name:
        product_name = (attributes.get("product_name") or "").strip()

    return variant_name, product_name


# ══════════════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════════════

@lemon_bp.route("/api/lemon/webhook", methods=["POST"])
def lemon_webhook():
    """
    Lemon Squeezy webhook receiver.

    Accepts POST requests from Lemon Squeezy when an order or subscription
    event occurs.  Automatically provisions or revokes license keys.

    Headers:
      X-Signature : HMAC-SHA256 hex digest of the raw request body

    Events handled:
      - order_created          — generate & store a license key
      - subscription_cancelled — revoke the license
      - order_refunded         — revoke the license

    ---
    tags:
      - License (Lemon Squeezy)
    responses:
      200:
        description: Webhook processed successfully
      400:
        description: Invalid payload or missing data
      401:
        description: Invalid webhook signature
    """
    # ── 1. Read the raw request body for signature verification ──────
    raw_body = request.get_data()

    # ── 2. Verify webhook signature ──────────────────────────────────
    signature_header = request.headers.get("X-Signature", "")
    if not _verify_webhook_signature(raw_body, signature_header):
        return jsonify({"success": False, "message": "Invalid webhook signature"}), 401

    # ── 3. Parse JSON payload ───────────────────────────────────────
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid JSON payload"}), 400

    meta = payload.get("meta") or {}
    event_name = (meta.get("event_name") or "").strip()
    data = payload.get("data") or {}
    attributes = data.get("attributes") or {}

    if not event_name:
        return jsonify({"success": False, "message": "Missing event_name in payload"}), 400

    # ── 4. Handle event ─────────────────────────────────────────────
    if event_name == "order_created":
        return _handle_order_created(attributes)
    elif event_name in ("subscription_cancelled", "order_refunded"):
        return _handle_revocation(attributes, event_name)
    else:
        # Acknowledge unknown events without error (Lemon Squeezy expects 2xx)
        return jsonify({
            "success": True,
            "message": f"Event '{event_name}' acknowledged (no action required)",
            "event": event_name,
        }), 200


@lemon_bp.route("/api/lemon/verify", methods=["GET"])
def lemon_verify():
    """
    Verify whether a license key is valid (for use by client apps / support tools).

    Query parameters:
      key : The license key string (e.g. DOCLEAN-eyAi...)

    Returns:
      valid   : true / false
      details : license payload if valid, null otherwise

    ---
    tags:
      - License (Lemon Squeezy)
    parameters:
      - name: key
        in: query
        type: string
        required: true
        description: License key to verify
    responses:
      200:
        description: Verification result
    """
    key = (request.args.get("key") or "").strip()

    if not key:
        return jsonify({
            "valid": False,
            "message": "Missing 'key' query parameter",
            "details": None,
        }), 400

    license_info = verify_license_key(key)

    if license_info:
        return jsonify({
            "valid": True,
            "message": f"Valid {license_info.get('type', 'unknown').upper()} license",
            "details": license_info,
        }), 200
    else:
        return jsonify({
            "valid": False,
            "message": "Invalid or expired license key",
            "details": None,
        }), 200


# ══════════════════════════════════════════════════════════════════════
#  Webhook event handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_order_created(attributes):
    """
    Handle the 'order_created' webhook event.

    1. Extract customer email, product variant, and subscription info
    2. Determine the license tier and expiry date
    3. Generate a license key using license_service.generate_license_key()
    4. Persist the key to backend/data/licenses.json
    """
    email = _extract_customer_email(attributes)
    if not email:
        return jsonify({
            "success": False,
            "message": "Missing customer email in webhook payload",
        }), 400

    variant_name, product_name = _extract_variant_and_product(attributes)
    tier = _determine_tier(variant_name, product_name)
    expiry = _calculate_expiry(attributes)

    # Generate the license key using the project's existing key format
    license_key = generate_license_key(
        license_type=tier,
        expiry_date=expiry,
        customer_email=email,
    )

    # Persist to the local license store
    licenses = _load_licenses()

    order_number = attributes.get("order_number", "")
    licenses[email] = {
        "email": email,
        "license_key": license_key,
        "tier": tier,
        "expiry": expiry,
        "order_number": order_number,
        "variant": variant_name,
        "product": product_name,
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    _save_licenses(licenses)

    return jsonify({
        "success": True,
        "message": f"License key generated for {email}",
        "tier": tier,
        "expiry": expiry,
        # Only include the key in the API response; do NOT email it from here.
        # Use Lemon Squeezy's built-in email system or a separate mail service.
        "license_key": license_key,
    }), 200


def _handle_revocation(attributes, event_name):
    """
    Handle revocation events:
      - subscription_cancelled
      - order_refunded

    Marks the customer's license as revoked in the local store.
    """
    email = _extract_customer_email(attributes)
    if not email:
        return jsonify({
            "success": False,
            "message": "Missing customer email in webhook payload",
        }), 400

    licenses = _load_licenses()

    if email in licenses:
        licenses[email]["status"] = "revoked"
        licenses[email]["revoked_at"] = datetime.now().isoformat()
        licenses[email]["revoke_reason"] = event_name
        _save_licenses(licenses)
        return jsonify({
            "success": True,
            "message": f"License revoked for {email}",
            "event": event_name,
        }), 200
    else:
        return jsonify({
            "success": True,
            "message": f"No license found for {email}; nothing to revoke",
            "event": event_name,
        }), 200
