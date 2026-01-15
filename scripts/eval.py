#!/usr/bin/env python3
"""
RAG 系统评估脚本
v2.0 - 批量评估问答效果

用法:
    python scripts/eval.py [--input data/eval/questions.jsonl] [--output data/eval/results.jsonl]

输入文件格式 (questions.jsonl):
    {"question": "问题1", "expected": "预期关键词或答案片段"}
    {"question": "问题2", "expected": "预期关键词或答案片段"}

输出文件格式 (results.jsonl):
    {"question": "...", "answer": "...", "sources": [...], "confidence": "...", "latency_ms": ..., "expected": "...", "match": true/false}
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")


def load_questions(input_file: Path) -> List[Dict[str, Any]]:
    """加载评估问题"""
    questions = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def evaluate_question(
    question: str,
    expected: str = None,
    base_url: str = "http://localhost:5001",
    agentic_mode: bool = False,
) -> Dict[str, Any]:
    """评估单个问题"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={
                "user_id": "eval_user",
                "thread_id": "eval_thread",
                "message": question,
                "top_k": 5,
                "agentic_mode": agentic_mode,
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 简单匹配检查
        match = False
        if expected:
            answer_lower = data.get("answer", "").lower()
            expected_lower = expected.lower()
            # 检查预期关键词是否出现在答案中
            keywords = [kw.strip() for kw in expected_lower.split(",")]
            match = all(kw in answer_lower for kw in keywords)
        
        return {
            "question": question,
            "answer": data.get("answer", ""),
            "sources": [
                {
                    "source": s.get("source"),
                    "chunk_id": s.get("chunk_id"),
                    "score": s.get("score"),
                }
                for s in data.get("sources", [])
            ],
            "confidence": data.get("confidence"),
            "latency_ms": latency_ms,
            "expected": expected,
            "match": match,
            "error": None,
        }
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "question": question,
            "answer": None,
            "sources": [],
            "confidence": None,
            "latency_ms": latency_ms,
            "expected": expected,
            "match": False,
            "error": str(e),
        }


def run_evaluation(
    input_file: Path,
    output_file: Path,
    base_url: str = "http://localhost:5001",
    agentic_mode: bool = False,
) -> Dict[str, Any]:
    """运行完整评估"""
    questions = load_questions(input_file)
    print(f"📋 加载了 {len(questions)} 个评估问题")
    
    results = []
    total_latency = 0
    match_count = 0
    error_count = 0
    
    for i, q in enumerate(questions, 1):
        question = q.get("question", "")
        expected = q.get("expected", "")
        
        print(f"  [{i}/{len(questions)}] 评估: {question[:50]}...")
        
        result = evaluate_question(
            question=question,
            expected=expected,
            base_url=base_url,
            agentic_mode=agentic_mode,
        )
        
        results.append(result)
        total_latency += result["latency_ms"]
        
        if result["error"]:
            error_count += 1
            print(f"    ❌ 错误: {result['error']}")
        elif result["match"]:
            match_count += 1
            print(f"    ✅ 匹配 ({result['latency_ms']}ms)")
        else:
            print(f"    ⚠️ 不匹配 ({result['latency_ms']}ms)")
    
    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    # 统计摘要
    summary = {
        "total_questions": len(questions),
        "match_count": match_count,
        "error_count": error_count,
        "match_rate": match_count / len(questions) if questions else 0,
        "avg_latency_ms": total_latency / len(questions) if questions else 0,
        "agentic_mode": agentic_mode,
    }
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="RAG 系统评估脚本")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=PROJECT_ROOT / "data/eval/questions.jsonl",
        help="输入的问题文件 (jsonl 格式)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "data/eval/results.jsonl",
        help="输出的结果文件 (jsonl 格式)"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default="http://localhost:5001",
        help="API 服务地址"
    )
    parser.add_argument(
        "--agentic", "-a",
        action="store_true",
        help="使用 Agentic RAG 模式"
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"❌ 输入文件不存在: {args.input}")
        print("请创建 questions.jsonl 文件，格式如下：")
        print('{"question": "问题内容", "expected": "预期关键词"}')
        sys.exit(1)
    
    print("=" * 60)
    print("🔬 RAG 系统评估")
    print("=" * 60)
    print(f"📥 输入文件: {args.input}")
    print(f"📤 输出文件: {args.output}")
    print(f"🌐 API 地址: {args.url}")
    print(f"🤖 Agentic 模式: {'开启' if args.agentic else '关闭'}")
    print("=" * 60)
    
    summary = run_evaluation(
        input_file=args.input,
        output_file=args.output,
        base_url=args.url,
        agentic_mode=args.agentic,
    )
    
    print("=" * 60)
    print("📊 评估结果摘要")
    print("=" * 60)
    print(f"  总问题数: {summary['total_questions']}")
    print(f"  匹配数: {summary['match_count']}")
    print(f"  错误数: {summary['error_count']}")
    print(f"  匹配率: {summary['match_rate']:.1%}")
    print(f"  平均延迟: {summary['avg_latency_ms']:.0f}ms")
    print("=" * 60)
    print(f"✅ 结果已保存到: {args.output}")


if __name__ == "__main__":
    main()

