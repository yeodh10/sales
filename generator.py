"""
Phase 5: 영업 산출물 생성.

매칭 결과(공고 + 추천제품)를 받아 공고별 영업 토킹포인트 초안을 만든다.
구조: 고객 요구 → 우리 강점 → 차별점.

결과 한 건:
    {
      "공고번호": str,
      "공고명": str,
      "고객요구": str,
      "우리강점": str,
      "차별점": str,
      "토킹포인트": str,   # 한 문단 요약
    }
"""

from __future__ import annotations

import json
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 공공기관 보안 영업 담당자를 돕는 카피라이터입니다. "
    "각 공고와 추천제품을 바탕으로 영업 토킹포인트 초안을 작성하세요. "
    "과장·단정 대신 공고 근거에 기반한 현실적인 표현을 쓰고, "
    "'고객요구'는 공고가 무엇을 원하는지, '우리강점'은 추천제품이 그걸 어떻게 충족하는지, "
    "'차별점'은 경쟁사 대비 우위를, '토킹포인트'는 이 셋을 묶은 2~3문장 멘트로 쓰세요. "
    "모든 값은 한국어. 반드시 JSON 배열만 출력하세요."
)


def _extract_json_array(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"JSON 배열을 찾지 못했습니다. 응답: {text[:200]}")
    return json.loads(text[start : end + 1])


def generate_talking_points(matched_bids: list[dict]) -> list[dict]:
    """
    매칭된 공고별 영업 토킹포인트를 생성한다.

    Args:
        matched_bids: matcher.match_bids 결과(추천제품 포함) 리스트.

    Returns:
        토킹포인트 dict 리스트.
    """
    # 추천제품이 있는 공고만 대상으로 한다.
    targets = [b for b in matched_bids if b.get("추천제품")]
    if not targets:
        return []

    client = config.make_anthropic_client()

    payload = json.dumps(targets, ensure_ascii=False, indent=2)
    user_prompt = (
        "다음은 보안 입찰공고와 매칭된 추천제품입니다. 각 공고에 대해 "
        '{"공고번호","공고명","고객요구","우리강점","차별점","토킹포인트"} '
        "JSON 객체를 만들어 입력 순서대로 JSON 배열로 출력하세요.\n\n"
        f"{payload}"
    )

    try:
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"토킹포인트 생성 API 호출 실패: {e}") from e

    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        parsed = _extract_json_array(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"토킹포인트 파싱 실패: {e}") from e

    # 입력과 결과를 공고번호(키) 기준으로 매핑한다.
    # (응답 순서가 입력과 어긋날 수 있어 index 병합은 토킹포인트를 엉뚱한 공고에 붙일 위험이 있다.)
    by_no = {
        str(item.get("공고번호", "")).strip(): item
        for item in parsed
        if isinstance(item, dict) and str(item.get("공고번호", "")).strip()
    }

    results: list[dict] = []
    missing: list[str] = []
    for src in targets:
        no = str(src.get("공고번호", "")).strip()
        item = by_no.get(no)
        if item is None:
            # 입력에 있으나 응답에 없는 공고: 누락 기록 후 토킹포인트는 빈 값으로 보존.
            missing.append(no or src.get("공고명", ""))
            results.append(
                {
                    "공고번호": src.get("공고번호", ""),
                    "공고명": src.get("공고명", ""),
                    "고객요구": "",
                    "우리강점": "",
                    "차별점": "",
                    "토킹포인트": "",
                }
            )
            continue
        results.append(
            {
                "공고번호": item.get("공고번호") or src.get("공고번호", ""),
                "공고명": item.get("공고명") or src.get("공고명", ""),
                "고객요구": item.get("고객요구", ""),
                "우리강점": item.get("우리강점", ""),
                "차별점": item.get("차별점", ""),
                "토킹포인트": item.get("토킹포인트", ""),
            }
        )

    if missing:
        logger.warning(
            "토킹포인트 응답에서 %d건 누락(공고번호 기준): %s",
            len(missing),
            ", ".join(missing),
        )
    return results
