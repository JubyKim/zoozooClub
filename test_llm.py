#!/usr/bin/env python
"""LLM Client 테스트 스크립트"""
import asyncio
from src.ai.llm_client import get_gemini_client

def test_sync():
    print("=== 동기 테스트 시작 ===")
    client = get_gemini_client()
    
    questions = [
        "연차에 대해 알려줘",
        "파이썬이란?",
        "안녕하세요"
    ]
    
    for q in questions:
        print(f"\n질문: {q}")
        answer = client.generate_answer(q)
        print(f"답변: {answer[:100]}...")

async def test_async():
    print("\n\n=== 비동기 테스트 시작 ===")
    client = get_gemini_client()
    
    questions = [
        "연차 사용 방법은?",
        "회사 복지는?"
    ]
    
    for q in questions:
        print(f"\n질문: {q}")
        answer = await client.generate_answer_async(q)
        print(f"답변: {answer[:100]}...")

if __name__ == "__main__":
    test_sync()
    asyncio.run(test_async())
    print("\n\n=== 테스트 완료 ===")
