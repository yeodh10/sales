# 보안 영업부 · 코파일럿 포털

공공조달(나라장터) 보안 입찰을 다루는 **영업부 전용 내부 대시보드**입니다.
AI 영업 코파일럿이 정리한 결과 — 우선순위 공고, 제품 매칭, 영업 토킹포인트 — 를 한 화면에서 보고,
공고별 **영업 상태·담당자·메모**까지 관리합니다. 빌드 없는 순수 정적 사이트(HTML/CSS/JS)입니다.

> 이 포털은 sales 에이전트 프로젝트의 **프런트엔드**입니다. 데이터(`data.js`)는 에이전트 산출물에서 생성됩니다.

> ⚠️ **내부용 · 예시 데이터.** 화면의 공고·제품·점수는 예시입니다(나라장터 샘플 브리핑 + 예시 카탈로그). `robots: noindex`.

## 구성

| 섹션 | 내용 |
| --- | --- |
| 현황(Hero) | 수집·보안·영업대상·연관기회·D-7 임박 KPI |
| 우선순위 공고 | **코파일럿 점수(0–100)** 순 보드 — 등급·카테고리·**상태** 필터, 검색, 점수·D-day·추천제품·토킹포인트·복사 |
| 영업 관리 | 공고별 **상태(미정·검토·제안·수주·보류)·담당자·메모** — 브라우저(localStorage) 저장 |
| 카테고리 분포 | 보안 공고 카테고리별 집계 |
| 제품 카탈로그 | 제품 6종(핵심기능·적합요구·차별점) |
| 토킹포인트 | 고객요구 → 강점 → 차별점 멘트(카테고리 필터·복사) |
| 작동 방식 | 수집 → 분류 → 매칭 → 스코어링 → 토킹포인트 |

## 우선순위 점수 (scoring)

`script.js`의 점수는 `scoring.py`를 그대로 이식했습니다(결정론적):

```
점수 = 적합도(0–49) + 카테고리 전략가중(4–20) + 마감 임박도(0–30)
```

핫(≥72) · 주목(≥58) · 검토(≥40) · 후순위. 마감 지난 공고는 30점으로 강등.

## 파일 구조

```
sales/
├─ portal_export.py   # 브리핑 JSON → portal/data.js 생성기
└─ portal/
   ├─ index.html      # 섹션 골격 (대부분 JS가 채움)
   ├─ styles.css      # 다크 모던 대시보드 디자인 시스템
   ├─ script.js       # 렌더링 + 스코어링 + 필터/정렬/검색 + 영업 관리(localStorage)
   ├─ data.js         # window.PORTAL_DATA (자동 생성, 직접 편집 금지)
   └─ README.md
```

## 데이터 생성

```powershell
# sales/ 에서 실행. data/briefing_latest.json(라이브) 우선, 없으면 data/sample_briefing.json
python portal_export.py                 # 기준일 = 오늘
python portal_export.py --ref 2026-06-15  # 기준일 지정
```

코파일럿 파이프라인이 새 브리핑을 만들면 `portal_export.py`만 다시 실행해 `data.js`를 갱신하면 화면 전체가 바뀝니다.

## 로컬에서 보기

```powershell
# sales/ 에서
python -m http.server 4571 --directory portal
# → http://localhost:4571
```

(`data.js`는 `<script>`로 직접 로드하므로 `portal/index.html`을 더블클릭해도 동작합니다.)

## 영업 관리(상태·담당자·메모)

- 각 공고 카드 하단에서 **상태·담당자·메모**를 바로 입력하며, 즉시 **브라우저 localStorage**(`salesportal.tracking.v1`)에 저장됩니다.
- **기기/브라우저 로컬**이라 팀 공유는 되지 않습니다. 공유가 필요하면 서버 저장(예: 에이전트 측 API)으로 확장하세요.
- 상단 **상태 필터**로 "검토/제안/수주" 등 진행 단계별로 추려 볼 수 있습니다.

## 기술

순수 HTML5 · CSS3 · 바닐라 JavaScript(의존성 0). Pretendard 가변폰트.
접근성: 스킵링크 · aria · `:focus-visible` · `prefers-reduced-motion`.
