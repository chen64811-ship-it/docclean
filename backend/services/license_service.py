# -*- coding: utf-8 -*-
"""
DocClean License Key System
============================
为海外售卖提供 License Key 验证机制。

License 分级：
  free       — 基础功能（文件上传/转换/下载/编辑），无需 Key
  pro        — 高级功能（RAG 知识库、AI 问答、批量处理）
  enterprise — 全部功能（含书籍编译器），无限制

Key 格式：DOCLEAN-<payload_b64>-<signature_b64>
  payload  = base64url(json)  例如 {"t":"pro","e":"2026-12-31","c":"user@example.com"}
  signature = base64url(HMAC-SHA256(payload, SECRET))

许可证文件：backend/license.json（通过 API 激活后自动生成）
"""
import os
import json
import hmac
import hashlib
import base64
import time
from datetime import datetime
from config import BASE_DIR

# ========== 密钥（生产环境请更换）==========
_SECRET = b"docclean-2026-overseas-first-product"

# ========== 许可证文件路径 ==========
LICENSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "license.json")

# ========== 功能分级定义 ==========
# Free 功能：始终可用，无需 License
# Pro 功能：需要 pro 及以上 License
# Enterprise 功能：需要 enterprise License
FEATURE_TIERS = {
    # 基础功能 — 永远免费
    "upload": "free",
    "convert": "free",
    "download": "free",
    "editor": "free",
    "pdf_export": "free",
    "tree_view": "free",
    # 高级功能 — Pro
    "knowledge_base": "pro",
    "rag_search": "pro",
    "ai_qa": "pro",
    "batch_process": "pro",
    # 企业功能 — Enterprise
    "book_compiler": "enterprise",
    "api_access": "enterprise",
}


def _b64url_encode(data: bytes) -> str:
    """Base64URL 编码（去掉末尾 =，替换 +/ 为 -_）"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64URL 解码（补齐末尾 =）"""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def generate_license_key(license_type: str, expiry_date: str, customer_email: str) -> str:
    """
    生成一个 License Key（仅由卖方使用）

    参数：
        license_type: "pro" 或 "enterprise"
        expiry_date: 到期日期，如 "2026-12-31"
        customer_email: 客户邮箱

    返回：
        License Key 字符串，如 "DOCLEAN-eyJ0IjoicHJvIi..."
    """
    payload = {
        "t": license_type,         # type
        "e": expiry_date,          # expiry
        "c": customer_email,       # customer
        "iat": int(time.time()),   # issued at
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))

    # HMAC-SHA256 签名
    sig = hmac.new(_SECRET, payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"DOCLEAN-{payload_b64}.{sig_b64}"


def verify_license_key(key: str) -> dict | None:
    """
    验证 License Key 的有效性

    参数：
        key: License Key 字符串（格式：DOCLEAN-<payload_b64>.<sig_b64>）

    返回：
        有效 → {"type": "pro", "expiry": "2026-12-31", "customer": "user@example.com"}
        无效 → None
    """
    if not key or not key.startswith("DOCLEAN-"):
        return None

    # 格式：DOCLEAN-<payload_b64>.<signature_b64>
    # base64url 不含 `.`，所以用 `.` 做分隔符绝对可靠
    try:
        after_prefix = key[len("DOCLEAN-"):]
        parts = after_prefix.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_part, sig_part = parts
    except Exception:
        return None

    # 验证签名
    expected_sig = hmac.new(_SECRET, payload_part.encode("ascii"), hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if expected_sig_b64 != sig_part:
        return None

    # 解码 payload
    try:
        payload_json = _b64url_decode(payload_part).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        return None

    # 检查过期
    expiry_str = payload.get("e", "")
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            if expiry_date < datetime.now():
                return None  # 已过期
        except ValueError:
            return None

    return {
        "type": payload.get("t", "free"),
        "expiry": expiry_str,
        "customer": payload.get("c", "unknown"),
    }


def load_license() -> dict:
    """
    从本地文件加载已激活的 License 信息

    返回：
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
        # 检查存储的 license 是否过期
        type_ = data.get("type", "free")
        if type_ != "free":
            expiry = data.get("expiry", "")
            if expiry:
                try:
                    expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
                    if expiry_date < datetime.now():
                        # 过期了，降级为 free
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
    """保存 License 信息到本地文件"""
    try:
        file_path = os.path.abspath(LICENSE_FILE)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[License] Failed to save license: {e}")


def activate_license(key: str) -> tuple[bool, str]:
    """
    激活一个 License Key

    返回：
        (success, message)
    """
    # 验证 Key 格式和签名
    license_info = verify_license_key(key)
    if not license_info:
        return False, "Invalid license key. Please check and try again."

    # 保存到本地文件
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
    检查某个功能是否可用

    参数：
        feature_name: 功能名（如 "rag_search", "book_compiler"）

    返回：
        True = 可用，False = 需要升级 License
    """
    required_tier = FEATURE_TIERS.get(feature_name, "free")
    if required_tier == "free":
        return True

    license_info = load_license()
    current_tier = license_info.get("type", "free") if license_info.get("activated") else "free"

    tier_levels = {"free": 0, "pro": 1, "enterprise": 2}
    return tier_levels.get(current_tier, 0) >= tier_levels.get(required_tier, 0)


def get_license_status() -> dict:
    """
    获取当前 License 状态（给前端展示）
    """
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
