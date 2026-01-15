"""
向量存储管理模块
v1.1 - 增加 MMR 检索、chunk 索引
"""
import os
import json
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.documents import Document
from .llm import get_embeddings
from .utils import get_chroma_dir, get_memory_dir, logger

# 全局向量存储实例
_vectorstore: Optional[Chroma] = None
_is_ready: bool = False

# Chunk 索引文件路径
CHUNKS_INDEX_FILE = "chunks_index.json"


def get_chunks_index_path() -> Path:
    """获取 chunks 索引文件路径"""
    return get_memory_dir() / CHUNKS_INDEX_FILE


def load_chunks_index() -> Dict[str, Any]:
    """加载 chunks 索引"""
    index_path = get_chunks_index_path()
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载 chunks 索引失败: {e}")
    return {"chunks": {}}


def save_chunks_index(index: Dict[str, Any]) -> None:
    """保存 chunks 索引"""
    index_path = get_chunks_index_path()
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 chunks 索引: {len(index.get('chunks', {}))} 个 chunks")


def update_chunks_index(documents: List[Document]) -> None:
    """
    更新 chunks 索引
    
    Args:
        documents: 文档列表
    """
    index = load_chunks_index()
    
    for doc in documents:
        chunk_id = doc.metadata.get('chunk_id', '')
        if chunk_id:
            index['chunks'][chunk_id] = {
                'source': doc.metadata.get('source', 'unknown'),
                'content': doc.page_content,
                'metadata': doc.metadata,
            }
    
    save_chunks_index(index)


def get_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 chunk_id 获取 chunk 内容
    
    Args:
        chunk_id: chunk 唯一标识
    
    Returns:
        chunk 信息字典或 None
    """
    index = load_chunks_index()
    return index.get('chunks', {}).get(chunk_id)


def get_vectorstore() -> Optional[Chroma]:
    """获取向量存储实例"""
    global _vectorstore, _is_ready
    
    if _vectorstore is not None:
        return _vectorstore
    
    # 尝试加载已存在的向量库
    chroma_dir = get_chroma_dir()
    
    try:
        embeddings = get_embeddings()
        
        # 检查是否存在持久化数据
        if (chroma_dir / "chroma.sqlite3").exists():
            logger.info(f"加载已存在的向量库: {chroma_dir}")
            _vectorstore = Chroma(
                persist_directory=str(chroma_dir),
                embedding_function=embeddings,
                collection_name="knowledge_base"
            )
            _is_ready = True
            doc_count = _vectorstore._collection.count()
            logger.info(f"向量库加载成功，文档数量: {doc_count}")
        else:
            logger.info("向量库不存在，需要先进行入库操作")
            _vectorstore = None
            _is_ready = False
            
    except Exception as e:
        logger.error(f"加载向量库失败: {e}")
        _vectorstore = None
        _is_ready = False
    
    return _vectorstore


def create_vectorstore(documents: List[Document]) -> Chroma:
    """
    创建新的向量存储
    
    Args:
        documents: 文档列表
    
    Returns:
        Chroma 向量存储实例
    """
    global _vectorstore, _is_ready
    
    chroma_dir = get_chroma_dir()
    embeddings = get_embeddings()
    
    logger.info(f"创建向量库，文档数量: {len(documents)}")
    
    # 删除旧的向量库
    import shutil
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        chroma_dir.mkdir(exist_ok=True)
    
    # 创建新的向量库
    _vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(chroma_dir),
        collection_name="knowledge_base"
    )
    
    _is_ready = True
    logger.info(f"向量库创建成功，持久化目录: {chroma_dir}")
    
    # 更新 chunks 索引
    update_chunks_index(documents)
    
    return _vectorstore


def search_similar(query: str, k: int = 5) -> List[Tuple[Document, float]]:
    """
    搜索相似文档
    
    Args:
        query: 查询文本
        k: 返回数量
    
    Returns:
        (Document, score) 元组列表
    """
    vs = get_vectorstore()
    if vs is None:
        logger.warning("向量库未初始化，无法搜索")
        return []
    
    logger.info(f"相似度搜索: '{query[:50]}...', top_k={k}")
    
    try:
        results = vs.similarity_search_with_score(query, k=k)
        logger.info(f"检索命中 {len(results)} 条文档")
        return results
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


def search_mmr(
    query: str, 
    k: int = 5, 
    fetch_k: int = 20, 
    lambda_mult: float = 0.5
) -> List[Tuple[Document, float]]:
    """
    MMR（最大边际相关性）搜索
    
    Args:
        query: 查询文本
        k: 最终返回数量
        fetch_k: 初始检索数量
        lambda_mult: 多样性权重 (0-1, 越小越多样)
    
    Returns:
        (Document, score) 元组列表
    """
    vs = get_vectorstore()
    if vs is None:
        logger.warning("向量库未初始化，无法搜索")
        return []
    
    logger.info(f"MMR 搜索: '{query[:50]}...', k={k}, fetch_k={fetch_k}, lambda={lambda_mult}")
    
    try:
        # Chroma 的 MMR 搜索返回 Document 列表，不带分数
        docs = vs.max_marginal_relevance_search(
            query, 
            k=k, 
            fetch_k=fetch_k, 
            lambda_mult=lambda_mult
        )
        
        # 为了保持接口一致性，计算相似度分数
        results = []
        if docs:
            # 重新计算分数
            embeddings = get_embeddings()
            query_embedding = embeddings.embed_query(query)
            
            for doc in docs:
                # 简单使用相似度搜索获取分数
                try:
                    score_results = vs.similarity_search_with_score(
                        doc.page_content[:200], k=1
                    )
                    if score_results:
                        _, score = score_results[0]
                    else:
                        score = 0.5  # 默认分数
                except:
                    score = 0.5
                results.append((doc, score))
        
        logger.info(f"MMR 检索命中 {len(results)} 条文档")
        return results
    except Exception as e:
        logger.error(f"MMR 搜索失败: {e}")
        return []


def delete_by_source(source_name: str) -> int:
    """
    根据来源删除文档
    
    Args:
        source_name: 文件名
    
    Returns:
        删除的文档数量
    """
    vs = get_vectorstore()
    if vs is None:
        return 0
    
    try:
        # 获取要删除的文档 IDs
        collection = vs._collection
        results = collection.get(
            where={"source": source_name}
        )
        
        if results and results['ids']:
            ids_to_delete = results['ids']
            collection.delete(ids=ids_to_delete)
            logger.info(f"已删除来源 '{source_name}' 的 {len(ids_to_delete)} 个文档")
            return len(ids_to_delete)
        
        return 0
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return 0


def add_documents(documents: List[Document]) -> int:
    """
    添加文档到向量库
    
    Args:
        documents: 文档列表
    
    Returns:
        添加的文档数量
    """
    vs = get_vectorstore()
    if vs is None:
        logger.error("向量库未初始化，无法添加文档")
        return 0
    
    try:
        vs.add_documents(documents)
        logger.info(f"已添加 {len(documents)} 个文档")
        
        # 更新 chunks 索引
        update_chunks_index(documents)
        
        return len(documents)
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        return 0


def is_vectorstore_ready() -> bool:
    """检查向量库是否就绪"""
    global _is_ready
    if not _is_ready:
        # 尝试重新检查
        get_vectorstore()
    return _is_ready


def get_document_count() -> int:
    """获取文档数量"""
    vs = get_vectorstore()
    if vs is None:
        return 0
    try:
        return vs._collection.count()
    except:
        return 0


def reset_vectorstore():
    """重置向量存储状态"""
    global _vectorstore, _is_ready
    _vectorstore = None
    _is_ready = False
