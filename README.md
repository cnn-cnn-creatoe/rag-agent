# 知识库助手 v2.0

**AI 知识工作台 · Agentic RAG**

> 一个基于私有文档的智能问答与分析工作台，支持**证据引用**与**自动再检索**。

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.2-orange.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple.svg)
![Version](https://img.shields.io/badge/Version-2.0.0-brightgreen.svg)

---

## 🎯 30 秒了解这个项目

```
这是一个 AI 知识工作台，用户可以上传自己的文档，
系统基于 RAG 和 Agentic 架构进行问答，
所有回答都有可核验的来源，并且在资料不足时会自动再检索，保证可信度。
```

### 核心能力

| 能力 | 说明 |
|------|------|
| **Agentic RAG** | 自动检查回答质量，证据不足时多轮检索 |
| **证据可追溯** | 每个回答都有来源，可点击查看原文 |
| **置信度评估** | 高/中/低可信度标签，低置信度自动兜底 |

> 📖 **了解系统边界**：查看 [安全与边界说明](SAFETY.md) 了解系统在不同状态下的行为规则。

---

## ⚡ 快速体验

### 1. 安装并启动

```bash
# 克隆项目
git clone <your-repo-url>
cd rag-kb-assistant-ui

# 安装依赖
pip install -r requirements.txt

# 配置 API Key（最小配置）
echo "OPENAI_API_KEY=your-key-here" > .env

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 5001
```

### 2. 打开浏览器

访问 **http://localhost:5001/**

### 3. 推荐示例（直接体验核心能力）

打开界面后，你会看到 3 个推荐示例，点击即可快速体验：

| 示例 | 问题 | 体验能力 |
|------|------|----------|
| **理解系统** | "请介绍这个系统的主要功能，并说明每个功能的使用场景。" | 基础问答 |
| **严谨问答** | "根据知识库内容，总结核心要点，并给出引用来源。" | 证据引用 |
| **Agentic 能力** | "如果资料不足，请自动补充检索并给出更严格的回答。" | 自动再检索 |

---

## 📸 功能亮点

### 1. 证据可追溯

每条回答都显示参考来源，包含：
- 来源文件名
- 相关度评分
- 原文片段

点击「查看原文」可在侧边栏预览完整文档，并高亮匹配内容。

### 2. 置信度评估

| 置信度 | 含义 | 系统行为 |
|--------|------|----------|
| 🟢 高可信 | 证据充分 | 正常输出 |
| 🟡 中可信 | 证据基本足够 | 提示结合实际判断 |
| 🔴 待补充 | 证据不足 | 兜底模板 + 建议补充文档 |

### 3. Agentic RAG（v2.0）

传统 RAG 只检索一次。Agentic RAG 会：

```
1. 检索文档 → 生成草稿
2. 自动检查：每个声明是否有证据？
3. 证据不足？→ 优化检索词 → 再次检索
4. 最多循环 N 次，确保回答质量
```

启用方式：勾选「Agentic 模式」复选框

### 4. LangSmith 追踪

配置后自动记录：
- 每次检索调用
- LLM 推理过程
- 完整 Agentic 循环轨迹

### 5. 保存为文档

勾选「保存为文档」后，回答将自动生成结构化 Markdown 文档，保存到 `data/outputs/` 目录。

文档包含：
- 完整问题与回答
- 置信度评估
- 引用来源列表
- 会话元信息

---

## 🔄 重新索引（Reindex）

### 什么是重新索引？

重新索引是一个**全量重建**操作，会清空当前所有向量索引，然后重新处理 `data/knowledge/` 目录下的所有文档。

### 什么时候需要重新索引？

| 场景 | 是否需要重新索引 |
|------|------------------|
| **上传新文档** | ❌ 不需要（上传时自动处理） |
| **修改了已有文档内容** | ✅ 需要 |
| **调整了切块大小（CHUNK_SIZE）** | ✅ 需要 |
| **更换了 Embedding 模型** | ✅ 需要 |
| **升级了系统版本** | ⚠️ 建议执行 |
| **向量索引出现异常** | ✅ 需要 |

### 与「上传并入库」的区别

| 操作 | 行为 | 适用场景 |
|------|------|----------|
| **上传并入库** | 增量更新，只处理新文件 | 日常添加文档 |
| **重新索引** | 全量重建，清空后重新处理所有文档 | 配置变更、文档修改 |

### 操作步骤

1. 点击左下角「重新索引」按钮
2. 确认弹窗中点击「确认重新索引」
3. 等待索引完成（顶部会显示进度状态）
4. 完成后显示索引结果（文档数、文本块数）

⚠️ **注意**：索引过程中会暂时禁用上传和问答功能。

---

## 📁 项目结构

```
rag-kb-assistant-ui/
├── app/
│   ├── main.py           # FastAPI 应用
│   ├── rag.py            # RAG 问答逻辑
│   ├── agentic_rag.py    # LangGraph Agentic RAG
│   ├── ingest.py         # 文档入库
│   ├── vectorstore.py    # 向量存储 (ChromaDB)
│   ├── llm.py            # LLM 配置
│   ├── schemas.py        # 数据模型
│   ├── utils.py          # 工具函数
│   ├── templates/
│   │   └── index.html    # Web UI
│   └── static/
│       ├── app.js        # 前端逻辑
│       └── ui_texts.js   # UI 文案集中管理
├── data/
│   ├── knowledge/        # 知识库文档
│   ├── outputs/          # 生成的文档
│   └── chroma/           # 向量数据库
├── scripts/
│   └── eval.py           # 评估脚本
├── requirements.txt
├── env.example
└── README.md
```

---

## ⚙️ 配置说明

### 最小配置

```env
OPENAI_API_KEY=your-api-key
```

### 完整配置

```env
# ====== 必填 ======
OPENAI_API_KEY=your-api-key

# ====== 可选：模型配置 ======
MODEL_NAME=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# ====== 可选：RAG 参数 ======
RAG_MIN_SCORE=0.25          # 最低相关度分数
RAG_MIN_SOURCES=1           # 最少来源数
RAG_AGENTIC_ENABLED=false   # 全局启用 Agentic
RAG_AGENTIC_MAX_LOOPS=2     # 最大循环次数

# ====== 可选：LangSmith 追踪 ======
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=rag-kb-assistant
```

---

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web UI |
| `/health` | GET | 健康检查 |
| `/files` | GET | 文件列表 |
| `/files/{filename}` | DELETE | 删除文档 |
| `/upload` | POST | 上传文档 |
| `/ingest` | POST | 重新索引（全量重建） |
| `/chat` | POST | 问答（支持 save_as_document） |
| `/chat/stream` | POST | 流式问答 (SSE) |
| `/doc` | GET | 文档原文 |

### /chat 请求示例

```json
{
  "user_id": "user_001",
  "thread_id": "thread_001",
  "message": "请介绍系统功能",
  "top_k": 5,
  "agentic_mode": true,
  "save_as_document": true
}
```

### /chat 响应示例

```json
{
  "message_id": "uuid...",
  "answer": "系统主要功能包括...",
  "sources": [
    {
      "source": "README.md",
      "chunk_id": "chunk_0",
      "snippet": "...",
      "score": 0.82
    }
  ],
  "confidence": "high",
  "saved_document": {
    "filename": "2026-01-系统功能.md",
    "path": "data/outputs/2026-01-系统功能.md"
  },
  "reasoning_trace": [
    {"step": "retrieve", "query": "系统功能"},
    {"step": "draft"},
    {"step": "critique", "decision": "final"}
  ]
}
```

---

## 🔬 评估脚本

```bash
# 准备评估问题（编辑 data/eval/questions.jsonl）
{"question": "系统有哪些功能？"}
{"question": "如何上传文档？"}

# 运行评估
python scripts/eval.py

# Agentic 模式评估
python scripts/eval.py --agentic

# 查看结果
cat data/eval/results.jsonl
```

---

## 📋 版本历史

| 版本 | 主要更新 |
|------|----------|
| **v2.2** | 侧边栏收起/展开 + 删除文档 + 空知识库防护 + 安全边界文档 |
| v2.1 | 保存为文档功能 + 重新索引完善 |
| v2.0 | Agentic RAG + LangSmith + 企业级 UI |
| v1.1 | 流式输出 + 置信度 + 原文预览 |
| v1.0 | 基础 RAG 问答 |

---

## 🚀 技术栈

- **后端**：FastAPI + LangChain + LangGraph
- **向量库**：ChromaDB
- **前端**：原生 JS + Tailwind CSS
- **追踪**：LangSmith

---

## 🛡️ 安全与系统边界

系统设计遵循「诚实透明」原则，在以下情况会主动限制或拒绝回答：

| 场景 | 系统行为 |
|------|----------|
| 知识库为空 | 禁用问答、严格模式、文档导出 |
| 检索无结果 | 标记为「低置信度」，不显示来源 |
| 严格模式失败 | 明确告知失败，不伪装成功 |

详细说明请查看：**[📖 安全与系统边界说明（SAFETY.md）](SAFETY.md)**

该文档包含：
- 知识库不同状态下的系统行为规则
- 引用来源的可信性约束
- 删除文档与索引一致性说明
- 系统不保证的能力边界
- 面向用户的透明性设计

---

## 📄 许可证

MIT License
