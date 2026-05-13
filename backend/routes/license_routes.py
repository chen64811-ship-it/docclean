# -*- coding: utf-8 -*-
"""
License Management Routes
Provides license activation and status query API
"""
from flask import Blueprint, request, jsonify
from services.license_service import activate_license, get_license_status, load_license

license_bp = Blueprint("license", __name__)


@license_bp.route("/api/license/status", methods=["GET"])
def license_status():
    """
    Get current license status including feature availability.
    ---
    tags:
      - License
    responses:
      200:
        description: Current license status
        schema:
          type: object
          properties:
            success:
              type: boolean
            license:
              type: object
              properties:
                activated:
                  type: boolean
                type:
                  type: string
                  enum: [free, pro, enterprise]
                expiry:
                  type: string
                customer:
                  type: string
                features:
                  type: object
    """
    status = get_license_status()
    return jsonify({"success": True, "license": status})


@license_bp.route("/api/license/activate", methods=["POST"])
def license_activate():
    """
    Activate a license key to unlock Pro or Enterprise features.
    ---
    tags:
      - License
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - key
          properties:
            key:
              type: string
              description: License key string (e.g. DOCLEAN-xxxx-xxxx)
    responses:
      200:
        description: Activation result with updated license status
      400:
        description: Invalid license key
    """
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()

    if not key:
        return jsonify({"success": False, "message": "License key is required"}), 400

    success, message = activate_license(key)
    status = get_license_status()

    return jsonify({
        "success": success,
        "message": message,
        "license": status,
    }), (200 if success else 400)


@license_bp.route("/api/license/deactivate", methods=["POST"])
def license_deactivate():
    """
    Deactivate current license (revert to Free tier).
    ---
    tags:
      - License
    responses:
      200:
        description: License deactivated
    """
    from services.license_service import save_license
    import time
    save_license({
        "activated": False,
        "type": "free",
        "expiry": "",
        "customer": "",
        "activated_at": 0,
    })
    return jsonify({
        "success": True,
        "message": "License deactivated. Reverted to Free tier.",
        "license": get_license_status(),
    })
