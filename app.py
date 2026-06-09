"""
Phase 6: Streamlit 데모 대시보드.

실행:
    venv\\Scripts\\streamlit run app.py

기능: 기간/업무구분/키워드 필터 → 분류·매칭·토킹포인트 실행 →
결과 표 + 토킹포인트 보기 + CSV 다운로드.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import config
import narajangteo
import pipeline

st.set_page_config(page_title="보안 영업 코파일럿", page_icon="🔒", layout="wide")

st.title("🔒 공공기관 보안 영업 코파일럿")
st.caption(
    "나라장터 입찰공고 → 보안 분류 → 제품 매칭 → 영업 토킹포인트. "
    "AI 결과는 사람이 최종 검수하는 보조 도구입니다."
)

with st.sidebar:
    st.header("검색 조건")
    use_sample = st.toggle(
        "예시 공고로 실행", value=True,
        help="끄면 나라장터 실데이터를 조회합니다(인증키 필요).",
    )
    division = st.selectbox("업무구분", list(narajangteo.BUSINESS_DIVISIONS), index=1)
    keyword = st.text_input("키워드(공고명)", value="")
    days = st.slider("최근 며칠", min_value=3, max_value=60, value=14)
    run = st.button("브리핑 생성", type="primary", use_container_width=True)

    st.divider()
    # 키 상태 표시
    anth_ok = "✅" if config.ANTHROPIC_API_KEY and "여기에" not in config.ANTHROPIC_API_KEY else "❌"
    data_ok = "✅" if config.DATA_GO_KR_SERVICE_KEY and "여기에" not in config.DATA_GO_KR_SERVICE_KEY else "❌"
    st.caption(f"Anthropic 키 {anth_ok} · 나라장터 키 {data_ok}")


def _flatten(briefing: list[dict]) -> pd.DataFrame:
    rows = []
    for r in briefing:
        recs = "; ".join(
            f"{p['제품명']}({p['매칭이유']})" for p in r.get("추천제품", [])
        )
        rows.append(
            {
                "보안": "🔒" if r["보안여부"] else "",
                "카테고리": r["카테고리"],
                "공고명": r["공고명"],
                "공고번호": r["공고번호"],
                "추천제품": recs,
                "토킹포인트": r.get("토킹포인트", ""),
            }
        )
    return pd.DataFrame(rows)


if run:
    try:
        bids = pipeline.get_bids(
            sample=use_sample, division=division,
            keyword=keyword or None, days=days,
        )
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    if not bids:
        st.warning("조회된 공고가 없습니다.")
        st.stop()

    with st.spinner(f"공고 {len(bids)}건 분류·매칭·토킹포인트 처리 중..."):
        try:
            out = pipeline.run_pipeline(bids)
        except RuntimeError as e:
            st.error(str(e))
            st.stop()

    df = _flatten(out["briefing"])
    sec_count = len(out["security"])

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 공고", len(out["briefing"]))
    c2.metric("보안 관련", sec_count)
    c3.metric("제품 매칭", len(out["matched"]))

    st.subheader("브리핑 결과")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "CSV 다운로드",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="보안공고_브리핑.csv",
        mime="text/csv",
    )

    st.subheader("영업 토킹포인트")
    for r in out["briefing"]:
        if not r["보안여부"] or not r.get("토킹포인트"):
            continue
        with st.expander(f"🔒 [{r['카테고리']}] {r['공고명']}"):
            for p in r.get("추천제품", []):
                st.markdown(f"- **{p['제품명']}** — {p['매칭이유']}")
            st.markdown(f"**고객요구** · {r.get('고객요구','')}")
            st.markdown(f"**우리강점** · {r.get('우리강점','')}")
            st.markdown(f"**차별점** · {r.get('차별점','')}")
            st.info(r["토킹포인트"])
else:
    st.info("왼쪽에서 조건을 정하고 **브리핑 생성**을 눌러주세요. (예시 공고로 키 없이 UI 흐름만 볼 수도 있지만, 분류·매칭에는 Anthropic 키가 필요합니다.)")
