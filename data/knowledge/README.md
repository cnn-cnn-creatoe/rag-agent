# 知识库 RAG 助理

基于 LangChain + OpenAI + ChromaDB 的本地知识库问答系统，支持文档上传、向量化入库、智能问答，并带有美观的 Web 界面。

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.1-orange.svg)

## ✨ 功能特性

- 📚 **知识库管理**：支持上传 `.md` / `.txt` 文档，自动切块入库
- 🔍 **智能问答**：基于 RAG 架构，回答准确且带来源引用
- 💾 **交付物生成**：可将回答保存为 Markdown 文档
- 👤 **用户偏好记忆**：支持个性化的语言、风格、语气设置
- 🎨 **现代化 UI**：深色主题，毛玻璃效果，流畅交互

## 🚀 快速开始

### 1. 安装依赖

```bash
# 进入项目目录
cd rag-kb-assistant-ui

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填：OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# 可选：自定义 API 地址（用于代理或兼容 API）
# OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：模型名称
# MODEL_NAME=gpt-3.5-turbo

# 可选：Embedding 模型
# EMBEDDING_MODEL=text-embedding-ada-002

# 可选：文档切块配置
# CHUNK_SIZE=800
# CHUNK_OVERLAP=120
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

### 4. 访问界面

打开浏览器访问：**http://localhost:5001/**

## 📖 使用指南

### 完整操作流程

1. **上传文档**
   - 点击左侧「上传文档」区域，选择 `.md` 或 `.txt` 文件
   - 也可直接拖拽文件到上传区域
   - 点击「上传并入库」按钮

2. **入库（向量化）**
   - 上传时可自动入库
   - 也可点击「重新入库全部文件」手动触发
   - 入库完成后，顶部状态灯变绿

3. **提问**
   - 在右侧输入框输入问题
   - 点击发送或按 Enter 键
   - AI 会基于知识库内容回答，并显示参考来源

4. **保存文档**
   - 勾选「保存为文档」
   - 可选填文件名
   - 回答会自动保存到 `data/outputs/` 目录

### 示例提问

假设您上传了公司产品文档，可以这样提问：

```
1. "我们的产品有哪些核心功能？"
2. "如何配置系统的安全策略？"
3. "请总结一下 API 接口的使用方法"
```

## 📁 项目结构

```
rag-kb-assistant-ui/
├── app/
│   ├── main.py           # FastAPI 应用入口
│   ├── rag.py            # RAG 问答逻辑
│   ├── ingest.py         # 文档入库逻辑
│   ├── vectorstore.py    # 向量存储管理
│   ├── llm.py            # LLM 配置
│   ├── memory.py         # 用户偏好记忆
│   ├── schemas.py        # Pydantic 数据模型
│   ├── utils.py          # 工具函数
│   ├── templates/
│   │   └── index.html    # Web UI 模板
│   └── static/
│       └── app.js        # 前端逻辑
├── data/
│   ├── knowledge/        # 知识库文档存放目录
│   ├── outputs/          # 生成的文档输出目录
│   ├── memory/           # 用户偏好配置存储
│   └── chroma/           # ChromaDB 持久化目录
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web UI 主页 |
| `/health` | GET | 健康检查，返回向量库状态 |
| `/files` | GET | 获取知识库文件列表 |
| `/upload` | POST | 上传文档（支持多文件） |
| `/ingest` | POST | 将知识库文档入库到向量数据库 |
| `/chat` | POST | 知识库问答 |

### /chat 请求示例

```json
{
  "user_id": "user_001",
  "thread_id": "thread_001",
  "message": "请介绍一下系统的主要功能",
  "top_k": 5,
  "save_to_file": true,
  "file_name": "功能介绍"
}
```

### /chat 响应示例

```json
{
  "answer": "根据知识库内容，系统主要功能包括...",
  "sources": [
    {
      "source": "产品手册.md",
      "chunk_id": "产品手册.md_chunk_0",
      "snippet": "系统提供以下核心功能..."
    }
  ],
  "saved_file": "data/outputs/功能介绍_20240115_143022.md"
}
```

## ⚙️ 配置说明

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | ❌ | - | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | ❌ | - | 自定义 API 地址 |
| `MODEL_NAME` | ❌ | gpt-3.5-turbo | 聊天模型 |
| `EMBEDDING_MODEL` | ❌ | text-embedding-ada-002 | 向量化模型 |
| `CHUNK_SIZE` | ✅ | 800 | 文档切块大小 |
| `CHUNK_OVERLAP` | ✅ | 120 | 切块重叠字符数 |

### 用户偏好

用户偏好存储在 `data/memory/profile_{user_id}.json`，支持以下设置：

- `language`: 首选语言（如 zh-CN, en-US）
- `output_style`: 输出风格（简洁/详细/学术）
- `format`: 输出格式（markdown/plain）
- `tone`: 语气（友好/专业/正式）

## 🔧 开发说明

### 本地开发

```bash
# 开启热重载
uvicorn app.main:app --reload --port 5001
```

### 日志

系统会输出关键操作日志：
- 文档加载数量
- 切块数量
- 检索命中数量
- 文件保存路径

## 📝 注意事项

1. **API Key 安全**：请勿将 `.env` 文件提交到版本控制
2. **文件格式**：仅支持 `.md` 和 `.txt` 格式
3. **向量库状态**：首次使用需要先上传文档并入库
4. **内存占用**：大量文档入库可能需要较多内存

## 🐛 常见问题

**Q: 提示"知识库尚未初始化"？**
A: 请先上传文档并点击「上传并入库」或「重新入库全部文件」

**Q: 入库失败？**
A: 检查 `data/knowledge/` 目录是否有文档，以及 OpenAI API Key 是否正确

**Q: 回答不准确？**
A: 尝试上传更多相关文档，或调整提问方式

## 📄 许可证

MIT License

