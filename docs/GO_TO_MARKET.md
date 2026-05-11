# DocClean 项目海外售卖商业计划书

> 更新日期：2026-05-09
> 项目代号：DocClean — 多格式文档清洗与 Markdown 导出系统
> 仓库：https://git.kitchain.cn/chenxingyu/clear_plus
> 技术栈：Python Flask + PaddleOCR GPU + 纯 HTML/JS 前端 + SQLite

---

## 一、项目核心能力总结

| 能力 | 说明 | 完成度 |
|------|------|--------|
| 文件解析 | PDF（文字版 + 扫描件OCR）、Word（docx）、Excel（xlsx）、图片（png/jpg）、Markdown | ✅ 完成 |
| OCR 引擎 | PaddleOCR + RTX 3060 GPU 加速，支持中英文混合识别 | ✅ 完成 |
| 数据清洗 | 去乱码、去多余空格空行、排版整理 | ✅ 完成 |
| 格式输出 | 统一转换为 Markdown，可在线编辑预览，支持导出 PDF | ✅ 完成 |
| RAG 知识库 | TF-IDF 关键词检索 + LLM 智能问答（MiniMax API） | ✅ 完成 |
| AI 分类 | Excel 大纲自动分类，兼容任意行业 | ✅ 完成 |
| 书籍编译 | Word 大纲 → 匹配 Markdown → 编译成书，Notion 风格拖拽编辑器 | ✅ 完成 |
| 国际化 | 前端 HTML + 所有 API 响应 + 后端日志，**全部英文** | ✅ 完成 |
| 行业兼容 | 代码不做任何行业假设，餐饮/金融/法律/学术全兼容 | ✅ 完成 |

---

## 二、海外市场分析

### 2.1 有没有人在卖类似产品？

**有，而且市场不小。** 以下是海外已知的同类竞品：

| 竞品 | 定价 | 特点 | DocClean 的差异化优势 |
|------|------|------|----------|
| **Mathpix** | $4.99~$49.99/月 | 图片/PDF转LaTeX/Markdown | 支持更多格式，可私有化部署，无需上传云端 |
| **Marker（开源）** | 免费 | PDF转Markdown，需自己部署 | 多了OCR、Word/Excel、Web界面、RAG知识库 |
| **Docparser** | $39~$149/月 | 云端PDF/文档解析API | 本地运行，数据不出本机，适合合规场景 |
| **Zamzar** | $9~$25/月 | 在线文件格式转换 | PaddleOCR 中文识别远优于 Tesseract |
| **Smallpdf** | $9~$12/月 | PDF工具合集 | Markdown 输出质量更高，支持在线编辑 |
| **Nanonets OCR** | $0.3/页起 | 企业级OCR API | 一次性付费/私有部署，长期成本更低 |

### 2.2 市场机会在哪里？

1. **AI/LLM 训练数据预处理**：大量公司在用文档训练AI模型，需要把PDF/Word转成干净的Markdown。**这是目前最大的需求场景。**
2. **技术文档团队**：开源项目、SaaS公司需要把各种格式的文档统一成Markdown发布。
3. **学术研究者**：把论文PDF转成可编辑格式做笔记、做文献综述。
4. **数据隐私敏感客户**：银行、律所、医院不愿意把文件上传到云端（Mathpix/Docparser 等），需要本地部署方案——**这是 DocClean 最大的卖点**。
5. **中英双语场景**：PaddleOCR 对中文的识别效果比 Tesseract/Google OCR 好一个量级，中英双语文档处理有独特优势，海外华人/东南亚市场是天然切入点。

---

## 三、优势分析（为什么能卖）

| 优势 | 详细说明 |
|------|----------|
| **本地部署 + 数据安全** | 不需要上传到第三方服务器。律所/医院/银行最看重的就是数据不出内网 |
| **PaddleOCR 中文最强** | 海外竞品多用 Tesseract/Google OCR，中文OCR远不如PaddleOCR。中英双语场景无人能敌 |
| **全格式覆盖** | PDF + Word + Excel + 图片 + Markdown，一个工具解决所有文档转换 |
| **内置 Markdown 编辑器** | 解析完直接在线编辑，不需要导出再导入到别的编辑器 |
| **GPU 加速** | RTX 3060 批量处理速度远超纯CPU方案，企业自备显卡即可 |
| **RAG 知识库 + LLM 问答** | 不止是转换工具，还能建知识库做问答。与纯转换工具拉开差距 |
| **AI 自动分类** | Excel 大纲自动分类，兼容任意行业（金融报表、法律文书、学术论文…） |
| **书籍级编译** | 多文档 → 按大纲编译成一本书，支持拖拽排序，这是竞品完全没有的功能 |
| **全英文界面** | 前端 + API + 日志已全面英文化，海外用户零门槛上手 |
| **一次性买断可能** | 不同于竞品的纯订阅制，可以用买断制+年度维护费吸引企业客户 |

---

## 四、劣势与风险分析（当前状态）

| 劣势 | 详细说明 | 严重程度 | 应对方案 |
|------|----------|----------|----------|
| ~~只有中文界面~~ | ~~海外用户看不懂~~ | ~~已解决~~ | ✅ 前端、后端API、日志已全部英文化 |
| **PaddleOCR 安装复杂** | PaddlePaddle GPU 安装依赖 CUDA/cuDNN，海外用户可能搞不定 | ⭐⭐⭐⭐⭐ | 制作 Docker 镜像，一键拉取即用 |
| **Windows Only** | 目前只在 Windows 上测试过，Mac/Linux 用户无法使用 | ⭐⭐⭐⭐ | Docker 可解决 Linux；Mac 需额外适配 |
| **没有 Docker 部署** | 海外技术产品标配 Docker，没有 Docker 等于没有部署方案 | ⭐⭐⭐⭐ | 优先级最高，下一步就做 |
| **英文 OCR 未专项优化** | PaddleOCR 对英文可以正常识别，但参数没有针对英文文档调优 | ⭐⭐⭐ | 调整 PaddleOCR 参数配置，做英文场景专项测试 |
| **没有 API 文档** | SaaS 产品需要 REST API 文档（Swagger/OpenAPI），目前为零 | ⭐⭐⭐ | 后端路由已有，加 Swagger 包装即可 |
| **界面风格朴素** | 纯 HTML/JS + 基础 CSS，海外用户对 UI 期望较高 | ⭐⭐⭐ | 中长期任务，可以用 Tailwind CSS 快速美化 |
| **没有 License 系统** | 没有 License Key 验证、付费墙、用户管理 | ⭐⭐⭐⭐ | 做成 Docker 镜像时内置 License 验证 |
| **品牌信任度为零** | 个人开发者卖 B2B 工具，用户信任门槛高 | ⭐⭐⭐ | 靠 GitHub 开源 + Product Hunt 社区积累口碑 |

---

## 五、三条商业路线

### 路线A：开源 + 付费增值（推荐起步）

```
做法：
1. 代码开源在 GitHub（英文 README + 完善的文档）
2. 提供 Docker 一键部署
3. 免费版：基础 PDF/图片 OCR 转 Markdown
4. 付费版：高级功能（RAG 知识库、AI 分类、书籍编译、批量处理）
5. 企业定制服务另收费（按需开发功能）

定价参考：
- 免费版 Community：基础 PDF/图片 OCR 转 Markdown
- Pro 版：$49/月 或 $199/年（含 RAG + AI 分类 + 批量处理）
- Enterprise 版：$999/年起（私有部署支持 + SLA + 源码）

优点：风险低，靠社区积累信任，开源本身就是最好的营销
缺点：赚钱慢，需要长期维护，可能被白嫖
```

### 路线B：SaaS 在线服务

```
做法：
1. 部署到云端（AWS/GCP/阿里云国际版）
2. 用户上传文件 → 云端 GPU 处理 → 下载 Markdown
3. 按页数/按功能 tier 收费

定价参考：
- Free：每月50页
- Pro：$19/月（500页）
- Business：$99/月（5000页 + API 接入）

优点：持续收入，规模化后利润可观
缺点：GPU 服务器成本高（OCR 吃显存），隐私敏感客户不会用
```

### 路线C：私有化部署 + 一次性买断（利润最高）

```
做法：
1. 打包成 Docker 镜像 / Windows 安装包
2. 卖给企业客户，部署在他们自己的服务器上
3. 一次性收费 + 年度维护费

定价参考：
- 标准版：$999/一次性（单服务器，含1年维护）
- 企业版：$4，999/一次性（不限服务器 + 交付源码）
- 年度维护续费：$299/年（技术更新 + 远程支持）

优点：客单价高，不依赖用户规模，利润清晰
缺点：销售周期长，需要直销能力或代理商
```

### 建议策略

```
阶段1（现在）：路线A起步
→ Docker 化 → GitHub 开源 → Product Hunt 发布
→ 目的：验证海外需求，积累第一批用户和口碑

阶段2（3个月后）：看反馈选方向
→ 如果开发者和技术团队反馈好 → 深化路线A，推 Pro 订阅
→ 如果有企业主动咨询 → 同时走路线C，接私有化部署单
→ 不要急着自己做 SaaS（路线B），GPU 服务器成本会吃掉利润

阶段3（6-12个月后）：建立品牌
→ Gumroad / AWS Marketplace 上架标准产品
→ 积累案例：XX银行/XX律所用 DocClean 做文档管理
→ 有了案例背书，价格可以翻倍
```

---

## 六、海外平台选择

| 平台 | 适合卖什么 | 抽成 | 适合度 | 说明 |
|------|------------|------|--------|------|
| **Gumroad** | 软件许可、数字产品 | 10% | ⭐⭐⭐⭐⭐ | 最简单，支持 License Key 分发 |
| **Product Hunt** | 新品发布、获取早期用户 | 无 | ⭐⭐⭐⭐⭐ | 先在这里亮相，积累初始用户 |
| **GitHub Marketplace** | 开发者工具 | 0%（自己收款） | ⭐⭐⭐⭐ | 适合开源路线，与 GitHub Actions 集成 |
| **AppSumo** | 买断制SaaS工具 | 70%（平台拿大头） | ⭐⭐⭐ | 能快速获客但利润极薄，仅作备选 |
| **Paddle.com** | SaaS 全球收款 + 税务合规 | 5%+$0.5 | ⭐⭐⭐ | 处理全球税务合规，省心 |
| **自建网站 + Stripe** | 完全自主 | 2.9%+$0.3 | ⭐⭐⭐ | 需要自己引流，适合后期 |
| **AWS Marketplace** | 企业级私有部署 | 20% | ⭐⭐⭐ | 触达企业客户，但审核门槛高 |

---

## 七、收入预估（三种场景）

### 场景1：保守（路线A，开源+付费）
- 定价：$49/月 Pro版
- 假设：6个月内积累 **20 个付费用户**
- 月收入：20 × $49 = **$980/月（约 7,100 人民币）**
- 年收入：**$11,760（约 8.5 万人民币）**

### 场景2：中等（路线A+B，SaaS混搭）
- 免费用户：500人 → 付费转化 5% = 25人
- Pro $19/月 × 20 + Business $99/月 × 5 = **$875/月**
- 企业定制项目：$3,000/次 × 每年2单 = $500/月均摊
- 合计：**约 $1,375/月（约 10,000 人民币）**
- 年收入：**$16,500（约 12 万人民币）**

### 场景3：乐观（路线C，私有化部署）
- 每月成交 2 个企业客户
- Enterprise $4,999 × 2 = $9,998/月
- 年度维护费 $299 × 累计客户（第一年12月约24个客户）= $7,176/年
- 年收入：**$120,000+（约 87 万人民币）**

> 注意：场景3需要销售能力。一个人做不了，需要找代理商或合作伙伴。

---

## 八、出海改造路线图（更新版）

### 已完成 ✅

| 改造项 | 完成日期 | 说明 |
|--------|----------|------|
| ✅ **前端界面英文化** | 2026-05-09 | 全部 226 处中文字符串已翻译为英文 |
| ✅ **后端 API 英文化** | 2026-05-09 | 所有 API 响应消息、错误提示、进度阶段已翻译 |
| ✅ **代码行业无关化** | 2026-05-09 | 移除行业特定逻辑，兼容金融/法律/医疗/学术等任意行业 |
| ✅ **AI 分类链路重构** | 2026-05-09 | Excel 分类兼容任意行业，不再报错 |
| ✅ **PaddleOCR 错误修复** | 2026-05-09 | 修复 GPU angle_cls 报错，动态 DLL 路径检测 |
| ✅ **Docker 镜像（CPU + GPU）** | 2026-05-10 | Dockerfile + Dockerfile.gpu + docker-compose.yml，一键部署 |
| ✅ **英文 README + LICENSE** | 2026-05-10 | 完整英文 README（含 API 文档、FAQ、对比表）+ MIT 许可证 |
| ✅ **英文 OCR 参数优化** | 2026-05-10 | 语言自动检测 + 英文专用模型 + 垃圾文本判定修复，纯英文不再误判 |
| ✅ **Swagger API 文档** | 2026-05-10 | 15 个核心端点 OpenAPI 注解 + /api/docs 交互式文档 |
| ✅ **License Key 系统** | 2026-05-10 | HMAC-SHA256 签名验证 + 分级功能控制 + Key 生成工具 |
| ✅ **Mac/Linux 兼容** | 2026-05-10 | macOS 字体支持 + 交叉编译审查 + 平台适配完成 |
| ✅ **UI 美化** | 2026-05-10 | 现代化 SaaS 风格 CSS 重写：Indigo 配色 + CSS 变量体系 + 专业阴影/圆角/间距 + 响应式优化 |
| ✅ **单元测试 + CI/CD** | 2026-05-10 | 67 个 pytest 用例（License/OCR/提取器/PDF）+ GitHub Actions 矩阵（Windows+Linux, py3.10+3.11） |
| ✅ **Product Hunt 上线包** | 2026-05-10 | 完整上线材料：文案/Tagline/Description/截图指南/演示脚本/定价表/Reddit帖子/HN帖子/检查清单 |

### 待完成 — 需手动操作

> 🎉 **所有开发 + 文案已 100% 完成！** 以下 2 项需要你手动操作（必须本地运行）：

| 序号 | 项 | 预估时间 | 说明 |
|------|-----|----------|------|
| 1 | 📸 **截取 5 张截图** | 20 分钟 | `docker-compose up` 后按 `docs/PRODUCT_HUNT_LAUNCH.md` 截图指南操作 |
| 2 | 🎥 **录制 2 分钟演示视频** | 40 分钟 | OBS Studio 录屏，用上面文档的脚本，可加文字叠加层 |

### 下一步行动清单（按顺序）

```
第一步：✅ 所有开发改造（12/12 项全部完成）
├── ✅ 国际化（前端 + 后端）
├── ✅ Docker 镜像
├── ✅ 英文 README + LICENSE
├── ✅ 英文 OCR 优化
├── ✅ Swagger API 文档
├── ✅ License Key 系统
├── ✅ Mac/Linux 兼容
├── ✅ UI 美化
├── ✅ 单元测试 + CI/CD
├── ✅ Product Hunt 上线包（文案+脚本+定价+检查清单）
└── ⬜ 手动操作：截图 + 录视频（看 PRODUCT_HUNT_LAUNCH.md）

第二步：上线发布
├── 在 Product Hunt 发布 → 收集第一波用户
├── 在 Reddit r/selfhosted、r/MachineLearning 发帖
├── 在 Hacker News 发 Show HN
└── 观察反馈，决定下一步走向
```

### 下一步行动清单（按顺序）

```
第一步：✅ Docker 镜像制作（已完成）
├── ✅ Dockerfile（CPU）+ Dockerfile.gpu（CUDA 11.8）
├── ✅ docker-compose.yml 一键编排
├── ✅ .dockerignore + .env.example
└── ✅ fonts-wqy-microhei 中文字体支持

第二步：✅ GitHub 开源准备（已完成）
├── ✅ 英文 README.md（项目介绍、快速开始、API 参考、FAQ、对比表）
├── ✅ LICENSE 文件（MIT）
├── ✅ docs/GO_TO_MARKET.md（海外售卖商业计划书）
└── ✅ GitHub Actions（自动测试 — 67 tests, Win+Linux, py3.10+3.11）

第三步：Product Hunt 发布准备（1天）
├── 产品截图（5张：上传、编辑、RAG问答、书籍编译、PDF查看）
├── 产品描述文案（围绕"本地部署+数据安全"）
├── 演示视频（2分钟，录屏操作全流程）
└── 定价页（Free / Pro / Enterprise）

第四步：上线发布
├── 在 Product Hunt 发布 → 收集第一波用户
├── 在 Reddit r/selfhosted、r/MachineLearning 发帖
├── 在 Hacker News 发 Show HN
└── 观察反馈，决定下一步走向
```

---

## 九、风险与应对

| 风险 | 等级 | 说明 | 应对方案 |
|------|------|------|----------|
| **PyMuPDF AGPL 协议** | 🔴 高 | PyMuPDF 使用 AGPL，商业闭源使用需购买商业许可 | 换用 `pdfplumber`（MIT）或购买 PyMuPDF 商业许可（$399/年） |
| **PaddleOCR 海外信任度** | 🟡 中 | 百度 PaddlePaddle 主要面向中国，海外开发者可能不信任 | 开源透明，Docker 镜像可审计，技术文档写清楚 |
| **单人维护瓶颈** | 🟡 中 | 一个人长期维护海外产品，时差+语言+精力都是挑战 | 先用 Issue 跟踪 + 每周集中处理，有余力再招人 |
| **支付与税务** | 🟡 中 | 收美元涉及跨境收款、VAT/GST 税务 | 用 Paddle.com 处理全球税务合规，自己只做产品 |
| **客服时差** | 🟢 低 | 海外用户期望24h内回复 | 用 GitHub Issues 做公开客服，FAQ 覆盖常见问题 |
| **抄袭风险** | 🟢 低 | 开源后可能被直接复制 | 品牌 + 社区 + 持续迭代是最好的护城河，代码可以抄但信任和口碑抄不走 |
| **GPU 云成本** | 🟡 中 | 若走 SaaS 路线，GPU 服务器（A10/RTX 4090）月成本 $300-$1000 | 初期不做 SaaS，先走私有化部署 + 开源路线避开这个问题 |

---

## 十、最终结论

### 总体判断：✅ 可以卖，前提条件正在逐一满足

**DocClean 的核心价值**是"本地部署 + 多格式 OCR + Markdown 清洗 + AI 知识库"这个组合。在海外的竞品中，这四个能力集于一身的产品确实不存在。数据隐私敏感的企业客户会愿意为这种方案付费。

### 当前进度

```
界面英文化          ████████████ ✅ 100%
后端英文化          ████████████ ✅ 100%
代码行业无关化      ████████████ ✅ 100%
AI分类链路修复      ████████████ ✅ 100%
Docker 镜像         ████████████ ✅ 100%
英文 README         ████████████ ✅ 100%
英文OCR优化         ████████████ ✅ 100%
Swagger API文档     ████████████ ✅ 100%
License Key系统     ████████████ ✅ 100%
跨平台兼容          ████████████ ✅ 100%
UI美化              ████████████ ✅ 100%
单元测试+CI/CD      ████████████ ✅ 100%
Product Hunt 准备   ████████████ ✅ 100%
─────────────────────────────────────
整体出海准备度      ████████████ ✅ 100%
```

### 三个关键决策

1. **先做 Docker，再谈其他。** PaddleOCR 安装是最大痛点，Docker 镜像一键部署是解决这个痛点的唯一方案。没有 Docker，海外用户根本不会尝试你的产品。

2. **宣传核心词：Privacy-First + Local-First。** "Your documents never leave your server" —— 这是 DocClean 唯一能碾压 Mathpix/Docparser/Smallpdf 的武器。所有营销文案都围绕这句话展开。

3. **初期只走路线A，不做SaaS。** GPU 云服务器成本太高，会吃掉所有利润。先让用户在他们自己的机器上跑，验证产品价值后，再考虑要不要上云。

### 最重要的一句话

> **DocClean is not just another file converter. It's a privacy-first document intelligence tool that keeps your data where it belongs — on your own machine. That's the one thing no cloud competitor can offer, and that's what customers will pay for.**

---

## 附录A：竞品速查

| 竞品 | 网址 | 定位 | 与 DocClean 对比 |
|------|------|------|------------------|
| Mathpix | mathpix.com | 图片/PDF 转 LaTeX/Markdown | DocClean 多Word/Excel，可本地部署 |
| Marker（开源） | github.com/VikParuchuri/marker | PDF 转 Markdown | DocClean 多了 GUI + OCR + RAG |
| Docparser | docparser.com | 文档解析 API | DocClean 本地运行，数据不出网 |
| Nanonets | nanonets.com | AI OCR 平台 | DocClean 买断制，长期更便宜 |
| Smallpdf | smallpdf.com | PDF 在线工具 | DocClean Markdown 输出质量更高 |
| Zamzar | zamzar.com | 文件格式转换 | DocClean OCR 能力更强（中英文） |
| ABBYY FineReader | abbyy.com | 专业 OCR 软件 | $199/年起，DocClean 开源免费版即可替代基础功能 |

## 附录B：技术依赖合规检查

| 库 | 用途 | 许可证 | 商业使用 |
|----|------|--------|----------|
| Flask | Web 框架 | BSD-3 | ✅ 自由商用 |
| PaddleOCR | OCR 引擎 | Apache 2.0 | ✅ 自由商用 |
| pdfplumber | PDF 解析 | MIT | ✅ 自由商用 |
| PyMuPDF | PDF/图片处理 | AGPL | ⚠️ 闭源需购买许可（$399/年）或换用 pdfplumber |
| openpyxl | Excel 解析 | MIT | ✅ 自由商用 |
| python-docx | Word 解析 | MIT | ✅ 自由商用 |
| fpdf2 | PDF 生成 | LGPL-3 | ✅ 可商用 |
| EasyMDE | Markdown 编辑器 | MIT | ✅ 自由商用 |
| PDF.js | PDF 查看器 | Apache 2.0 | ✅ 自由商用 |

> ⚠️ 重点：PyMuPDF（fitz）使用 AGPL 协议。如果闭源商业化，有两个选择：(1) 花 $399/年买商业许可；(2) 把 `fitz` 替换成 `pdfplumber`（MIT 协议）。建议上线前完成替换。

---

> 本计划书基于 2026年5月9日的项目状态编写。随着改造推进，市场分析、定价和策略可能需要调整。建议每完成一个里程碑后重新评估。
