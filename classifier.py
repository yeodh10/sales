"""
Phase 2: 보안 관련 분류.

입찰공고 목록을 Claude에 보내 각 공고가 보안 관련인지 + 어떤 카테고리인지
판단해 구조화된 결과로 돌려준다.

결과 한 건:
    {
      "공고번호": str,
      "공고명": str,
      "보안여부": bool,
      "카테고리": str,   # 보안이 아니면 "비보안"
      "판단근거": str,
    }
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass, asdict
from typing import Any

import config

# 분류 카테고리(고정 집합). 모델이 이 안에서만 고르도록 프롬프트로 강제한다.
CATEGORIES = [
    "방화벽",
    "망분리",
    "접근통제(IAM)",
    "보안관제(SOC)",
    "백신/EDR",
    "정보보호 컨설팅",
    "기타 보안",
    "비보안",
]

_SYSTEM_PROMPT = (
    "당신은 공공조달 입찰공고를 분석하는 정보보안 도메인 전문가입니다. "
    "각 공고가 '정보보안 제품/서비스 도입'과 관련 있는지 판단하고, "
    "아래 카테고리 중 정확히 하나로 분류하세요.\n"
    f"카테고리: {', '.join(CATEGORIES)}\n"
    "보안과 무관하면 보안여부=false, 카테고리='비보안'.\n"
    "판단근거는 공고명 근거를 들어 1문장으로 한국어로 작성하세요. "
    "반드시 JSON 배열만 출력하고 다른 말은 붙이지 마세요."
)


def _to_dict(bid: Any) -> dict:
    if is_dataclass(bid):
        return asdict(bid)
    if isinstance(bid, dict):
        return bid
    raise TypeError(f"지원하지 않는 공고 타입: {type(bid)}")


def _extract_json_array(text: str) -> list:
    """모델 응답에서 JSON 배열을 추출(코드펜스로 감싸도 대응)."""
    text = text.strip()
    if text.startswith("```"):
        # ```json ... ``` 형태 제거
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"JSON 배열을 찾지 못했습니다. 응답: {text[:200]}")
    return json.loads(text[start : end + 1])


def classify_bids(bids: list[Any]) -> list[dict]:
    """
    공고 목록을 보안 관련성 기준으로 분류한다.

    Args:
        bids: Bid 데이터클래스 또는 dict의 리스트.

    Returns:
        분류 결과 dict 리스트.

    Raises:
        RuntimeError: API 키 미설정 또는 호출/파싱 오류.
    """
    if not bids:
        return []

    from anthropic import Anthropic

    api_key = config.require_anthropic_key()
    client = Anthropic(api_key=api_key)

    rows = [_to_dict(b) for b in bids]
    numbered = "\n".join(
        f"{i}. 공고번호={r.get('공고번호','')} | 공고명={r.get('공고명','')} "
        f"| 업무구분={r.get('업무구분','')}"
        for i, r in enumerate(rows, 1)
    )

    user_prompt = (
        "다음 입찰공고들을 분류하세요. 각 공고에 대해 "
        '{"공고번호","공고명","보안여부","카테고리","판단근거"} 키를 가진 '
        "JSON 객체를 만들고, 입력 순서대로 JSON 배열로 출력하세요.\n\n"
        f"{numbered}"
    )

    try:
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"분류 API 호출 실패: {e}") from e

    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        parsed = _extract_json_array(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"분류 결과 파싱 실패: {e}") from e

    # 입력과 결과 매핑 보정: 공고명이 비면 원본으로 채운다.
    results: list[dict] = []
    for i, item in enumerate(parsed):
        src = rows[i] if i < len(rows) else {}
        results.append(
            {
                "공고번호": item.get("공고번호") or src.get("공고번호", ""),
                "공고명": item.get("공고명") or src.get("공고명", ""),
                "보안여부": bool(item.get("보안여부", False)),
                "카테고리": item.get("카테고리", "비보안"),
                "판단근거": item.get("판단근거", ""),
            }
        )
    return results
