# -*- coding: utf-8 -*-
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

outputs = os.path.join(os.path.dirname(__file__), '..', 'outputs')
tree_file = None
for f in os.listdir(outputs):
    if f.endswith('_excel_tree.json'):
        tree_file = os.path.join(outputs, f)
        print(f"找到: {f}")

if not tree_file:
    print('未找到 excel_tree.json')
    sys.exit(1)

with open(tree_file, encoding='utf-8') as fp:
    t = json.load(fp)

def dump(node, indent=0):
    prefix = '  ' * indent
    tp = node.get('type', '?')
    title = node.get('title', '')
    children = node.get('children', [])
    preview = (node.get('content_preview') or node.get('summary') or '')[:60].replace('\n',' ')
    print(f"{prefix}[{tp}] {title}  子节点:{len(children)}  预览:{preview}")
    for c in children:
        dump(c, indent + 1)

dump(t)
print(f"\n原始 MD 文件字数:")
for f in os.listdir(outputs):
    if f.endswith('.md') and not f.endswith('_tree.json'):
        path = os.path.join(outputs, f)
        with open(path, encoding='utf-8') as fp:
            content = fp.read()
        print(f"  {f}: {len(content)} 字")
