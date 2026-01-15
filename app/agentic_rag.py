"""
LangGraph Agentic RAG 模块
v2.0 - 自检 + 再检索循环
"""
import os
import json
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from .llm import get_llm
from .vectorstore import search_similar, search_mmr
from .memory import get_profile_prompt
from .utils import logger, truncate_text, get_rag_config, generate_message_id
from .schemas import ConfidenceLevel, RetrievalMode


# ============ 状态定义 ============
class AgentState(TypedDict):
    """Agentic RAG 状态"""
    # 输入
    original_query: str
    current_query: str
    user_id: str
    top_k: int
    retrieval_mode: str
    filters: Optional[Dict[str, Any]]
    
    # 检索结果
    retrieved_chunks: List[Dict[str, Any]]
    all_sources: Annotated[List[Dict[str, Any]], add]  # 累积所有来源
    
    # 生成结果
    draft_answer: str
    claims: List[str]
    
    # 自检结果
    critique_result: Dict[str, Any]
    decision: str  # "final" | "need_more"
    refined_query: Optional[str]
    gaps: List[str]
    
    # 循环控制
    loop_count: int
    max_loops: int
    
    # 最终输出
    final_answer: str
    confidence: str
    reasoning_trace: List[Dict[str, Any]]


# ============ 提示模板 ============
DRAFT_SYSTEM_PROMPT = """你是一个专业的知识库助手。请基于提供的上下文信息回答用户问题。

重要规则：
1. 回答必须基于提供的上下文信息
2. 在回答中，明确标注你使用了哪些来源
3. 如果信息不足，指出哪些方面需要更多资料

用户偏好：{user_preferences}

上下文信息：
{context}

请生成回答，并列出你回答中的核心声明（claims）。
按以下 JSON 格式输出：
{{
    "answer": "你的完整回答",
    "claims": ["声明1", "声明2", ...]
}}

注意：claims 是你回答中的关键事实陈述，每个 claim 应该可以被验证。"""

CRITIQUE_SYSTEM_PROMPT = """你是一个严格的质量检查员。请检查以下回答草稿和声明是否有充分的证据支持。

原始问题：{question}
回答草稿：{draft_answer}
声明列表：{claims}
检索到的来源：{sources}

请检查：
1. 每个 claim 是否有来源支撑？
2. 是否存在与来源矛盾的内容？
3. 是否有关键信息缺失？

按以下 JSON 格式输出：
{{
    "decision": "final" 或 "need_more",
    "supported_claims": ["有证据支持的声明"],
    "unsupported_claims": ["缺乏证据的声明"],
    "conflicts": ["与来源矛盾的点"],
    "gaps": ["缺失的信息"],
    "refined_query": "如果 decision 是 need_more，提供改进后的检索词，否则为 null",
    "confidence": "high/medium/low",
    "reasoning": "简短说明你的判断理由"
}}

判断标准：
- 如果 >70% claims 有支撑且无重大冲突 → "final"
- 否则 → "need_more"（除非已达到最大循环次数）"""

FALLBACK_PROMPT = """基于有限的证据，请生成一个保守、诚实的回答。

原始问题：{question}
收集到的信息：{context}
已知的缺口：{gaps}

要求：
1. 明确说明哪些是有证据支持的
2. 明确说明哪些是不确定的
3. 建议用户补充什么资料
4. 不要编造没有证据的内容"""


# ============ 节点函数 ============
def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """检索节点：根据当前 query 检索候选 chunks"""
    logger.info(f"[Agentic] 检索节点: query='{state['current_query'][:50]}...'")
    
    config = get_rag_config()
    
    # 选择检索模式
    if state['retrieval_mode'] == 'mmr':
        results = search_mmr(
            state['current_query'],
            k=state['top_k'],
            fetch_k=20,
            lambda_mult=config['mmr_lambda']
        )
    else:
        results = search_similar(state['current_query'], k=state['top_k'])
    
    # 格式化检索结果
    chunks = []
    sources = []
    for i, (doc, score) in enumerate(results):
        chunk_info = {
            'content': doc.page_content,
            'source': doc.metadata.get('source', 'unknown'),
            'chunk_id': doc.metadata.get('chunk_id', f'chunk_{i}'),
            'score': round(float(score), 3),
        }
        chunks.append(chunk_info)
        sources.append({
            'source': chunk_info['source'],
            'chunk_id': chunk_info['chunk_id'],
            'snippet': truncate_text(doc.page_content, 300),
            'score': chunk_info['score'],
            'rank_before': i + 1,
            'rank_after': i + 1,
        })
    
    # 记录追踪
    trace_entry = {
        'step': 'retrieve',
        'query': state['current_query'],
        'chunks_found': len(chunks),
        'top_score': chunks[0]['score'] if chunks else 0,
    }
    
    logger.info(f"[Agentic] 检索到 {len(chunks)} 个 chunks")
    
    return {
        'retrieved_chunks': chunks,
        'all_sources': sources,
        'reasoning_trace': [trace_entry],
    }


def draft_node(state: AgentState) -> Dict[str, Any]:
    """草稿节点：基于 chunks 生成草稿 answer + claims"""
    logger.info("[Agentic] 草稿节点: 生成回答草稿")
    
    if not state['retrieved_chunks']:
        return {
            'draft_answer': '未能找到相关信息。',
            'claims': [],
            'reasoning_trace': [{'step': 'draft', 'status': 'no_chunks'}],
        }
    
    # 格式化上下文
    context_parts = []
    for i, chunk in enumerate(state['retrieved_chunks'], 1):
        context_parts.append(
            f"[来源 {i}] {chunk['source']} (相似度: {chunk['score']})\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)
    
    # 获取用户偏好
    user_preferences = get_profile_prompt(state['user_id'])
    
    # 构建提示
    prompt = ChatPromptTemplate.from_messages([
        ("system", DRAFT_SYSTEM_PROMPT),
        ("human", "{question}")
    ])
    
    llm = get_llm()
    
    try:
        response = llm.invoke(
            prompt.format_messages(
                user_preferences=user_preferences,
                context=context,
                question=state['original_query']
            )
        )
        
        # 解析 JSON 响应
        content = response.content
        # 尝试提取 JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        try:
            result = json.loads(content)
            draft_answer = result.get('answer', content)
            claims = result.get('claims', [])
        except json.JSONDecodeError:
            draft_answer = response.content
            claims = []
        
        trace_entry = {
            'step': 'draft',
            'claims_count': len(claims),
        }
        
        logger.info(f"[Agentic] 生成草稿，包含 {len(claims)} 个声明")
        
        return {
            'draft_answer': draft_answer,
            'claims': claims,
            'reasoning_trace': [trace_entry],
        }
        
    except Exception as e:
        logger.error(f"[Agentic] 草稿生成失败: {e}")
        return {
            'draft_answer': f'生成回答时出错: {str(e)}',
            'claims': [],
            'reasoning_trace': [{'step': 'draft', 'error': str(e)}],
        }


def critique_node(state: AgentState) -> Dict[str, Any]:
    """自检节点：检查证据支撑、冲突、缺失"""
    logger.info("[Agentic] 自检节点: 检查回答质量")
    
    # 如果没有 claims，直接通过
    if not state['claims']:
        return {
            'critique_result': {'decision': 'final', 'confidence': 'medium'},
            'decision': 'final',
            'refined_query': None,
            'gaps': [],
            'confidence': 'medium',
            'reasoning_trace': [{'step': 'critique', 'status': 'no_claims_to_check'}],
        }
    
    # 格式化来源信息
    sources_text = json.dumps([
        {
            'source': s['source'],
            'chunk_id': s['chunk_id'],
            'snippet': s['snippet'][:200]
        }
        for s in state['all_sources']
    ], ensure_ascii=False, indent=2)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIQUE_SYSTEM_PROMPT),
        ("human", "请检查上述内容。")
    ])
    
    llm = get_llm()
    
    try:
        response = llm.invoke(
            prompt.format_messages(
                question=state['original_query'],
                draft_answer=state['draft_answer'],
                claims=json.dumps(state['claims'], ensure_ascii=False),
                sources=sources_text
            )
        )
        
        # 解析响应
        content = response.content
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {
                'decision': 'final',
                'confidence': 'medium',
                'gaps': [],
                'refined_query': None,
            }
        
        decision = result.get('decision', 'final')
        confidence = result.get('confidence', 'medium')
        gaps = result.get('gaps', [])
        refined_query = result.get('refined_query')
        
        # 如果已达到最大循环次数，强制 final
        if state['loop_count'] >= state['max_loops'] - 1:
            decision = 'final'
            logger.info(f"[Agentic] 已达最大循环次数，强制结束")
        
        trace_entry = {
            'step': 'critique',
            'decision': decision,
            'confidence': confidence,
            'gaps_count': len(gaps),
            'refined_query': refined_query[:50] if refined_query else None,
        }
        
        logger.info(f"[Agentic] 自检结果: decision={decision}, confidence={confidence}")
        
        return {
            'critique_result': result,
            'decision': decision,
            'refined_query': refined_query,
            'gaps': gaps,
            'confidence': confidence,
            'reasoning_trace': [trace_entry],
        }
        
    except Exception as e:
        logger.error(f"[Agentic] 自检失败: {e}")
        return {
            'critique_result': {},
            'decision': 'final',
            'refined_query': None,
            'gaps': [],
            'confidence': 'low',
            'reasoning_trace': [{'step': 'critique', 'error': str(e)}],
        }


def refine_query_node(state: AgentState) -> Dict[str, Any]:
    """改进查询节点：准备下一轮检索"""
    logger.info(f"[Agentic] 改进查询: {state.get('refined_query', '')[:50]}...")
    
    new_query = state.get('refined_query') or state['original_query']
    new_loop_count = state['loop_count'] + 1
    
    return {
        'current_query': new_query,
        'loop_count': new_loop_count,
        'reasoning_trace': [{
            'step': 'refine_query',
            'new_query': new_query[:50],
            'loop': new_loop_count,
        }],
    }


def finalize_node(state: AgentState) -> Dict[str, Any]:
    """最终化节点：确定最终答案"""
    logger.info("[Agentic] 最终化节点")
    
    # 如果有足够证据，使用草稿答案
    if state['confidence'] in ['high', 'medium'] or not state['gaps']:
        final_answer = state['draft_answer']
    else:
        # 生成保守的兜底回答
        llm = get_llm()
        
        context_parts = [c['snippet'] for c in state['all_sources'][:5]]
        context = "\n---\n".join(context_parts) if context_parts else "无可用信息"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", FALLBACK_PROMPT),
            ("human", "请生成回答。")
        ])
        
        try:
            response = llm.invoke(
                prompt.format_messages(
                    question=state['original_query'],
                    context=context,
                    gaps=", ".join(state['gaps']) if state['gaps'] else "无明确缺口"
                )
            )
            final_answer = response.content
        except Exception as e:
            final_answer = state['draft_answer']
            logger.error(f"[Agentic] 兜底生成失败: {e}")
    
    # 映射置信度
    confidence_map = {
        'high': ConfidenceLevel.HIGH,
        'medium': ConfidenceLevel.MEDIUM,
        'low': ConfidenceLevel.LOW,
    }
    final_confidence = confidence_map.get(state['confidence'], ConfidenceLevel.MEDIUM)
    
    return {
        'final_answer': final_answer,
        'confidence': final_confidence.value,
        'reasoning_trace': [{'step': 'finalize', 'confidence': final_confidence.value}],
    }


# ============ 路由函数 ============
def should_continue(state: AgentState) -> str:
    """决定是继续循环还是结束"""
    if state['decision'] == 'need_more' and state['loop_count'] < state['max_loops']:
        return 'refine'
    return 'finalize'


# ============ 构建图 ============
def create_agentic_rag_graph() -> StateGraph:
    """创建 Agentic RAG 工作流图"""
    
    # 创建图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("refine", refine_query_node)
    workflow.add_node("finalize", finalize_node)
    
    # 添加边
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "draft")
    workflow.add_edge("draft", "critique")
    
    # 条件边
    workflow.add_conditional_edges(
        "critique",
        should_continue,
        {
            "refine": "refine",
            "finalize": "finalize",
        }
    )
    
    workflow.add_edge("refine", "retrieve")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# ============ 主入口 ============
_agentic_graph = None


def get_agentic_graph():
    """获取或创建 Agentic RAG 图实例"""
    global _agentic_graph
    if _agentic_graph is None:
        _agentic_graph = create_agentic_rag_graph()
    return _agentic_graph


def agentic_rag_query(
    question: str,
    user_id: str,
    top_k: int = 5,
    retrieval_mode: str = "similarity",
    max_loops: int = 2,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    执行 Agentic RAG 查询
    
    Args:
        question: 用户问题
        user_id: 用户ID
        top_k: 检索数量
        retrieval_mode: 检索模式
        max_loops: 最大循环次数
        filters: 过滤条件
    
    Returns:
        包含 answer, sources, confidence, reasoning_trace, message_id 的字典
    """
    message_id = generate_message_id()
    logger.info(f"[Agentic RAG] 开始查询: message_id={message_id}, question='{question[:50]}...'")
    
    # 获取配置
    config = get_rag_config()
    if max_loops is None:
        max_loops = int(os.getenv('RAG_AGENTIC_MAX_LOOPS', '2'))
    
    # 初始状态
    initial_state: AgentState = {
        'original_query': question,
        'current_query': question,
        'user_id': user_id,
        'top_k': top_k,
        'retrieval_mode': retrieval_mode,
        'filters': filters,
        'retrieved_chunks': [],
        'all_sources': [],
        'draft_answer': '',
        'claims': [],
        'critique_result': {},
        'decision': '',
        'refined_query': None,
        'gaps': [],
        'loop_count': 0,
        'max_loops': max_loops,
        'final_answer': '',
        'confidence': 'medium',
        'reasoning_trace': [],
    }
    
    try:
        # 执行图
        graph = get_agentic_graph()
        final_state = graph.invoke(initial_state)
        
        # 去重来源
        seen = set()
        unique_sources = []
        for s in final_state.get('all_sources', []):
            key = (s['source'], s['chunk_id'])
            if key not in seen:
                seen.add(key)
                unique_sources.append(s)
        
        # 清理 reasoning_trace（移除敏感信息）
        safe_trace = []
        for entry in final_state.get('reasoning_trace', []):
            safe_entry = {
                'step': entry.get('step'),
            }
            if 'query' in entry:
                safe_entry['query'] = entry['query'][:50] + '...' if len(entry.get('query', '')) > 50 else entry.get('query')
            if 'decision' in entry:
                safe_entry['decision'] = entry['decision']
            if 'loop' in entry:
                safe_entry['loop'] = entry['loop']
            safe_trace.append(safe_entry)
        
        logger.info(f"[Agentic RAG] 完成: confidence={final_state.get('confidence')}, loops={final_state.get('loop_count')}")
        
        return {
            'message_id': message_id,
            'answer': final_state.get('final_answer', ''),
            'sources': unique_sources,
            'confidence': final_state.get('confidence', 'medium'),
            'reasoning_trace': safe_trace,
            'loops_used': final_state.get('loop_count', 0) + 1,
            'saved_file': None,
        }
        
    except Exception as e:
        logger.error(f"[Agentic RAG] 执行失败: {e}")
        return {
            'message_id': message_id,
            'answer': f'Agentic RAG 执行出错: {str(e)}',
            'sources': [],
            'confidence': 'low',
            'reasoning_trace': [{'step': 'error', 'message': str(e)}],
            'loops_used': 0,
            'saved_file': None,
        }


