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

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()
DATA_GO_KR_SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()


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
