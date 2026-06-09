"""
Phase 6: Streamlit 데모 대시보드 (무료 경로 + API 모드 겸용).

실행:
    venv\\Scripts\\streamlit run app.py

- 📁 저장된 브리핑 (무료): fetch_bids.py로 수집 후 Claude Code가 만든
  data/briefing_latest.json(없으면 sample_briefing.json)을 읽어 표시. API 키 불필요.
- ⚡ 지금 분석 (API 키): 나라장터에서 바로 받아 Claude API로 분류·매칭·토킹포인트.
"""

from __future__ import annotations

import html
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
GRADE_COLOR = {"영업대상": "#3DDC97", "보안주제/매칭약함": "#F5B14C", "제외": "#6B7280"}

st.set_page_config(page_title="보안 영업 코파일럿", page_icon="🔒", layout="wide")

# ── 커스텀 스타일 ─────────────────────────────────────────
st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1200px;}
      #MainMenu, footer {visibility: hidden;}
      .hero {
        background: linear-gradient(120deg, #11352b 0%, #0E1117 60%);
        border: 1px solid #20303a; border-radius: 16px;
        padding: 22px 26px; margin-bottom: 18px;
      }
      .hero h1 {margin: 0; font-size: 1.7rem; letter-spacing: -.5px;}
      .hero p {margin: 6px 0 0; color: #9AA7B8; font-size: .92rem;}
      .kpi {
        background: #161B26; border: 1px solid #232A38; border-radius: 14px;
        padding: 16px 18px; text-align: left;
      }
      .kpi .v {font-size: 2rem; font-weight: 700; line-height: 1.1;}
      .kpi .l {color: #9AA7B8; font-size: .82rem; margin-top: 2px;}
      .deal {
        background: #141925; border: 1px solid #232A38; border-left: 4px solid #3DDC97;
        border-radius: 12px; padding: 16px 18px; margin-bottom: 12px;
      }
      .deal .title {font-size: 1.06rem; font-weight: 700; margin-bottom: 4px;}
      .deal .meta {color: #8B97A8; font-size: .82rem; margin-bottom: 10px;}
      .pill {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: .74rem; font-weight: 600; margin-right: 6px;
        background: #16302a; color: #3DDC97; border: 1px solid #224a3f;
      }
      .prod {background: #10151f; border-radius: 8px; padding: 8px 12px; margin: 4px 0; font-size: .9rem;}
      .prod b {color: #3DDC97;}
      .tp {font-size: .9rem; color: #C7D0DC; margin: 3px 0;}
      .tp b {color: #E6EAF1;}
      .quote {
        background: #11251f; border: 1px solid #1f4338; border-radius: 8px;
        padding: 10px 14px; margin-top: 10px; font-size: .92rem; color: #D6F5E9;
      }
    </style>
    """,
    unsafe_allow_html=True,
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
            }
        )
    return pd.DataFrame(rows)


def _kpi(col, value, label, color="#E6EAF1"):
    col.markdown(
        f'<div class="kpi"><div class="v" style="color:{color}">{value}</div>'
        f'<div class="l">{label}</div></div>',
        unsafe_allow_html=True,
    )


def _deal_card(it: dict) -> None:
    e = html.escape
    prods = "".join(
        f'<div class="prod">✓ <b>{e(p.get("제품명",""))}</b> — {e(p.get("매칭이유",""))}</div>'
        for p in it.get("추천제품", [])
    )
    tp = ""
    for k in ("고객요구", "우리강점", "차별점"):
        if it.get(k):
            tp += f'<div class="tp"><b>{k}</b> · {e(it[k])}</div>'
    quote = f'<div class="quote">💬 {e(it["토킹포인트"])}</div>' if it.get("토킹포인트") else ""
    st.markdown(
        f'<div class="deal">'
        f'<div class="title"><span class="pill">{e(it.get("카테고리",""))}</span>{e(it.get("공고명",""))}</div>'
        f'<div class="meta">{e(it.get("발주기관",""))} · {e(it.get("업무구분",""))} · {e(it.get("공고번호",""))}</div>'
        f"{prods}{tp}{quote}</div>",
        unsafe_allow_html=True,
    )


def render_briefing(items: list[dict], meta: dict | None = None) -> None:
    items = sorted(items, key=lambda x: GRADE_ORDER.get(x.get("등급", ""), 9))
    targets = [i for i in items if i.get("등급") == "영업대상"]
    security = [i for i in items if i.get("보안여부")]

    src_line = ""
    if meta:
        src_line = (
            f'출처 {e_meta(meta,"출처")} · 생성 {e_meta(meta,"생성일")} · 분석 {e_meta(meta,"분석")}'
        )
    st.markdown(
        f'<div class="hero"><h1>🔒 공공기관 보안 영업 코파일럿</h1>'
        f'<p>나라장터 입찰공고 → 보안 분류 → 제품 매칭 → 영업 토킹포인트. '
        f'AI 1차 분석이며 최종 판단은 담당자가 검수합니다.<br><span style="color:#6B7280">{src_line}</span></p></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    _kpi(c1, len(items), "전체 공고")
    _kpi(c2, len(security), "보안 관련", "#7FC8FF")
    _kpi(c3, len(targets), "⭐ 영업 우선대상", "#3DDC97")

    st.markdown("### ⭐ 영업 우선대상")
    if not targets:
        st.caption("매칭된 영업 대상이 없습니다.")
    for it in targets:
        _deal_card(it)

    st.markdown("### 📋 전체 브리핑")
    df = _items_to_df(items)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "공고명": st.column_config.TextColumn(width="large"),
            "등급": st.column_config.TextColumn(width="small"),
        },
    )
    st.download_button(
        "⬇️ CSV 다운로드",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="보안공고_브리핑.csv",
        mime="text/csv",
    )


def e_meta(meta: dict, key: str) -> str:
    return html.escape(str(meta.get(key, "")))


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
                "공고번호": r["공고번호"], "공고명": r["공고명"],
                "발주기관": src.get("공고기관", ""), "업무구분": src.get("업무구분", ""),
                "공고url": src.get("공고url", ""), "보안여부": r["보안여부"],
                "등급": grade, "카테고리": r["카테고리"], "판단근거": r.get("판단근거", ""),
                "추천제품": r.get("추천제품", []), "고객요구": r.get("고객요구", ""),
                "우리강점": r.get("우리강점", ""), "차별점": r.get("차별점", ""),
                "토킹포인트": r.get("토킹포인트", ""),
            }
        )
    return items


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 실행 모드")
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
    anth_ok = "🟢" if config.ANTHROPIC_API_KEY and "여기에" not in config.ANTHROPIC_API_KEY else "🔴"
    data_ok = "🟢" if config.DATA_GO_KR_SERVICE_KEY and "여기에" not in config.DATA_GO_KR_SERVICE_KEY else "🔴"
    st.caption(f"{anth_ok} Anthropic 키  ·  {data_ok} 나라장터 키")


# ── 본문 ──────────────────────────────────────────────────
if not analyze:
    data, src = _load_saved()
    if data is None:
        st.markdown(
            '<div class="hero"><h1>🔒 공공기관 보안 영업 코파일럿</h1>'
            '<p>저장된 브리핑이 없습니다. 터미널에서 <code>fetch_bids.py</code>로 공고를 모은 뒤 '
            'Claude Code에게 브리핑을 요청하세요.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        render_briefing(data.get("items", []), data)
else:
    if run:
        try:
            bids = pipeline.get_bids(
                sample=use_sample, division=division,
                keyword=keyword or None, days=days,
            )
        except RuntimeError as ex:
            st.error(str(ex)); st.stop()
        if not bids:
            st.warning("조회된 공고가 없습니다."); st.stop()
        with st.spinner(f"공고 {len(bids)}건 분류·매칭·토킹포인트 처리 중..."):
            try:
                out = pipeline.run_pipeline(bids)
            except RuntimeError as ex:
                st.error(str(ex)); st.stop()
        render_briefing(_pipeline_to_items(out, bids))
    else:
        st.markdown(
            '<div class="hero"><h1>🔒 공공기관 보안 영업 코파일럿</h1>'
            '<p>왼쪽에서 조건을 정하고 <b>분석 실행</b>을 눌러주세요. (Anthropic 키 필요)</p></div>',
            unsafe_allow_html=True,
        )
