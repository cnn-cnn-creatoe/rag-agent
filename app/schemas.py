"""
Pydantic schemas for API request/response
v2.0 - 增加 Agentic RAG 支持
"""
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RetrievalMode(str, Enum):
    """检索模式"""
    SIMILARITY = "similarity"
    MMR = "mmr"


class AnswerMode(str, Enum):
    """回答模式"""
    STRICT = "strict"
    BALANCED = "balanced"
    CREATIVE = "creative"


class ChatRequest(BaseModel):
    """聊天请求 v2.0"""
    user_id: str = Field(..., description="用户ID")
    thread_id: str = Field(..., description="会话线程ID")
    message: str = Field(..., description="用户消息")
    top_k: int = Field(default=5, ge=1, le=20, description="检索的文档数量")
    save_to_file: bool = Field(default=False, description="是否保存答案为文件")
    file_name: Optional[str] = Field(default=None, description="保存的文件名（不含扩展名）")
    # v2.1 作为文档保存
    save_as_document: bool = Field(default=False, description="是否将回答保存为结构化文档")
    # v1.2 新增参数
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.SIMILARITY, description="检索模式")
    answer_mode: AnswerMode = Field(default=AnswerMode.STRICT, description="回答模式")
    # v2.0 Agentic 模式
    agentic_mode: bool = Field(default=False, description="是否启用 Agentic RAG 模式")
    max_loops: int = Field(default=2, ge=1, le=5, description="Agentic 模式最大循环次数")


class SourceInfo(BaseModel):
    """来源信息 v1.1 增强"""
    source: str = Field(..., description="文件名")
    chunk_id: str = Field(..., description="切块ID")
    snippet: str = Field(..., description="相关片段")
    score: float = Field(default=0.0, description="相似度分数")
    # v1.3 rerank 字段 (预留)
    rank_before: Optional[int] = Field(default=None, description="重排前排名")
    rank_after: Optional[int] = Field(default=None, description="重排后排名")


class ReasoningStep(BaseModel):
    """推理步骤 v2.0"""
    step: str = Field(..., description="步骤名称")
    query: Optional[str] = Field(default=None, description="检索查询")
    decision: Optional[str] = Field(default=None, description="决策结果")
    loop: Optional[int] = Field(default=None, description="循环次数")


class SavedDocument(BaseModel):
    """保存的文档信息 v2.1"""
    filename: str = Field(..., description="文件名")
    path: str = Field(..., description="文件路径")


class ChatResponse(BaseModel):
    """聊天响应 v2.0 增强"""
    message_id: str = Field(..., description="消息唯一ID")
    answer: str = Field(..., description="AI回答")
    sources: List[SourceInfo] = Field(default_factory=list, description="来源列表")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="置信度")
    saved_file: Optional[str] = Field(default=None, description="保存的文件路径")
    # v2.1 作为文档保存
    saved_document: Optional[SavedDocument] = Field(default=None, description="保存的文档信息")
    # v2.0 Agentic 模式新增
    reasoning_trace: Optional[List[ReasoningStep]] = Field(default=None, description="推理轨迹（仅 Agentic 模式）")
    loops_used: Optional[int] = Field(default=None, description="使用的循环次数（仅 Agentic 模式）")


class StreamEvent(BaseModel):
    """SSE 流式事件"""
    event: str = Field(..., description="事件类型: token/end/error")
    data: dict = Field(default_factory=dict, description="事件数据")


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    message: str
    files: List[str] = Field(default_factory=list)
    ingested: bool = Field(default=False, description="是否已入库")


class IngestResponse(BaseModel):
    """入库响应 v1.2 增强"""
    success: bool
    message: str
    doc_count: int = Field(default=0, description="入库文档数量")
    chunk_count: int = Field(default=0, description="入库切块数量")
    # v1.2 增量入库字段
    processed: int = Field(default=0, description="处理的文件数")
    skipped: int = Field(default=0, description="跳过的文件数")
    added_chunks: int = Field(default=0, description="新增切块数")
    removed_chunks: int = Field(default=0, description="移除切块数")
    elapsed_ms: int = Field(default=0, description="耗时毫秒")


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[str]
    count: int


class FileInfo(BaseModel):
    """文件详情 v1.2"""
    name: str
    hash: Optional[str] = None
    chunks: int = 0
    status: str = Field(default="unknown", description="unknown/indexed/updated/new")
    updated_at: Optional[str] = None


class FileListDetailResponse(BaseModel):
    """文件列表详情响应"""
    files: List[FileInfo]
    count: int


class HealthResponse(BaseModel):
    """健康检查响应 v2.0"""
    status: str
    vectorstore_ready: bool
    doc_count: int
    agentic_enabled: bool = Field(default=False, description="Agentic 模式是否启用")
    langsmith_enabled: bool = Field(default=False, description="LangSmith 是否启用")


class UserProfile(BaseModel):
    """用户偏好配置"""
    user_id: str
    language: str = Field(default="zh-CN", description="首选语言")
    output_style: str = Field(default="详细", description="输出风格: 简洁/详细/学术")
    format: str = Field(default="markdown", description="输出格式: markdown/plain")
    tone: str = Field(default="专业", description="语气: 友好/专业/正式")


class DocContentResponse(BaseModel):
    """文档内容响应 v1.1"""
    name: str
    content: str
    file_type: str


class ChunkContentResponse(BaseModel):
    """切块内容响应 v1.1"""
    name: str
    chunk_id: str
    content: str
    metadata: dict = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    """反馈请求 v1.3"""
    user_id: str
    thread_id: str
    message_id: str
    rating: Literal["up", "down"]
    reason: Optional[str] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    message: str
