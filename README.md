# 공공기관 보안 영업 코파일럿 에이전트

나라장터(조달청) 입찰 공고를 자동 수집 → 보안 관련 공고만 분류 → 우리 제품과 매칭 → 영업 토킹포인트 초안까지 만들어주는 AI 에이전트.

전체 기획은 [security-sales-agent-plan.md](security-sales-agent-plan.md) 참고.

## 진행 현황

- [x] **Phase 0** — 셋업 (가상환경, Anthropic SDK, `.env`, Claude 호출 테스트)
- [~] **Phase 1** — 나라장터 API 연결 (코드 완료, 인증키 받으면 실호출 검증)
- [~] **Phase 2** — 보안 관련 분류 (코드 완료, Anthropic 키로 `--sample` 검증 가능)
- [~] **Phase 3** — 제품 매칭 ([matcher.py](matcher.py), 예시 카탈로그 `catalog.json`)
- [~] **Phase 4** — 에이전트화 tool use ([agent.py](agent.py), `search_bids` 도구)
- [~] **Phase 5** — 영업 토킹포인트 생성 ([generator.py](generator.py))
- [~] **Phase 6** — Streamlit 대시보드 ([app.py](app.py), 무료/API 2모드)
- [~] **Phase 7-A** — RFP PDF 요구사항 추출·제품 대응표 ([rfp_extract.py](rfp_extract.py))
- [~] **Phase 7-B** — 매일 아침 신규 보안공고 브리핑 ([daily_brief.py](daily_brief.py))

> `[~]` = 코드 완료. 실제 결과 확인에는 키가 필요합니다. 분류·매칭·토킹포인트·에이전트·UI는 **Anthropic 키만 있으면 `--sample`로 전부 검증** 가능하고, 나라장터 실데이터 수집에는 `DATA_GO_KR_SERVICE_KEY`가 추가로 필요합니다.

## 두 가지 실행 모드

AI 단계(분류·매칭·영업멘트)를 돌리는 방법이 둘 있습니다.

**(A) API 모드** — `.env`의 `ANTHROPIC_API_KEY`로 파이썬이 Claude API를 직접 호출.
`classifier.py`·`matcher.py`·`generator.py`·`agent.py`·`app.py`가 이 경로다. 독립 실행 앱.
console.anthropic.com 선불 크레딧 필요(실비용은 1회 수십 원 수준).

**(B) Claude Code 모드(무료)** — Anthropic API 키 없이, Max 구독으로 동작.
파이썬은 **수집만** 담당하고(`fetch_bids.py` → `data/bids_latest.json`),
분류·매칭·영업멘트는 Claude Code가 그 JSON과 `catalog.json`을 읽어 직접 작성한다.

```powershell
# (B) 무료 경로: 보안 공고 수집 (나라장터 키만 필요)
venv\Scripts\python.exe fetch_bids.py --division 용역 --keyword 보안 --days 30
venv\Scripts\python.exe fetch_bids.py --division 물품 --keyword 백신 --append
# → 이후 Claude Code에게 "data/bids_latest.json 분류·매칭·브리핑 해줘" 요청
# → 결과 예시: data/briefing_latest.md / .csv
```

> 나라장터 조회는 1회 기간이 약 31일로 제한되어, 코드가 30일 이하 구간으로 자동 분할 호출합니다.

## 셋업 방법

### 1. 의존성 설치

가상환경(`venv`)은 이미 생성돼 있습니다. 새로 만들려면:

```powershell
# Python 3.12 기준
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env.example`을 복사해 `.env`를 만들고 키를 채웁니다. (`.env`는 git에 커밋되지 않습니다)

```powershell
Copy-Item .env.example .env
```

| 변수 | 설명 | 발급처 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 키 | https://console.anthropic.com |
| `ANTHROPIC_MODEL` | 사용할 모델 (기본 `claude-sonnet-4-6`) | - |
| `DATA_GO_KR_SERVICE_KEY` | 나라장터 입찰공고 인증키 (Phase 1부터) | https://www.data.go.kr/data/15129394/openapi.do |

### 3. Phase 0 검증

```powershell
venv\Scripts\python.exe hello_claude.py
```

Claude의 응답과 함께 `[완료] Phase 0 셋업이 정상 동작합니다. ✅` 가 출력되면 성공입니다.

### 4. Phase 1 검증 (나라장터 인증키 필요)

`.env`의 `DATA_GO_KR_SERVICE_KEY`를 채운 뒤:

```powershell
venv\Scripts\python.exe phase1_fetch.py --division 용역 --keyword 정보보호 --days 30
```

최근 공고 목록이 표로 뜨고 `[완료] Phase 1 ... ✅` 가 출력되면 성공입니다.
업무구분(`--division`)은 물품/용역/공사/외자 중 선택합니다.

### 5. Phase 2 검증 (보안 분류 — Anthropic 키만 있으면 가능)

나라장터 인증키 없이 예시 공고로 먼저 확인할 수 있습니다:

```powershell
venv\Scripts\python.exe phase2_classify.py --sample
```

예시 공고 6건이 보안/비보안으로 갈리고 카테고리·근거가 표시됩니다.
실데이터로 돌리려면 `--sample` 대신 `--division 용역 --days 14` 등을 지정합니다
(나라장터 + Anthropic 키 둘 다 필요).

### 6. Phase 3+5 통합 브리핑 (분류 → 매칭 → 토킹포인트)

```powershell
venv\Scripts\python.exe brief.py --sample
```

보안 공고별 추천 제품과 영업 토킹포인트까지 한 번에 출력됩니다.

### 7. Phase 4 에이전트 (자연어 → 도구 호출)

```powershell
venv\Scripts\python.exe agent.py --sample "이번 주 보안 공고 정리해줘"
```

Claude가 스스로 `search_bids` 도구를 호출한 뒤 분류·매칭·토킹포인트를 수행합니다.

### 8. Phase 6 Streamlit 대시보드

```powershell
venv\Scripts\streamlit run app.py
```

브라우저에서 기간·업무구분·키워드 필터, 결과 표, 토킹포인트, CSV 다운로드를 사용합니다.
예시 공고 토글이 기본 켜져 있어 나라장터 키 없이도 흐름을 볼 수 있습니다(분류·매칭에는 Anthropic 키 필요).

### 9. Phase 7-A — RFP PDF 요구사항 추출

```powershell
venv\Scripts\python.exe rfp_extract.py "C:\경로\제안요청서.pdf"
# → data/rfp_extracted.txt 생성 후, Claude Code에게
#   "rfp_extracted.txt 요구사항 뽑고 catalog.json으로 대응표 만들어줘" 요청 (무료)
# API 키가 있으면:  ... rfp_extract.py rfp.pdf --api  (대응표까지 자동 생성)
```

### 10. Phase 7-B — 매일 아침 신규 보안공고 브리핑

```powershell
venv\Scripts\python.exe daily_brief.py --days 2
# → data/daily/보안공고_YYYY-MM-DD.md 에 '신규' 공고만 저장 (seen_bids.json으로 중복 제외)
```

**매일 자동 실행(Windows 작업 스케줄러):**

```powershell
schtasks /Create /SC DAILY /ST 08:00 /TN "보안공고_데일리브리핑" `
  /TR "C:\Claude\sales\venv\Scripts\python.exe C:\Claude\sales\daily_brief.py"
```

## 모듈 구조

| 파일 | 역할 |
|------|------|
| `config.py` | `.env` 로더 · 키 가드 · 콘솔 UTF-8 |
| `narajangteo.py` | 나라장터 입찰공고 수집·파싱 (Phase 1) |
| `classifier.py` | 보안 여부·카테고리 분류 (Phase 2) |
| `matcher.py` | 제품 카탈로그 매칭 (Phase 3) |
| `generator.py` | 영업 토킹포인트 생성 (Phase 5) |
| `pipeline.py` | 분류→매칭→토킹포인트 오케스트레이션 |
| `agent.py` | tool use 에이전트 (Phase 4) |
| `app.py` | Streamlit 대시보드 (Phase 6, 무료/API 2모드) |
| `fetch_bids.py` | 공고만 수집해 JSON 저장 (무료 경로 입력) |
| `rfp_extract.py` | RFP PDF 요구사항 추출·대응표 (Phase 7-A) |
| `daily_brief.py` | 매일 아침 신규 보안공고 브리핑 (Phase 7-B) |
| `brief.py` / `phase1_fetch.py` / `phase2_classify.py` | CLI 실행 스크립트 |

## 주의사항

- API 키·인증키는 반드시 `.env`로 관리하고 git에 커밋하지 않습니다.
- 입찰 판단·참여 결정은 항상 사람이 최종 검증합니다. 이 도구는 후보를 빠르게 추려주는 보조 수단입니다.
- 공공데이터·회사 제품정보는 모두 공개 범위 내에서만 사용합니다.
