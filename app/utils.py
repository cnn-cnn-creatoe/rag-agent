"""
工具函数模块
v1.1 - 增加 request_id 日志、路径安全校验
"""
import os
import re
import uuid
import logging
import hashlib
import contextvars
from datetime import datetime
from pathlib import Path
from typing import Optional

# Request ID 上下文变量
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')


class RequestIdFilter(logging.Filter):
    """日志过滤器，添加 request_id"""
    def filter(self, record):
        record.request_id = request_id_var.get() or '-'
        return True


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
)
logger = logging.getLogger("rag-assistant")
logger.addFilter(RequestIdFilter())


def generate_request_id() -> str:
    """生成请求ID"""
    return str(uuid.uuid4())[:8]


def set_request_id(request_id: Optional[str] = None) -> str:
    """设置当前请求的 request_id"""
    rid = request_id or generate_request_id()
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """获取当前请求的 request_id"""
    return request_id_var.get() or generate_request_id()


def generate_message_id() -> str:
    """生成消息ID"""
    return str(uuid.uuid4())


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """获取数据目录"""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_knowledge_dir() -> Path:
    """获取知识库目录"""
    knowledge_dir = get_data_dir() / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    return knowledge_dir


def get_outputs_dir() -> Path:
    """获取输出目录"""
    outputs_dir = get_data_dir() / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    return outputs_dir


def get_memory_dir() -> Path:
    """获取记忆目录"""
    memory_dir = get_data_dir() / "memory"
    memory_dir.mkdir(exist_ok=True)
    return memory_dir


def get_logs_dir() -> Path:
    """获取日志目录 v1.3"""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_chroma_dir() -> Path:
    """获取 Chroma 持久化目录"""
    chroma_dir = get_data_dir() / "chroma"
    chroma_dir.mkdir(exist_ok=True)
    return chroma_dir


# 允许访问的目录白名单
ALLOWED_DIRECTORIES = {
    'knowledge': get_knowledge_dir,
    'outputs': get_outputs_dir,
    'memory': get_memory_dir,
}


def validate_safe_path(filename: str, directory_type: str = 'knowledge') -> Path:
    """
    验证文件路径是否安全
    
    Args:
        filename: 文件名
        directory_type: 目录类型 (knowledge/outputs/memory)
    
    Returns:
        安全的完整路径
    
    Raises:
        ValueError: 如果路径不安全
    """
    # 检查目录类型
    if directory_type not in ALLOWED_DIRECTORIES:
        raise ValueError(f"不允许的目录类型: {directory_type}")
    
    # 获取基础目录
    base_dir = ALLOWED_DIRECTORIES[directory_type]()
    
    # 检查路径遍历攻击
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        raise ValueError(f"不安全的文件路径: {filename}")
    
    # 检查绝对路径
    if Path(filename).is_absolute():
        raise ValueError(f"不允许绝对路径: {filename}")
    
    # 构建完整路径并解析
    full_path = (base_dir / filename).resolve()
    
    # 确保路径在允许的目录内
    try:
        full_path.relative_to(base_dir.resolve())
    except ValueError:
        raise ValueError(f"路径越界: {filename}")
    
    return full_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        安全的文件名
    """
    # 只保留字母、数字、下划线、连字符、点、中文
    safe_name = re.sub(r'[^\w\-._\u4e00-\u9fff]', '_', filename)
    # 移除连续的下划线
    safe_name = re.sub(r'_+', '_', safe_name)
    # 移除开头和结尾的下划线
    safe_name = safe_name.strip('_')
    return safe_name or 'unnamed'


def generate_file_name(base_name: Optional[str] = None, prefix: str = "answer") -> str:
    """生成文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if base_name:
        safe_name = sanitize_filename(base_name)
        return f"{safe_name}_{timestamp}.md"
    return f"{prefix}_{timestamp}.md"


def calculate_file_hash(file_path: Path) -> str:
    """
    计算文件的 SHA256 哈希值
    
    Args:
        file_path: 文件路径
    
    Returns:
        哈希值字符串
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def save_answer_to_file(answer: str, sources: list, file_name: Optional[str] = None) -> str:
    """
    保存回答到 markdown 文件
    
    Args:
        answer: AI 回答内容
        sources: 来源列表
        file_name: 可选的文件名
    
    Returns:
        保存的文件路径
    """
    outputs_dir = get_outputs_dir()
    final_name = generate_file_name(file_name)
    file_path = outputs_dir / final_name
    
    # 构建 markdown 内容
    content_lines = [
        f"# 知识库问答结果",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 回答",
        f"",
        answer,
        f"",
        f"## 参考来源",
        f""
    ]
    
    if sources:
        for i, src in enumerate(sources, 1):
            content_lines.append(f"### 来源 {i}")
            content_lines.append(f"- **文件**: {src.get('source', 'N/A')}")
            content_lines.append(f"- **切块ID**: {src.get('chunk_id', 'N/A')}")
            score = src.get('score', src.get('relevance_score', 0))
            content_lines.append(f"- **相似度**: {score:.3f}")
            content_lines.append(f"- **片段**: {src.get('snippet', 'N/A')[:200]}...")
            content_lines.append("")
    else:
        content_lines.append("*无相关来源*")
    
    content = "\n".join(content_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"答案已保存到文件: {file_path}")
    return str(file_path)


def generate_document_title(question: str) -> str:
    """
    根据问题生成文档标题
    
    Args:
        question: 用户问题
    
    Returns:
        简短的标题
    """
    # 移除特殊字符，保留关键内容
    title = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
    # 截取前20个字符
    title = title[:20].strip()
    if not title:
        title = "知识库问答"
    return title


def generate_document_filename(question: str) -> str:
    """
    根据问题生成文档文件名
    格式：YYYY-MM-问题摘要.md
    
    Args:
        question: 用户问题
    
    Returns:
        安全的文件名
    """
    # 获取当前日期
    date_prefix = datetime.now().strftime("%Y-%m")
    
    # 从问题中提取关键词作为文件名
    keywords = re.sub(r'[^\w\u4e00-\u9fff]', '-', question)
    keywords = re.sub(r'-+', '-', keywords)
    keywords = keywords.strip('-')[:30]
    
    if not keywords:
        keywords = "document"
    
    # 确保文件名安全
    safe_keywords = sanitize_filename(keywords)
    
    return f"{date_prefix}-{safe_keywords}.md"


def save_answer_as_markdown(
    question: str,
    answer: str,
    sources: list,
    user_id: str,
    thread_id: str,
    confidence: str = "medium",
    agentic_mode: bool = False,
) -> Optional[dict]:
    """
    将回答保存为结构化 Markdown 文档
    
    Args:
        question: 用户原始问题
        answer: AI 回答内容
        sources: 来源列表
        user_id: 用户 ID
        thread_id: 会话 ID
        confidence: 置信度 (high/medium/low)
        agentic_mode: 是否为 Agentic 模式
    
    Returns:
        包含 filename 和 path 的字典，失败时返回 None
    """
    try:
        # 确保输出目录存在
        outputs_dir = get_outputs_dir()
        
        # 生成文件名
        filename = generate_document_filename(question)
        file_path = outputs_dir / filename
        
        # 避免文件名冲突
        counter = 1
        while file_path.exists():
            base_name = filename.rsplit('.', 1)[0]
            filename = f"{base_name}_{counter}.md"
            file_path = outputs_dir / filename
            counter += 1
        
        # 生成标题
        title = generate_document_title(question)
        
        # 置信度映射
        confidence_labels = {
            'high': '高可信',
            'medium': '中可信',
            'low': '待补充',
        }
        confidence_label = confidence_labels.get(confidence, '中可信')
        
        # 模式描述
        mode_label = "Agentic RAG（多轮检索）" if agentic_mode else "标准 RAG"
        
        # 构建 Markdown 内容
        content_lines = [
            f"# {title}",
            "",
            f"> 生成时间：{datetime.now().isoformat()}",
            f"> 用户：{user_id}",
            f"> 会话：{thread_id}",
            f"> 模式：{mode_label}",
            f"> 置信度：{confidence_label}",
            "",
            "---",
            "",
            "## 问题",
            "",
            question,
            "",
            "---",
            "",
            "## 回答",
            "",
            answer,
            "",
            "---",
            "",
            "## 引用来源",
            "",
        ]
        
        if sources:
            for src in sources:
                source_name = src.get('source', 'N/A')
                chunk_id = src.get('chunk_id', 'N/A')
                score = src.get('score', src.get('relevance_score', 0))
                content_lines.append(f"- **{source_name}** · chunk {chunk_id} · 相关度 {score:.2f}")
        else:
            content_lines.append("> 本次回答未找到明确的知识库引用。")
        
        content_lines.append("")
        
        content = "\n".join(content_lines)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"文档已保存: {file_path}")
        
        return {
            "filename": filename,
            "path": str(file_path),
        }
        
    except Exception as e:
        logger.error(f"保存文档失败: {e}")
        return None


def list_knowledge_files() -> list:
    """列出知识库中的所有文件"""
    knowledge_dir = get_knowledge_dir()
    files = []
    for ext in ['*.md', '*.txt']:
        files.extend([f.name for f in knowledge_dir.glob(ext)])
    return sorted(files)


def delete_knowledge_file(filename: str) -> bool:
    """
    删除知识库中的指定文件
    
    Args:
        filename: 要删除的文件名
        
    Returns:
        bool: 删除是否成功
        
    Raises:
        ValueError: 文件名不安全或文件不存在
    """
    try:
        # 安全路径校验
        file_path = validate_safe_path(filename, 'knowledge')
        
        # 检查文件是否存在
        if not file_path.exists():
            raise ValueError(f"文件不存在: {filename}")
        
        # 检查是否是文件（不是目录）
        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {filename}")
        
        # 删除文件
        file_path.unlink()
        logger.info(f"已删除知识库文件: {filename}")
        return True
        
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"删除知识库文件失败: {filename}, 错误: {e}")
        raise ValueError(f"删除失败: {str(e)}")


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名是否合法"""
    allowed_extensions = {'.md', '.txt'}
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def truncate_text(text: str, max_length: int = 200) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def get_rag_config() -> dict:
    """
    获取 RAG 配置参数
    
    Returns:
        配置字典
    """
    return {
        'min_score': float(os.getenv('RAG_MIN_SCORE', '0.25')),
        'min_sources': int(os.getenv('RAG_MIN_SOURCES', '1')),
        'mmr_lambda': float(os.getenv('RAG_MMR_LAMBDA', '0.5')),
        'use_rerank': os.getenv('RAG_USE_RERANK', 'false').lower() == 'true',
        'chunk_size': int(os.getenv('CHUNK_SIZE', '800')),
        'chunk_overlap': int(os.getenv('CHUNK_OVERLAP', '120')),
    }
