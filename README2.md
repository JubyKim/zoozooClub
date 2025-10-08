# 교보DTS 온보딩 멘토 AI Agent 프로젝트

## 1. 프로젝트 목표
Microsoft Teams 환경에서 신규 입사자의 온보딩을 돕는 AI 멘토 챗봇을 개발합니다. 1차 목표는 PC(로컬) 환경에서 팀즈봇 연동 및 AI 연동을 성공적으로 수행하는 것입니다.

## 2. 최종 확정된 주요 기능
*   **기본 정보 제공:**
    *   자료 검색 및 Q&A (RAG 기술 활용)
    *   사내 용어/약어 안내
    *   온보딩 체크리스트
*   **내부 시스템 연동 기능:**
    *   조직도/직원 정보 검색 (회사 인트라넷 API 활용)
    *   회의실 예약 (별도 Web API 활용)
    *   신규 등록 글 일일 보고서 자동 작성 (웹페이지 크롤링 및 이메일 전송)
*   **향후 확장 가능 기능:**
    *   이메일 전송 기능 (개발 기간 내 충분할 경우 진행, 구조적으로 가능하게 설계)

## 3. 핵심 아키텍처
*   **어댑터(Adapter) 패턴**을 도입하여 봇의 핵심 로직과 외부 시스템(인트라넷, 회의실 예약 API, 웹 크롤링 대상 페이지 등)을 분리합니다.

## 4. 주요 기술 스택 (Google Cloud 기반)
*   **봇 프레임워크:** Microsoft Bot Framework (Python SDK)
*   **백엔드:** Python (FastAPI)
*   **AI/LLM:** Google Cloud Vertex AI (Gemini 등)
*   **검색 (RAG):** Google Cloud Vertex AI Vector Search (또는 Google Cloud Search)
*   **이메일 전송:** Google Cloud SendGrid (또는 다른 SMTP 서비스)
*   **실행 환경:** PC(로컬) 환경에서 실행 (클라우드 서비스는 API 연동 방식으로 활용)

## 5. 최종 개발 계획 (2인, 4주)
2명의 개발자가 4주 동안 MVP(최소 기능 제품)를 개발하는 것으로 계획을 확정했습니다.

*   **주차별 계획:**
    *   **1주차:** API 탐색 및 공동 설계 (인트라넷/회의실 API 명세 파악 및 테스트, 웹 크롤링 대상 페이지 분석 시작). Google Cloud 계정 설정 및 필요한 IAM 역할/권한 구성. Teams 봇 등록 (로컬 테스트를 위한 App ID/Password 확보).
    *   **2주차:** 핵심 로직(AI 기능)과 API 어댑터(임시 데이터 기반) 병렬 구현. 개발자 A는 웹 크롤링을 위한 초기 분석 및 설계, Google Cloud Vertex AI (LLM) 및 Vertex AI Vector Search (검색) 연동 초기 구현에 집중.
    *   **3주차:** 실제 API 연동 및 기능 통합. 개발자 A는 '일일 보고서' 기능의 웹페이지 크롤링 로직을 구현하고 LLM 요약 기능을 연동. 개발자 B는 어댑터에 실제 API 호출 코드 적용 및 Google Cloud SendGrid (또는 다른 SMTP 서비스)를 활용한 이메일 발송 기능 구현 시작.
    *   **4주차:** 통합 테스트 및 안정화. 모든 기능(AI + 실제 API 연동 + 웹 크롤링)을 통합하여 로컬 환경에서 최종 테스트 및 안정화를 진행합니다. 이메일 발송 기능을 완료하여 보고서 전송에 활용합니다.

## 6. 프로그램 디렉토리 구조 제안

프로젝트의 모듈성과 유지보수성을 높이고, 각 기능이 명확하게 분리되도록 다음과 같은 디렉토리 구조를 제안합니다. 이 구조는 Python 프로젝트의 일반적인 관례와 Microsoft Bot Framework, FastAPI, 그리고 어댑터 패턴을 고려하여 설계되었습니다.

```
.
├── .env                      # 환경 변수 (API 키, 설정 값 등)
├── .gitignore                # Git 버전 관리 제외 파일 설정
├── README.md                 # 프로젝트 설명 및 사용법 문서
├── requirements.txt          # Python 패키지 의존성 목록
├── app.py                    # 봇의 메인 진입점 (FastAPI 애플리케이션)
├── config.py                 # 애플리케이션 전반의 설정 (봇 ID, 비밀번호 등)
├── tests/                    # 단위 및 통합 테스트 코드
│   ├── __init__.py
│   ├── test_bot.py           # 봇의 대화 흐름 테스트
│   └── test_services.py      # 외부 서비스 연동 테스트
├── src/                      # 주요 소스 코드 디렉토리
│   ├── __init__.py
│   ├── bot/                  # 봇의 대화 로직 및 핸들러
│   │   ├── __init__.py
│   │   ├── dialogs/          # 대화 흐름 정의 (예: 메인 다이얼로그, 예약 다이얼로그)
│   │   │   ├── __init__.py
│   │   │   └── main_dialog.py
│   │   ├── activity_handler.py # 봇의 활동(메시지, 이벤트) 처리 로직
│   │   └── cards/            # Adaptive Card 템플릿 정의
│   │       ├── __init__.py
│   │       └── welcome_card.py
│   ├── services/             # 외부 시스템 연동 (어댑터 패턴 구현)
│   │   ├── __init__.py
│   │   ├── intranet_service.py     # 인트라넷 API 연동 (조직도/직원 정보)
│   │   ├── meeting_room_service.py # 회의실 예약 Web API 연동
│   │   ├── email_service.py        # 이메일 발송 서비스 (Google Cloud SendGrid 등)
│   │   └── crawling_service.py     # 웹페이지 크롤링 (일일 보고서 데이터 수집)
│   ├── ai/                   # AI/LLM 관련 컴포넌트
│   │   ├── __init__.py
│   │   ├── llm_client.py           # Google Cloud Vertex AI (LLM) 클라이언트 인터페이스
│   │   ├── vector_search.py        # Google Cloud Vertex AI Vector Search 클라이언트 인터페이스
│   │   └── knowledge_base.py       # RAG 지식 베이스 관리 로직
│   ├── models/               # 데이터 모델 정의 (Pydantic 등)
│   │   ├── __init__.py
│   │   ├── user_model.py           # 사용자 정보 모델
│   │   └── meeting_model.py        # 회의실/예약 정보 모델
│   └── utils/                # 공통 유틸리티 함수
│       ├── __init__.py
│       └── helpers.py
└── data/                     # 정적 데이터 파일 (Jargon, Checklist, RAG 문서 등)
    ├── jargon.json           # 사내 용어 사전
    ├── checklist.json        # 온보딩 체크리스트
    └── documents/            # RAG를 위한 원본 문서 (PDF, DOCX 등)
        ├── doc1.pdf
        └── doc2.docx

```

**주요 디렉토리 설명:**

*   **`app.py`**: 봇 애플리케이션의 시작점입니다. FastAPI를 사용하여 HTTP 요청을 처리하고 봇 활동을 라우팅합니다.
*   **`config.py`**: 봇의 App ID, Password, API 키 등 환경에 따라 달라지는 설정 값들을 관리합니다.
*   **`src/`**: 모든 핵심 소스 코드가 위치하는 디렉토리입니다.
    *   **`src/bot/`**: 봇의 대화 흐름, 사용자 입력 처리, Adaptive Card 생성 등 봇 자체의 로직을 담당합니다.
    *   **`src/services/`**: 외부 시스템(인트라넷, 회의실 예약 시스템, 이메일 서비스, 웹 크롤링 대상)과의 연동을 담당하는 어댑터 역할을 합니다. 봇의 핵심 로직은 이 서비스들의 내부 구현을 알 필요 없이 정의된 인터페이스를 통해 통신합니다.
    *   **`src/ai/`**: Google Cloud Vertex AI (LLM, Vector Search)와의 연동 및 RAG 지식 베이스 관리 로직을 포함합니다.
    *   **`src/models/`**: 프로젝트 전반에서 사용되는 데이터 구조를 정의합니다.
    *   **`src/utils/`**: 로깅, 헬퍼 함수 등 공통적으로 사용되는 유틸리티 코드를 모아둡니다.
*   **`data/`**: 봇이 사용하는 정적 데이터 파일(사내 용어 사전, 온보딩 체크리스트) 및 RAG를 위한 원본 문서들을 저장합니다.
*   **`tests/`**: 작성된 코드의 기능 검증을 위한 테스트 코드를 포함합니다.

이 구조는 각 기능의 책임이 명확하여 개발 및 유지보수가 용이하며, 향후 기능 확장에도 유연하게 대응할 수 있습니다.
