import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.absolute()

# 환경 변수 로드 (한 번만)
load_dotenv(PROJECT_ROOT / ".env")

class DefaultConfig:
    """봇의 기본 설정"""
    
    def __init__(self):
        self.PORT = int(os.getenv("PORT", "3978"))
        self.APP_ID = os.getenv("BOT_ID", "")
        self.APP_PASSWORD = os.getenv("BOT_PASSWORD", "")
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
        
        # 경로 설정
        self.DOCS_DIRECTORY = PROJECT_ROOT / "data" / "docs"
        self.PREPROCESS_CONFIG_FILE_PATH = PROJECT_ROOT / "data" / "preprocess_config.json"
        self.FAISS_INDEX_PATH = PROJECT_ROOT / "data" / "docs" / "faiss_index"

@lru_cache(maxsize=1)
def get_config():
    """설정 인스턴스 캐싱"""
    return DefaultConfig()
