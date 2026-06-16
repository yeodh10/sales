"""
Phase 3: 제품 매칭.

분류된 보안 공고를 회사 제품 카탈로그(catalog.json)와 대조해
공고별 추천 제품과 그 근거를 만든다.

결과 한 건:
    {
      "공고번호": str,
      "공고명": str,
      "카테고리": str,
      "추천제품": [ {"제품명": str, "매칭이유": str}, ... ],
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).parent / "catalog.json"

_SYSTEM_PROMPT = (
    "당신은 공공기관 보안 영업을 지원하는 솔루션 엔지니어입니다. "
    "주어진 보안 입찰공고 각각에 대해, 제공된 제품 카탈로그에서 가장 적합한 제품을 "
    "1~2개 고르고 왜 적합한지 공고의 요구와 제품의 핵심기능·적합한_요구를 연결해 "
    "1문장으로 설명하세요. 적합한 제품이 없으면 추천제품은 빈 배열로 두세요. "
    "반드시 JSON 배열만 출력하고 다른 말은 붙이지 마세요."
)


def load_catalog(path: Path | str = CATALOG_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


def match_bids(
    security_bids: list[dict],
    catalog: list[dict] | None = None,
) -> list[dict]:
    """
    보안 공고 목록을 제품 카탈로그와 매칭한다.

    Args:
        security_bids: classifier 결과 중 보안=True 인 dict 리스트
                       (최소 공고번호/공고명/카테고리 포함).
        catalog: 제품 카탈로그. None이면 catalog.json 로드.

    Returns:
        공고별 추천 제품 dict 리스트.
    """
    if not security_bids:
        return []
    if catalog is None:
        catalog = load_catalog()

    client = config.make_anthropic_client()

    bids_json = json.dumps(
        [
            {
                "공고번호": b.get("공고번호", ""),
                "공고명": b.get("공고명", ""),
                "카테고리": b.get("카테고리", ""),
            }
            for b in security_bids
        ],
        ensure_ascii=False,
        indent=2,
    )
    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2)

    user_prompt = (
        "## 제품 카탈로그\n"
        f"{catalog_json}\n\n"
        "## 보안 입찰공고\n"
        f"{bids_json}\n\n"
        "각 공고에 대해 "
        '{"공고번호","공고명","카테고리","추천제품":[{"제품명","매칭이유"}]} '
        "형태의 JSON 객체를 만들어 입력 순서대로 JSON 배열로 출력하세요."
    )

    try:
        resp = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"매칭 API 호출 실패: {e}") from e

    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        parsed = _extract_json_array(text)
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"매칭 결과 파싱 실패: {e}") from e

    # 입력과 결과를 공고번호(키) 기준으로 매핑한다.
    # (응답이 입력 순서를 보장하지 않으므로 index 기준 병합은 공고-제품을 뒤섞을 위험이 있다.)
    by_no = {
        str(item.get("공고번호", "")).strip(): item
        for item in parsed
        if isinstance(item, dict) and str(item.get("공고번호", "")).strip()
    }

    results: list[dict] = []
    missing: list[str] = []
    for src in security_bids:
        no = str(src.get("공고번호", "")).strip()
        item = by_no.get(no)
        if item is None:
            # 입력에 있으나 응답에 없는 공고: 누락 기록 후 추천제품 없이 보존.
            missing.append(no or src.get("공고명", ""))
            results.append(
                {
                    "공고번호": src.get("공고번호", ""),
                    "공고명": src.get("공고명", ""),
                    "카테고리": src.get("카테고리", ""),
                    "추천제품": [],
                }
            )
            continue
        recs = item.get("추천제품", []) or []
        norm_recs = [
            {"제품명": r.get("제품명", ""), "매칭이유": r.get("매칭이유", "")}
            for r in recs
            if isinstance(r, dict)
        ]
        results.append(
            {
                "공고번호": item.get("공고번호") or src.get("공고번호", ""),
                "공고명": item.get("공고명") or src.get("공고명", ""),
                "카테고리": item.get("카테고리") or src.get("카테고리", ""),
                "추천제품": norm_recs,
            }
        )

    if missing:
        logger.warning(
            "매칭 응답에서 %d건 누락(공고번호 기준): %s",
            len(missing),
            ", ".join(missing),
        )
    return results
