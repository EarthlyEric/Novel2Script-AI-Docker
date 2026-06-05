# 文剧智转 (Novel2Script-AI)

<p align="center">
  <strong>AI 驱动的小说转影视剧本工具</strong><br>
  将长篇小说文本智能转换为标准化影视短剧剧本 · 支持多模型 · 可视化编辑
</p>

<p align="center">
  <a href="#功能特性">特性</a> •
  <a href="#技术栈">技术栈</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#项目结构">项目结构</a> •
  <a href="#api-接口">API</a> •
  <a href="#使用流程">使用流程</a>
</p>

---

## 功能特性

- **智能转换** — 基于 AI 大模型，将长篇小说自动转换为符合影视规范的 YAML 结构化剧本
- **多章节批量** — 支持一次性输入多章内容（3章+），自动保持剧情连贯、场景合理拆分
- **多格式输入** — 支持粘贴文本 / 上传 `.txt`、`.md`、`.epub` 文件（EPUB 前端原生解析）
- **多模型兼容** — 支持 OpenAI、Claude、通义千问、DeepSeek、Gemini 等 OpenAI 兼容接口
- **结构化预览** — 剧本元数据、人物库、场次列表、剧情单元分级展示
- **可视化编辑** — 场次/单元的增删改查，支持人物名称自动补全
- **YAML 导出** — 一键导出标准 YAML 格式剧本文件
- **电影级 UI** — 暗色主题 + 暖金强调色 + 胶片穿孔装饰

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行时 |
| FastAPI | 0.115.0 | Web 框架 & RESTful API |
| Uvicorn | 0.30.0 | ASGI 服务器 |
| Pydantic | 2.9.0 | 数据校验 & Schema 定义 |
| OpenAI SDK | 1.50.0 | 大语言模型 API 调用 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.5.0 | 前端框架 (Composition API) |
| TypeScript | ~5.6.0 | 类型安全 |
| Vite | ^6.0.0 | 构建工具 & 开发服务器 |
| Element Plus | ^2.9.0 | UI 组件库 |
| JSZip | ^3.10.1 | EPUB 电子书解压解析 |

## 快速开始

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
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务（默认端口 8000）
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

后端启动后可访问 Swagger API 文档：`http://localhost:8000/docs`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，已配置代理将 `/api` 请求转发至后端。

### 4. 环境变量（可选）

后端支持通过环境变量覆盖默认 AI 配置：

```bash
export OPENAI_API_KEY="your-api-key"        # API 密钥
export OPENAI_BASE_URL="https://api.openai.com/v1"  # API 地址
export OPENAI_MODEL_NAME="gpt-4o-mini"       # 模型名称
```

> 也可以在前端界面中直接填写 API 配置，会覆盖后端默认值。

## 项目结构

```
Novel2Script-AI/
├── backend/                        # Python 后端
│   ├── main.py                     # FastAPI 应用入口
│   ├── config.py                   # 配置管理（AI 参数 / CORS）
│   ├── requirements.txt            # Python 依赖
│   ├── api/routes/
│   │   └── script_routes.py        # 剧本转换 API 路由（3 个接口）
│   ├── schemas/
│   │   └── script_schema.py        # Pydantic Schema（7 个模型类）
│   ├── services/
│   │   ├── text_preprocessor.py    # 小说文本预处理
│   │   ├── ai_parser_service.py    # AI 大模型调用与解析
│   │   └── yaml_renderer.py        # YAML 格式渲染输出
│   └── prompts/
│       └── system_prompt.txt       # AI 系统提示词模板
│
├── frontend/                       # Vue3 前端
│   ├── src/
│   │   ├── main.ts                 # 应用入口
│   │   ├── App.vue                 # 根组件（暗色主题 / 全局布局）
│   │   ├── router/index.ts         # 路由配置
│   │   ├── api/script.ts           # Axios API 封装
│   │   ├── types/script.ts         # TypeScript 类型定义
│   │   ├── views/
│   │   │   ├── HomeView.vue        # 上传页（输入 + AI 配置）
│   │   │   ├── PreviewView.vue     # 预览页（只读展示）
│   │   │   └── EditView.vue        # 编辑页（可视化编辑器）
│   │   └── components/
│   │       ├── CharacterTag.vue    # 人物标签组件
│   │       ├── SceneCard.vue       # 场次卡片组件
│   │       ├── UnitItem.vue        # 剧情单元组件
│   │       └── YamlEditor.vue      # YAML 源码预览组件
│   └── vite.config.ts              # Vite 构建配置（含代理）
│
└── .gitignore                      # Git 忽略规则
```

## API 接口

基础路径：`/api`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/script/convert` | **核心转换接口** — 输入小说文本或文件，返回结构化 YAML 剧本 |
| `GET` | `/script/schema` | 获取 YAML Schema 规范说明文档 |
| `POST` | `/script/validate` | 校验 YAML 内容合法性，返回字段级错误详情 |

### POST `/api/script/convert`

**请求参数**（FormData）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `novel_text` | string | 二选一 | 小说纯文本内容 |
| `file` | file | 二选一 | 支持 `.txt` / `.md` / `.epub` |
| `novel_title` | string | 是 | 小说/原著名称 |
| `api_key` | string | 否 | 覆盖默认 API Key |
| `base_url` | string | 否 | 覆盖默认 API 地址 |
| `model_name` | string | 否 | 覆盖默认模型名 |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "yaml_content": "---\nscript_meta:\n  script_title: ...\n...",
    "schema_data": { /* 完整结构化数据 */ }
  }
}
```

## 使用流程

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  ① 上传输入  │ ──▶ │  ② AI 智能转换   │ ──▶ │  ③ 结构化预览  │ ──▶ │  ④ 编辑导出  │
│             │     │                 │     │              │     │             │
│ 粘贴文本     │     │ 多章节处理       │     │ 元数据展示     │     │ 可视化编辑   │
│ 或上传文件   │     │ 场景自动拆分     │     │ 人物库浏览     │     │ YAML 导出   │
│ .txt/.md/.epub│    │ 人物统一规整     │     │ 场次列表查看   │     │             │
└─────────────┘     └─────────────────┘     └──────────────┘     └─────────────┘
```

### 剧本输出结构

AI 生成的剧本遵循以下 YAML Schema：

```yaml
script_meta:                    # 全局元数据
  script_title: "剧本名称"
  original_novel_title: "原著名"
  chapter_range: "第1-5章"
  create_time: "2026-01-01"
  script_type: "短剧"
  version: "v1.0"

script_scenes:                  # 场次列表
  - scene_id: 1
    scene_serial: "S01"
    scene_attr:
      location: "咖啡厅"
      scene_type: "内景"
      time_type: "日"
    scene_summary: "主角初次相遇..."
    content_units:
      - unit_id: 1
        unit_type: "action"      # action / dialogue / narration / psy
        character: "林晓"
        content: "推门走进..."
    scene_note: ""

global_characters:              # 全局人物库
  - char_id: 1
    char_name: "林晓"
    char_profile: "25岁，设计师..."

adapt_rule_note: "改编说明..."
```

### 剧情单元类型说明

| 类型 | 英文标识 | 说明 |
|------|----------|------|
| 动作 | `action` | 人物肢体动作、神态、行为表现 |
| 台词 | `dialogue` | 人物对话、口语表达 |
| 旁白 | `narration` | 剧情旁白、场景补充、过渡解说 |
| 心理 | `psy` | 关键人物心理活动（仅保留核心所需） |

## License

MIT License
