# -*- coding: utf-8 -*-
"""
前端 HTML 结构自测脚本
检查 index.html 的 CSS 布局规则和 HTML 结构是否正确
确保预览区域可滚动、双向编辑、滚动同步等功能全部正常
"""
import re
import os
import sys

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "index.html")
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

def find_css_rule(css_text, selector):
    """提取某个CSS选择器对应的规则内容"""
    # 匹配 selector { ... }
    pattern = re.escape(selector) + r'\s*\{([^}]+)\}'
    m = re.search(pattern, css_text)
    return m.group(1).strip() if m else None

def css_has(rule_content, prop, value=None):
    """检查CSS规则中是否包含某个属性（和可选的值）"""
    if not rule_content:
        return False
    if value:
        return f"{prop}:{value}" in rule_content.replace(" ", "") or f"{prop}: {value}" in rule_content
    return prop in rule_content

# 读取 HTML 文件
with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 提取 <style> 标签中的 CSS
style_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
css = style_match.group(1) if style_match else ""

# 提取 <script> 标签中的 JS（最后一个大的 script 标签）
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
js = "\n".join(scripts)

print("=" * 60)
print("前端 HTML 自测报告")
print("=" * 60)

# ================================================================
# 1. CDN 依赖检查
# ================================================================
print("\n[1] CDN 依赖检查...")
test("引入了 marked.js", "marked" in html and "marked.min.js" in html)
test("引入了 turndown.js", "turndown" in html and "turndown.min.js" in html)
test("引入了 EasyMDE", "easymde.min.js" in html)
test("引入了 pdf.js", "pdf.min.js" in html)

# ================================================================
# 2. PDF对照视图 - 预览区 CSS 检查
# ================================================================
print("\n[2] PDF对照视图 - 预览区CSS...")
md_preview_content = find_css_rule(css, ".md-preview-content")
test(".md-preview-content 存在", md_preview_content is not None)
if md_preview_content:
    test("  有 flex:1", css_has(md_preview_content, "flex", "1") or css_has(md_preview_content, "flex:1"))
    test("  有 overflow-y:auto", css_has(md_preview_content, "overflow-y", "auto") or css_has(md_preview_content, "overflow-y:auto"))
    test("  不是 overflow:hidden", "overflow:hidden" not in md_preview_content.replace(" ", "") or "overflow-y:auto" in md_preview_content.replace(" ", ""))

md_preview_wrap = find_css_rule(css, ".md-preview-wrap")
test(".md-preview-wrap 存在", md_preview_wrap is not None)
if md_preview_wrap:
    test("  有 overflow:hidden", css_has(md_preview_wrap, "overflow", "hidden") or css_has(md_preview_wrap, "overflow:hidden"))
    test("  有 flex-direction:column", css_has(md_preview_wrap, "flex-direction", "column"))
    test("  有 min-width:0", css_has(md_preview_wrap, "min-width", "0"))

md_editor_wrap = find_css_rule(css, ".md-editor-wrap")
test(".md-editor-wrap 有 min-height:0", md_editor_wrap and css_has(md_editor_wrap, "min-height", "0"))

# ================================================================
# 3. 编辑器视图 - 预览区 CSS 检查
# ================================================================
print("\n[3] 编辑器视图 - 预览区CSS...")
preview_pane = find_css_rule(css, ".preview-pane")
test(".preview-pane 存在", preview_pane is not None)
if preview_pane:
    test("  有 flex:1", css_has(preview_pane, "flex", "1") or css_has(preview_pane, "flex:1"))
    test("  有 overflow:hidden (不是 auto)", css_has(preview_pane, "overflow", "hidden") or css_has(preview_pane, "overflow:hidden"))
    test("  有 display:flex", css_has(preview_pane, "display", "flex") or css_has(preview_pane, "display:flex"))
    test("  有 flex-direction:column", css_has(preview_pane, "flex-direction", "column"))
    test("  有 min-height:0", css_has(preview_pane, "min-height", "0"))

preview_scroll = find_css_rule(css, ".preview-scroll")
test(".preview-scroll 存在", preview_scroll is not None)
if preview_scroll:
    test("  有 flex:1", css_has(preview_scroll, "flex", "1") or css_has(preview_scroll, "flex:1"))
    test("  有 overflow-y:auto", css_has(preview_scroll, "overflow-y", "auto") or css_has(preview_scroll, "overflow-y:auto"))
    test("  有 min-height:0", css_has(preview_scroll, "min-height", "0"))

preview_pane_header = find_css_rule(css, ".preview-pane-header")
test(".preview-pane-header 有 flex-shrink:0", preview_pane_header and css_has(preview_pane_header, "flex-shrink", "0"))

# ================================================================
# 4. HTML 结构 - contenteditable 检查
# ================================================================
print("\n[4] HTML 结构检查...")
test("mdPreviewContent 有 contenteditable='true'", 'id="mdPreviewContent" contenteditable="true"' in html)
test("previewDoc 有 contenteditable='true'", 'id="previewDoc" contenteditable="true"' in html)

# ================================================================
# 5. JS - Turndown 双向同步检查
# ================================================================
print("\n[5] JS 双向同步功能检查...")
test("getTurndown 函数存在", "function getTurndown()" in js)
test("TurndownService 实例化", "new TurndownService" in js)
test("_syncLock 防循环锁存在", "_syncLock" in js)
test("_previewInputTimer 防抖存在", "_previewInputTimer" in js)

# 检查 PDF 对照视图反向同步
test("mdPreviewContent 监听 input 事件", "preview.addEventListener('input'" in js or "preview.addEventListener(\"input\"" in js)
test("反向同步调用 turndown()", "td.turndown(preview.innerHTML)" in js)

# 检查编辑器视图反向同步
test("previewDoc 监听 input 事件", "pd.addEventListener('input'" in js or "pd.addEventListener(\"input\"" in js)
test("反向同步到 EasyMDE", "mdeInstance.value(newMd)" in js)

# ================================================================
# 6. JS - 滚动同步检查
# ================================================================
print("\n[6] JS 滚动同步检查...")
test("PDF视图 ta.onscroll 存在", "ta.onscroll = function()" in js)
test("PDF视图 mdPreviewContent 滚动目标", "preview.scrollTop" in js)

# 编辑器视图的滚动同步应该指向 .preview-scroll（不是 .preview-pane）
test("编辑器视图用 .preview-scroll 滚动", "document.querySelector('.preview-scroll')" in js)
test("编辑器视图不再用 .preview-pane 做滚动", "document.querySelector('.preview-pane')" not in js)

# ================================================================
# 7. JS - 源码→预览同步
# ================================================================
print("\n[7] JS 源码→预览同步检查...")
test("ta.oninput 调用 renderMdPreview", "ta.oninput" in js and "renderMdPreview" in js)
test("renderMdPreview 函数存在", "function renderMdPreview(" in js)
test("marked.parse 渲染", "marked.parse(" in js)
test("EasyMDE change 事件更新预览", "mdeInstance.codemirror.on('change'" in js)

# ================================================================
# 8. 保存功能检查
# ================================================================
print("\n[8] 保存功能检查...")
test("doSave 函数存在", "function doSave()" in js)
test("doSave 从 mdSourceTa 获取内容", "mdSourceTa" in js and "ta.value" in js)
test("doSave 从 mdeInstance 获取内容", "mdeInstance.value()" in js)

# ================================================================
# 9. 下载功能检查
# ================================================================
print("\n[9] 合成书下载功能检查...")
test("downloadBookFile 函数存在", "function downloadBookFile()" in js)
test("使用 fetch+blob 下载", "URL.createObjectURL(blob)" in js)
test("设置 .download 属性", "a.download" in js)
test("_bookDownloadUrl 全局变量", "_bookDownloadUrl" in js)

# ================================================================
# 总结
# ================================================================
print("\n" + "=" * 60)
print(f"自测结果：✅ {PASS} 通过，❌ {FAIL} 失败")
print("=" * 60)

if FAIL > 0:
    print("\n⚠️ 有失败项，请检查上方标记 ❌ 的项目！")
    sys.exit(1)
else:
    print("\n🎉 所有检查全部通过！")
    sys.exit(0)
