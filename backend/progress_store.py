# -*- coding: utf-8 -*-
"""
解析进度存储（内存中，线程安全）
后台线程写入，前端轮询读取
"""
import threading

# {file_id: {"total": int, "done": int, "stage": str, "pct": int}}
_progress_store = {}
_store_lock = threading.Lock()


def set_progress(file_id, total, done, stage=""):
    """
    设置某个文件的解析进度
    """
    pct = int(done / total * 100) if total > 0 else 0
    with _store_lock:
        _progress_store[file_id] = {
            "total": total,
            "done": done,
            "stage": stage,
            "pct": pct
        }


def get_progress(file_id):
    """
    获取某个文件的解析进度，返回字典或None
    """
    with _store_lock:
        return dict(_progress_store.get(file_id, {})) or None


def del_progress(file_id):
    """
    删除某个文件的进度记录
    """
    with _store_lock:
        _progress_store.pop(file_id, None)


def get_all_progress():
    """
    获取所有文件的进度（用于批量轮询）
    """
    with _store_lock:
        return {fid: dict(p) for fid, p in _progress_store.items()}
