"""
文档入库模块
"""
import os
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from .vectorstore import create_vectorstore, reset_vectorstore
from .utils import get_knowledge_dir, logger

# 加载环境变量
load_dotenv()


def load_documents() -> List[Document]:
    """
    加载知识库目录下的所有文档
    
    Returns:
        Document 列表
    """
    knowledge_dir = get_knowledge_dir()
    documents = []
    
    # 支持的文件类型
    file_patterns = ['*.md', '*.txt']
    
    for pattern in file_patterns:
        for file_path in knowledge_dir.glob(pattern):
            try:
                logger.info(f"加载文件: {file_path}")
                
                # 使用文本加载器
                loader = TextLoader(str(file_path), encoding='utf-8')
                docs = loader.load()
                
                # 添加文件名元数据
                for doc in docs:
                    doc.metadata['source'] = file_path.name
                    doc.metadata['file_path'] = str(file_path)
                
                documents.extend(docs)
                logger.info(f"成功加载 {len(docs)} 个文档块")
                
            except Exception as e:
                logger.error(f"加载文件失败 {file_path}: {e}")
                continue
    
    logger.info(f"总共加载 {len(documents)} 个原始文档")
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """
    切分文档
    
    Args:
        documents: 原始文档列表
    
    Returns:
        切分后的文档列表
    """
    # 从环境变量获取配置
    chunk_size = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "120"))
    
    logger.info(f"文档切块配置: chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
    )
    
    chunks = []
    for doc in documents:
        split_docs = splitter.split_documents([doc])
        
        # 为每个切块添加唯一 ID
        for i, chunk in enumerate(split_docs):
            source_name = doc.metadata.get('source', 'unknown')
            chunk.metadata['chunk_id'] = f"{source_name}_chunk_{i}"
            chunk.metadata['chunk_index'] = i
        
        chunks.extend(split_docs)
    
    logger.info(f"文档切块完成，共 {len(chunks)} 个切块")
    return chunks


def ingest_documents() -> Tuple[int, int]:
    """
    执行完整的文档入库流程
    
    Returns:
        (原始文档数, 切块数) 元组
    """
    logger.info("=" * 50)
    logger.info("开始文档入库流程")
    logger.info("=" * 50)
    
    # 重置向量库状态
    reset_vectorstore()
    
    # 1. 加载文档
    documents = load_documents()
    if not documents:
        logger.warning("知识库目录为空，请先上传文档")
        raise ValueError("知识库目录为空，请先上传 .md 或 .txt 文件到 data/knowledge/ 目录")
    
    doc_count = len(documents)
    
    # 2. 切分文档
    chunks = split_documents(documents)
    chunk_count = len(chunks)
    
    # 3. 创建向量库
    create_vectorstore(chunks)
    
    logger.info("=" * 50)
    logger.info(f"入库完成! 文档数: {doc_count}, 切块数: {chunk_count}")
    logger.info("=" * 50)
    
    return doc_count, chunk_count
