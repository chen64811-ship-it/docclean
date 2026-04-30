# -*- coding: utf-8 -*-
"""
配置管理服务
管理 LLM API 配置（API Key、Base URL、模型名称）
配置持久化到 backend/llm_config.json
"""
import os
import json
from dotenv import load_dotenv

# 加载 .env 文件（backend/.env）
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

CONFIG_PATH = os.path.join(BACKEND_DIR, "llm_config.json")


def get_config():
    """
    读取配置，返回字典
    优先级：.env 文件 > llm_config.json > 默认值
    """
    # 优先从 .env 读取
    env_api_key = os.getenv("LLM_API_KEY", "").strip()
    env_api_base = os.getenv("LLM_API_BASE", "").strip()
    env_model = os.getenv("LLM_MODEL", "").strip()

    default_config = {
        "api_key": "",
        "api_base": "https://api.minimax.chat/v1",
        "model": "MiniMax-M2.7",
        "temperature": 0.7,
        "max_tokens": 2000,
        "enabled": True  # 是否启用了 LLM 增强问答
    }

    # 如果 .env 中有配置，优先使用
    if env_api_key:
        default_config["api_key"] = env_api_key
        default_config["api_base"] = env_api_base or "https://api.minimax.chat/v1"
        default_config["model"] = env_model or "MiniMax-M2.7"
        default_config["enabled"] = True
        return default_config

    # 否则读取 llm_config.json
    if not os.path.exists(CONFIG_PATH):
        return default_config

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
        # 合并默认值，防止新增字段缺失
        for k, v in default_config.items():
            if k not in config:
                config[k] = v
        return config
    except Exception:
        return default_config


def save_config(config):
    """
    保存配置到文件
    """
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[配置保存失败] {e}")
        return False


def is_llm_enabled():
    """
    检查是否配置了有效的 LLM
    """
    cfg = get_config()
    return bool(cfg.get("api_key", "").strip()) and cfg.get("enabled", False)
