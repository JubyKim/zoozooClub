# -*- coding: utf-8 -*-
"""
데이터 소스 설정 파일
각 데이터 소스의 우선순위, 접근 레벨, 업데이트 주기 등을 정의
"""

# 데이터 소스 분류 및 설정
DATA_SOURCES = {
    "board": {
        "공지사항": {
            "priority": 1,
            "access_level": "public",
            "update_freq": "daily",
            "source_type": "board",
            "category": "공지사항"
        },
        "회사소식": {
            "priority": 2,
            "access_level": "public",
            "update_freq": "weekly",
            "source_type": "board",
            "category": "회사소식"
        },
        "교육": {
            "priority": 1,
            "access_level": "public",
            "update_freq": "monthly",
            "source_type": "board",
            "category": "교육"
        },
        "자유게시판": {
            "priority": 3,
            "access_level": "public",
            "update_freq": "daily",
            "source_type": "board",
            "category": "자유게시판"
        },
        "직원정보": {
            "priority": 2,
            "access_level": "internal",
            "update_freq": "monthly",
            "source_type": "board",
            "category": "직원정보"
        },
        "동아리정보": {
            "priority": 3,
            "access_level": "public",
            "update_freq": "monthly",
            "source_type": "board",
            "category": "동아리정보"
        },
        "노조활동": {
            "priority": 2,
            "access_level": "public",
            "update_freq": "weekly",
            "source_type": "board",
            "category": "노조활동"
        },
        "helpdesk": {
            "priority": 1,
            "access_level": "public",
            "update_freq": "daily",
            "source_type": "board",
            "category": "helpdesk"
        },
        "내부통제규정": {
            "priority": 1,
            "access_level": "internal",
            "update_freq": "quarterly",
            "source_type": "board",
            "category": "내부통제규정"
        }
    },
    "documents": {
        "제안서": {
            "priority": 2,
            "access_level": "internal",
            "extensions": [".ppt", ".pptx", ".doc", ".docx"],
            "source_type": "documents",
            "category": "제안서"
        },
        "안내서": {
            "priority": 1,
            "access_level": "public",
            "extensions": [".pdf", ".doc", ".docx"],
            "source_type": "documents",
            "category": "안내서"
        },
        "교육자료": {
            "priority": 1,
            "access_level": "public",
            "extensions": [".ppt", ".pptx", ".pdf"],
            "source_type": "documents",
            "category": "교육자료"
        }
    },
    "restricted": {
        "이력서": {
            "priority": 3,
            "access_level": "hr_only",
            "extensions": [".pdf", ".doc", ".docx"],
            "source_type": "restricted",
            "category": "이력서"
        },
        "수지분석서": {
            "priority": 2,
            "access_level": "finance_only",
            "extensions": [".xlsx", ".xls"],
            "source_type": "restricted",
            "category": "수지분석서"
        },
        "계약서": {
            "priority": 1,
            "access_level": "legal_only",
            "extensions": [".pdf", ".doc", ".docx"],
            "source_type": "restricted",
            "category": "계약서"
        }
    }
}

# 접근 레벨 매핑
ACCESS_LEVEL_MAP = {
    "public": ["public"],
    "internal": ["public", "internal"],
    "hr_only": ["public", "internal", "restricted"],
    "finance_only": ["public", "internal", "restricted"],
    "legal_only": ["public", "internal", "restricted"]
}

# 사용자 역할 매핑 (예시 - 실제 환경에 맞게 수정 필요)
USER_ROLES = {
    "일반직원": "public",
    "팀장": "internal",
    "인사담당자": "hr_only",
    "재무담당자": "finance_only",
    "법무담당자": "legal_only"
}

def get_access_level(source_type: str, category: str) -> str:
    """데이터 소스의 접근 레벨 반환"""
    if source_type in DATA_SOURCES:
        source_config = DATA_SOURCES[source_type].get(category, {})
        return source_config.get("access_level", "public")
    return "public"

def get_priority(source_type: str, category: str) -> int:
    """데이터 소스의 우선순위 반환"""
    if source_type in DATA_SOURCES:
        source_config = DATA_SOURCES[source_type].get(category, {})
        return source_config.get("priority", 3)
    return 3

def get_available_indexes(user_access_level: str) -> list:
    """사용자 권한에 따른 접근 가능한 인덱스 목록"""
    return ACCESS_LEVEL_MAP.get(user_access_level, ["public"])
