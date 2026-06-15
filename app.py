"""
Phase 6: Streamlit 데모 대시보드 (무료 경로 + API 모드 겸용).

실행:
    venv\\Scripts\\streamlit run app.py
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
import scoring

DATA_DIR = Path(__file__).parent / "data"
BRIEFING_LATEST = DATA_DIR / "briefing_latest.json"
BRIEFING_SAMPLE = DATA_DIR / "sample_briefing.json"

GRADE_ORDER = {"영업대상": 0, "연관기회": 1, "보안주제/매칭약함": 2, "제외": 3}
GRADE_META = {
    "영업대상": ("⭐", "#3DDC97"),
    "연관기회": ("🔗", "#7FC8FF"),
    "보안주제/매칭약함": ("🔸", "#F5B14C"),
    "제외": ("✕", "#6B7280"),
}
CAT_COLORS = {
    "정보보호 컨설팅": "#A78BFA", "보안관제(SOC)": "#60A5FA",
    "방화벽": "#2DD4BF", "네트워크 보안": "#2DD4BF", "망분리": "#22D3EE",
    "접근통제(IAM)": "#818CF8", "백신/EDR": "#FB923C", "보안 교육": "#F472B6",
    "보안 유지관리": "#34D399", "OT 보안": "#FBBF24", "보안 거버넌스": "#A3A3A3",
    "인프라": "#94A3B8", "보안 행사": "#F472B6",
}
TIER_COLOR = {
    "🔥 핫": "#3DDC97", "주목": "#7FC8FF", "검토": "#F5B14C",
    "후순위": "#6B7280", "마감 지남": "#6B7280", "제외": "#6B7280",
}


def cat_color(cat: str) -> str:
    return CAT_COLORS.get(cat, "#3DDC97")


st.set_page_config(page_title="보안 영업 코파일럿", page_icon="🔒", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
      html, body, [class*="css"], .stMarkdown, .stApp { font-family: 'Pretendard', -apple-system, sans-serif; }
      .stApp { background: radial-gradient(1100px 520px at 18% -8%, #15271f 0%, #0B0E14 48%) fixed; }
      .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1180px; }
      #MainMenu, footer, header[data-testid="stHeader"] { display: none; }

      .hero {
        background: linear-gradient(135deg, rgba(61,220,151,.16), rgba(96,165,250,.06) 55%, rgba(15,20,28,.2));
        border: 1px solid rgba(61,220,151,.22); border-radius: 22px;
        padding: 26px 32px; margin-bottom: 20px;
        box-shadow: 0 16px 48px rgba(0,0,0,.45);
      }
      .hero .eyebrow { font-size:.74rem; font-weight:700; letter-spacing:2px;
        color:#3DDC97; text-transform:uppercase; }
      .hero h1 { margin:6px 0 4px; font-size:2.05rem; font-weight:800; letter-spacing:-1px;
        background:linear-gradient(92deg,#FFFFFF 20%,#3DDC97); -webkit-background-clip:text;
        background-clip:text; -webkit-text-fill-color:transparent; }
      .hero p { margin:6px 0 0; color:#9FB0C3; font-size:.92rem; line-height:1.55; }
      .hero .src { color:#5C6B7E; font-size:.8rem; }

      .kpi { background:linear-gradient(180deg,#141B27,#10151E); border:1px solid #222B3B;
        border-radius:18px; padding:18px 20px 16px; position:relative; overflow:hidden;
        box-shadow:0 6px 22px rgba(0,0,0,.28); }
      .kpi::before { content:''; position:absolute; inset:0 0 auto 0; height:3px; background:var(--a); }
      .kpi .ic { font-size:1.1rem; opacity:.9; }
      .kpi .v { font-size:2.3rem; font-weight:800; line-height:1.05; margin-top:6px; color:var(--a); }
      .kpi .l { color:#93A2B5; font-size:.84rem; margin-top:2px; }

      .sec-h { font-size:1.15rem; font-weight:800; margin:22px 0 12px; letter-spacing:-.3px; }

      .grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
      @media (max-width:900px){ .grid{ grid-template-columns:1fr; } }
      .deal { background:linear-gradient(180deg,#141B27,#0F141D); border:1px solid #232C3D;
        border-top:3px solid var(--c); border-radius:16px; padding:16px 18px;
        box-shadow:0 6px 22px rgba(0,0,0,.30); transition:transform .15s, border-color .15s; }
      .deal:hover { transform:translateY(-3px); border-color:#37445A; }
      .deal .top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }
      .scorebox { text-align:center; flex:0 0 auto; line-height:1; }
      .scorebox .sc { font-size:1.5rem; font-weight:800; color:var(--t); }
      .scorebox .sct { font-size:.66rem; font-weight:700; color:var(--t); white-space:nowrap; }
      .dday { display:inline-block; padding:1px 8px; border-radius:6px; font-size:.72rem;
        font-weight:700; margin-left:6px; color:var(--t);
        background:color-mix(in srgb,var(--t) 16%, transparent); }
      .deal .title { font-size:1.02rem; font-weight:700; line-height:1.4; margin:8px 0 6px; color:#EDF1F7; }
      .deal .meta { color:#7F8D9F; font-size:.8rem; margin-bottom:10px; }
      .pill { display:inline-block; padding:3px 11px; border-radius:999px; font-size:.72rem;
        font-weight:700; color:var(--c); background:color-mix(in srgb, var(--c) 16%, transparent);
        border:1px solid color-mix(in srgb, var(--c) 38%, transparent); }
      .prod { background:#0E141E; border:1px solid #1d2636; border-radius:10px;
        padding:9px 12px; margin:5px 0; font-size:.9rem; color:#CBD5E1; }
      .prod b { color:var(--c); }
      .tp { font-size:.88rem; color:#B9C4D2; margin:4px 0; }
      .tp b { color:#EDF1F7; }
      .cross { font-size:.85rem; margin-top:6px; color:#9FD2F2;
        background:rgba(127,200,255,.08); border:1px solid rgba(127,200,255,.2);
        border-radius:8px; padding:8px 11px; }
      .quote { background:linear-gradient(180deg, color-mix(in srgb,var(--c) 12%, #0E141E), #0E141E);
        border:1px solid color-mix(in srgb,var(--c) 30%, transparent); border-radius:10px;
        padding:11px 14px; margin-top:11px; font-size:.9rem; color:#E4EEF6; line-height:1.55; }

      table.bf { width:100%; border-collapse:separate; border-spacing:0 6px; font-size:.86rem; }
      table.bf th { text-align:left; color:#7C8A9C; font-weight:600; font-size:.76rem;
        padding:0 12px 4px; }
      table.bf td { background:#121823; padding:11px 12px; color:#D5DDE8; }
      table.bf tr td:first-child { border-radius:10px 0 0 10px; }
      table.bf tr td:last-child { border-radius:0 10px 10px 0; }
      .chip { display:inline-block; padding:2px 9px; border-radius:7px; font-size:.74rem;
        font-weight:700; color:var(--g); background:color-mix(in srgb,var(--g) 18%, transparent); }
      .catdot { display:inline-block; width:8px; height:8px; border-radius:50%;
        background:var(--c); margin-right:7px; vertical-align:middle; }
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


def _hero(meta: dict | None) -> None:
    src = ""
    if meta:
        src = (f'출처 {html.escape(str(meta.get("출처","")))} · '
               f'생성 {html.escape(str(meta.get("생성일","")))} · '
               f'분석 {html.escape(str(meta.get("분석","")))}')
    st.markdown(
        f'<div class="hero"><div class="eyebrow">🔒 PUBLIC SECTOR SECURITY SALES</div>'
        f'<h1>보안 영업 코파일럿</h1>'
        f'<p>나라장터 입찰공고 → 보안 분류 → 제품 매칭 → 영업 토킹포인트.<br>'
        f'AI 1차 분석이며 최종 판단은 담당자가 검수합니다. '
        f'<span class="src">{src}</span></p></div>',
        unsafe_allow_html=True,
    )


def _kpis(total: int, tgt: int, adj: int, hot: int) -> None:
    cols = st.columns(4)
    data = [("📄", total, "전체 공고", "#9FB0C3"),
            ("⭐", tgt, "영업 우선대상", "#3DDC97"),
            ("🔗", adj, "연관 기회", "#7FC8FF"),
            ("🔥", hot, "핫 리드(72점+)", "#FB7185")]
    for col, (ic, v, l, a) in zip(cols, data):
        col.markdown(
            f'<div class="kpi" style="--a:{a}"><div class="ic">{ic}</div>'
            f'<div class="v">{v}</div><div class="l">{l}</div></div>',
            unsafe_allow_html=True,
        )


def _deal_html(it: dict) -> str:
    e = html.escape
    c = cat_color(it.get("카테고리", ""))
    s = it.get("_score", {})
    t = TIER_COLOR.get(s.get("등급표시", ""), "#6B7280")
    prods = "".join(
        f'<div class="prod">✓ <b>{e(p.get("제품명",""))}</b> — {e(p.get("매칭이유",""))}</div>'
        for p in it.get("추천제품", [])
    )
    tp = "".join(
        f'<div class="tp"><b>{k}</b> · {e(it[k])}</div>'
        for k in ("고객요구", "우리강점", "차별점") if it.get(k)
    )
    quote = f'<div class="quote">💬 {e(it["토킹포인트"])}</div>' if it.get("토킹포인트") else ""
    dday = (f'<span class="dday" style="--t:{t}">{e(s.get("마감표시",""))}</span>'
            if s.get("마감표시") else "")
    score_box = (
        f'<div class="scorebox" style="--t:{t}">'
        f'<div class="sc">{s.get("점수", 0)}</div><div class="sct">{e(s.get("등급표시",""))}</div></div>'
    )
    return (
        f'<div class="deal" style="--c:{c}">'
        f'<div class="top"><span class="pill" style="--c:{c}">{e(it.get("카테고리",""))}</span>{score_box}</div>'
        f'<div class="title">{e(it.get("공고명",""))}{dday}</div>'
        f'<div class="meta">{e(it.get("발주기관",""))} · {e(it.get("업무구분",""))} · {e(it.get("공고번호",""))}</div>'
        f'{prods}{tp}{quote}</div>'
    )


def _adj_html(it: dict) -> str:
    e = html.escape
    c = cat_color(it.get("카테고리", ""))
    s = it.get("_score", {})
    t = TIER_COLOR.get(s.get("등급표시", ""), "#7FC8FF")
    dday = (f'<span class="dday" style="--t:{t}">{e(s.get("마감표시",""))}</span>'
            if s.get("마감표시") else "")
    score_box = (f'<div class="scorebox" style="--t:{t}"><div class="sc">{s.get("점수",0)}</div>'
                 f'<div class="sct">{e(s.get("등급표시",""))}</div></div>')
    cross = f'<div class="cross">🔗 크로스셀 · {e(it["크로스셀"])}</div>' if it.get("크로스셀") else ""
    return (
        f'<div class="deal" style="--c:{c}">'
        f'<div class="top"><span class="pill" style="--c:{c}">{e(it.get("카테고리",""))}</span>{score_box}</div>'
        f'<div class="title">{e(it.get("공고명",""))}{dday}</div>'
        f'<div class="meta">{e(it.get("발주기관",""))} · {e(it.get("업무구분",""))} · {e(it.get("공고번호",""))}</div>'
        f'{cross}</div>'
    )


def _table_html(items: list[dict]) -> str:
    e = html.escape
    head = ('<table class="bf"><thead><tr>'
            '<th>점수</th><th>등급</th><th>카테고리</th><th>공고명</th>'
            '<th>마감</th><th>추천제품</th>'
            '</tr></thead><tbody>')
    rows = []
    for it in items:
        ic, gc = GRADE_META.get(it.get("등급", ""), ("", "#888"))
        c = cat_color(it.get("카테고리", ""))
        s = it.get("_score", {})
        t = TIER_COLOR.get(s.get("등급표시", ""), "#6B7280")
        sc = s.get("점수", 0)
        score_cell = (f'<span class="chip" style="--g:{t}">{sc}</span>' if sc
                      else '<span style="color:#4B5563">—</span>')
        recs = ", ".join(p.get("제품명", "") for p in it.get("추천제품", [])) or "—"
        rows.append(
            f'<tr><td style="white-space:nowrap;text-align:center">{score_cell}</td>'
            f'<td style="white-space:nowrap"><span class="chip" style="--g:{gc}">{ic} {e(it.get("등급",""))}</span></td>'
            f'<td style="white-space:nowrap"><span class="catdot" style="--c:{c}"></span>{e(it.get("카테고리",""))}</td>'
            f'<td style="min-width:220px">{e(it.get("공고명",""))}</td>'
            f'<td style="color:#9AA7B8;white-space:nowrap">{e(s.get("마감표시","")) or "—"}</td>'
            f'<td style="color:#A9B6C6;white-space:nowrap">{e(recs)}</td></tr>'
        )
    return head + "".join(rows) + "</tbody></table>"


def render_briefing(items: list[dict], meta: dict | None = None) -> None:
    scoring.annotate(items)  # 각 항목에 _score 부여(우선순위 점수)
    targets = scoring.rank_targets(items)           # 영업대상: 점수 내림차순
    adj = sorted([i for i in items if i.get("등급") == "연관기회"],
                 key=lambda x: -x.get("_score", {}).get("점수", 0))
    hot = sum(1 for t in targets if t["_score"]["점수"] >= 72)
    # 표: 등급 순 → 점수 내림차순
    items = sorted(items, key=lambda x: (GRADE_ORDER.get(x.get("등급", ""), 9),
                                         -x.get("_score", {}).get("점수", 0)))

    _hero(meta)
    _kpis(len(items), len(targets), len(adj), hot)

    st.markdown('<div class="sec-h">⭐ 영업 우선대상 <span style="color:#7C8A9C;font-size:.85rem;font-weight:500">· 직접 보안, 우선순위 점수순</span></div>',
                unsafe_allow_html=True)
    if targets:
        st.markdown('<div class="grid">' + "".join(_deal_html(i) for i in targets) + "</div>",
                    unsafe_allow_html=True)
    else:
        st.caption("매칭된 영업 대상이 없습니다.")

    if adj:
        st.markdown('<div class="sec-h">🔗 연관 기회 <span style="color:#7C8A9C;font-size:.85rem;font-weight:500">· 보안이 따라붙는 IT 사업 (크로스셀)</span></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="grid">' + "".join(_adj_html(i) for i in adj) + "</div>",
                    unsafe_allow_html=True)

    st.markdown('<div class="sec-h">📋 전체 브리핑</div>', unsafe_allow_html=True)
    st.markdown(_table_html(items), unsafe_allow_html=True)

    df = pd.DataFrame([{
        "점수": it.get("_score", {}).get("점수", 0),
        "우선순위": it.get("_score", {}).get("등급표시", ""),
        "등급": it.get("등급", ""), "카테고리": it.get("카테고리", ""),
        "공고명": it.get("공고명", ""), "발주기관": it.get("발주기관", ""),
        "업무": it.get("업무구분", ""), "마감": it.get("마감일시", ""),
        "추천제품": "; ".join(p.get("제품명", "") for p in it.get("추천제품", [])),
    } for it in items])
    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
    st.download_button(
        "⬇️  CSV 다운로드",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="보안공고_브리핑.csv", mime="text/csv",
    )


def _pipeline_to_items(out: dict, bids: list[dict]) -> list[dict]:
    by_no = {b.get("공고번호"): b for b in bids}
    items = []
    for r in out["briefing"]:
        src = by_no.get(r["공고번호"], {})
        grade = ("제외" if not r["보안여부"]
                 else "영업대상" if r.get("추천제품") else "보안주제/매칭약함")
        items.append({
            "공고번호": r["공고번호"], "공고명": r["공고명"],
            "발주기관": src.get("공고기관", ""), "업무구분": src.get("업무구분", ""),
            "공고url": src.get("공고url", ""), "마감일시": src.get("마감일시", ""),
            "보안여부": r["보안여부"],
            "등급": grade, "카테고리": r["카테고리"], "추천제품": r.get("추천제품", []),
            "고객요구": r.get("고객요구", ""), "우리강점": r.get("우리강점", ""),
            "차별점": r.get("차별점", ""), "토킹포인트": r.get("토킹포인트", ""),
        })
    return items


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 실행 모드")
    mode = st.radio(
        "모드 선택", ["📁 저장된 브리핑 (무료)", "⚡ 지금 분석 (API 키 필요)"],
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
        st.caption("무료 경로: `fetch_bids.py`로 공고 수집 후 Claude Code에게 "
                   "브리핑을 요청하면 `briefing_latest.json`이 생기고 여기 표시됩니다.")

    st.divider()
    anth = "🟢" if config.ANTHROPIC_API_KEY and "여기에" not in config.ANTHROPIC_API_KEY else "🔴"
    data = "🟢" if config.DATA_GO_KR_SERVICE_KEY and "여기에" not in config.DATA_GO_KR_SERVICE_KEY else "🔴"
    st.caption(f"{anth} Anthropic 키   ·   {data} 나라장터 키")

    st.divider()
    st.markdown("### 🖥️ 영업부 포털")
    PORTAL_PORT = 4571
    if st.button("📤 포털 데이터 갱신", use_container_width=True,
                 help="최신 브리핑으로 포털 data.js를 다시 생성"):
        import portal_export
        try:
            s = portal_export.export()
            st.success(f"data.js 갱신 · {s['bids']}건 ({s['source']})")
        except Exception as ex:  # noqa: BLE001
            st.error(f"갱신 실패: {ex}")
    if st.button("🚀 포털 서버 열기", use_container_width=True,
                 help=f"localhost:{PORTAL_PORT} 에 포털 서버 시작"):
        import subprocess
        import sys
        try:
            subprocess.Popen([sys.executable,
                              str(Path(__file__).parent / "serve_portal.py"),
                              "--port", str(PORTAL_PORT)])
            st.success(f"서버 시작 → http://localhost:{PORTAL_PORT}")
        except Exception as ex:  # noqa: BLE001
            st.warning(f"시작 실패(이미 떠 있을 수 있음): {ex}")
    st.markdown(f"열기 → [localhost:{PORTAL_PORT}](http://localhost:{PORTAL_PORT})")
    st.caption("터미널: `python serve_portal.py`")


# ── 본문 ──────────────────────────────────────────────────
if not analyze:
    saved, _src = _load_saved()
    if saved is None:
        _hero(None)
        st.info("저장된 브리핑이 없습니다. `fetch_bids.py`로 공고를 모은 뒤 Claude Code에게 브리핑을 요청하세요.")
    else:
        render_briefing(saved.get("items", []), saved)
else:
    if run:
        try:
            bids = pipeline.get_bids(sample=use_sample, division=division,
                                     keyword=keyword or None, days=days)
        except RuntimeError as ex:
            st.error(str(ex)); st.stop()
        if not bids:
            st.warning("조회된 공고가 없습니다."); st.stop()
        with st.spinner(f"공고 {len(bids)}건 분류·매칭·토킹포인트 처리 중..."):
            try:
                out = pipeline.run_pipeline(bids)
            except RuntimeError as ex:
                st.error(str(ex)); st.stop()
        items = _pipeline_to_items(out, bids)
        # 라이브 분석 결과를 briefing_latest.json 으로 저장 → 포털(portal_export)이 같은 데이터를 서빙.
        try:
            from datetime import date as _date
            payload = {"생성일": _date.today().isoformat(),
                       "출처": "나라장터(조달청) 입찰공고정보서비스",
                       "분석": "API 분석", "수집건수": len(items), "items": items}
            BRIEFING_LATEST.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        render_briefing(items)
    else:
        _hero(None)
        st.info("왼쪽에서 조건을 정하고 **분석 실행**을 눌러주세요. (Anthropic 키 필요)")
