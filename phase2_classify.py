"""
Phase 2 검증 스크립트.
공고를 가져와(실데이터 또는 예시) 보안 관련 여부로 분류해 출력한다.

실행 예시:
    # 예시 공고로 (나라장터 키 불필요, Anthropic 키만 필요)
    venv\\Scripts\\python.exe phase2_classify.py --sample

    # 실데이터로 (나라장터 + Anthropic 키 둘 다 필요)
    venv\\Scripts\\python.exe phase2_classify.py --division 용역 --days 14
"""

import argparse
import json
import sys
from pathlib import Path

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)
import classifier
import narajangteo

SAMPLE_PATH = Path(__file__).parent / "data" / "sample_bids.json"


def _load_bids(args) -> list:
    if args.sample:
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)
    bids = narajangteo.search_bids(
        division=args.division,
        keyword=args.keyword,
        days=args.days,
        rows=args.rows,
    )
    return [b.to_dict() for b in bids]


def main() -> int:
    parser = argparse.ArgumentParser(description="보안 공고 분류 (Phase 2)")
    parser.add_argument("--sample", action="store_true", help="예시 공고로 실행")
    parser.add_argument(
        "--division", default="용역", choices=list(narajangteo.BUSINESS_DIVISIONS)
    )
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--rows", type=int, default=20)
    args = parser.parse_args()

    try:
        bids = _load_bids(args)
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    if not bids:
        print("  (조회된 공고가 없습니다)")
        return 0

    print(f"\n공고 {len(bids)}건 분류 중...\n")

    try:
        results = classifier.classify_bids(bids)
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    security = [r for r in results if r["보안여부"]]

    for r in results:
        mark = "🔒" if r["보안여부"] else "  "
        cat = r["카테고리"]
        print(f"{mark} [{cat}] {r['공고명']}")
        print(f"     └ {r['판단근거']}")

    print(f"\n전체 {len(results)}건 중 보안 관련 {len(security)}건")
    print("[완료] Phase 2: 보안 분류 정상 동작. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
