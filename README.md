# 공공기관 보안 영업 코파일럿 에이전트

나라장터(조달청) 입찰 공고를 자동 수집 → 보안 관련 공고만 분류 → 우리 제품과 매칭 → 영업 토킹포인트 초안까지 만들어주는 AI 에이전트.

전체 기획은 [security-sales-agent-plan.md](security-sales-agent-plan.md) 참고.

## 진행 현황

- [x] **Phase 0** — 셋업 (가상환경, Anthropic SDK, `.env`, Claude 호출 테스트)
- [ ] Phase 1 — 나라장터 API 연결
- [ ] Phase 2 — 보안 관련 분류
- [ ] Phase 3 — 제품 매칭
- [ ] Phase 4 — 에이전트화 (tool use)
- [ ] Phase 5 — 영업 산출물 생성
- [ ] Phase 6 — Streamlit UI & 데모

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

## 주의사항

- API 키·인증키는 반드시 `.env`로 관리하고 git에 커밋하지 않습니다.
- 입찰 판단·참여 결정은 항상 사람이 최종 검증합니다. 이 도구는 후보를 빠르게 추려주는 보조 수단입니다.
- 공공데이터·회사 제품정보는 모두 공개 범위 내에서만 사용합니다.
