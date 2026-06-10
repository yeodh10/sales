"""
영업 우선순위 스코어링 (Phase A) — AI 없이 결정론적 계산.

점수 = 적합도(등급·매칭 제품 수) + 카테고리 전략가중 + 마감 임박도.
'추려주는 보조 도구'를 한 단계 더: 보안 공고를 '지금 덤빌 순서'로 정렬한다.

설계 의도:
- 적합도: 제품과 잘 맞을수록 ↑ (영업대상 > 매칭약함 > 제외)
- 카테고리: 수주 가치가 큰 영역(보안관제·컨설팅·IAM)에 가중
- 마감 임박도: 준비 가능한 임박(D-4~21)이 최적, 이미 지난 공고는 강한 감점
"""

from __future__ import annotations

from datetime import datetime

# 카테고리별 전략 가중치(수주 규모·반복매출 관점). 미지정은 10.
CATEGORY_WEIGHT = {
    "보안관제(SOC)": 20,
    "정보보호 컨설팅": 18,
    "접근통제(IAM)": 16,
    "망분리": 15,
    "방화벽": 15,
    "네트워크 보안": 15,
    "백신/EDR": 13,
    "보안 유지관리": 14,
    "OT 보안": 8,
    "보안 교육": 6,
    "보안 거버넌스": 9,
    "인프라": 6,
    "보안 행사": 4,
}
GRADE_FIT = {"영업대상": 35, "보안주제/매칭약함": 12, "제외": 0}

_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def days_left(deadline: str, today: datetime) -> int | None:
    dt = _parse_dt(deadline)
    if dt is None:
        return None
    return (dt.date() - today.date()).days


def _deadline_score(dleft: int | None) -> tuple[int, str]:
    if dleft is None:
        return 12, "마감 미정"
    if dleft < 0:
        return 0, f"마감 지남(D+{-dleft})"
    if dleft <= 3:
        return 18, f"D-{dleft} 임박"
    if dleft <= 21:
        return 30, f"D-{dleft} 최적"
    if dleft <= 45:
        return 20, f"D-{dleft}"
    return 12, f"D-{dleft} 여유"


def _tier(score: int, expired: bool) -> str:
    if expired:
        return "마감 지남"
    if score >= 72:
        return "🔥 핫"
    if score >= 58:
        return "주목"
    if score >= 40:
        return "검토"
    return "후순위"


def score_item(item: dict, today: datetime | None = None) -> dict:
    """공고 한 건의 우선순위 점수와 근거를 계산한다."""
    today = today or datetime.now()
    grade = item.get("등급", "")

    # 제외 공고는 점수 0.
    if grade == "제외" or not item.get("보안여부", False):
        return {"점수": 0, "등급표시": "제외", "Dday": None,
                "마감표시": "", "내역": {"적합도": 0, "카테고리": 0, "마감": 0}}

    fit = min(GRADE_FIT.get(grade, 0) + min(len(item.get("추천제품", [])), 2) * 7, 49)
    cat = CATEGORY_WEIGHT.get(item.get("카테고리", ""), 10)
    dleft = days_left(item.get("마감일시", ""), today)
    dsc, dlabel = _deadline_score(dleft)

    total = fit + cat + dsc
    expired = dleft is not None and dleft < 0
    if expired:
        total = min(total, 30)  # 좋은 적합도라도 마감 지나면 강등
    total = max(0, min(100, total))

    return {
        "점수": total,
        "등급표시": _tier(total, expired),
        "Dday": dleft,
        "마감표시": dlabel,
        "내역": {"적합도": fit, "카테고리": cat, "마감": dsc},
    }


def annotate(items: list[dict], today: datetime | None = None) -> list[dict]:
    """각 item에 _score(스코어 dict)를 붙여 반환(원본 변형)."""
    today = today or datetime.now()
    for it in items:
        it["_score"] = score_item(it, today)
    return items


def rank_targets(items: list[dict]) -> list[dict]:
    """영업대상만 점수 내림차순 정렬."""
    targets = [i for i in items if i.get("등급") == "영업대상"]
    return sorted(targets, key=lambda x: x.get("_score", {}).get("점수", 0), reverse=True)
