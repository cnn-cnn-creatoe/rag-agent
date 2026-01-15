"""
RAG 问答模块
v1.1 - 增加流式输出、置信度计算、兜底策略
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from .llm import get_llm, stream_chat_completion
from .vectorstore import search_similar, search_mmr, is_vectorstore_ready
from .memory import get_profile_prompt
from .utils import (
    logger, truncate_text, save_answer_to_file, 
    get_rag_config, generate_message_id, save_answer_as_markdown
)
from .schemas import ConfidenceLevel, RetrievalMode, AnswerMode


# RAG 系统提示模板
RAG_SYSTEM_TEMPLATE = """你是一个专业的知识库助手。请基于以下提供的上下文信息回答用户的问题。

重要规则：
1. 回答必须基于提供的上下文信息
2. 如果上下文中没有足够的信息来回答问题，请明确说明"根据现有知识库内容，无法确定这个问题的答案，建议补充相关资料"
3. 不要编造或猜测上下文中没有的信息
4. 尽量引用具体来源来支持你的回答

用户偏好设置：
{user_preferences}

---
上下文信息：
{context}
---

请根据以上信息回答用户问题。"""

# 严格模式提示
RAG_STRICT_TEMPLATE = """你是一个专业的知识库助手。请**严格**基于以下提供的上下文信息回答用户的问题。

重要规则：
1. 回答**必须且只能**基于提供的上下文信息
2. 如果上下文中没有相关信息，请直接说明"根据现有知识库内容，无法回答该问题"
3. **严禁**编造、猜测或使用上下文之外的知识
4. 引用具体来源支持你的回答
5. 如果证据不足，要明确指出

用户偏好设置：
{user_preferences}

---
上下文信息：
{context}
---

请根据以上信息回答用户问题。"""

# 平衡模式提示
RAG_BALANCED_TEMPLATE = """你是一个专业的知识库助手。请基于以下提供的上下文信息回答用户的问题。

重要规则：
1. 回答主要基于提供的上下文信息
2. 可以进行合理推断，但必须用"根据上下文推断"等表述标注
3. 如果需要使用上下文之外的常识，请用"一般来说"标注
4. 尽量引用具体来源支持你的回答

用户偏好设置：
{user_preferences}

---
上下文信息：
{context}
---

请根据以上信息回答用户问题。"""

# 创意模式提示
RAG_CREATIVE_TEMPLATE = """你是一个专业的知识库助手。请基于以下提供的上下文信息回答用户的问题，并可以适当扩展。

重要规则：
1. 回答以提供的上下文信息为基础
2. 可以结合上下文进行扩展和建议
3. 明确区分"基于资料"和"建议/扩展"的内容
4. 引用来源支持核心回答

用户偏好设置：
{user_preferences}

---
上下文信息：
{context}
---

请根据以上信息回答用户问题。"""

# 证据不足兜底模板
FALLBACK_TEMPLATE = """根据我在知识库中的检索，**证据不足以完整回答您的问题**。

## 我能找到的相关资料
{found_info}

## 我不确定的点
- 上下文信息与您的问题相关性较低（最高相似度: {max_score:.3f}）
- 检索到的信息可能不够完整或不够具体

## 建议补充的资料
为了更好地回答您的问题，建议您补充以下类型的文档：
- 与"{query_keywords}"相关的详细说明文档
- 包含具体数据、条款或规定的资料

**请注意**：为了确保回答准确性，我不会基于不充分的证据给出具体结论。"""

RAG_HUMAN_TEMPLATE = "{question}"


def get_prompt_template(answer_mode: AnswerMode) -> str:
    """根据回答模式获取提示模板"""
    templates = {
        AnswerMode.STRICT: RAG_STRICT_TEMPLATE,
        AnswerMode.BALANCED: RAG_BALANCED_TEMPLATE,
        AnswerMode.CREATIVE: RAG_CREATIVE_TEMPLATE,
    }
    return templates.get(answer_mode, RAG_STRICT_TEMPLATE)


def format_documents(docs: List[tuple]) -> str:
    """
    格式化检索到的文档
    
    Args:
        docs: (Document, score) 元组列表
    
    Returns:
        格式化的文档字符串
    """
    formatted_parts = []
    for i, (doc, score) in enumerate(docs, 1):
        source = doc.metadata.get('source', 'unknown')
        chunk_id = doc.metadata.get('chunk_id', f'chunk_{i}')
        content = doc.page_content
        
        part = f"[来源 {i}] 文件: {source}, ID: {chunk_id}, 相似度: {score:.3f}\n{content}\n"
        formatted_parts.append(part)
    
    return "\n---\n".join(formatted_parts)


def extract_sources(docs: List[tuple]) -> List[Dict[str, Any]]:
    """
    提取来源信息
    
    Args:
        docs: (Document, score) 元组列表
    
    Returns:
        来源信息字典列表
    """
    sources = []
    for i, (doc, score) in enumerate(docs):
        source_info = {
            "source": doc.metadata.get('source', 'unknown'),
            "chunk_id": doc.metadata.get('chunk_id', 'unknown'),
            "snippet": truncate_text(doc.page_content, 300),
            "score": round(float(score), 3),
            "rank_before": i + 1,
            "rank_after": i + 1,
        }
        sources.append(source_info)
    return sources


def calculate_confidence(docs: List[tuple], config: dict) -> Tuple[ConfidenceLevel, bool]:
    """
    计算置信度
    
    Args:
        docs: 检索结果
        config: RAG 配置
    
    Returns:
        (置信度等级, 是否需要兜底)
    """
    if not docs:
        return ConfidenceLevel.LOW, True
    
    min_score = config['min_score']
    min_sources = config['min_sources']
    
    # 获取最高分
    max_score = max(score for _, score in docs) if docs else 0
    
    # 计算有效来源数（高于阈值的）
    valid_sources = sum(1 for _, score in docs if score >= min_score)
    
    logger.info(f"置信度计算: max_score={max_score:.3f}, valid_sources={valid_sources}, "
                f"min_score={min_score}, min_sources={min_sources}")
    
    # 判断是否需要兜底
    need_fallback = max_score < min_score or valid_sources < min_sources
    
    # 计算置信度等级
    if need_fallback:
        confidence = ConfidenceLevel.LOW
    elif max_score >= 0.7 and valid_sources >= 3:
        confidence = ConfidenceLevel.HIGH
    elif max_score >= 0.4 and valid_sources >= 2:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.MEDIUM
    
    return confidence, need_fallback


def generate_fallback_response(question: str, docs: List[tuple]) -> str:
    """
    生成兜底响应
    
    Args:
        question: 用户问题
        docs: 检索结果
    
    Returns:
        兜底响应文本
    """
    max_score = max(score for _, score in docs) if docs else 0
    
    # 提取关键词（简单实现）
    query_keywords = question[:30]
    
    # 格式化找到的资料
    if docs:
        found_info_parts = []
        for i, (doc, score) in enumerate(docs[:3], 1):
            source = doc.metadata.get('source', 'unknown')
            snippet = truncate_text(doc.page_content, 150)
            found_info_parts.append(f"{i}. **{source}** (相似度: {score:.3f})\n   > {snippet}")
        found_info = "\n".join(found_info_parts)
    else:
        found_info = "未找到任何相关资料"
    
    return FALLBACK_TEMPLATE.format(
        found_info=found_info,
        max_score=max_score,
        query_keywords=query_keywords
    )


def rag_query(
    question: str,
    user_id: str,
    top_k: int = 5,
    save_to_file: bool = False,
    file_name: Optional[str] = None,
    retrieval_mode: RetrievalMode = RetrievalMode.SIMILARITY,
    answer_mode: AnswerMode = AnswerMode.STRICT,
) -> Dict[str, Any]:
    """
    执行 RAG 查询
    
    Args:
        question: 用户问题
        user_id: 用户ID
        top_k: 检索文档数量
        save_to_file: 是否保存为文件
        file_name: 保存的文件名
        retrieval_mode: 检索模式
        answer_mode: 回答模式
    
    Returns:
        包含 answer, sources, confidence, saved_file, message_id 的字典
    """
    message_id = generate_message_id()
    logger.info(f"RAG 查询: user={user_id}, question='{question[:50]}...', message_id={message_id}")
    
    config = get_rag_config()
    
    # 检查向量库状态
    if not is_vectorstore_ready():
        logger.warning("向量库未就绪")
        return {
            "message_id": message_id,
            "answer": "抱歉，知识库尚未初始化。请先上传文档并执行入库操作。",
            "sources": [],
            "confidence": ConfidenceLevel.LOW,
            "saved_file": None
        }
    
    # 1. 检索相关文档
    if retrieval_mode == RetrievalMode.MMR:
        retrieved_docs = search_mmr(question, k=top_k, fetch_k=20, lambda_mult=config['mmr_lambda'])
    else:
        retrieved_docs = search_similar(question, k=top_k)
    
    # 2. 计算置信度
    confidence, need_fallback = calculate_confidence(retrieved_docs, config)
    
    # 3. 提取来源信息
    sources = extract_sources(retrieved_docs)
    
    # 4. 处理兜底情况
    if need_fallback and answer_mode == AnswerMode.STRICT:
        logger.warning(f"证据不足，使用兜底策略: confidence={confidence}")
        answer = generate_fallback_response(question, retrieved_docs)
    else:
        if not retrieved_docs:
            logger.warning("未检索到相关文档")
            answer = "抱歉，在知识库中没有找到与您问题相关的内容。建议：\n1. 尝试换一种方式描述问题\n2. 检查知识库是否包含相关主题的文档\n3. 上传更多相关资料"
        else:
            # 5. 获取用户偏好
            user_preferences = get_profile_prompt(user_id)
            
            # 6. 格式化上下文
            context = format_documents(retrieved_docs)
            
            # 7. 构建 prompt
            system_template = get_prompt_template(answer_mode)
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                ("human", RAG_HUMAN_TEMPLATE)
            ])
            
            # 8. 获取 LLM 并生成回答
            llm = get_llm()
            chain = prompt | llm | StrOutputParser()
            
            logger.info(f"调用 LLM 生成回答... mode={answer_mode}")
            answer = chain.invoke({
                "context": context,
                "question": question,
                "user_preferences": user_preferences
            })
    
    # 9. 可选保存到文件
    saved_file = None
    if save_to_file:
        saved_file = save_answer_to_file(answer, sources, file_name)
    
    logger.info(f"RAG 查询完成: message_id={message_id}, confidence={confidence}, 来源数={len(sources)}")
    
    return {
        "message_id": message_id,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "saved_file": saved_file
    }


async def rag_query_stream(
    question: str,
    user_id: str,
    thread_id: str = "default",
    top_k: int = 5,
    retrieval_mode: RetrievalMode = RetrievalMode.SIMILARITY,
    answer_mode: AnswerMode = AnswerMode.STRICT,
    save_as_document: bool = False,
) -> AsyncIterator[Dict[str, Any]]:
    """
    流式 RAG 查询
    
    Args:
        question: 用户问题
        user_id: 用户ID
        thread_id: 会话ID
        top_k: 检索文档数量
        retrieval_mode: 检索模式
        answer_mode: 回答模式
        save_as_document: 是否将回答保存为文档
    
    Yields:
        SSE 事件字典
    """
    message_id = generate_message_id()
    logger.info(f"流式 RAG 查询: user={user_id}, question='{question[:50]}...', message_id={message_id}")
    
    config = get_rag_config()
    
    # 检查向量库状态
    if not is_vectorstore_ready():
        logger.warning("向量库未就绪")
        yield {
            "event": "error",
            "data": {"error": "知识库尚未初始化，请先上传文档并执行入库操作。"}
        }
        return
    
    # 1. 检索相关文档
    if retrieval_mode == RetrievalMode.MMR:
        retrieved_docs = search_mmr(question, k=top_k, fetch_k=20, lambda_mult=config['mmr_lambda'])
    else:
        retrieved_docs = search_similar(question, k=top_k)
    
    # 2. 计算置信度
    confidence, need_fallback = calculate_confidence(retrieved_docs, config)
    
    # 3. 提取来源信息
    sources = extract_sources(retrieved_docs)
    
    full_answer = ""
    
    # 4. 处理兜底情况
    if need_fallback and answer_mode == AnswerMode.STRICT:
        logger.warning(f"证据不足，使用兜底策略: confidence={confidence}")
        answer = generate_fallback_response(question, retrieved_docs)
        # 兜底响应逐字输出
        for char in answer:
            yield {"event": "token", "data": {"delta": char}}
            full_answer += char
            await asyncio.sleep(0.01)  # 模拟流式效果
    elif not retrieved_docs:
        logger.warning("未检索到相关文档")
        answer = "抱歉，在知识库中没有找到与您问题相关的内容。建议：\n1. 尝试换一种方式描述问题\n2. 检查知识库是否包含相关主题的文档\n3. 上传更多相关资料"
        for char in answer:
            yield {"event": "token", "data": {"delta": char}}
            full_answer += char
            await asyncio.sleep(0.01)
    else:
        # 5. 获取用户偏好
        user_preferences = get_profile_prompt(user_id)
        
        # 6. 格式化上下文
        context = format_documents(retrieved_docs)
        
        # 7. 构建提示
        system_template = get_prompt_template(answer_mode)
        system_prompt = system_template.format(
            user_preferences=user_preferences,
            context=context
        )
        
        # 8. 流式生成
        logger.info(f"开始流式生成... mode={answer_mode}")
        try:
            async for token in stream_chat_completion(system_prompt, question):
                yield {"event": "token", "data": {"delta": token}}
                full_answer += token
        except Exception as e:
            logger.error(f"流式生成错误: {e}")
            yield {"event": "error", "data": {"error": str(e)}}
            return
    
    # 9. 保存文档（如果请求）
    saved_document = None
    if save_as_document and full_answer:
        doc_result = save_answer_as_markdown(
            question=question,
            answer=full_answer,
            sources=sources,
            user_id=user_id,
            thread_id=thread_id,
            confidence=confidence.value,
            agentic_mode=False,
        )
        if doc_result:
            saved_document = doc_result
    
    # 10. 发送结束事件
    yield {
        "event": "end",
        "data": {
            "message_id": message_id,
            "answer": full_answer,
            "sources": sources,
            "confidence": confidence.value,
            "saved_file": None,
            "saved_document": saved_document,
        }
    }
    
    logger.info(f"流式 RAG 查询完成: message_id={message_id}, confidence={confidence}")
