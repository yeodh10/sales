"""
공고 → 분류 → 매칭 → 토킹포인트로 이어지는 전체 파이프라인.
CLI(phase3~5)와 Streamlit UI가 공유한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import classifier
import generator
import matcher
import narajangteo

SAMPLE_PATH = Path(__file__).parent / "data" / "sample_bids.json"


def get_bids(
    sample: bool = False,
    division: str = "용역",
    keyword: str | None = None,
    days: int = 14,
    rows: int = 20,
) -> list[dict]:
    """예시 공고 또는 나라장터 실데이터를 dict 리스트로 반환."""
    if sample:
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)
    bids = narajangteo.search_bids(
        division=division, keyword=keyword, days=days, rows=rows
    )
    return [b.to_dict() for b in bids]


def build_briefing(
    classified: list[dict],
    matched: list[dict],
    talking_points: list[dict],
) -> list[dict]:
    """세 단계 결과를 공고번호 기준으로 합쳐 브리핑 행 리스트를 만든다."""
    match_by_no = {m["공고번호"]: m for m in matched}
    tp_by_no = {t["공고번호"]: t for t in talking_points}

    rows: list[dict] = []
    for c in classified:
        no = c["공고번호"]
        m = match_by_no.get(no, {})
        t = tp_by_no.get(no, {})
        rows.append(
            {
                "공고번호": no,
                "공고명": c["공고명"],
                "보안여부": c["보안여부"],
                "카테고리": c["카테고리"],
                "판단근거": c["판단근거"],
                "추천제품": m.get("추천제품", []),
                "토킹포인트": t.get("토킹포인트", ""),
                "고객요구": t.get("고객요구", ""),
                "우리강점": t.get("우리강점", ""),
                "차별점": t.get("차별점", ""),
            }
        )
    return rows


def run_pipeline(
    bids: list[dict],
    do_match: bool = True,
    do_talking_points: bool = True,
) -> dict:
    """
    전체 파이프라인 실행.

    Returns:
        {"classified", "security", "matched", "talking_points", "briefing"}
    """
    classified = classifier.classify_bids(bids)
    security = [c for c in classified if c["보안여부"]]

    matched: list[dict] = []
    talking_points: list[dict] = []

    if do_match and security:
        matched = matcher.match_bids(security)
        if do_talking_points and matched:
            talking_points = generator.generate_talking_points(matched)

    briefing = build_briefing(classified, matched, talking_points)
    return {
        "classified": classified,
        "security": security,
        "matched": matched,
        "talking_points": talking_points,
        "briefing": briefing,
    }
