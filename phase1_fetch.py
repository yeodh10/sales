"""
Phase 1 검증 스크립트 (AI 없음).
나라장터 입찰공고 API를 호출해 최근 공고 목록을 받아 표로 출력한다.

실행 예시:
    venv\\Scripts\\python.exe phase1_fetch.py
    venv\\Scripts\\python.exe phase1_fetch.py --division 용역 --keyword 정보보호 --days 30
"""

import argparse
import sys

import config  # noqa: F401  (import 시 .env 로드 + 콘솔 인코딩 설정)
import narajangteo


def main() -> int:
    parser = argparse.ArgumentParser(description="나라장터 입찰공고 조회 (Phase 1)")
    parser.add_argument(
        "--division",
        default="용역",
        choices=list(narajangteo.BUSINESS_DIVISIONS),
        help="업무구분 (기본: 용역)",
    )
    parser.add_argument("--keyword", default=None, help="공고명 키워드 필터")
    parser.add_argument("--days", type=int, default=7, help="최근 며칠 (기본: 7)")
    parser.add_argument("--rows", type=int, default=20, help="가져올 행 수 (기본: 20)")
    args = parser.parse_args()

    try:
        bids = narajangteo.search_bids(
            division=args.division,
            keyword=args.keyword,
            days=args.days,
            rows=args.rows,
        )
    except RuntimeError as e:
        print(f"[오류] {e}")
        return 1

    kw = f" / 키워드 '{args.keyword}'" if args.keyword else ""
    print(f"\n[{args.division}] 최근 {args.days}일{kw} — 공고 {len(bids)}건\n")

    if not bids:
        print("  (조회된 공고가 없습니다)")
        return 0

    for i, b in enumerate(bids, 1):
        print(f"{i:>2}. {b.공고명}")
        print(f"    공고번호 {b.공고번호} | 발주 {b.공고기관} | 마감 {b.마감일시}")

    print("\n[완료] Phase 1: 나라장터 공고 수집·파싱 정상 동작. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
