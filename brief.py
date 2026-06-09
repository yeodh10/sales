"""
통합 브리핑 CLI (Phase 3 매칭 + Phase 5 토킹포인트).
공고를 가져와 분류 → 매칭 → 토킹포인트까지 한 번에 출력한다.

실행 예시:
    venv\\Scripts\\python.exe brief.py --sample
    venv\\Scripts\\python.exe brief.py --division 용역 --keyword 정보보호 --days 30
"""

import argparse
import sys

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)
import narajangteo
import pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="보안 공고 브리핑 (Phase 3+5)")
    parser.add_argument("--sample", action="store_true", help="예시 공고로 실행")
    parser.add_argument(
        "--division", default="용역", choices=list(narajangteo.BUSINESS_DIVISIONS)
    )
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--rows", type=int, default=20)
    args = parser.parse_args()

    try:
        bids = pipeline.get_bids(
            sample=args.sample,
            division=args.division,
            keyword=args.keyword,
            days=args.days,
            rows=args.rows,
        )
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    if not bids:
        print("  (조회된 공고가 없습니다)")
        return 0

    print(f"\n공고 {len(bids)}건 — 분류 → 매칭 → 토킹포인트 처리 중...\n")

    try:
        out = pipeline.run_pipeline(bids)
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    security = out["security"]
    briefing = out["briefing"]
    sec_rows = [r for r in briefing if r["보안여부"]]

    print("=" * 64)
    print(f"보안 관련 공고 {len(security)}건 / 전체 {len(briefing)}건")
    print("=" * 64)

    for r in sec_rows:
        print(f"\n🔒 [{r['카테고리']}] {r['공고명']}  ({r['공고번호']})")
        if r["추천제품"]:
            for p in r["추천제품"]:
                print(f"   · 추천: {p['제품명']} — {p['매칭이유']}")
        else:
            print("   · 추천 제품 없음")
        if r["토킹포인트"]:
            print(f"   💬 {r['토킹포인트']}")

    nonsec = [r for r in briefing if not r["보안여부"]]
    if nonsec:
        print(f"\n— 비보안 공고 {len(nonsec)}건 (제외):")
        for r in nonsec:
            print(f"   · {r['공고명']}")

    print("\n[완료] Phase 3+5: 매칭·토킹포인트 정상 동작. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
