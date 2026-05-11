"""
Unit tests for license_service.py

Covers: key generation, verification, activation, feature tiering, expiry.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.license_service import (
    generate_license_key,
    verify_license_key,
    activate_license,
    check_feature,
    get_license_status,
    load_license,
    save_license,
    FEATURE_TIERS,
    _SECRET,
    LICENSE_FILE,
)


class TestKeyGeneration:
    """License Key generation and format validation."""

    def test_generate_pro_key(self):
        key = generate_license_key("pro", "2026-12-31", "test@example.com")
        assert key.startswith("DOCLEAN-")
        # Must contain exactly one "." after prefix (as separator)
        after = key[len("DOCLEAN-"):]
        assert after.count(".") == 1
        # Payload part must be base64url (no "=", no "+", no "/")
        payload_part, sig_part = after.split(".")
        assert "=" not in payload_part
        assert "+" not in payload_part
        assert "/" not in payload_part
        # Signature must be 43 chars (SHA256 in base64url)
        assert len(sig_part) == 43

    def test_generate_enterprise_key(self):
        key = generate_license_key("enterprise", "2027-06-15", "enterprise@corp.com")
        assert key.startswith("DOCLEAN-")
        info = verify_license_key(key)
        assert info is not None
        assert info["type"] == "enterprise"
        assert info["customer"] == "enterprise@corp.com"

    def test_generated_key_is_self_verifiable(self):
        key = generate_license_key("pro", "2026-12-31", "verify@test.com")
        info = verify_license_key(key)
        assert info is not None
        assert info["type"] == "pro"
        assert info["expiry"] == "2026-12-31"
        assert info["customer"] == "verify@test.com"

    def test_generate_multiple_keys_are_unique(self):
        keys = set()
        for i in range(10):
            key = generate_license_key("pro", "2026-12-31", f"user{i}@test.com")
            keys.add(key)
        # All 10 keys should be unique (different iat timestamps or email)
        assert len(keys) == 10


class TestKeyVerification:
    """License Key verification logic."""

    def test_valid_key_returns_info(self):
        key = generate_license_key("pro", "2026-12-31", "valid@test.com")
        info = verify_license_key(key)
        assert info["type"] == "pro"
        assert info["expiry"] == "2026-12-31"
        assert info["customer"] == "valid@test.com"

    def test_none_key_returns_none(self):
        assert verify_license_key(None) is None

    def test_empty_key_returns_none(self):
        assert verify_license_key("") is None

    def test_missing_prefix_returns_none(self):
        assert verify_license_key("NOT-DOCLEAN-xxx.yyy") is None

    def test_tampered_payload_returns_none(self):
        key = generate_license_key("pro", "2026-12-31", "tamper@test.com")
        # Flip a character in the payload
        after = key[len("DOCLEAN-"):]
        payload_part, sig_part = after.split(".")
        tampered_payload = payload_part[:-1] + ("A" if payload_part[-1] != "A" else "B")
        tampered_key = f"DOCLEAN-{tampered_payload}.{sig_part}"
        assert verify_license_key(tampered_key) is None

    def test_tampered_signature_returns_none(self):
        key = generate_license_key("pro", "2026-12-31", "tamper@test.com")
        after = key[len("DOCLEAN-"):]
        payload_part, sig_part = after.split(".")
        # Flip a character in the signature
        tampered_sig = sig_part[:-1] + ("A" if sig_part[-1] != "A" else "B")
        tampered_key = f"DOCLEAN-{payload_part}.{tampered_sig}"
        assert verify_license_key(tampered_key) is None

    def test_wrong_secret_fails(self):
        key = generate_license_key("pro", "2026-12-31", "secret@test.com")
        info = verify_license_key(key)
        assert info is not None  # valid with correct secret

        # Generate with one secret, verify the structure is correct
        # (cross-secret verification would fail — this is the whole point)
        after = key[len("DOCLEAN-"):]
        payload_part, sig_part = after.split(".")
        # Sign with a different secret
        import hmac
        import hashlib
        import base64
        wrong_secret = b"wrong-secret-key-for-testing"
        wrong_sig = hmac.new(wrong_secret, payload_part.encode("ascii"), hashlib.sha256).digest()
        wrong_sig_b64 = base64.urlsafe_b64encode(wrong_sig).rstrip(b"=").decode("ascii")
        wrong_key = f"DOCLEAN-{payload_part}.{wrong_sig_b64}"
        assert verify_license_key(wrong_key) is None

    def test_expired_key_returns_none(self):
        key = generate_license_key("pro", "2020-01-01", "expired@test.com")
        info = verify_license_key(key)
        assert info is None  # Expired

    def test_future_key_is_valid(self):
        key = generate_license_key("enterprise", "2030-01-01", "future@test.com")
        info = verify_license_key(key)
        assert info is not None
        assert info["type"] == "enterprise"


class TestFeatureTiering:
    """Feature tier access control."""

    def test_free_features(self):
        free_features = [k for k, v in FEATURE_TIERS.items() if v == "free"]
        assert "upload" in free_features
        assert "convert" in free_features
        assert "download" in free_features
        assert "editor" in free_features
        assert "pdf_export" in free_features

    def test_pro_features(self):
        pro_features = [k for k, v in FEATURE_TIERS.items() if v == "pro"]
        assert "knowledge_base" in pro_features
        assert "rag_search" in pro_features
        assert "ai_qa" in pro_features
        assert "batch_process" in pro_features

    def test_enterprise_features(self):
        ent_features = [k for k, v in FEATURE_TIERS.items() if v == "enterprise"]
        assert "book_compiler" in ent_features
        assert "api_access" in ent_features

    def test_free_always_accessible(self):
        # Without any license file, free features should work
        for feature, tier in FEATURE_TIERS.items():
            if tier == "free":
                assert check_feature(feature) is True

    def test_unknown_feature_defaults_free(self):
        assert check_feature("nonexistent_feature") is True


class TestLicensePersistence:
    """License save/load round-trip."""

    def test_save_and_load_license(self):
        # Save a test license
        test_info = {
            "activated": True,
            "type": "pro",
            "expiry": "2026-12-31",
            "customer": "save@test.com",
            "activated_at": time.time(),
        }
        save_license(test_info)
        loaded = load_license()
        # Clean up: remove license after test to restore state
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
        assert loaded["activated"] is True
        assert loaded["type"] == "pro"
        assert loaded["customer"] == "save@test.com"

    def test_load_license_when_no_file(self):
        # Ensure no license file exists
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
        info = load_license()
        assert info["activated"] is False
        assert info["type"] == "free"

    def test_load_expired_license_downgrades(self):
        # Save an expired license
        expired_info = {
            "activated": True,
            "type": "pro",
            "expiry": "2020-01-01",
            "customer": "old@test.com",
            "activated_at": time.time(),
        }
        save_license(expired_info)
        loaded = load_license()
        # Should be downgraded to free
        assert loaded["activated"] is False
        assert loaded["type"] == "free"
        # License file should have been overwritten
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, "r") as f:
                data = json.load(f)
            assert data["type"] == "free"


class TestActivation:
    """End-to-end activation flow."""

    def test_activate_valid_pro_key(self):
        key = generate_license_key("pro", "2026-12-31", "activate@test.com")
        success, msg = activate_license(key)
        assert success is True
        assert "PRO" in msg
        # Verify it was saved
        loaded = load_license()
        assert loaded["type"] == "pro"
        assert loaded["customer"] == "activate@test.com"
        # Clean up
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)

    def test_activate_invalid_key(self):
        success, msg = activate_license("INVALID-KEY")
        assert success is False
        assert "Invalid" in msg

    def test_activate_then_check_features(self):
        key = generate_license_key("pro", "2026-12-31", "features@test.com")
        activate_license(key)

        # Free features still work
        assert check_feature("upload") is True
        assert check_feature("editor") is True
        # Pro features now work
        assert check_feature("rag_search") is True
        assert check_feature("ai_qa") is True
        # Enterprise features still blocked
        assert check_feature("book_compiler") is False

        # Clean up
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)

    def test_activate_enterprise_unlocks_all(self):
        key = generate_license_key("enterprise", "2026-12-31", "full@test.com")
        activate_license(key)

        assert check_feature("upload") is True
        assert check_feature("rag_search") is True
        assert check_feature("book_compiler") is True
        assert check_feature("api_access") is True

        # Clean up
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)

    def test_get_license_status(self):
        key = generate_license_key("pro", "2026-12-31", "status@test.com")
        activate_license(key)
        status = get_license_status()
        assert status["activated"] is True
        assert status["type"] == "pro"
        assert "features" in status
        assert status["features"]["upload"] is True
        assert status["features"]["rag_search"] is True
        assert status["features"]["book_compiler"] is False

        # Clean up
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
