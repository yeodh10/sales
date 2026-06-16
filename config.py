"""
환경설정 로더. .env에서 키와 기본값을 읽어 한 곳에서 관리한다.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Windows 콘솔 한글 깨짐 방지 (각 실행 스크립트에서 import만 해도 적용)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _from_secrets(name: str):
    """Streamlit Cloud 배포 시 st.secrets에서 값을 읽는다(로컬 CLI에는 영향 없음).

    .env(os.environ)에 값이 있으면 이 함수는 호출되지 않으므로, streamlit이
    설치돼 있지 않거나 secrets가 없는 일반 CLI 실행에서는 전혀 동작하지 않는다.
    """
    try:
        import streamlit as st  # 배포 환경에서만 사용 가능

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        return None
    return None


def _get(name: str, default: str = "") -> str:
    """우선순위: 환경변수(.env) → Streamlit secrets → 기본값."""
    value = os.getenv(name)
    if not value:
        value = _from_secrets(name)
    return (value if value is not None else default).strip()


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
DATA_GO_KR_SERVICE_KEY = _get("DATA_GO_KR_SERVICE_KEY", "")

# ── 호출 신뢰성(재시도/타임아웃) 공통 설정 ───────────────────────
# Anthropic SDK는 429/5xx/연결오류를 지수 백오프로 자동 재시도한다.
# 기본값을 환경변수로 조정 가능하게 노출한다.
ANTHROPIC_MAX_RETRIES = int(os.getenv("ANTHROPIC_MAX_RETRIES", "3"))
ANTHROPIC_TIMEOUT = float(os.getenv("ANTHROPIC_TIMEOUT", "60"))

# 나라장터(requests) 호출 재시도 횟수(429/5xx 대상).
DATA_GO_KR_MAX_RETRIES = int(os.getenv("DATA_GO_KR_MAX_RETRIES", "3"))

# 포털 공유 서버 CSRF 토큰. 하드코딩을 피하고 환경변수로 분리한다.
# (전면 인증이 아닌 비단순요청 강제용 커스텀 헤더. 배포 시 .env로 재정의 권장.)
PORTAL_TOKEN = _get("PORTAL_TOKEN", "portal-sales-2026")


def _is_placeholder(value: str) -> bool:
    """키가 비었거나 아직 예시값 그대로인지 판단."""
    return (not value) or ("여기에" in value)


def require_anthropic_key() -> str:
    if _is_placeholder(ANTHROPIC_API_KEY):
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env에 실제 키를 입력해 주세요.\n"
            "발급: https://console.anthropic.com"
        )
    return ANTHROPIC_API_KEY


def require_data_go_kr_key() -> str:
    if _is_placeholder(DATA_GO_KR_SERVICE_KEY):
        raise RuntimeError(
            "DATA_GO_KR_SERVICE_KEY가 설정되지 않았습니다. .env에 실제 인증키를 입력해 주세요.\n"
            "활용신청: https://www.data.go.kr/data/15129394/openapi.do"
        )
    return DATA_GO_KR_SERVICE_KEY


def make_anthropic_client():
    """재시도/타임아웃이 적용된 Anthropic 클라이언트를 생성한다.

    SDK가 429/5xx/연결오류를 지수 백오프로 자동 재시도하며, 요청별 타임아웃을
    적용한다. 모든 호출부에서 이 헬퍼를 써 동일한 신뢰성 설정을 공유한다.
    """
    from anthropic import Anthropic

    return Anthropic(
        api_key=require_anthropic_key(),
        max_retries=ANTHROPIC_MAX_RETRIES,
        timeout=ANTHROPIC_TIMEOUT,
    )
