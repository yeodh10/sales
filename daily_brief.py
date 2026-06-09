"""
Phase 7-B: 매일 아침 신규 보안 공고 브리핑.

최근 보안 키워드 공고를 수집해, 이전에 본 적 없는 '신규' 공고만 골라
날짜별 마크다운 파일로 저장하고 콘솔에 요약한다.
data/seen_bids.json 에 이미 본 공고번호를 기록해 다음 실행 때 중복을 제외한다.

매일 아침 자동 실행(Windows 작업 스케줄러) 예:
    schtasks /Create /SC DAILY /ST 08:00 /TN "보안공고_데일리브리핑" ^
      /TR "C:\\Claude\\sales\\venv\\Scripts\\python.exe C:\\Claude\\sales\\daily_brief.py"

수동 실행:
    venv\\Scripts\\python.exe daily_brief.py            # 최근 2일 신규
    venv\\Scripts\\python.exe daily_brief.py --days 3
    venv\\Scripts\\python.exe daily_brief.py --reset    # 본 기록 초기화
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config  # noqa: F401  (.env 로드 + 콘솔 인코딩)
import narajangteo

DATA_DIR = Path(__file__).parent / "data"
SEEN_PATH = DATA_DIR / "seen_bids.json"
DAILY_DIR = DATA_DIR / "daily"

# 보안 영업 후보를 폭넓게 잡는 키워드(오탐은 사람이/Claude가 2차 필터).
KEYWORDS_SERVC = ["보안", "정보보호", "관제", "망분리", "접근통제", "취약점", "개인정보", "암호"]
KEYWORDS_THNG = ["보안", "방화벽", "백신", "EDR", "스토리지"]


def _load_seen() -> set[str]:
    if SEEN_PATH.exists():
        with open(SEEN_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def collect(days: int) -> list[dict]:
    """보안 키워드로 용역+물품 공고를 모아 공고번호로 중복 제거."""
    by_no: dict[str, dict] = {}
    plan = [("용역", KEYWORDS_SERVC), ("물품", KEYWORDS_THNG)]
    for division, keywords in plan:
        for kw in keywords:
            try:
                bids = narajangteo.search_bids(
                    division=division, keyword=kw, days=days, rows=100
                )
            except RuntimeError as e:
                print(f"  [경고] {division}/{kw} 조회 실패: {e}")
                continue
            for b in bids:
                by_no.setdefault(b.공고번호, b.to_dict())
    return list(by_no.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="신규 보안 공고 데일리 브리핑 (Phase 7-B)")
    parser.add_argument("--days", type=int, default=2, help="최근 며칠 (기본 2)")
    parser.add_argument("--reset", action="store_true", help="본 기록 초기화 후 종료")
    args = parser.parse_args()

    if args.reset:
        if SEEN_PATH.exists():
            SEEN_PATH.unlink()
        print("[완료] seen_bids.json 초기화")
        return 0

    seen = _load_seen()
    all_bids = collect(args.days)
    new_bids = [b for b in all_bids if b["공고번호"] not in seen]

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n[{today}] 최근 {args.days}일 보안 공고 {len(all_bids)}건 중 신규 {len(new_bids)}건")

    if new_bids:
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        out = DAILY_DIR / f"보안공고_{today}.md"
        lines = [f"# 신규 보안 공고 브리핑 — {today}", "",
                 f"> 최근 {args.days}일 · 신규 {len(new_bids)}건 · 출처 나라장터",
                 "> ⚠️ 키워드 1차 수집입니다. 보안 영업 적합성은 Claude Code/담당자 2차 검토.", ""]
        for b in new_bids:
            lines.append(f"- **{b['공고명']}**")
            lines.append(f"  - {b['공고기관']} · {b['업무구분']} · 마감 {b['마감일시'] or '미정'} · `{b['공고번호']}`")
            if b.get("공고url"):
                lines.append(f"  - {b['공고url']}")
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"  저장: {out}")
        for b in new_bids[:15]:
            print(f"   · [{b['업무구분']}] {b['공고명']} ({b['공고기관']})")
        if len(new_bids) > 15:
            print(f"   · ... 외 {len(new_bids)-15}건")

        # 본 목록 갱신
        seen.update(b["공고번호"] for b in all_bids)
        _save_seen(seen)
    else:
        print("  신규 공고가 없습니다.")
        seen.update(b["공고번호"] for b in all_bids)
        _save_seen(seen)

    print("\n[완료] Phase 7-B: 데일리 브리핑. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
