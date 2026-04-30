# 项目永久记忆：文档清洗与 Markdown 编辑系统

> 重要：这是项目的核心记忆文件，所有开发必须严格遵守本文档的要求。

---

## 一、项目基本信息

- **项目名称**：文档清洗与 Markdown 编辑系统
- **本地路径**：`C:\Users\ChengXingYu\Desktop\vip`
- **远程仓库**：无（本地项目）
- **技术栈**：Python Flask + 纯 HTML/JS 前端（无框架）
- **核心原则**：只专注实现功能，不关心分支管理，同事后续会自己集成。

---

## 二、用户信息

- **用户身份**：编程零基础小白
- **沟通要求**：
  - 必须给完整可直接运行的代码，不允许用户修改任何内容
  - 必须给可直接复制的命令，一步一步指导
  - 所有沟通、代码注释、文档必须全中文
- **开发约束**：
  - ❌ 不要讲原理，只给代码和命令
  - ❌ 不要让用户自己修改代码
  - ❌ 不要超出需求范围做多余功能
  - ✅ 代码加详细中文注释
  - ✅ 每完成一步明确告知"完成了什么"和"下一步做什么"

---

## 三、目录结构

```
vip/
├── backend/                    # Python Flask 后端
│   ├── app.py                  # 主入口（运行 python app.py 启动）
│   ├── config.py                # 配置文件（从 .env 读取配置）
│   ├── .env                     # 环境变量（仅 OCR_USE_GPU=true）
│   ├── progress_store.py        # 解析进度内存存储
│   ├── models/
│   │   └── file_model.py        # SQLite 数据库操作
│   ├── routes/
│   │   └── upload_routes.py      # 所有 API 接口
│   └── services/
│       ├── ocr_service.py       # PaddleOCR 图片文字识别（GPU 加速）
│       ├── extractor_service.py  # PDF/Word/Excel/Markdown 内容提取
│       └── cleaner_service.py   # 数据清洗
├── frontend/
│   └── index.html               # 前端页面（纯 HTML + JS，无需构建）
├── uploads/                     # 上传文件存放目录
├── outputs/                     # 导出的 Markdown 文件目录
└── files.db                     # SQLite 数据库（自动生成）
```

---

## 四、已实现功能

### 前端功能（index.html）

| 功能 | 状态 | 说明 |
|------|------|------|
| 文件上传 | ✅ 完成 | 点击或拖拽上传，支持多文件 |
| 格式校验 | ✅ 完成 | 仅允许 pdf/docx/xlsx/png/jpg/jpeg/md |
| 大小校验 | ✅ 完成 | 限制 50MB，超出提示错误 |
| 上传进度条 | ✅ 完成 | 实时显示 0%~100% |
| 文件列表 | ✅ 完成 | 显示所有文件及其状态 |
| 解析进度条 | ✅ 完成 | 每个文件独立进度，500ms 轮询 |
| 状态自动刷新 | ✅ 完成 | 解析完成后停止轮询 |
| 批量删除 | ✅ 完成 | 勾选后删除，有确认弹窗 |
| 单个下载 | ✅ 完成 | 点击文件名旁边的"已完成"徽章 |
| 打包下载全部 | ✅ 完成 | 右上角"打包下载"按钮 |
| Markdown 编辑器 | ✅ 完成 | EasyMDE 左右分栏实时预览 |
| 保存编辑 | ✅ 完成 | PUT /api/file-content/{id} |
| 分享预览弹窗 | ✅ 完成 | 只读模式预览 |
| 错误详情弹窗 | ✅ 完成 | 解析失败时显示错误信息 |

**文件状态流转**：uploading → parsing → done / error

### 后端功能（Flask API）

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/upload` | POST | 上传文件（支持多文件） |
| `/api/files` | GET | 获取文件列表 |
| `/api/download/<id>` | GET | 下载单个 Markdown |
| `/api/download/all` | GET | 打包下载所有完成文件 |
| `/api/delete` | POST | 批量删除文件 |
| `/api/parse-progress` | GET | 轮询解析进度 |
| `/api/file-content/<id>` | GET | 读取 Markdown 内容 |
| `/api/file-content/<id>` | PUT | 保存编辑后的 Markdown |

### 文档解析策略

| 格式 | 引擎 | 特殊说明 |
|------|------|----------|
| PDF（文字版） | pdfminer.six（主力） + PyMuPDF（补漏） | 多进程逐页提取，中文 CID 字体支持最好 |
| PDF（扫描件） | PaddleOCR GPU | 检测到乱码自动降级到 OCR |
| Word（docx） | python-docx | 保留标题层级、加粗、斜体、列表、表格、图片 |
| Excel（xlsx） | openpyxl | 每个工作表转为 Markdown 表格 |
| 图片（png/jpg） | PaddleOCR GPU | RTX 3060 GPU 加速 |
| Markdown | 直接读取 | 原文返回 |
| 数据清洗 | cleaner_service | 去除乱码、统一换行、合并空行、去除多余空格 |

---

## 五、技术细节

### OCR 配置
- **GPU 模式**：启用（RTX 3060，CUDA v11.8）
- **CUDA 路径**：`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin`
- **OCR 库**：PaddleOCR + PaddlePaddle GPU
- **自动降级**：GPU 初始化失败时自动切换到 CPU
- **OCR 参数**：use_angle_cls=True, lang=ch, det_db_thresh=0.3, rec_batch_num=16

### PDF 解析策略
- 策略1：pdfminer.six 整体提取（中文最强）
- 策略2：PyMuPDF 多模式（text/blocks/dict）逐页补漏
- 策略3：PaddleOCR 并行 OCR（扫描件兜底）
- 多进程：`min(cpu_count(), 8)` 个进程并行提取
- OCR 线程数：`cpu_count() * 2`（GPU 模式）或 `cpu_count()`（CPU 模式）

### 数据库
- **引擎**：SQLite（文件数据库 `files.db`）
- **表结构**：id, original_name, stored_name, file_size, file_ext, status, output_path, error_msg, created_at, updated_at
- **状态枚举**：uploading / parsing / done / error

### 进度上报
- **机制**：进度存储在内存字典 `progress_store.py`，前端每 500ms 轮询 `/api/parse-progress`
- **格式**：`{fileId: {total: 100, done: 0~100, stage: "描述文字", pct: 0~100}}`

---

## 六、环境配置

### .env（backend/.env）

```env
# OCR GPU 加速（true = 启用 RTX 3060，false = CPU）
OCR_USE_GPU=true
```

> 注意：其他配置（上传路径、最大文件大小、端口等）使用 config.py 中的默认值，无需修改。

### 默认配置值（config.py）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| UPLOAD_FOLDER | `vip/uploads` | 上传文件存放 |
| OUTPUT_FOLDER | `vip/outputs` | Markdown 输出 |
| MAX_CONTENT_LENGTH | 52428800 (50MB) | 最大文件大小 |
| ALLOWED_EXTENSIONS | pdf,docx,xlsx,png,jpg,jpeg,md | 允许的格式 |
| HOST | 0.0.0.0 | 监听地址 |
| PORT | 5000 | 监听端口 |

---

## 七、启动方式

```powershell
cd C:\Users\ChengXingYu\Desktop\vip\backend
python app.py
```

访问地址：`http://localhost:5000`

---

## 八、常见问题速查

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| 图片 OCR 很慢 | 未使用 GPU | 确认 .env 中 `OCR_USE_GPU=true`，并安装 `paddlepaddle-gpu` |
| PDF 解析全是乱码 | PDF 是扫描件 | 系统会自动降级到 OCR，无需手动处理 |
| 端口 5000 被占用 | 端口冲突 | 修改 `backend/config.py` 中 `PORT = 5001` |
| 状态一直是"解析中" | 后端崩溃 | 重启 `python app.py`，刷新页面 |
| 前端显示 404 | Flask 未运行 | 确认 PowerShell 中 `python app.py` 在运行 |
