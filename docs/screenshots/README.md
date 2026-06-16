# 스크린샷 넣는 곳

상위 README.md의 "화면" 표가 아래 파일명을 참조합니다.
앱/포털을 띄운 뒤 `Win + Shift + S`(영역 캡처)로 찍어 같은 이름의 PNG로 이 폴더에 저장하세요.

| 파일명 | 캡처할 화면 | 띄우는 법 |
|--------|-------------|-----------|
| `01-portal-hero.png` | 포털 메인 — 히어로 + KPI 카드(수집/보안/영업대상/연관기회/D-7) | `python serve_portal.py` → `localhost:4571` 상단 |
| `02-priority-board.png` | 우선순위 공고 보드 — 필터 칩 + 상태 필터 + 검색 | 같은 화면에서 "우선순위 공고"까지 스크롤 |
| `03-bid-cards.png` | 공고 카드 — 점수 배지·등급/카테고리·추천제품·멘트 복사 | 보드 아래 카드 그리드 |
| `04-streamlit-dashboard.png` | Streamlit 대시보드 — 필터·표·CSV | `streamlit run app.py` → `localhost:8501` |

> 팁: 가로폭 1200~1600px 정도면 README에서 보기 좋습니다.
> 04번 대시보드가 안 뜨면 `venv\Scripts\streamlit run app.py`로 venv의 streamlit을 직접 실행하세요.
