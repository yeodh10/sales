"""
Phase 6: Streamlit 데모 대시보드 (무료 경로 + API 모드 겸용).

실행:
    venv\\Scripts\\streamlit run app.py

- 📁 저장된 브리핑 (무료): fetch_bids.py로 수집 후 Claude Code가 만든
  data/briefing_latest.json(없으면 sample_briefing.json)을 읽어 표시. API 키 불필요.
- ⚡ 지금 분석 (API 키): 나라장터에서 바로 받아 Claude API로 분류·매칭·토킹포인트.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

import config
import narajangteo
import pipeline

DATA_DIR = Path(__file__).parent / "data"
BRIEFING_LATEST = DATA_DIR / "briefing_latest.json"
BRIEFING_SAMPLE = DATA_DIR / "sample_briefing.json"

GRADE_BADGE = {"영업대상": "⭐", "보안주제/매칭약함": "🔸", "제외": "❌"}
GRADE_ORDER = {"영업대상": 0, "보안주제/매칭약함": 1, "제외": 2}

st.set_page_config(page_title="보안 영업 코파일럿", page_icon="🔒", layout="wide")
st.title("🔒 공공기관 보안 영업 코파일럿")
st.caption(
    "나라장터 입찰공고 → 보안 분류 → 제품 매칭 → 영업 토킹포인트. "
    "AI 결과는 사람이 최종 검수하는 보조 도구입니다."
)


def _load_saved() -> tuple[dict | None, str]:
    for p in (BRIEFING_LATEST, BRIEFING_SAMPLE):
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f), p.name
    return None, ""


def _items_to_df(items: list[dict]) -> pd.DataFrame:
    rows = []
    for it in items:
        recs = "; ".join(p.get("제품명", "") for p in it.get("추천제품", []))
        rows.append(
            {
                "등급": GRADE_BADGE.get(it.get("등급", ""), "") + " " + it.get("등급", ""),
                "카테고리": it.get("카테고리", ""),
                "공고명": it.get("공고명", ""),
                "발주기관": it.get("발주기관", ""),
                "업무": it.get("업무구분", ""),
                "추천제품": recs,
                "공고번호": it.get("공고번호", ""),
            }
        )
    return pd.DataFrame(rows)


def render_briefing(items: list[dict], meta: dict | None = None) -> None:
    items = sorted(items, key=lambda x: GRADE_ORDER.get(x.get("등급", ""), 9))
    targets = [i for i in items if i.get("등급") == "영업대상"]
    security = [i for i in items if i.get("보안여부")]

    if meta:
        st.caption(
            f"출처 {meta.get('출처','')} · 생성 {meta.get('생성일','')} · "
            f"분석 {meta.get('분석','')}"
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 공고", len(items))
    c2.metric("보안 관련", len(security))
    c3.metric("⭐ 영업 우선대상", len(targets))

    df = _items_to_df(items)
    st.subheader("브리핑 결과")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "CSV 다운로드",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="보안공고_브리핑.csv",
        mime="text/csv",
    )

    st.subheader("⭐ 영업 우선대상 — 토킹포인트")
    if not targets:
        st.write("매칭된 영업 대상이 없습니다.")
    for it in targets:
        with st.expander(f"⭐ [{it.get('카테고리','')}] {it.get('공고명','')}"):
            st.caption(f"{it.get('발주기관','')} · {it.get('업무구분','')} · {it.get('공고번호','')}")
            for p in it.get("추천제품", []):
                st.markdown(f"- **{p.get('제품명','')}** — {p.get('매칭이유','')}")
            if it.get("고객요구"):
                st.markdown(f"**고객요구** · {it['고객요구']}")
            if it.get("우리강점"):
                st.markdown(f"**우리강점** · {it['우리강점']}")
            if it.get("차별점"):
                st.markdown(f"**차별점** · {it['차별점']}")
            if it.get("토킹포인트"):
                st.info(it["토킹포인트"])
            if it.get("공고url"):
                st.markdown(f"[나라장터 공고 바로가기]({it['공고url']})")


def _pipeline_to_items(out: dict, bids: list[dict]) -> list[dict]:
    by_no = {b.get("공고번호"): b for b in bids}
    items = []
    for r in out["briefing"]:
        src = by_no.get(r["공고번호"], {})
        if not r["보안여부"]:
            grade = "제외"
        elif r.get("추천제품"):
            grade = "영업대상"
        else:
            grade = "보안주제/매칭약함"
        items.append(
            {
                "공고번호": r["공고번호"],
                "공고명": r["공고명"],
                "발주기관": src.get("공고기관", ""),
                "업무구분": src.get("업무구분", ""),
                "공고url": src.get("공고url", ""),
                "보안여부": r["보안여부"],
                "등급": grade,
                "카테고리": r["카테고리"],
                "판단근거": r.get("판단근거", ""),
                "추천제품": r.get("추천제품", []),
                "고객요구": r.get("고객요구", ""),
                "우리강점": r.get("우리강점", ""),
                "차별점": r.get("차별점", ""),
                "토킹포인트": r.get("토킹포인트", ""),
            }
        )
    return items


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.header("실행 모드")
    mode = st.radio(
        "모드 선택",
        ["📁 저장된 브리핑 (무료)", "⚡ 지금 분석 (API 키 필요)"],
        label_visibility="collapsed",
    )
    analyze = mode.startswith("⚡")

    if analyze:
        st.divider()
        use_sample = st.toggle("예시 공고로 실행", value=True)
        division = st.selectbox("업무구분", list(narajangteo.BUSINESS_DIVISIONS), index=1)
        keyword = st.text_input("키워드(공고명)", value="")
        days = st.slider("최근 며칠", 3, 30, 14)
        run = st.button("분석 실행", type="primary", use_container_width=True)
    else:
        run = False
        st.divider()
        st.caption(
            "무료 경로: `fetch_bids.py`로 공고 수집 후 Claude Code에게 "
            "'data/bids_latest.json 분류·브리핑'을 요청하면 "
            "`briefing_latest.json`이 생기고 여기 표시됩니다."
        )

    st.divider()
    anth_ok = "✅" if config.ANTHROPIC_API_KEY and "여기에" not in config.ANTHROPIC_API_KEY else "❌"
    data_ok = "✅" if config.DATA_GO_KR_SERVICE_KEY and "여기에" not in config.DATA_GO_KR_SERVICE_KEY else "❌"
    st.caption(f"Anthropic 키 {anth_ok} · 나라장터 키 {data_ok}")


# ── 본문 ──────────────────────────────────────────────────
if not analyze:
    data, src = _load_saved()
    if data is None:
        st.info(
            "저장된 브리핑이 없습니다. 터미널에서 `fetch_bids.py`로 공고를 모은 뒤 "
            "Claude Code에게 브리핑을 요청하세요."
        )
    else:
        st.success(f"`{src}` 표시 중")
        render_briefing(data.get("items", []), data)
else:
    if run:
        try:
            bids = pipeline.get_bids(
                sample=use_sample, division=division,
                keyword=keyword or None, days=days,
            )
        except RuntimeError as e:
            st.error(str(e)); st.stop()
        if not bids:
            st.warning("조회된 공고가 없습니다."); st.stop()
        with st.spinner(f"공고 {len(bids)}건 분류·매칭·토킹포인트 처리 중..."):
            try:
                out = pipeline.run_pipeline(bids)
            except RuntimeError as e:
                st.error(str(e)); st.stop()
        render_briefing(_pipeline_to_items(out, bids))
    else:
        st.info("왼쪽에서 조건을 정하고 **분석 실행**을 눌러주세요. (Anthropic 키 필요)")
