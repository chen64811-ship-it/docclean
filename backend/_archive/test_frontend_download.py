# -*- coding: utf-8 -*-
"""测试：模拟前端构造的下载URL"""
import urllib.request
import urllib.parse
import json

BASE = "http://localhost:5000"
PASS = 0
FAIL = 0

def test(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")

print("=" * 60)
print("模拟前端下载流程测试")
print("=" * 60)

# 步骤1：调用合成接口
print("\n[1] 调用合成接口...")
req_data = json.dumps({}).encode("utf-8")
req = urllib.request.Request(
    BASE + "/api/compile-book",
    data=req_data,
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req)
result = json.loads(r.read().decode("utf-8"))
test("合成成功", result.get("success"))
download_url = result.get("download_url", "")
print(f"    download_url = {download_url}")

# 步骤2：模拟前端JS构造URL
# 前端代码：API + '/download-book/' + encodeURIComponent(filename)
filename = download_url.split("/")[-1]  # 从 download_url 中提取文件名
encoded_filename = urllib.parse.quote(filename)  # 相当于 JS 的 encodeURIComponent
frontend_url = BASE + "/api/download-book/" + encoded_filename
print(f"\n[2] 前端构造的URL:")
print(f"    原始文件名: {filename}")
print(f"    编码后文件名: {encoded_filename}")
print(f"    完整URL: {frontend_url}")

# 步骤3：用这个URL发请求
print(f"\n[3] 下载测试...")
try:
    req2 = urllib.request.Request(frontend_url)
    resp = urllib.request.urlopen(req2)
    ct = resp.headers.get("Content-Type", "")
    cd = resp.headers.get("Content-Disposition", "")
    content = resp.read().decode("utf-8", errors="replace")
    
    print(f"    Content-Type: {ct}")
    print(f"    Content-Disposition: {cd}")
    print(f"    内容长度: {len(content)} 字符")
    print(f"    内容前100字符: {content[:100]}")
    
    test("状态码200", resp.status == 200)
    test("Content-Type是markdown", "text/markdown" in ct, ct)
    test("内容是Markdown", content.strip().startswith("#"), content[:50])
    test("内容不是404页面", "404 Not Found" not in content, content[:200])
    test("内容不是HTML", "<html" not in content[:200].lower(), content[:200])
    
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    test("下载请求", False, f"HTTP {e.code}: {body[:200]}")
except Exception as e:
    test("下载请求", False, str(e))

# 步骤4：也测试不编码的情况（直接中文URL）
print(f"\n[4] 测试不编码的中文URL（对比）...")
raw_url = BASE + download_url
print(f"    URL: {raw_url}")
try:
    # urllib会自动编码非ASCII字符
    req3 = urllib.request.Request(raw_url)
    resp3 = urllib.request.urlopen(req3)
    content3 = resp3.read().decode("utf-8", errors="replace")
    test("直接中文URL也能下载", content3.strip().startswith("#"))
except Exception as e:
    test("直接中文URL", False, str(e))

print(f"\n{'='*60}")
print(f"结果：✅ {PASS} 通过，❌ {FAIL} 失败")
print(f"{'='*60}")
