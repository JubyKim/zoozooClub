import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from functools import lru_cache
import sqlite3

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.ai.llm_client import get_gemini_client
from config import get_config

logger = logging.getLogger(__name__)

class RAGHandler:
    """RAG 검색 핸들러 - 단순화된 버전"""
    _instance = None
    _embeddings = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        config = get_config()
        self.docs_dir = config.DOCS_DIRECTORY
        self.faiss_index_path = config.FAISS_INDEX_PATH
        self.llm_client = get_gemini_client()
        
        # 임베딩 모델 초기화 (한 번만)
        if RAGHandler._embeddings is None:
            logger.info("Initializing embeddings model...")
            RAGHandler._embeddings = HuggingFaceEmbeddings(
                model_name="intfloat/multilingual-e5-large-instruct",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("Embeddings model initialized")
        
        self.embeddings = RAGHandler._embeddings
        self.vectorstore = None
        self._initialize_vectorstore()
        self._initialized = True

    def _initialize_vectorstore(self):
        """기존 FAISS 인덱스 로드만"""
        if self.faiss_index_path.exists():
            try:
                logger.info("Loading existing FAISS index...")
                self.vectorstore = FAISS.load_local(
                    str(self.faiss_index_path), 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")
                self.vectorstore = None
        else:
            logger.warning("FAISS index not found. Run preprocessing first.")
            self.vectorstore = None

    async def get_rag_answer(self, query: str) -> Tuple[Optional[str], List[Dict]]:
        """RAG 답변 생성"""
        if not self.vectorstore or not query.strip():
            return None, []

        try:
            # 문서 검색
            retrieved_docs = self.vectorstore.similarity_search(query, k=5)
            if not retrieved_docs:
                return None, []

            # 컨텍스트 구성
            context = "\n\n".join(doc.page_content for doc in retrieved_docs)
            
            # 참조 정보 수집
            references = []
            metadata_list = []
            
            for doc in retrieved_docs:
                meta = doc.metadata
                ref = f"- {meta.get('source', '출처 불명')}"
                
                if meta.get('reguser'):
                    ref += f" (작성자: {meta['reguser']})"
                if meta.get('url'):
                    ref += f" (URL: {meta['url']})"
                
                references.append(ref)
                metadata_list.append(meta)

            # LLM 프롬프트
            prompt = f"""다음 정보를 바탕으로 질문에 정확하게 답변해 주세요.
정보에서 답변을 찾을 수 없다면 '내부 정보로는 답변을 찾을 수 없습니다.'라고 응답하세요.

참고 정보:
{context}

질문: {query}
답변:"""

            # 답변 생성
            answer = await self.llm_client.generate_answer_async(prompt)
            
            # 답변 불가 확인
            if "내부 정보로는 답변을 찾을 수 없습니다" in answer:
                return None, metadata_list

            # 출처 정보 추가
            if references:
                unique_refs = sorted(set(references))
                answer_with_sources = f"{answer}\n\n---\n**출처:**\n" + "\n".join(unique_refs)
                return answer_with_sources, metadata_list
            
            return answer, metadata_list

        except Exception as e:
            logger.error(f"Error in RAG answer generation: {e}")
            return None, []

    async def record_feedback(self, query: str, answer: str, feedback_type: str, 
                            retrieved_docs_metadata: List[Dict]):
        """피드백 기록"""
        db_path = self.faiss_index_path / "feedback.db"
        
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        query TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        retrieved_docs TEXT
                    )
                """)
                
                conn.execute("""
                    INSERT INTO feedback (timestamp, query, answer, feedback_type, retrieved_docs)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    query,
                    answer,
                    feedback_type,
                    json.dumps(retrieved_docs_metadata, ensure_ascii=False)
                ))
                
            logger.info("Feedback recorded successfully")
            
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")

@lru_cache(maxsize=1)
def get_rag_handler():
    """RAG 핸들러 인스턴스 캐싱"""
    return RAGHandler()
