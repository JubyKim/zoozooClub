import asyncio
import logging
from functools import lru_cache
from typing import Optional
import google.generativeai as genai
from config import get_config

logger = logging.getLogger(__name__)

class GeminiClient:
    """Google Gemini AI 클라이언트 - 싱글톤 패턴"""
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        config = get_config()
        try:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self._model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini Client initialized with gemini-2.5-flash")
        except Exception as e:
            logger.error(f"Error initializing Gemini Client: {e}")
            self._model = None
        
        self._initialized = True
    
    @property
    def model(self):
        return self._model
    
    def generate_answer(self, question: str) -> str:
        """동기 답변 생성"""
        if not self.model:
            return "AI 모델이 정상적으로 초기화되지 않았습니다."
        
        if not question.strip():
            return "질문을 입력해 주세요."
        
        try:
            prompt = f"다음 질문에 대해 정확하고 간결하게 한국어로 답변해 주세요:\n\n{question}"
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    top_p=0.8,
                    top_k=40
                ),
                safety_settings={
                    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                }
            )

            if not response.candidates:
                return "답변을 생성할 수 없습니다. 다른 질문을 시도해 주세요."
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                logger.warning(f"No content in response. Finish reason: {candidate.finish_reason}")
                return "답변을 생성할 수 없습니다. 다른 질문을 시도해 주세요."

            return response.text
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "답변 생성 중 오류가 발생했습니다."


    async def generate_answer_async(self, question: str) -> str:
        """비동기 답변 생성"""
        return await asyncio.to_thread(self.generate_answer, question)

@lru_cache(maxsize=1)
def get_gemini_client():
    """Gemini 클라이언트 인스턴스 캐싱"""
    return GeminiClient()
