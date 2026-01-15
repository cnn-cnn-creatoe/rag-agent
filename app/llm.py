"""
LLM 配置模块
v1.1 - 增加流式输出支持
"""
import os
from typing import AsyncIterator, Iterator
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from .utils import logger

# 加载环境变量
load_dotenv()


def get_llm(streaming: bool = False) -> ChatOpenAI:
    """
    获取 LLM 实例
    
    Args:
        streaming: 是否启用流式输出
    
    Returns:
        ChatOpenAI 实例
    
    Raises:
        ValueError: 如果缺少必要的环境变量
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("缺少 OPENAI_API_KEY 环境变量，请在 .env 文件中配置")
    
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    
    logger.info(f"初始化 LLM: {model_name}, streaming={streaming}")
    
    kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.7,
        "streaming": streaming,
    }
    
    if base_url:
        kwargs["base_url"] = base_url
        logger.info(f"使用自定义 API 地址: {base_url}")
    
    return ChatOpenAI(**kwargs)


def get_embeddings() -> OpenAIEmbeddings:
    """
    获取 Embeddings 实例
    
    Returns:
        OpenAIEmbeddings 实例
    
    Raises:
        ValueError: 如果缺少必要的环境变量
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("缺少 OPENAI_API_KEY 环境变量，请在 .env 文件中配置")
    
    base_url = os.getenv("OPENAI_BASE_URL")
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    logger.info(f"初始化 Embeddings: {embedding_model}")
    
    kwargs = {
        "model": embedding_model,
        "api_key": api_key,
    }
    
    if base_url:
        kwargs["base_url"] = base_url
    
    return OpenAIEmbeddings(**kwargs)


async def stream_chat_completion(
    system_prompt: str,
    user_message: str,
) -> AsyncIterator[str]:
    """
    异步流式聊天补全
    
    Args:
        system_prompt: 系统提示
        user_message: 用户消息
    
    Yields:
        文本片段
    """
    llm = get_llm(streaming=True)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    logger.info("开始流式生成...")
    
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content


def sync_stream_chat_completion(
    system_prompt: str,
    user_message: str,
) -> Iterator[str]:
    """
    同步流式聊天补全
    
    Args:
        system_prompt: 系统提示
        user_message: 用户消息
    
    Yields:
        文本片段
    """
    llm = get_llm(streaming=True)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    logger.info("开始同步流式生成...")
    
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content
