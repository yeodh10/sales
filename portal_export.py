# -*- coding: utf-8 -*-
"""영업부 포털 데이터 익스포터.

에이전트 브리핑 JSON(+ 제품 카탈로그)을 읽어 portal/data.js 를 생성한다.
우선순위: data/briefing_latest.json(라이브 산출물) → data/sample_briefing.json(샘플).

사용:
    python portal_export.py                 # 오늘 기준
    python portal_export.py --ref 2026-06-15  # 기준일 지정
"""
from __future__ import annotations

import argparse
import io
import json
import os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(BASE, "data", "briefing_latest.json")
SAMPLE = os.path.join(BASE, "data", "sample_briefing.json")
CAT = os.path.join(BASE, "catalog.json")
OUT = os.path.join(BASE, "portal", "data.js")


def _safe_url(u: object) -> str:
    """저장형 XSS 2차 방어: http/https 로 시작하는 URL만 통과시키고,
    javascript:/data: 등 위험 스킴은 빈 문자열로 정제한다.
    (클라이언트 safeUrl 과 이중 방어)."""
    s = str(u or "").strip()
    return s if s[:7].lower() == "http://" or s[:8].lower() == "https://" else ""


def load_briefing() -> tuple[dict, str]:
    path = LIVE if os.path.exists(LIVE) else SAMPLE
    with open(path, encoding="utf-8") as f:
        return json.load(f), os.path.basename(path)


def export(ref: str | None = None) -> dict:
    """브리핑 + 카탈로그 → portal/data.js 생성. 통계 dict 반환(app.py에서도 호출)."""
    ref = ref or date.today().isoformat()
    brief, src_file = load_briefing()
    with open(CAT, encoding="utf-8") as f:
        catalog = json.load(f)

    bids = []
    for it in brief.get("items", []):
        bids.append({
            "id": it.get("공고번호", ""),
            "name": it.get("공고명", ""),
            "org": it.get("발주기관", ""),
            "type": it.get("업무구분", ""),
            "url": _safe_url(it.get("공고url", "")),
            "deadline": it.get("마감일시", ""),
            "security": bool(it.get("보안여부", False)),
            "grade": it.get("등급", ""),
            "category": it.get("카테고리", ""),
            "reason": it.get("판단근거", ""),
            "products": [p.get("제품명", "") for p in it.get("추천제품", [])],
            "match": [p.get("매칭이유", "") for p in it.get("추천제품", [])],
            "crosssell": it.get("크로스셀", ""),
            "need": it.get("고객요구", ""),
            "strength": it.get("우리강점", ""),
            "diff": it.get("차별점", ""),
            "talk": it.get("토킹포인트", ""),
        })

    products = [{
        "name": p.get("제품명", ""),
        "category": p.get("카테고리", ""),
        "features": p.get("핵심기능", []),
        "fits": p.get("적합한_요구", []),
        "diff": p.get("차별점", ""),
    } for p in catalog]

    data = {
        "generatedAt": brief.get("생성일", ""),
        "source": brief.get("출처", ""),
        "analyzedBy": brief.get("분석", ""),
        "total": brief.get("수집건수", len(bids)),
        "refDate": ref,
        "sourceFile": src_file,
        "bids": bids,
        "products": products,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성: portal_export.py — 직접 편집하지 마세요. 출처: "
                + src_file + " + catalog.json */\n")
        f.write("window.PORTAL_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    return {"out": OUT, "source": src_file, "bids": len(bids),
            "products": len(products), "ref": ref}


def main() -> None:
    ap = argparse.ArgumentParser(description="영업부 포털 data.js 생성")
    ap.add_argument("--ref", default=None,
                    help="우선순위 점수 계산 기준일 (기본: 오늘)")
    args = ap.parse_args()
    s = export(args.ref)
    print("wrote", s["out"])
    print("source:", s["source"], "| bids:", s["bids"],
          "| products:", s["products"], "| ref:", s["ref"])


if __name__ == "__main__":
    main()
