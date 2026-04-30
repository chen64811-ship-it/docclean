# -*- coding: utf-8 -*-
"""
知识库路由
API:
- GET  /api/kb/list                    获取知识库文档列表
- GET  /api/kb/tree/<file_id>         获取文档树结构
- GET  /api/kb/chunks/<file_id>       获取文档所有分块
- GET  /api/kb/search                 搜索文档（支持全文搜索）
- POST /api/kb/ask                    问答（需配置 LLM）
- GET  /api/kb/config                  获取 LLM 配置
- POST /api/kb/config                  保存 LLM 配置
- POST /api/kb/test-llm                测试 LLM 连接
- POST /api/kb/rebuild/<file_id>       重建文档的树结构和分块
- POST /api/kb/classify-excel/<id>    LLM + Excel 大纲智能分类（需配置 LLM）
"""
import os
import threading
from flask import Blueprint, request, jsonify
from models.file_model import get_all_files, get_file_by_id
from services.tree_parser import parse_markdown_to_tree
from services.rag_service import (
    chunk_content, search_chunks, generate_answer,
    test_llm_connection
)
from services.excel_classifier import excel_classify_and_build
from config_manager import get_config, save_config, is_llm_enabled
from config import OUTPUT_FOLDER
from progress_store import set_progress, del_progress

knowledge_bp = Blueprint("knowledge", __name__)

# 全局缓存：file_id -> (tree_data, chunks, cache_time)
_cache = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 300  # 缓存有效期（秒）


def _get_cached(file_id):
    with _CACHE_LOCK:
        entry = _cache.get(str(file_id))
        if entry:
            import time
            if time.time() - entry["cache_time"] < _CACHE_TTL:
                return entry["tree"], entry["chunks"]
    return None, None


def _set_cached(file_id, tree, chunks):
    import time
    with _CACHE_LOCK:
        _cache[str(file_id)] = {
            "tree": tree, "chunks": chunks, "cache_time": time.time()
        }


def _build_doc(doc_file_id, md_content, original_name):
    """构建文档的树结构和分块"""
    tree = parse_markdown_to_tree(md_content, original_name)
    chunks = chunk_content(md_content, doc_file_id, original_name)
    _set_cached(doc_file_id, tree, chunks)
    return tree, chunks


# ========== 知识库列表 ==========

@knowledge_bp.route("/api/kb/list", methods=["GET"])
def kb_list():
    """
    获取知识库文档列表（已完成解析的文档）
    """
    files = get_all_files()
    done_files = [f for f in files if f["status"] == "done"]

    result = []
    for f in done_files:
        file_id = f["id"]
        original_name = f["original_name"]
        file_ext = (f.get("file_ext") or "").upper()

        # 优先从缓存获取（快）
        tree, _ = _get_cached(file_id)

        # 缓存没有才从文件重建（只重建一次）
        if tree is None:
            tree, _ = _build_tree_from_file(f)

        node_count = _count_nodes(tree) if tree else 0
        result.append({
            "id": file_id,
            "original_name": original_name,
            "file_ext": file_ext,
            "file_size": f.get("file_size", 0),
            "created_at": f.get("created_at", 0),
            "node_count": node_count
        })

    result.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify({"success": True, "documents": result})


def _build_tree_from_file(f):
    """从文件系统加载并构建树"""
    output_path = f.get("output_path", "")
    if not output_path:
        return None, []
    output_path = os.path.abspath(output_path)
    if not os.path.exists(output_path):
        return None, []
    try:
        with open(output_path, encoding="utf-8") as fp:
            md_content = fp.read()
        tree, chunks = _build_doc(f["id"], md_content, f.get("original_name", ""))
        return tree, chunks
    except Exception:
        return None, []


def _count_nodes(tree):
    """统计树节点总数"""
    if not tree:
        return 0
    count = 1
    for child in tree.get("children", []):
        count += _count_nodes(child)
    return count


# ========== 文档树结构 ==========

@knowledge_bp.route("/api/kb/tree/<int:file_id>", methods=["GET"])
def kb_tree(file_id):
    """
    获取指定文档的树结构
    """
    f = get_file_by_id(file_id)
    if not f:
        return jsonify({"success": False, "message": "文档不存在"}), 404
    if f["status"] != "done":
        return jsonify({"success": False, "message": "文档尚未解析完成"}), 400

    tree, _ = _get_cached(file_id)
    if tree is None:
        tree, _ = _build_tree_from_file(f)

    return jsonify({
        "success": True,
        "file_id": file_id,
        "original_name": f.get("original_name", ""),
        "tree": tree or {}
    })


# ========== 文档分块 ==========

@knowledge_bp.route("/api/kb/chunks/<int:file_id>", methods=["GET"])
def kb_chunks(file_id):
    """
    获取指定文档的所有分块
    """
    f = get_file_by_id(file_id)
    if not f:
        return jsonify({"success": False, "message": "文档不存在"}), 404
    if f["status"] != "done":
        return jsonify({"success": False, "message": "文档尚未解析完成"}), 400

    _, chunks = _get_cached(file_id)
    if chunks is None:
        _, chunks = _build_tree_from_file(f)

    return jsonify({
        "success": True,
        "file_id": file_id,
        "chunks": chunks or []
    })


# ========== 全文搜索 ==========

@knowledge_bp.route("/api/kb/search", methods=["GET"])
def kb_search():
    """
    搜索文档内容
    参数：
      q: 查询词（必填）
      file_id: 可选，限定文档ID
      top_k: 返回数量，默认5
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "message": "查询词不能为空"}), 400

    file_id = request.args.get("file_id", type=int)
    top_k = request.args.get("top_k", default=5, type=int)

    if file_id:
        # 搜索指定文档
        f = get_file_by_id(file_id)
        if f and f["status"] == "done":
            _, chunks = _get_cached(file_id)
            if chunks is None:
                _, chunks = _build_tree_from_file(f)
            if chunks:
                results = search_chunks(chunks, query, top_k=top_k)
                return jsonify({
                    "success": True,
                    "query": query,
                    "results": results,
                    "llm_available": is_llm_enabled()
                })
        return jsonify({"success": True, "query": query, "results": [], "llm_available": is_llm_enabled()})

    # 全库搜索
    all_chunks = []
    files = get_all_files()
    done_files = [f for f in files if f["status"] == "done"]

    for f in done_files:
        fid = f["id"]
        _, chunks = _get_cached(fid)
        if chunks is None:
            _, chunks = _build_tree_from_file(f)
        if chunks:
            all_chunks.extend(chunks)

    results = search_chunks(all_chunks, query, top_k=top_k)
    return jsonify({
        "success": True,
        "query": query,
        "results": results,
        "llm_available": is_llm_enabled()
    })


# ========== 问答 ==========

@knowledge_bp.route("/api/kb/ask", methods=["POST"])
def kb_ask():
    """
    问答接口
    请求体：{"query": "问题", "file_id": 可选, "top_k": 5}
    """
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    file_id = data.get("file_id")
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify({"success": False, "message": "问题不能为空"}), 400

    # 获取相关块
    chunks = []
    if file_id:
        f = get_file_by_id(file_id)
        if f and f["status"] == "done":
            _, chunks = _get_cached(file_id)
            if chunks is None:
                _, chunks = _build_tree_from_file(f)
    else:
        # 全库搜索
        all_chunks = []
        files = get_all_files()
        for f in [x for x in files if x["status"] == "done"]:
            _, c = _get_cached(f["id"])
            if c is None:
                _, c = _build_tree_from_file(f)
            if c:
                all_chunks.extend(c)
        chunks = all_chunks

    results = search_chunks(chunks, query, top_k=top_k)

    # 调用 LLM 生成答案
    if is_llm_enabled() and results:
        answer = generate_answer(query, results)
        return jsonify({
            "success": True,
            "query": query,
            "answer": answer,
            "sources": [
                {
                    "title": r.get("title", ""),
                    "file_name": r.get("file_name", ""),
                    "page_range": r.get("page_range", ""),
                    "score": r.get("score", 0),
                    "preview": r.get("content_preview", "")[:200]
                }
                for r in results
            ]
        })
    elif is_llm_enabled() and not results:
        return jsonify({
            "success": True,
            "query": query,
            "answer": "没有找到相关内容，请尝试不同的查询词。",
            "sources": []
        })
    else:
        # 未配置 LLM，返回检索结果
        return jsonify({
            "success": True,
            "query": query,
            "answer": None,
            "llm_not_configured": True,
            "sources": [
                {
                    "title": r.get("title", ""),
                    "file_name": r.get("file_name", ""),
                    "page_range": r.get("page_range", ""),
                    "score": r.get("score", 0),
                    "preview": r.get("content_preview", "")[:200]
                }
                for r in results
            ]
        })


# ========== LLM 配置 ==========

@knowledge_bp.route("/api/kb/config", methods=["GET"])
def kb_get_config():
    """获取 LLM 配置（不返回 api_key 明文）"""
    cfg = get_config()
    # 脱敏 api_key
    api_key = cfg.get("api_key", "")
    if api_key:
        cfg["api_key"] = api_key[:4] + "****" + api_key[-4:] if len(api_key) > 8 else "****"
    cfg["is_enabled"] = is_llm_enabled()
    return jsonify({"success": True, "config": cfg})


@knowledge_bp.route("/api/kb/config", methods=["POST"])
def kb_save_config():
    """保存 LLM 配置"""
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    api_base = data.get("api_base", "https://api.minimax.chat/v1").strip()
    model = data.get("model", "MiniMax-M2.7").strip()
    temperature = float(data.get("temperature", 0.7))
    max_tokens = int(data.get("max_tokens", 2000))
    enabled = bool(data.get("enabled", False))

    # 如果 api_key 未传入或脱敏格式，保留原有值
    current = get_config()
    if "api_key" not in data or "****" in api_key:
        api_key = current.get("api_key", "")

    new_config = {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "enabled": enabled
    }

    ok = save_config(new_config)
    if ok:
        return jsonify({"success": True, "message": "配置已保存"})
    return jsonify({"success": False, "message": "保存失败，请检查权限"}), 500


def _read_env(key, default=""):
    """直接从 .env 文件读取配置"""
    _backend_dir = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(_backend_dir, ".env")
    if not os.path.exists(env_path):
        return default
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    return default


@knowledge_bp.route("/api/kb/test-llm", methods=["POST"])
def kb_test_llm():
    """测试 LLM 连接"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            data = {}
    except:
        data = {}

    # 从请求体获取，如果没有则从 .env 文件读取
    _key = data.get("api_key", "") if isinstance(data, dict) else ""
    if _key:
        api_key = _key.strip()
    else:
        api_key = _read_env("LLM_API_KEY")

    _base = data.get("api_base", "") if isinstance(data, dict) else ""
    api_base = _base.strip() if _base else _read_env("LLM_API_BASE", "https://api.minimax.chat/v1")

    _model = data.get("model", "") if isinstance(data, dict) else ""
    model = _model.strip() if _model else _read_env("LLM_MODEL", "MiniMax-M2.7")

    if not api_key:
        return jsonify({"success": False, "message": "API Key 不能为空，请在设置中配置"})

    # 临时保存测试配置
    import time
    import tempfile
    import shutil
    tmp_config = {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "temperature": 0.7,
        "max_tokens": 10,
        "enabled": True
    }
    # 用临时配置测试
    import sys
    import importlib
    old_config = get_config()
    save_config(tmp_config)

    # 重新加载 config_manager
    import config_manager
    importlib.reload(config_manager)

    # test_llm_connection 在 rag_service 中
    from services import rag_service
    importlib.reload(rag_service)
    success, msg = rag_service.test_llm_connection()

    # 恢复原配置
    save_config(old_config)
    importlib.reload(config_manager)

    return jsonify({"success": success, "message": msg})


# ========== 重建索引 ==========

@knowledge_bp.route("/api/kb/rebuild/<int:file_id>", methods=["POST"])
def kb_rebuild(file_id):
    """
    重建指定文档的树结构和分块索引
    """
    f = get_file_by_id(file_id)
    if not f:
        return jsonify({"success": False, "message": "文档不存在"}), 404
    if f["status"] != "done":
        return jsonify({"success": False, "message": "文档尚未解析完成"}), 400

    # 清除缓存
    with _CACHE_LOCK:
        _cache.pop(str(file_id), None)

    # 重新构建
    tree, chunks = _build_tree_from_file(f)
    return jsonify({
        "success": True,
        "message": f"重建完成，共 {len(chunks)} 个分块，{sum(1 for _ in _flatten_tree(tree))} 个节点"
    })


def _flatten_tree(tree):
    """扁平化树（用于统计节点数）"""
    yield tree
    for child in tree.get("children", []):
        yield from _flatten_tree(child)


# ================================================================
# LLM 智能分类（按 Excel 大纲）—— 异步后台处理
# ================================================================

# 全局分类任务状态
_classify_tasks = {}  # file_id -> { status: 'running'|'done'|'error', message, tree, stats }


def _classify_worker(file_id, output_path, original_name):
    """
    后台线程：执行 LLM 分类，完成后更新任务状态
    """
    import json as _json
    try:
        # 读取 Markdown
        with open(os.path.abspath(output_path), encoding="utf-8") as fp:
            md_content = fp.read()

        # 定义进度回调
        def progress_callback(done, total, msg):
            pct = int(done * 100 / max(total, 1))
            set_progress(file_id, 100, min(pct, 99), msg)

        # 执行分类（同步调用，但因为在线程里不会阻塞 Flask）
        tree, stats = excel_classify_and_build(
            md_content,
            original_name=original_name,
            progress_callback=progress_callback
        )

        # 保存结果文件
        tree_basename = os.path.splitext(os.path.basename(output_path))[0] + "_excel_tree.json"
        tree_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, tree_basename))
        with open(tree_path, "w", encoding="utf-8") as fp:
            _json.dump(tree, fp, ensure_ascii=False, indent=2)

        # 更新缓存
        _set_cached(file_id, tree, [])
        del_progress(file_id)

        _classify_tasks[file_id] = {
            "status": "done",
            "message": f"分类完成！共 {stats['total_chunks']} 个段落，丢弃 {stats['discarded']} 个无效段落",
            "tree": tree,
            "stats": stats
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        del_progress(file_id)
        _classify_tasks[file_id] = {
            "status": "error",
            "message": f"分类失败: {e}"
        }


@knowledge_bp.route("/api/kb/classify-excel/<int:file_id>", methods=["POST"])
def kb_classify_excel(file_id):
    """
    启动 LLM 分类（异步，后台处理）
    启动后前端轮询 /api/kb/classify-status/<id> 查看进度
    """
    f = get_file_by_id(file_id)
    if not f:
        return jsonify({"success": False, "message": "文档不存在"}), 404
    if f["status"] != "done":
        return jsonify({"success": False, "message": "文档尚未解析完成"}), 400

    if not is_llm_enabled():
        return jsonify({
            "success": False,
            "message": "LLM 未配置，请在设置中配置 API Key 后重试"
        }), 400

    output_path = f.get("output_path", "")
    if not output_path or not os.path.exists(os.path.abspath(output_path)):
        return jsonify({"success": False, "message": "Markdown 文件不存在"}), 404

    # 如果任务已在运行，拒绝重复启动
    task = _classify_tasks.get(file_id)
    if task and task["status"] == "running":
        return jsonify({"success": False, "message": "分类正在进行中，请稍候..."}), 409

    # 立即返回，启动后台线程
    set_progress(file_id, 100, 0, "启动 LLM 分类...")
    _classify_tasks[file_id] = {"status": "running", "message": "分类中...", "tree": None, "stats": None}

    thread = threading.Thread(
        target=_classify_worker,
        args=(file_id, output_path, f.get("original_name", ""))
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "success": True,
        "message": "分类已启动，请稍候...",
        "status": "running"
    })


@knowledge_bp.route("/api/kb/classify-status/<int:file_id>", methods=["GET"])
def kb_classify_status(file_id):
    """
    查询分类任务状态（供前端轮询）
    """
    task = _classify_tasks.get(file_id)
    if not task:
        return jsonify({"success": False, "message": "无分类任务"}), 404

    return jsonify({
        "success": True,
        "status": task["status"],
        "message": task.get("message", ""),
        "stats": task.get("stats"),
        "tree": task.get("tree")
    })
