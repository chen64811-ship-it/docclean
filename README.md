# 文档清洗与 Markdown 导出系统

> 支持 PDF、Word、Excel、图片（OCR）、Markdown → 可编辑 Markdown

---

## 一、整体目录结构

```
clear_plus/
├── backend/              # Python Flask 后端
│   ├── app.py            # 主入口，运行这个文件即可启动
│   ├── config.py         # 配置文件（路径、限制等）
│   ├── .env              # 环境变量（不要改）
│   ├── requirements.txt  # Python 依赖
│   ├── files.db          # 自动生成，存放文件记录（不要删）
│   ├── services/         # 核心处理服务
│   │   ├── ocr_service.py       # PaddleOCR 图片文字识别
│   │   ├── extractor_service.py # PDF/Word/Excel 内容提取
│   │   └── cleaner_service.py   # 数据清洗
│   ├── routes/           # 接口路由
│   │   └── upload_routes.py
│   └── models/           # 数据模型
│       └── file_model.py
├── frontend/             # 前端界面
│   └── index.html        # 网页界面（双击打开，或由 Flask 提供）
├── uploads/              # 上传的文件存放目录（自动创建）
└── outputs/              # 导出的 Markdown 文件目录（自动创建）
```

---

## 二、安装步骤（一步一步来，不要跳过）

### 第 1 步：安装 Python

打开 PowerShell（Win+R → 输入 `powershell` → 回车），运行：

```powershell
python --version
```

如果没有显示版本号，去 https://www.python.org/downloads/ 下载安装，**安装时勾选"Add Python to PATH"**。

---

### 第 2 步：安装 PaddlePaddle GPU 版本（用于 OCR，有 RTX 3060 用这个）

打开 PowerShell，进入项目目录：

```powershell
cd C:\Users\ChengXingYu\Desktop\kg\clear_plus\backend
```

然后安装 GPU 版本（使用 CUDA）：

```powershell
pip install paddlepaddle-gpu
```

安装完成后验证（看到 `True` 就说明成功了）：

```powershell
python -c "import paddle; print(paddle.__version__)"
```

---

### 第 3 步：安装所有依赖

```powershell
cd C:\Users\ChengXingYu\Desktop\kg\clear_plus\backend
pip install flask flask-cors paddleocr pdfplumber pymupdf python-docx openpyxl python-dotenv werkzeug
```

然后安装 GPU 加速（PaddleOCR 用，RTX 3060 用这个更快）：

```powershell
pip install paddlepaddle-gpu
```

验证是否成功：

```powershell
python -c "import flask; import pdfplumber; import fitz; import docx; import openpyxl; print('全部依赖 OK')"
```

如果显示 `全部依赖 OK` 就说明安装好了。

---

## 三、启动系统

### 方法 1：用 PowerShell 启动（推荐）

```powershell
cd C:\Users\ChengXingYu\Desktop\kg\clear_plus\backend
python app.py
```

看到下面这些字说明启动成功了：

```
==================================================
文档清洗与 Markdown 导出系统
访问地址：http://localhost:5000
==================================================
```

### 方法 2：双击启动

双击文件 `backend/app.py` 即可启动（需要先关联 Python）。

---

## 四、使用方法

### 打开网页

在浏览器里打开：

```
http://localhost:5000
```

### 上传文件

1. 点击虚线区域，或直接把文件拖进去
2. 支持格式：**PDF、Word（.docx）、Excel（.xlsx）、图片（.png/.jpg）、Markdown（.md）**
3. 文件大小不能超过 **50MB**，超过了会提示错误

### 查看状态

上传后，文件列表会显示：
- **上传中** → 文件刚传上去
- **解析中** → 正在提取文字和清洗
- **已完成** → 可以下载了
- **失败** → 出了错误

解析中的文件会自动刷新状态，**完成后会停止刷新**。

### 下载

- 单个文件：点击文件名旁边的**「下载」**按钮
- 全部下载：点击右上角**「打包下载全部」**，会下载一个 zip 文件

### 删除

1. 勾选要删除的文件
2. 点击**「删除」**
3. 会弹出确认框，问你"确定要删除吗？"
4. 点击**「确认删除」**即可

---

## 五、常见问题

### Q：启动后浏览器打开 http://localhost:5000 显示 404？

先确认在 PowerShell 里 `python app.py` 正在运行，没有报错。然后刷新浏览器。

### Q：图片 OCR 识别很慢？

因为用了 CPU。如果有 NVIDIA 显卡，按第二步安装 GPU 版本后会快很多。

### Q：PDF/Word 解析失败？

检查 PDF 是否是文字版（扫描版 PDF 没有文字，只能靠 OCR）。如果 PDF 是扫描的，用图片格式上传效果更好。

### Q：端口 5000 被占用？

打开 `backend/config.py`，把 `PORT = 5000` 改成其他端口，比如 `PORT = 5001`，然后重启。

### Q：文件上传后状态一直是"解析中"？

可能是 Python 程序崩溃了。关掉 PowerShell 窗口，重新 `python app.py`，然后刷新页面看状态。

---

## 六、技术说明（不用看也知道怎么用）

- **后端**：Flask（Python，轻量级 Web 框架）
- **OCR**：PaddleOCR + PaddlePaddle（GPU 加速）
- **PDF 解析**：pdfplumber
- **Word 解析**：python-docx
- **Excel 解析**：openpyxl
- **前端**：纯 HTML + JavaScript，不需要 npm/React
- **数据存储**：SQLite（文件数据库，自动创建在 backend/files.db）
