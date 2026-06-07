<div align="center">

# 文剧智转 · Novel2Script-AI

**AI-Powered Novel-to-Screenplay Conversion Engine**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5+-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

基于大语言模型的长篇小说→影视剧本智能转换系统，支持分片解析、人物缓存锚定、SSE 实时流式进度、YAML 三层防护与可视化剧本编辑。

[功能特性](#-功能特性) · [架构设计](#-架构设计) · [快速开始](#-快速开始) · [API 文档](#-api-文档) · [配置说明](#-配置说明)

</div>

---

## ✦ 功能特性

### 核心能力

- **智能剧本转换** — 基于 LLM 将长篇小说自动转换为符合影视工业规范的 YAML 结构化剧本，输出包含场次、场景属性、剧情单元、人物库等完整剧本要素
- **长文本分片引擎** — 超过 2500 字的文本自动进入分片处理管线：滑动窗口切割 → 人物预提取 → 逐片 AI 转换（注入人物缓存 + 上文摘要）→ 全局合并重排
- **YAML 三层防护** — 提示词强约束 → 后置语法校验与自动修复（字段名映射、缩进修复、缺失字段注入）→ 兜底补全，确保 LLM 输出可解析
- **心理占比巡检** — 自动检测 `psy` 类型单元占比，超过 8% 时触发二次 LLM 精简，避免心理描写过度

### 接口与兼容

- **多模型兼容** — 支持所有 OpenAI 兼容接口（OpenAI / Claude / 通义千问 / DeepSeek / Gemini 等），前端可动态配置 API Key / Base URL / 模型名
- **连通性测试** — 独立的 LLM 接口测试端点，一键验证 API Key / Base URL / 模型名有效性
- **多格式输入** — 支持粘贴文本 / 上传 `.txt` / `.md` / `.epub` 文件

### 交互体验

- **SSE 流式进度** — 基于 `asyncio.Queue` 的实时事件推送，展示预处理 / 人物提取 / 分片解析 / 合并 / 精简等全链路阶段进度
- **可视化编辑** — 场次 / 单元的增删改查，人物名称自动补全，单元类型着色（动作蓝 / 台词绿 / 旁白灰 / 心理橙）
- **YAML 导出** — 一键导出标准 YAML 格式剧本文件
- **电影级 UI** — 暗色主题 + 暖金强调色 + 胶片穿孔装饰

### 稳定性保障

- **智能限流与重试** — 429 速率限制指数退避（5s → 10s → 20s）+ 连接超时独立退避（2s → 4s → 8s）+ ±25% 随机抖动防惊群
- **字段名自动映射** — 上下文感知的字段名修复，全局无歧义映射 + 缩进层级判断，容错 AI 输出的非标准字段命名

---

## ✦ 架构设计

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3 + TS)                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ HomeView │  │ PreviewView  │  │  EditView    │  │ Components │  │
│  │ 上传+配置 │  │  只读预览     │  │  可视化编辑   │  │ 卡片/标签  │  │
│  └─────┬────┘  └──────┬───────┘  └──────┬───────┘  └────────────┘  │
│        └───────────────┼────────────────┘                           │
│                   Axios / Fetch SSE                                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │ /api
┌────────────────────────┼────────────────────────────────────────────┐
│                   Backend (FastAPI)                                   │
│  ┌─────────────────────┼──────────────────────────────┐              │
│  │              script_routes.py                       │              │
│  │   /convert  /convert-stream  /test-connection      │              │
│  │   /schema   /validate                                │              │
│  └──────┬──────────────┬──────────────┬───────────────┘              │
│         │              │              │                              │
│  ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐                       │
│  │ Preprocessor │ │ AI Parser  │ │   YAML     │                       │
│  │ 文本预处理    │ │ 核心解析    │ │  Renderer  │                       │
│  │ · 章节识别    │ │ · 分片引擎  │ │  格式渲染   │                       │
│  │ · 广告过滤    │ │ · 人物缓存  │ │            │                       │
│  │ · 内容清洗    │ │ · 三层防护  │ │            │                       │
│  └─────────────┘ │ · 智能限流  │ └────────────┘                       │
│                  └──────┬──────┘                                       │
│                         │                                              │
│                  ┌──────▼──────┐                                       │
│                  │  Prompts    │                                       │
│                  │ · system    │                                       │
│                  │ · chunk     │                                       │
│                  │ · character│                                       │
│                  │ · psy      │                                       │
│                  └────────────┘                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 核心处理管线

```
用户输入小说文本
       │
       ▼
 ┌─────────────┐
 │  文本预处理   │  章节识别 · 广告过滤 · 内容清洗
 └──────┬──────┘
        │
        ▼
   文本长度判断
   ┌────┴─────┐
   ▼          ▼
 ≤2500字    >2500字
 单次调用    分片处理
   │          │
   │    ┌─────▼──────────────────────────────┐
   │    │ 1. 前置人物预提取 (LLM, temp=0.1)  │
   │    │    采样首3000字 + 尾1500字          │
   │    │ 2. 滑动分片 (2500字/片, 500字重叠)  │
   │    │ 3. 逐片 AI 转换                    │
   │    │    ├ 注入 CharacterCache            │
   │    │    ├ 注入上文摘要 + 已确定上下文     │
   │    │    └ 流式接收 + SSE 进度推送        │
   │    │ 4. 全局合并 (ID重排/人物去重/场景重编)│
   │    │ 5. 心理占比巡检 (psy>8% → 二次精简) │
   │    └─────┬──────────────────────────────┘
   │          │
   └────┬─────┘
        │
        ▼
 ┌─────────────┐
 │ YAML 三层防护 │  提示词约束 → 语法修复 → 兜底补全
 └──────┬──────┘
        │
        ▼
 ┌─────────────┐
 │  输出结果     │  结构化数据 + YAML 文本
 └─────────────┘
```

---

## ✦ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行时 |
| FastAPI | 0.115.0 | Web 框架 & RESTful API |
| Uvicorn | 0.30.0 | ASGI 服务器 |
| Pydantic | 2.9.0 | 数据校验 & Schema 定义 |
| OpenAI SDK | 1.50.0 | LLM API 调用（兼容 OpenAI 接口） |
| PyYAML | 6.0.1 | YAML 序列化 / 反序列化 |
| python-multipart | 0.0.12 | 文件上传支持 |
| httpx | 0.27.0 | HTTP 客户端（OpenAI SDK 依赖） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.5.0 | 前端框架（Composition API） |
| TypeScript | ~5.6.0 | 类型安全 |
| Vite | ^6.0.0 | 构建工具 & 开发服务器 |
| Element Plus | ^2.9.0 | UI 组件库 |
| Vue Router | ^4.4.0 | 路由管理 |
| Axios | ^1.7.0 | HTTP 请求 |
| @element-plus/icons-vue | ^2.3.0 | 图标库 |

---

## ✦ 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 一个 OpenAI 兼容的 API Key

### 1. 克隆项目

```bash
git clone https://github.com/your-org/Novel2Script-AI.git
cd Novel2Script-AI
```

### 2. 启动后端

```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务（默认端口 8000）
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后可访问 Swagger API 文档：`http://localhost:8000/docs`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，已配置代理将 `/api` 请求转发至后端。

### 4. 配置 AI 模型

在前端首页的 **AI 配置** 面板中填写：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| API Key | LLM 服务密钥 | `sk-xxxxxxxx` |
| Base URL | API 地址（需兼容 OpenAI 接口格式） | `https://api.openai.com/v1` |
| Model | 模型名称 | `gpt-4o-mini` |

也可通过环境变量预设默认值（见[配置说明](#-配置说明)）。

---

## ✦ 项目结构

```
Novel2Script-AI/
├── backend/                            # Python 后端
│   ├── main.py                         # FastAPI 应用入口 & CORS 配置
│   ├── config.py                       # 配置管理（AI 参数 / 应用参数 / CORS）
│   ├── requirements.txt                # Python 依赖
│   ├── api/routes/
│   │   └── script_routes.py            # RESTful API 路由（5 个接口）
│   ├── schemas/
│   │   └── script_schema.py            # Pydantic v2 数据模型（7 个模型类）
│   ├── services/
│   │   ├── text_preprocessor.py        # 小说文本预处理（章节识别 / 广告过滤 / 清洗）
│   │   ├── ai_parser_service.py        # AI 核心解析引擎（分片 / 缓存 / 限流 / 防护）
│   │   └── yaml_renderer.py            # YAML 格式渲染输出
│   └── prompts/
│       ├── system_prompt.txt           # 单次解析系统提示词
│       ├── system_prompt_chunk.txt      # 分片解析系统提示词（含占位符注入）
│       ├── character_extraction_prompt.txt  # 人物信息提取提示词
│       └── psy_refinement_prompt.txt    # 心理占比精简提示词
│
├── frontend/                           # Vue3 前端
│   ├── src/
│   │   ├── main.ts                     # 应用入口
│   │   ├── App.vue                     # 根组件（暗色主题 / 全局布局 / CSS 变量）
│   │   ├── router/index.ts             # 路由配置（3 页面，懒加载）
│   │   ├── api/script.ts               # Axios API 封装（含 SSE 流式请求）
│   │   ├── types/script.ts             # TypeScript 类型定义（与后端 Schema 对齐）
│   │   ├── views/
│   │   │   ├── HomeView.vue            # 首页（上传 + AI 配置 + 实时进度）
│   │   │   ├── PreviewView.vue         # 预览页（只读结构化展示）
│   │   │   └── EditView.vue            # 编辑页（可视化剧本编辑器）
│   │   └── components/
│   │       ├── CharacterTag.vue        # 人物标签组件
│   │       ├── SceneCard.vue           # 场次卡片组件
│   │       ├── UnitItem.vue            # 剧情单元组件（类型着色）
│   │       └── YamlEditor.vue          # YAML 源码预览 / 编辑
│   └── vite.config.ts                  # Vite 构建配置（代理 / 路径别名）
│
└── .gitignore
```

---

## ✦ API 文档

基础路径：`/api`

### 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/script/convert` | 同步转换 — 输入小说文本或文件，返回结构化 YAML 剧本 |
| `POST` | `/script/convert-stream` | SSE 流式转换 — 实时推送解析进度事件，最终返回完整结果 |
| `POST` | `/script/test-connection` | 连通性测试 — 验证 API Key / Base URL / 模型名是否有效 |
| `GET` | `/script/schema` | 获取 YAML Schema 规范说明文档 |
| `POST` | `/script/validate` | 校验 YAML 内容合法性，返回字段级错误详情 |

### POST `/api/script/convert`

**请求参数**（FormData）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `novel_text` | string | 二选一 | 小说纯文本内容 |
| `file` | file | 二选一 | 支持 `.txt` / `.md` / `.epub` |
| `novel_title` | string | 是 | 小说 / 原著名称 |
| `api_key` | string | 否 | 覆盖默认 API Key |
| `base_url` | string | 否 | 覆盖默认 API 地址 |
| `model_name` | string | 否 | 覆盖默认模型名 |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "yaml_content": "---\nscript_meta:\n  script_title: ...\n...",
    "schema_data": { }
  }
}
```

### POST `/api/script/convert-stream`

SSE 事件流接口，事件格式：

```
event: progress
data: {"stage": "preprocessing", "message": "正在预处理文本..."}

event: progress
data: {"stage": "character_extraction", "message": "正在提取人物信息..."}

event: progress
data: {"stage": "chunk_parsing", "message": "正在解析第 3/12 片...", "progress": 25}

event: progress
data: {"stage": "merging", "message": "正在合并结果..."}

event: result
data: {"success": true, "data": {...}}

event: error
data: {"detail": "错误信息"}
```

### POST `/api/script/test-connection`

**请求参数**（JSON Body）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_key` | string | 是 | API 密钥 |
| `base_url` | string | 是 | API 地址 |
| `model_name` | string | 是 | 模型名称 |

**响应示例**：

```json
{
  "success": true,
  "message": "连接成功，模型 gpt-4o-mini 可用"
}
```

---

## ✦ 配置说明

### 后端配置

通过环境变量覆盖默认 AI 配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OPENAI_API_KEY` | — | API 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 地址 |
| `OPENAI_MODEL_NAME` | `gpt-4o-mini` | 模型名称 |

> 前端界面中填写的配置会覆盖环境变量默认值。

### 核心参数

以下参数定义在 `backend/services/ai_parser_service.py` 中，可根据需要调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_SIZE` | 2500 | 分片大小（字数） |
| `CHUNK_OVERLAP` | 500 | 分片重叠区（字数） |
| `CHAR_EXTRACT_HEAD` | 3000 | 人物提取采样 - 首部字数 |
| `CHAR_EXTRACT_TAIL` | 1500 | 人物提取采样 - 尾部字数 |
| `CHUNK_CALL_INTERVAL` | 0.5 | 分片调用间隔（秒） |
| `PSY_RATIO_THRESHOLD` | 0.08 | 心理占比巡检阈值 |
| `CONN_BACKOFF_START` | 2.0 | 连接错误退避初始等待（秒） |
| `CONN_BACKOFF_MAX` | 30.0 | 连接错误退避最大等待（秒） |
| `CONN_MAX_RETRIES` | 3 | 连接错误最大重试次数 |
| `BACKOFF_JITTER_RATIO` | 0.25 | 退避随机抖动比例 |

### 重试策略

| 错误类型 | 退避策略 | 最大重试 |
|----------|----------|----------|
| `RateLimitError` (429) | 5s → 10s → 20s + ±25% jitter | 3 次 |
| `APIConnectionError` / `APITimeoutError` | 2s → 4s → 8s + ±25% jitter | 3 次 |
| 其他异常 | 不重试，直接抛出 | — |

---

## ✦ 剧本输出规范

AI 生成的剧本遵循以下 YAML Schema：

```yaml
script_meta:                        # 全局元数据
  script_title: "剧本名称"
  original_novel_title: "原著名"
  chapter_range: "第1-5章"
  create_time: "2026-01-01"
  script_type: "短剧"
  version: "v1.0"

script_scenes:                      # 场次列表
  - scene_id: 1
    scene_serial: "S01"
    scene_attr:                     # 场景属性
      location: "咖啡厅"
      scene_type: "内景"            # 内景 / 外景 / 内外
      time_type: "日"               # 日 / 夜 / 黎明 / 黄昏
    scene_summary: "主角初次相遇..."
    content_units:                   # 剧情单元
      - unit_id: 1
        unit_type: "action"         # action / dialogue / narration / psy
        character: "林晓"
        content: "推门走进..."
    scene_note: ""

global_characters:                   # 全局人物库
  - char_id: 1
    char_name: "林晓"
    char_profile: "25岁，设计师..."

adapt_rule_note: "改编说明..."
```

### 剧情单元类型

| 类型 | 标识 | 说明 | 前端着色 |
|------|------|------|----------|
| 动作 | `action` | 人物肢体动作、神态、行为表现 | 蓝色 |
| 台词 | `dialogue` | 人物对话、口语表达 | 绿色 |
| 旁白 | `narration` | 剧情旁白、场景补充、过渡解说 | 灰色 |
| 心理 | `psy` | 关键人物心理活动（仅保留核心所需） | 橙色 |

---

## ✦ 使用流程

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│  ① 上传输入   │ ──▶ │  ② AI 智能转换    │ ──▶ │  ③ 结构化预览  │ ──▶ │  ④ 编辑导出   │
│              │     │                  │     │              │     │              │
│ · 粘贴文本    │     │ · 文本预处理       │     │ · 元数据展示   │     │ · 可视化编辑  │
│ · 上传文件    │     │ · 人物预提取       │     │ · 人物库浏览   │     │ · YAML 导出  │
│ .txt/.md/.epub│    │ · 分片 AI 转换     │     │ · 场次列表查看 │     │              │
│              │     │ · 全局合并重排     │     │ · 实时进度追踪 │     │              │
│              │     │ · 心理占比巡检     │     │              │     │              │
└──────────────┘     └──────────────────┘     └──────────────┘     └──────────────┘
```

---

## ✦ License

[MIT License](LICENSE)
