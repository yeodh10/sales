"""
브리핑 빌더 (무료 경로 도구).

수집한 공고(JSON) + 분류 규칙(JSON)을 합쳐 대시보드용 브리핑 JSON을 만든다.
Claude Code가 분류 '규칙'만 작성하면(공고명 substring → 등급/카테고리/제품/멘트),
이 스크립트가 공고 원본과 병합해 완성한다. → 48건이든 100건이든 반복 없이 처리.

규칙 파일 형식(data/decisions.json):
{
  "default": {"등급": "제외", "카테고리": "무관", "판단근거": "키워드 오탐/무관"},
  "rules": [
    {"match": "보안관제 위탁운영", "등급": "영업대상", "카테고리": "보안관제(SOC)",
     "판단근거": "...", "추천제품": [{"제품명": "...", "매칭이유": "..."}],
     "고객요구": "...", "우리강점": "...", "차별점": "...", "토킹포인트": "...",
     "크로스셀": ""}
  ]
}

실행:
    venv\\Scripts\\python.exe build_briefing.py --bids data/bids_broad.json \\
        --decisions data/decisions.json --out data/sample_briefing.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)

SECURITY_GRADES = {"영업대상", "보안주제/매칭약함"}


def _norm(s: str) -> str:
    return (s or "").replace(" ", "")


def _match_rule(공고명: str, rules: list[dict]) -> dict | None:
    name = _norm(공고명)
    for r in rules:
        if _norm(r.get("match", "")) and _norm(r["match"]) in name:
            return r
    return None


def build(bids: list[dict], decisions: dict) -> list[dict]:
    rules = decisions.get("rules", [])
    default = decisions.get("default", {"등급": "제외", "카테고리": "무관",
                                        "판단근거": "키워드 오탐/무관"})
    items = []
    for b in bids:
        rule = _match_rule(b.get("공고명", ""), rules) or default
        grade = rule.get("등급", "제외")
        items.append({
            "공고번호": b.get("공고번호", ""),
            "공고명": b.get("공고명", ""),
            "발주기관": b.get("공고기관", ""),
            "업무구분": b.get("업무구분", ""),
            "공고url": b.get("공고url", ""),
            "마감일시": b.get("마감일시", ""),
            "보안여부": grade in SECURITY_GRADES,
            "등급": grade,
            "카테고리": rule.get("카테고리", "무관"),
            "판단근거": rule.get("판단근거", ""),
            "추천제품": rule.get("추천제품", []),
            "크로스셀": rule.get("크로스셀", ""),
            "고객요구": rule.get("고객요구", ""),
            "우리강점": rule.get("우리강점", ""),
            "차별점": rule.get("차별점", ""),
            "토킹포인트": rule.get("토킹포인트", ""),
        })
    return items


def main() -> int:
    p = argparse.ArgumentParser(description="공고+분류규칙 → 브리핑 JSON")
    p.add_argument("--bids", required=True)
    p.add_argument("--decisions", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    bids = json.load(open(a.bids, encoding="utf-8"))
    decisions = json.load(open(a.decisions, encoding="utf-8"))
    items = build(bids, decisions)

    out = {
        "생성일": datetime.now().strftime("%Y-%m-%d"),
        "출처": "나라장터(조달청) 입찰공고정보서비스",
        "분석": "Claude Code (무료 경로)",
        "수집건수": len(items),
        "items": items,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    from collections import Counter
    c = Counter(i["등급"] for i in items)
    print(f"[완료] {len(items)}건 → {a.out}")
    for g in ("영업대상", "연관기회", "보안주제/매칭약함", "제외"):
        if c.get(g):
            print(f"  {g}: {c[g]}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
