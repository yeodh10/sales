"""
공고 수집 전용 스크립트 (AI 없음, 나라장터 키만 필요).
나라장터에서 공고를 받아 JSON 파일로 저장한다.

무료 경로(API 키 없이) 워크플로:
  1) 이 스크립트로 공고를 모아 data/bids_latest.json 에 저장
  2) Claude Code가 그 JSON + catalog.json 을 읽어 분류·매칭·토킹포인트 작성

실행 예시:
    venv\\Scripts\\python.exe fetch_bids.py --division 용역 --keyword 보안 --days 30
    venv\\Scripts\\python.exe fetch_bids.py --division 물품 --keyword 백신 --append
"""

import argparse
import json
import sys
from pathlib import Path

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)
import keywords
import narajangteo

OUT_DEFAULT = Path(__file__).parent / "data" / "bids_latest.json"


def collect_scope(scope: str, days: int, rows: int) -> list[dict]:
    """키워드 그룹(core/adjacent/all)을 용역+물품에 걸쳐 수집·중복제거."""
    by_no: dict[str, dict] = {}
    for division in ("용역", "물품"):
        for kw in keywords.keywords_for(scope):
            try:
                bids = narajangteo.search_bids(
                    division=division, keyword=kw, days=days, rows=rows
                )
            except RuntimeError as e:
                print(f"  [경고] {division}/{kw} 실패: {e}")
                continue
            for b in bids:
                by_no.setdefault(b.공고번호, b.to_dict())
    return list(by_no.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="나라장터 공고 수집 → JSON 저장")
    parser.add_argument(
        "--division", default="용역", choices=list(narajangteo.BUSINESS_DIVISIONS)
    )
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--scope", default=None, choices=["core", "adjacent", "all"],
                        help="키워드 그룹 일괄 수집(용역+물품). 지정 시 --division/--keyword 무시")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--rows", type=int, default=50)
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    parser.add_argument(
        "--append", action="store_true",
        help="기존 out 파일에 합치고 공고번호로 중복 제거",
    )
    args = parser.parse_args()

    try:
        if args.scope:
            new_rows = collect_scope(args.scope, args.days, args.rows)
        else:
            bids = narajangteo.search_bids(
                division=args.division, keyword=args.keyword,
                days=args.days, rows=args.rows,
            )
            new_rows = [b.to_dict() for b in bids]
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if args.append and out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    # 공고번호 기준 중복 제거(기존 우선)
    by_no = {r["공고번호"]: r for r in existing}
    for r in new_rows:
        by_no.setdefault(r["공고번호"], r)
    merged = list(by_no.values())

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    if args.scope:
        label = f"[scope={args.scope}]"
    else:
        kw = f" / '{args.keyword}'" if args.keyword else ""
        label = f"[{args.division}]{kw}"
    print(f"{label} 신규 {len(new_rows)}건 → 누적 {len(merged)}건 저장: {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
