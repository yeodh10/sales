"""
공고 수집 키워드 그룹.

- CORE: 정보보안 '직접' 공고를 잡는 키워드(보안관제·정보보호·방화벽 등)
- ADJACENT: 보안이 따라붙는 '연관' 사업(정보시스템 구축·클라우드·네트워크·
  통합관제·전자정부 등). 직접 보안은 아니지만 보안 적합성·장비·관제를 크로스셀
  할 수 있는 기회.

scope:
  "core"     → 직접 보안만
  "adjacent" → 연관만
  "all"      → 둘 다 (기본)
"""

CORE = [
    "보안", "정보보호", "정보보안", "보안관제", "침해대응",
    "망분리", "접근통제", "방화벽", "백신", "EDR",
    "취약점", "모의해킹", "암호", "인증서", "개인정보", "ISMS",
]

ADJACENT = [
    "정보시스템", "정보화", "시스템 구축", "시스템 통합", "전산",
    "클라우드", "데이터센터", "네트워크", "서버", "통합관제",
    "CCTV", "영상정보", "스마트시티", "전자정부", "홈페이지", "디지털 전환",
]


def keywords_for(scope: str = "all") -> list[str]:
    if scope == "core":
        return list(CORE)
    if scope == "adjacent":
        return list(ADJACENT)
    # all (중복 제거, 순서 유지)
    seen, out = set(), []
    for kw in CORE + ADJACENT:
        if kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out
