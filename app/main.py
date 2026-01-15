"""
FastAPI 主应用
知识库 RAG 助理 API 服务
v2.0 - Agentic RAG + LangSmith
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from .schemas import (
    ChatRequest, ChatResponse, SourceInfo, ConfidenceLevel, ReasoningStep,
    UploadResponse, IngestResponse,
    FileListResponse, HealthResponse,
    DocContentResponse, ChunkContentResponse,
    RetrievalMode, AnswerMode, SavedDocument,
)
from .rag import rag_query, rag_query_stream
from .ingest import ingest_documents
from .vectorstore import is_vectorstore_ready, get_document_count, get_chunk_by_id
from .utils import (
    get_knowledge_dir, list_knowledge_files, delete_knowledge_file,
    validate_file_extension, logger,
    set_request_id, validate_safe_path, sanitize_filename,
    save_answer_as_markdown
)

# 加载环境变量
load_dotenv()

# ============ LangSmith 配置 ============
# 如果配置了 LangSmith，自动启用 tracing
LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
AGENTIC_ENABLED = os.getenv("RAG_AGENTIC_ENABLED", "false").lower() == "true"

if LANGSMITH_ENABLED:
    logger.info("LangSmith Tracing 已启用")
    # LangChain 会自动读取环境变量进行配置
    # LANGCHAIN_API_KEY, LANGCHAIN_PROJECT 等

if AGENTIC_ENABLED:
    logger.info("Agentic RAG 模式已全局启用")

# ============ 延迟导入 Agentic 模块 ============
def get_agentic_query():
    """延迟导入 agentic_rag 模块"""
    from .agentic_rag import agentic_rag_query
    return agentic_rag_query


# 创建 FastAPI 应用
app = FastAPI(
    title="知识库 RAG 助理",
    description="基于 LangChain + LangGraph 的本地知识库问答系统 v2.0",
    version="2.0.0"
)

# 获取当前文件目录
BASE_DIR = Path(__file__).parent

# 挂载静态文件
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 配置模板
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求添加 request_id"""
    request_id = set_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    返回 Web UI 主页
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口
    返回系统状态、向量库状态和文档数量
    """
    try:
        vectorstore_ready = is_vectorstore_ready()
        doc_count = get_document_count() if vectorstore_ready else 0
        
        return HealthResponse(
            status="healthy",
            vectorstore_ready=vectorstore_ready,
            doc_count=doc_count,
            agentic_enabled=AGENTIC_ENABLED,
            langsmith_enabled=LANGSMITH_ENABLED,
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="error",
            vectorstore_ready=False,
            doc_count=0,
            agentic_enabled=AGENTIC_ENABLED,
            langsmith_enabled=LANGSMITH_ENABLED,
        )


@app.get("/files", response_model=FileListResponse)
async def list_files():
    """
    获取知识库文件列表
    """
    try:
        files = list_knowledge_files()
        return FileListResponse(files=files, count=len(files))
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    删除知识库中的指定文件
    
    注意：删除文件后需要重新索引才能更新向量库
    """
    try:
        delete_knowledge_file(filename)
        return {
            "success": True,
            "message": f"文件 {filename} 已删除，请重新索引以更新知识库",
            "filename": filename,
            "needs_reindex": True
        }
    except ValueError as e:
        logger.warning(f"删除文件失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.get("/doc", response_model=DocContentResponse)
async def get_document_content(name: str = Query(..., description="文件名")):
    """
    获取知识库文档内容 v1.1
    用于原文预览
    """
    try:
        # 安全路径校验
        file_path = validate_safe_path(name, 'knowledge')
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {name}")
        
        # 检查文件类型
        if not validate_file_extension(name):
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {name}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_type = file_path.suffix.lstrip('.')
        
        logger.info(f"读取文档: {name}, 长度: {len(content)}")
        
        return DocContentResponse(
            name=name,
            content=content,
            file_type=file_type
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chunk", response_model=ChunkContentResponse)
async def get_chunk_content(
    name: str = Query(..., description="文件名"),
    chunk_id: str = Query(..., description="chunk ID")
):
    """
    获取指定 chunk 的内容 v1.1
    """
    try:
        # 从 chunks 索引获取
        chunk_info = get_chunk_by_id(chunk_id)
        
        if chunk_info:
            return ChunkContentResponse(
                name=chunk_info.get('source', name),
                chunk_id=chunk_id,
                content=chunk_info.get('content', ''),
                metadata=chunk_info.get('metadata', {})
            )
        
        # 如果索引中没有，尝试从文件中定位
        logger.warning(f"chunk 索引中未找到: {chunk_id}，尝试从文件读取")
        
        # 安全路径校验
        file_path = validate_safe_path(name, 'knowledge')
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return ChunkContentResponse(
            name=name,
            chunk_id=chunk_id,
            content=content,
            metadata={"source": name, "note": "完整文件内容（chunk索引中未找到）"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 chunk 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    auto_ingest: bool = False
):
    """
    上传文件到知识库
    
    Args:
        files: 上传的文件列表（支持 .md, .txt）
        auto_ingest: 是否自动入库
    """
    knowledge_dir = get_knowledge_dir()
    uploaded_files = []
    errors = []
    
    for file in files:
        # 验证文件类型
        if not validate_file_extension(file.filename):
            errors.append(f"不支持的文件类型: {file.filename}（仅支持 .md, .txt）")
            continue
        
        try:
            # 清理文件名
            safe_filename = sanitize_filename(Path(file.filename).stem) + Path(file.filename).suffix
            
            # 保存文件
            file_path = knowledge_dir / safe_filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append(safe_filename)
            logger.info(f"文件上传成功: {safe_filename}")
            
        except Exception as e:
            errors.append(f"上传失败 {file.filename}: {str(e)}")
            logger.error(f"文件上传失败: {file.filename}, 错误: {e}")
    
    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail=f"没有文件上传成功。错误: {'; '.join(errors)}"
        )
    
    # 可选自动入库
    ingested = False
    if auto_ingest and uploaded_files:
        try:
            ingest_documents()
            ingested = True
            logger.info("自动入库完成")
        except Exception as e:
            logger.error(f"自动入库失败: {e}")
    
    message = f"成功上传 {len(uploaded_files)} 个文件"
    if errors:
        message += f"，{len(errors)} 个文件失败"
    if ingested:
        message += "，已自动入库"
    
    return UploadResponse(
        success=True,
        message=message,
        files=uploaded_files,
        ingested=ingested
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_knowledge_base():
    """
    将知识库文件入库到向量数据库
    """
    try:
        doc_count, chunk_count = ingest_documents()
        
        return IngestResponse(
            success=True,
            message=f"入库成功！处理了 {doc_count} 个文档，生成 {chunk_count} 个切块",
            doc_count=doc_count,
            chunk_count=chunk_count,
            processed=doc_count,
            added_chunks=chunk_count,
        )
    except ValueError as e:
        # 知识库为空等业务错误
        logger.warning(f"入库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"入库失败: {e}")
        raise HTTPException(status_code=500, detail=f"入库失败: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    知识库问答接口 v2.0
    支持普通 RAG 和 Agentic RAG 模式
    
    Args:
        request: 聊天请求，包含 user_id, thread_id, message, agentic_mode 等
    
    Returns:
        ChatResponse: 包含回答、来源、置信度、推理轨迹等
    """
    # 验证环境变量
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="服务器未配置 OPENAI_API_KEY，请联系管理员"
        )
    
    try:
        logger.info(f"收到聊天请求: user={request.user_id}, thread={request.thread_id}, agentic={request.agentic_mode}")
        
        # 决定使用哪种模式
        use_agentic = request.agentic_mode or AGENTIC_ENABLED
        
        if use_agentic:
            # 使用 Agentic RAG
            agentic_query = get_agentic_query()
            result = agentic_query(
                question=request.message,
                user_id=request.user_id,
                top_k=request.top_k,
                retrieval_mode=request.retrieval_mode.value,
                max_loops=request.max_loops,
            )
            
            # 转换 sources
            sources = [
                SourceInfo(
                    source=s["source"],
                    chunk_id=s["chunk_id"],
                    snippet=s["snippet"],
                    score=s.get("score", 0),
                    rank_before=s.get("rank_before"),
                    rank_after=s.get("rank_after"),
                )
                for s in result["sources"]
            ]
            
            # 转换 reasoning_trace
            reasoning_trace = None
            if result.get("reasoning_trace"):
                reasoning_trace = [
                    ReasoningStep(
                        step=r.get("step", ""),
                        query=r.get("query"),
                        decision=r.get("decision"),
                        loop=r.get("loop"),
                    )
                    for r in result["reasoning_trace"]
                ]
            
            # 映射 confidence
            confidence_map = {
                'high': ConfidenceLevel.HIGH,
                'medium': ConfidenceLevel.MEDIUM,
                'low': ConfidenceLevel.LOW,
            }
            confidence = confidence_map.get(result.get("confidence", "medium"), ConfidenceLevel.MEDIUM)
            
            # 保存为文档（如果请求）
            saved_document = None
            if request.save_as_document:
                doc_result = save_answer_as_markdown(
                    question=request.message,
                    answer=result["answer"],
                    sources=result["sources"],
                    user_id=request.user_id,
                    thread_id=request.thread_id,
                    confidence=result.get("confidence", "medium"),
                    agentic_mode=True,
                )
                if doc_result:
                    saved_document = SavedDocument(
                        filename=doc_result["filename"],
                        path=doc_result["path"],
                    )
            
            return ChatResponse(
                message_id=result["message_id"],
                answer=result["answer"],
                sources=sources,
                confidence=confidence,
                saved_file=result.get("saved_file"),
                saved_document=saved_document,
                reasoning_trace=reasoning_trace,
                loops_used=result.get("loops_used"),
            )
        else:
            # 使用普通 RAG
            result = rag_query(
                question=request.message,
                user_id=request.user_id,
                top_k=request.top_k,
                save_to_file=request.save_to_file,
                file_name=request.file_name,
                retrieval_mode=request.retrieval_mode,
                answer_mode=request.answer_mode,
            )
            
            # 转换 sources 为 SourceInfo 对象
            sources = [
                SourceInfo(
                    source=s["source"],
                    chunk_id=s["chunk_id"],
                    snippet=s["snippet"],
                    score=s.get("score", 0),
                    rank_before=s.get("rank_before"),
                    rank_after=s.get("rank_after"),
                )
                for s in result["sources"]
            ]
            
            # 保存为文档（如果请求）
            saved_document = None
            if request.save_as_document:
                # 获取 confidence 值
                confidence_value = result["confidence"].value if hasattr(result["confidence"], 'value') else result["confidence"]
                doc_result = save_answer_as_markdown(
                    question=request.message,
                    answer=result["answer"],
                    sources=result["sources"],
                    user_id=request.user_id,
                    thread_id=request.thread_id,
                    confidence=confidence_value,
                    agentic_mode=False,
                )
                if doc_result:
                    saved_document = SavedDocument(
                        filename=doc_result["filename"],
                        path=doc_result["path"],
                    )
            
            return ChatResponse(
                message_id=result["message_id"],
                answer=result["answer"],
                sources=sources,
                confidence=result["confidence"],
                saved_file=result.get("saved_file"),
                saved_document=saved_document,
            )
        
    except ValueError as e:
        logger.error(f"业务错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口 (SSE) v1.1
    注意：Agentic 模式暂不支持流式输出，会自动降级为普通 RAG 流式
    
    Args:
        request: 聊天请求
    
    Returns:
        StreamingResponse: SSE 事件流
    """
    # 验证环境变量
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="服务器未配置 OPENAI_API_KEY，请联系管理员"
        )
    
    # 如果请求了 Agentic 模式但使用流式，给出提示
    if request.agentic_mode:
        logger.info("Agentic 模式暂不支持流式输出，使用普通 RAG 流式")
    
    logger.info(f"收到流式聊天请求: user={request.user_id}, thread={request.thread_id}")
    
    async def generate_sse():
        """生成 SSE 事件流"""
        try:
            async for event in rag_query_stream(
                question=request.message,
                user_id=request.user_id,
                thread_id=request.thread_id,
                top_k=request.top_k,
                retrieval_mode=request.retrieval_mode,
                answer_mode=request.answer_mode,
                save_as_document=request.save_as_document,
            ):
                event_type = event.get("event", "token")
                event_data = json.dumps(event.get("data", {}), ensure_ascii=False)
                yield f"event: {event_type}\ndata: {event_data}\n\n"
                
        except asyncio.CancelledError:
            logger.info("流式请求被取消")
            yield f"event: cancelled\ndata: {json.dumps({'message': '请求已取消'})}\n\n"
        except Exception as e:
            logger.error(f"流式生成错误: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# 异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
