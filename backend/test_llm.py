# -*- coding: utf-8 -*-
"""测试 LLM API 是否可用"""
import json, urllib.request, urllib.error
from config_manager import get_config

config = get_config()
api_base = config["api_base"].rstrip("/")
if api_base.endswith("/v1"):
    url = api_base + "/chat/completions"
else:
    url = api_base + "/v1/chat/completions"

print(f"测试地址: {url}")
print(f"模型: {config['model']}")
print(f"API Key: {config['api_key'][:15]}...")
print()

payload = {
    "model": "MiniMax-Text-01",
    "messages": [{"role": "user", "content": "你好，请回复'LLM可用'四个字"}],
    "temperature": 0.1,
    "max_tokens": 50
}

try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["api_key"]
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        reply = result["choices"][0]["message"]["content"].strip()
        print(f"✅ LLM 响应成功！回复: {reply}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="ignore")
    print(f"❌ HTTP 错误 {e.code}: {e.reason}")
    print(f"   响应体: {body[:500]}")
except Exception as e:
    print(f"❌ 调用失败: {e}")
