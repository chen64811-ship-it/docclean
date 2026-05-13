# -*- coding: utf-8 -*-
"""
端到端测试：合成书下载接口
验证内容：
1. 后端 /api/compile-book 合成成功
2. /api/download-book/<filename> 返回正确的 Content-Type 和 Content-Disposition
3. Content-Disposition 含有 .md 扩展名
4. 下载内容是 Markdown 而非 HTML
"""
import urllib.request
import urllib.parse
import json
import os

BASE = "http://localhost:5000"
PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


print("=" * 60)
print("测试合成书下载接口")
print("=" * 60)

# ---- 测试1：后端是否运行 ----
print("\n[1] 检查后端服务...")
try:
    r = urllib.request.urlopen(BASE + "/api/files")
    test("后端运行中", r.status == 200)
except Exception as e:
    test("后端运行中", False, str(e))
    print("\n⚠️ 后端未运行，无法继续测试。请先启动后端。")
    exit(1)

# ---- 测试2：检查是否有大纲文件 ----
print("\n[2] 检查大纲文件...")
try:
    r = urllib.request.urlopen(BASE + "/api/list-docx")
    data = json.loads(r.read().decode("utf-8"))
    has_docx = data.get("success") and len(data.get("files", [])) > 0
    test("存在 .docx 大纲文件", has_docx, "项目根目录无 .docx 文件")
    if has_docx:
        docx_path = data["files"][0]["path"]
        print(f"    大纲文件: {data['files'][0]['filename']}")
except Exception as e:
    test("获取大纲列表", False, str(e))
    exit(1)

# ---- 测试3：调用合成接口 ----
print("\n[3] 调用合成书接口...")
try:
    req_data = json.dumps({"docx_path": docx_path}).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/compile-book",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    r = urllib.request.urlopen(req)
    result = json.loads(r.read().decode("utf-8"))
    test("合成成功", result.get("success") == True, result.get("message", ""))
    
    download_url = result.get("download_url", "")
    book_title = result.get("book_title", "")
    test("返回了 download_url", bool(download_url), "download_url 为空")
    test("download_url 以 .md 结尾", download_url.endswith(".md"), f"实际: {download_url}")
    print(f"    书名: {book_title}")
    print(f"    下载URL: {download_url}")
    print(f"    匹配: {result.get('matched_count')}/{result.get('total_md_files')} 个文件")
    print(f"    章节: {result.get('total_sections')} 个")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    test("合成接口调用", False, f"HTTP {e.code}: {body}")
    exit(1)
except Exception as e:
    test("合成接口调用", False, str(e))
    exit(1)

# ---- 测试4：下载接口响应头验证 ----
print("\n[4] 验证下载接口响应头...")
try:
    # download_url 类似 /api/download-book/xxx.md，中文需要编码
    # Flask 路由会自动解码，所以我们需要对文件名部分编码
    parts = download_url.split("/")
    filename_part = parts[-1]
    encoded_filename = urllib.parse.quote(filename_part)
    full_url = BASE + "/".join(parts[:-1]) + "/" + encoded_filename
    
    print(f"    请求: {full_url}")
    req = urllib.request.Request(full_url)
    resp = urllib.request.urlopen(req)
    
    ct = resp.headers.get("Content-Type", "")
    cd = resp.headers.get("Content-Disposition", "")
    
    print(f"    Content-Type: {ct}")
    print(f"    Content-Disposition: {cd}")
    
    test("Content-Type 是 text/markdown", "text/markdown" in ct, f"实际: {ct}")
    test("Content-Disposition 是 attachment", "attachment" in cd, f"实际: {cd}")
    test("Content-Disposition 含 .md", ".md" in cd, f"实际: {cd}")
    test("Content-Disposition 不含 .htm", ".htm" not in cd, f"实际: {cd}")
    
    # 读取内容验证
    content = resp.read().decode("utf-8", errors="replace")
    test("内容以 # 开头（Markdown标题）", content.strip().startswith("#"), f"内容开头: {content[:50]}")
    test("内容不含 <html> 标签", "<html" not in content.lower()[:500])
    test("内容不含 <!DOCTYPE", "<!doctype" not in content.lower()[:500])
    
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    test("下载接口", False, f"HTTP {e.code}: {body}")
except Exception as e:
    test("下载接口", False, str(e))

# ---- 测试5：确认输出文件存在并是 .md ----
print("\n[5] 检查输出文件...")
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
book_files = [f for f in os.listdir(output_dir) if f.endswith(".md") and not all(c in "0123456789abcdef-" for c in f.replace(".md", ""))]
test("outputs/ 中有合成书 .md 文件", len(book_files) > 0, "未找到合成书 .md 文件")
for bf in book_files:
    print(f"    找到: {bf}")
    fpath = os.path.join(output_dir, bf)
    with open(fpath, "r", encoding="utf-8") as f:
        head = f.read(200)
    test(f"{bf} 内容是 Markdown", head.strip().startswith("#"), f"开头: {head[:50]}")

# ---- 总结 ----
print("\n" + "=" * 60)
print(f"测试结果：✅ {PASS} 通过，❌ {FAIL} 失败")
print("=" * 60)
