# kyobo_rag_build_and_query.py
# -*- coding: utf-8 -*-
"""
CSV/TXT → 임베딩 → FAISS 인덱스 저장, 그리고 질의까지 한 번에.
- 1) Bedrock Titan Embeddings 우선 사용 (AWS 자격/region 필요)
- 2) 실패 시 CPU 친화적인 e5-small(HuggingFace)로 폴백
- 3) CLI:
     인덱스 구축: python kyobo_rag_build_and_query.py build --data-dir ./data --out ./faiss_index
     질의 테스트: python kyobo_rag_build_and_query.py query --out ./faiss_index --q "인사규정 징계 절차?"
"""

import os
import argparse
from pathlib import Path
from typing import List

# LangChain / Vector
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# 임베딩: Bedrock 우선, 실패 시 HuggingFace로 폴백
def get_embeddings():
    """
    1) Amazon Bedrock: amazon.titan-embed-text-v2:0 (또는 v1)
    2) Fallback: intfloat/multilingual-e5-small (CPU)
    """
    try:
        from langchain_community.embeddings import BedrockEmbeddings
        # region은 환경변수 AWS_REGION 또는 AWS_DEFAULT_REGION 로 읽힘
        # credentials는 aws configure 또는 EC2 role 사용
        print("[INFO] Using Amazon Bedrock Titan Embeddings")
        return BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
    except Exception as e:
        print(f"[WARN] BedrockEmbeddings 사용 실패 → HuggingFace 폴백: {e}")
        from langchain_community.embeddings import HuggingFaceEmbeddings
        # e5-small: 가볍고 한국어 포함 다국어 지원
        return HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-small",
            encode_kwargs={"normalize_embeddings": True},
        )

def load_csv_and_txt(data_dir: Path) -> List[Document]:
    """
    data_dir 아래의 *.csv, *.txt 파일을 모두 읽어 Document 리스트로 반환
    """
    docs: List[Document] = []

    # CSV
    from langchain_community.document_loaders import CSVLoader
    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            loader = CSVLoader(str(csv_path))
            loaded = loader.load()
            for d in loaded:
                d.metadata.update({"source": csv_path.name, "type": "csv"})
            docs.extend(loaded)
            print(f"[INFO] Loaded CSV: {csv_path.name} ({len(loaded)} rows)")
        except Exception as e:
            print(f"[WARN] CSV 로드 실패: {csv_path} → {e}")

    # TXT
    from langchain_community.document_loaders import TextLoader
    for txt_path in sorted(data_dir.glob("*.txt")):
        try:
            loaded = TextLoader(str(txt_path), encoding="utf-8").load()
            for d in loaded:
                d.metadata.update({"source": txt_path.name, "type": "txt"})
            docs.extend(loaded)
            print(f"[INFO] Loaded TXT: {txt_path.name} ({len(loaded)} docs)")
        except Exception as e:
            print(f"[WARN] TXT 로드 실패: {txt_path} → {e}")

    if not docs:
        print("[WARN] 로드된 문서가 없습니다. (CSV/TXT 파일을 확인하세요)")
    return docs

def split_docs(docs: List[Document], chunk_size=800, chunk_overlap=120) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    out: List[Document] = []
    for d in docs:
        chunks = splitter.split_text(d.page_content)
        # Document로 다시 포장(메타데이터 유지)
        out.extend([Document(page_content=c, metadata=d.metadata) for c in chunks])
    print(f"[INFO] Split into {len(out)} chunks")
    return out

def build_index(data_dir: str, out_dir: str):
    data_dir_p = Path(data_dir)
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    docs = load_csv_and_txt(data_dir_p)
    if not docs:
        return

    chunks = split_docs(docs)

    embeddings = get_embeddings()
    print("[INFO] Building FAISS index ... (임베딩 계산 중)")
    vs = FAISS.from_documents(chunks, embeddings)

    vs.save_local(str(out_dir_p))
    print(f"[INFO] Saved FAISS to: {out_dir_p.resolve()}")

def _load_index(out_dir: str):
    embeddings = get_embeddings()
    # allow_dangerous_deserialization=True 는 pickle 보안 경고용. 신뢰 경로에서만 사용.
    return FAISS.load_local(out_dir, embeddings, allow_dangerous_deserialization=True)

def query(out_dir: str, question: str, k: int = 4):
    vs = _load_index(out_dir)
    retriever = vs.as_retriever(search_kwargs={"k": k})
    ctx = retriever.get_relevant_documents(question)

    # 생성형 모델(Bedrock Claude 등)로 요약하고 싶다면 아래 주석 해제
    # from langchain_community.llms import Bedrock
    # llm = Bedrock(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
    # prompt = "다음 컨텍스트를 근거로 한국어로 간결하게 답하라.\n\n{context}\n\n질문: {q}\n답변:"
    # joined = "\n\n---\n\n".join([c.page_content for c in ctx])
    # answer = llm(prompt.format(context=joined, q=question))
    # print("\n[ANSWER]\n", answer)

    # 우선은 검색 결과만 보기 좋게 출력
    print("\n[TOP CONTEXTS]")
    for i, d in enumerate(ctx, 1):
        src = d.metadata.get("source")
        print(f"--- {i}. ({src}) ---")
        snippet = d.page_content.strip().replace("\n", " ")
        print(snippet[:500] + ("..." if len(snippet) > 500 else ""))

def main():
    parser = argparse.ArgumentParser(description="Build/query RAG index (Bedrock/HF + FAISS)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="CSV/TXT → FAISS 인덱스 생성")
    p_build.add_argument("--data-dir", required=True, help="CSV/TXT 위치 디렉토리")
    p_build.add_argument("--out", default="./faiss_index", help="FAISS 저장 경로")

    p_query = sub.add_parser("query", help="FAISS 인덱스에서 검색/요약")
    p_query.add_argument("--out", default="./faiss_index", help="FAISS 저장 경로")
    p_query.add_argument("--q", required=True, help="질문")
    p_query.add_argument("--k", type=int, default=4, help="가져올 문서 수")

    args = parser.parse_args()

    if args.cmd == "build":
        build_index(args.data_dir, args.out)
    elif args.cmd == "query":
        query(args.out, args.q, args.k)

if __name__ == "__main__":
    main()
