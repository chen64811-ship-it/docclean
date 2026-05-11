# -*- coding: utf-8 -*-
"""测试合成书下载接口"""
import urllib.request
import urllib.parse

# 测试1：检查后端是否在运行
try:
    r = urllib.request.urlopen("http://localhost:5000/api/files")
    print("后端运行中: OK")
except Exception as e:
    print("后端未运行:", e)
    exit(1)

# 测试2：检查合成书下载接口的响应头
# 测试2：先用 /api/list-books 获取第一个书籍文件名
try:
    import json
    list_url = "http://localhost:5000/api/list-books"
    list_resp = urllib.request.urlopen(list_url)
    books = json.loads(list_resp.read())["books"]
    if books:
        filename = urllib.parse.quote(books[0]["filename"])
    else:
        print("没有合成书，跳过下载测试")
        exit(0)
except Exception as e:
    print("获取书籍列表失败:", e)
    exit(1)

url = "http://localhost:5000/api/download-book/" + filename
print("请求URL:", url)

try:
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    ct = resp.headers.get("Content-Type")
    cd = resp.headers.get("Content-Disposition")
    print("状态码:", resp.status)
    print("Content-Type:", ct)
    print("Content-Disposition:", cd)
    data = resp.read(300).decode("utf-8", errors="replace")
    print("内容前300字符:", data[:300])
except urllib.error.HTTPError as e:
    print("HTTP错误:", e.code, e.reason)
    body = e.read().decode("utf-8", errors="replace")
    print("错误内容:", body)
except Exception as e:
    print("下载失败:", e)

print()
print("=" * 50)

# 测试3：测试不带URL编码的中文路径
print("测试不带URL编码的中文路径...")
if books:
    url2 = "http://localhost:5000/api/download-book/" + books[0]["filename"]
try:
    req2 = urllib.request.Request(url2)
    resp2 = urllib.request.urlopen(req2)
    ct2 = resp2.headers.get("Content-Type")
    cd2 = resp2.headers.get("Content-Disposition")
    print("状态码:", resp2.status)
    print("Content-Type:", ct2)
    print("Content-Disposition:", cd2)
except urllib.error.HTTPError as e:
    print("HTTP错误:", e.code, e.reason)
except Exception as e:
    print("下载失败:", e)
