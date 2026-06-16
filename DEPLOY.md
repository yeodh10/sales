# ☁️ Streamlit Community Cloud 배포 가이드

채용담당자가 설치 없이 브라우저로 바로 볼 수 있도록, 이 앱을 무료로 인터넷에 배포하는 방법입니다.

---

## 0. 준비물

- GitHub 계정 (이미 `yeodh10/sales` 저장소 보유)
- 저장소가 **공개(public)** 상태일 것 — Streamlit Community Cloud 무료 배포는 공개 저장소가 필요합니다.

> 저장소 공개 여부 확인: GitHub 저장소 페이지 → 우측 상단 이름 옆에 `Public`/`Private` 표시.
> 비공개라면: **Settings → General → 맨 아래 Danger Zone → Change repository visibility → Public**.

---

## 1. 배포 방식 선택

### (A) 예시 데모 배포 — 권장 ✅
- 키를 **넣지 않고** 그대로 배포합니다.
- 앱은 미리 만들어 둔 예시 브리핑(`data/sample_briefing.json`)을 보여줍니다.
- 누가 접속해도 **API 비용 0원, 키 노출·남용 위험 없음.**
- 채용 포트폴리오 용도로 가장 적합합니다.

### (B) 실시간 분석 데모 배포
- 실제 Claude/나라장터 키를 Streamlit Secrets에 넣어 실시간 분류까지 동작시킵니다.
- 공개 앱이므로 **접속자가 회원님의 API 크레딧을 소모**할 수 있습니다. 비용 관리에 유의하세요.
- 가능하면 Anthropic 콘솔에서 사용량 한도(spend limit)를 걸어두는 것을 권장합니다.

---

## 2. 배포 절차

1. 브라우저에서 **https://share.streamlit.io** 접속 → **Sign in with GitHub**.
2. **Create app** → **Deploy a public app from GitHub** 선택.
3. 아래와 같이 지정:
   - **Repository:** `yeodh10/sales`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (선택) **Advanced settings → Python version**을 `3.12`로 지정.
5. **Deploy** 클릭. 1~3분 후 `https://<자동생성-주소>.streamlit.app` 형태의 공개 주소가 생깁니다.

---

## 3. (B 방식만) Secrets 설정

앱 페이지 → 우측 하단/상단 **Manage app → Settings → Secrets** 에 아래 형식으로 입력 후 저장합니다.
(`.env`가 아니라 TOML 형식입니다.)

```toml
ANTHROPIC_API_KEY = "sk-ant-실제키"
ANTHROPIC_MODEL = "claude-sonnet-4-6"
DATA_GO_KR_SERVICE_KEY = "실제-나라장터-인증키"
```

> `config.py`가 `.env` → Streamlit Secrets 순으로 키를 읽도록 되어 있어, 위만 넣으면 코드 수정 없이 동작합니다.

---

## 4. 배포 후 할 일

- 생성된 공개 주소를 **README.md 상단의 `라이브 데모` 링크**와 **이력서 포트폴리오 칸**에 넣습니다.
- 앱이 잘 뜨는지, 예시 모드가 정상 표시되는지 한 번 확인합니다.

---

## 5. 자주 겪는 문제

| 증상 | 해결 |
|------|------|
| `ModuleNotFoundError` | `requirements.txt`에 해당 패키지가 있는지 확인 (이미 정리돼 있음). |
| 한글 깨짐 | 기본 `claude-sonnet-4-6` 모델·UTF-8 설정으로 처리됨. 폰트 이슈면 `.streamlit/config.toml` 확인. |
| 앱이 잠자기(sleep) | 무료 플랜은 트래픽이 없으면 절전됩니다. 접속하면 수십 초 내 다시 깨어납니다. |
| 키를 넣었는데 분석이 안 됨 | Secrets 저장 후 **Reboot app**. 키 형식(따옴표 포함)·오타 확인. |
