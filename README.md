# 교보DTS 온보딩 멘토 AI 챗봇

Microsoft Teams 환경에서 신규 입사자의 온보딩을 돕는 AI 멘토 챗봇입니다.

## 📋 목차
- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [설치 및 실행](#설치-및-실행)
- [프로젝트 구조](#프로젝트-구조)
- [환경 설정](#환경-설정)
- [사용 방법](#사용-방법)
- [개발 가이드](#개발-가이드)

## 🎯 프로젝트 개요

신규 입사자가 회사 생활에 빠르게 적응할 수 있도록 AI 기반 멘토 챗봇을 제공합니다. RAG(Retrieval-Augmented Generation) 기술을 활용하여 내부 문서를 검색하고, Google Gemini AI를 통해 자연스러운 대화형 답변을 제공합니다.

### 개발 목표
- PC(로컬) 환경에서 Microsoft Teams 봇 연동
- Google Gemini AI 및 RAG 기술 활용
- 내부 문서 기반 정확한 정보 제공
- 사용자 피드백 수집 및 개선

## ✨ 주요 기능

### 1. 내부 문서 검색 (RAG)
- FAISS 벡터 검색을 통한 관련 문서 검색
- 인사규정, 취업규칙 등 내부 문서 기반 답변
- 출처 정보 제공 (문서명, 작성자, URL)

### 2. 사내 용어 안내
- 사내 약어 및 전문 용어 설명
- 용어 사전 기반 즉시 답변

### 3. 온보딩 정보 제공
- 회사 생활 안내 (점심시간, 휴게실 등)
- 복지 혜택 정보
- 개발 환경 설정 가이드
- 담당자 연락처 안내

### 4. 외부 AI 검색
- 내부 문서에서 답변을 찾지 못한 경우
- Google Gemini AI를 통한 일반 지식 답변

### 5. 피드백 시스템
- 답변 품질 평가 (👍 도움됨 / 👎 도움 안됨 / ❓ 관련 없음)
- 피드백 데이터 수집 및 분석

## 🛠 기술 스택

### Backend
- **Python 3.11+**
- **FastAPI**: 웹 서버 프레임워크
- **Uvicorn**: ASGI 서버

### Bot Framework
- **Microsoft Bot Framework SDK**: Teams 봇 연동
- **botbuilder-core**: 봇 핵심 로직
- **botbuilder-schema**: 봇 스키마 정의

### AI/ML
- **Google Gemini 2.5 Flash**: LLM (대화형 AI)
- **HuggingFace Transformers**: 문서 전처리
- **sentence-transformers**: 텍스트 임베딩
- **intfloat/multilingual-e5-large-instruct**: 다국어 임베딩 모델

### RAG (검색 증강 생성)
- **LangChain**: RAG 파이프라인 구축
- **FAISS**: 벡터 검색 엔진
- **SQLite**: 문서 메타데이터 저장

### 한국어 처리
- **Kiwipiepy**: 한국어 형태소 분석
- **KoBART**: 한국어 요약 모델

## 🏗 시스템 아키텍처

```
┌─────────────────┐
│ Microsoft Teams │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         FastAPI Server              │
│  ┌──────────────────────────────┐   │
│  │   Bot Activity Handler       │   │
│  └──────────┬───────────────────┘   │
│             │                        │
│  ┌──────────▼───────────┐           │
│  │   RAG Handler        │           │
│  │  ┌────────────────┐  │           │
│  │  │ FAISS Search   │  │           │
│  │  └────────────────┘  │           │
│  │  ┌────────────────┐  │           │
│  │  │ SQLite DB      │  │           │
│  │  └────────────────┘  │           │
│  └──────────────────────┘           │
│             │                        │
│  ┌──────────▼───────────┐           │
│  │   Gemini AI Client   │           │
│  └──────────────────────┘           │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Google Gemini  │
│   2.5 Flash     │
└─────────────────┘
```

## 🚀 설치 및 실행

### 1. 사전 요구사항
- Python 3.11 이상
- Git
- Microsoft Teams 계정
- Google Cloud API 키

### 2. 프로젝트 클론
```bash
git clone <repository-url>
cd AI_CHATBOT_DTS
```

### 3. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

### 4. 패키지 설치
```bash
pip install -r requirements.txt
```

### 5. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 입력:
```env
BOT_ID="your-bot-id"
BOT_PASSWORD="your-bot-password"
GOOGLE_API_KEY="your-google-api-key"
PORT=3978
```

### 6. 문서 전처리 (최초 1회)
```bash
python preprocess_generic_document.py
```

이 과정에서:
- `data/docs/*.txt` 파일을 읽어 청크로 분할
- 키워드 추출 및 요약 생성
- SQLite DB에 저장
- FAISS 벡터 인덱스 생성

### 7. 봇 실행
```bash
python app.py
```

서버가 `http://localhost:3978`에서 실행됩니다.

### 8. Teams 연동
1. [Bot Framework Portal](https://dev.botframework.com/)에서 봇 등록
2. Messaging endpoint: `http://localhost:3978/api/messages`
3. Teams 채널 추가
4. Teams에서 봇 테스트

## 📁 프로젝트 구조

```
AI_CHATBOT_DTS/
├── app.py                          # FastAPI 메인 애플리케이션
├── config.py                       # 설정 관리
├── preprocess_generic_document.py  # 문서 전처리 스크립트
├── requirements.txt                # Python 패키지 의존성
├── .env                            # 환경 변수 (git 제외)
├── .gitignore                      # Git 제외 파일 목록
│
├── src/                            # 소스 코드
│   ├── bot/
│   │   ├── activity_handler.py    # 봇 메시지 처리 로직
│   │   └── __init__.py
│   └── ai/
│       ├── llm_client.py          # Gemini AI 클라이언트
│       ├── rag_handler.py         # RAG 검색 핸들러
│       └── __init__.py
│
├── data/                           # 데이터 파일
│   ├── docs/                       # 내부 문서
│   │   ├── 인사규정.txt
│   │   ├── 취업규칙.txt
│   │   ├── processed_documents.db  # 전처리된 문서 DB
│   │   ├── faiss_index/           # FAISS 벡터 인덱스
│   │   └── exported_json_chunks/  # JSON 형식 청크
│   ├── jargon.json                # 사내 용어 사전
│   ├── initial_questions.json     # 초기 질문 목록
│   ├── 개발_환경.json
│   ├── 담당자_안내.json
│   ├── 복지_혜택.json
│   ├── 사내_용어_질문.json
│   ├── 점심시간.json
│   ├── 회사_생활.json
│   └── 휴게실.json
│
├── config/                         # 설정 파일
│   └── data_sources_config.py
│
├── test_llm.py                     # LLM 테스트 스크립트
├── list_models.py                  # Gemini 모델 목록 확인
└── README.md                       # 프로젝트 문서 (본 파일)
```

## ⚙️ 환경 설정

### config.py 주요 설정
```python
class DefaultConfig:
    PORT = 3978                                    # 서버 포트
    APP_ID = os.getenv("BOT_ID", "")              # Teams 봇 ID
    APP_PASSWORD = os.getenv("BOT_PASSWORD", "")  # Teams 봇 비밀번호
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Google API 키
    
    DOCS_DIRECTORY = "data/docs"                   # 문서 디렉토리
    FAISS_INDEX_PATH = "data/docs/faiss_index"    # FAISS 인덱스 경로
```

### preprocess_config.json
문서 전처리 규칙 정의:
```json
{
  "chapter_regex": "^제(\\d+)장\\s+(.+)$",
  "article_regex": "^제(\\d+)조\\s*\\((.+)\\)$",
  "chapter_format": "제{}장 {}",
  "article_format": "제{}조",
  "cleaning_rules": [
    {"type": "startswith", "pattern": "페이지"},
    {"type": "contains", "pattern": "목차"}
  ]
}
```

## 📖 사용 방법

### 1. 기본 대화
Teams에서 봇에게 메시지를 보내면 자동으로 응답합니다.

**예시:**
- "연차는 어떻게 사용하나요?"
- "점심시간이 언제인가요?"
- "DTS가 뭐예요?"

### 2. 메인 메뉴
"메인메뉴" 입력 시 초기 질문 목록이 표시됩니다.

### 3. 피드백 제공
답변 후 표시되는 버튼으로 피드백을 제공할 수 있습니다:
- 👍 도움이 되었어요
- 👎 도움이 되지 않았어요
- ❓ 관련 없는 답변이에요

### 4. 외부 검색
내부 문서에서 답변을 찾지 못한 경우, 외부 AI 검색을 제안합니다.

## 🔧 개발 가이드

### 문서 추가
1. `data/docs/` 디렉토리에 `.txt` 파일 추가
2. `python preprocess_generic_document.py` 실행
3. 봇 재시작

### 용어 추가
`data/jargon.json` 파일 수정:
```json
{
  "DTS": {
    "definition": "Digital Transformation Service의 약자입니다.",
    "link": "https://example.com/dts"
  }
}
```

### 새로운 JSON 대화 흐름 추가
`data/` 디렉토리에 JSON 파일 생성:
```json
{
  "title": "질문 제목",
  "questions": [
    {"title": "옵션 1", "value": "option1"},
    {"title": "옵션 2", "value": "option2"}
  ]
}
```

### LLM 모델 변경
`src/ai/llm_client.py`에서 모델 변경:
```python
self._model = genai.GenerativeModel('gemini-2.5-flash')
# 또는
self._model = genai.GenerativeModel('gemini-2.5-pro')
```

### 테스트
```bash
# LLM 테스트
python test_llm.py

# 사용 가능한 모델 확인
python list_models.py
```

## 🐛 문제 해결

### 1. FAISS 인덱스를 찾을 수 없음
```bash
python preprocess_generic_document.py
```

### 2. Gemini API 오류
- API 키 확인: `.env` 파일의 `GOOGLE_API_KEY`
- 모델 이름 확인: `python list_models.py`

### 3. 봇이 응답하지 않음
- 서버 실행 확인: `http://localhost:3978/health`
- 로그 확인: 콘솔 출력 메시지

### 4. PowerShell 실행 정책 오류
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

또는 CMD 사용:
```cmd
.venv\Scripts\activate.bat
```

## 📊 성능 최적화

### 임베딩 모델
- CPU: `intfloat/multilingual-e5-large-instruct`
- GPU: `device='cuda'` 설정 (config.py)

### FAISS 인덱스
- 문서 수가 많을 경우 IVF 인덱스 사용 권장
- 청크 크기 조정: `chunk_size=500`, `chunk_overlap=50`

### 캐싱
- LRU 캐시 활용: `@lru_cache` 데코레이터
- 싱글톤 패턴: RAGHandler, GeminiClient

## 📝 라이선스

이 프로젝트는 교보DTS 내부용으로 개발되었습니다.

## 👥 개발팀

- 개발 기간: 4주
- 개발 인원: 2명
- 개발 환경: Python 3.11, Windows

## 📞 문의

프로젝트 관련 문의사항은 담당자에게 연락해주세요.

---

**마지막 업데이트:** 2025-01-04
