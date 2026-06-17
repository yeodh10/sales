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

# 배포(Streamlit Secrets) 환경에서는 모듈 import 시점에 키가 아직 비어 있을 수 있다.
# 스크립트가 재실행될 때마다 런타임에 키를 다시 읽어 config 값을 최신화한다.
config.ANTHROPIC_API_KEY = config._get("ANTHROPIC_API_KEY", "")
config.ANTHROPIC_MODEL = config._get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
config.DATA_GO_KR_SERVICE_KEY = config._get("DATA_GO_KR_SERVICE_KEY", "")

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


st.set_page_config(page_title="보안 영업 Copilot", page_icon="🔒", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

      :root{
        --bg:#08090C; --bg2:#0B0D12; --surface:#121419; --surface-2:#15181F;
        --line:rgba(255,255,255,.07); --line-2:rgba(255,255,255,.13);
        --text:#F4F6FA; --muted:#9AA3B2; --faint:#646C78;
        --accent:#3DDC97; --accent-2:#5AA2FF; --radius:20px; --radius-sm:13px;
      }
      html, body, [class*="css"], .stMarkdown, .stApp{
        font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
        -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
      }
      .stApp{
        background:
          radial-gradient(1200px 620px at 50% -260px, rgba(61,220,151,.10), transparent 60%),
          radial-gradient(900px 520px at 100% -40px, rgba(90,162,255,.06), transparent 55%),
          var(--bg);
      }
      .block-container{ padding-top:2.6rem; padding-bottom:5rem; max-width:1100px; }
      #MainMenu, footer, header[data-testid="stHeader"]{ display:none; }
      a{ text-decoration:none; }

      @keyframes rise{ from{opacity:0; transform:translateY(16px);} to{opacity:1; transform:none;} }

      /* ── Hero ── */
      .hero{ position:relative; overflow:hidden; margin:4px 0 34px; padding:48px 46px 44px;
        border-radius:28px; border:1px solid var(--line);
        background:linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.012));
        backdrop-filter:blur(16px); box-shadow:0 28px 80px rgba(0,0,0,.5);
        animation:rise .6s cubic-bezier(.2,.7,.2,1) both; }
      .hero::after{ content:''; position:absolute; right:-130px; top:-130px; width:360px; height:360px;
        background:radial-gradient(circle, rgba(61,220,151,.16), transparent 70%); pointer-events:none; }
      .hero .eyebrow{ display:inline-flex; align-items:center; gap:9px; font-size:.72rem; font-weight:600;
        letter-spacing:.2em; text-transform:uppercase; color:var(--accent); }
      .hero .eyebrow::before{ content:''; width:7px; height:7px; border-radius:50%; background:var(--accent);
        box-shadow:0 0 14px var(--accent); }
      .hero h1{ margin:18px 0 14px; font-size:3rem; font-weight:700; line-height:1.05;
        letter-spacing:-.038em; color:var(--text); }
      .hero h1 .ac{ background:linear-gradient(95deg,var(--accent),#8BEFC4); -webkit-background-clip:text;
        background-clip:text; -webkit-text-fill-color:transparent; }
      .hero p{ margin:0; max-width:660px; color:var(--muted); font-size:1.04rem; line-height:1.62; font-weight:400; }
      .hero .src{ display:block; margin-top:16px; color:var(--faint); font-size:.8rem; }

      /* ── KPI ── */
      .kpi{ background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
        padding:24px 26px; transition:transform .25s, border-color .25s; animation:rise .6s ease both; }
      .kpi:hover{ transform:translateY(-3px); border-color:var(--line-2); }
      .kpi .ic{ display:none; }
      .kpi .v{ font-size:2.7rem; font-weight:700; line-height:1; letter-spacing:-.035em; color:var(--a,var(--text)); }
      .kpi .l{ margin-top:10px; color:var(--muted); font-size:.86rem; font-weight:500; letter-spacing:-.01em; }

      /* ── Section headings ── */
      .sec-h{ font-size:1.4rem; font-weight:700; letter-spacing:-.025em; color:var(--text); margin:46px 0 18px; scroll-margin-top:24px; }
      .sec-h span{ color:var(--faint)!important; font-size:.86rem!important; font-weight:400!important; letter-spacing:0!important; }

      /* ── Deal cards ── */
      .grid{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }
      @media (max-width:900px){ .grid{ grid-template-columns:1fr; } }
      .deal{ background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
        padding:24px 26px 22px; transition:transform .25s, border-color .25s, box-shadow .25s;
        animation:rise .5s ease both; }
      .deal:hover{ transform:translateY(-4px); border-color:var(--line-2); box-shadow:0 22px 56px rgba(0,0,0,.46); }
      .deal .top{ display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
      .scorebox{ text-align:center; flex:0 0 auto; line-height:1.05; }
      .scorebox .sc{ font-size:1.75rem; font-weight:700; letter-spacing:-.03em; color:var(--t); }
      .scorebox .sct{ font-size:.6rem; font-weight:600; letter-spacing:.06em; color:var(--t); text-transform:uppercase; }
      .dday{ display:inline-block; padding:2px 9px; border-radius:7px; font-size:.7rem; font-weight:600;
        margin-left:8px; vertical-align:middle; color:var(--t);
        background:color-mix(in srgb, var(--t) 15%, transparent); }
      .deal .title{ font-size:1.14rem; font-weight:600; line-height:1.42; letter-spacing:-.012em;
        margin:14px 0 6px; color:var(--text); }
      .deal .meta{ color:var(--faint); font-size:.8rem; margin-bottom:15px; }
      .pill{ display:inline-block; padding:5px 13px; border-radius:999px; font-size:.72rem; font-weight:600;
        color:var(--c); background:color-mix(in srgb, var(--c) 13%, transparent);
        border:1px solid color-mix(in srgb, var(--c) 30%, transparent); }
      .prod{ background:rgba(255,255,255,.025); border:1px solid var(--line); border-radius:12px;
        padding:11px 14px; margin:7px 0; font-size:.9rem; color:#D4DBE6; }
      .prod b{ color:var(--c); font-weight:600; }
      .tp{ font-size:.9rem; color:var(--muted); margin:6px 0; line-height:1.5; }
      .tp b{ color:var(--text); font-weight:600; }
      .cross{ font-size:.86rem; margin-top:8px; color:#9FD2F2; background:rgba(90,162,255,.08);
        border:1px solid rgba(90,162,255,.18); border-radius:12px; padding:10px 13px; }
      .quote{ margin-top:14px; padding:14px 16px; border-radius:13px; font-size:.92rem; line-height:1.62;
        color:#E7EEF6; background:rgba(255,255,255,.03);
        border:1px solid color-mix(in srgb, var(--c) 22%, transparent);
        border-left:3px solid var(--c); }

      /* ── Table ── */
      table.bf{ width:100%; border-collapse:separate; border-spacing:0 8px; font-size:.88rem; }
      table.bf th{ text-align:left; color:var(--faint); font-weight:500; font-size:.75rem;
        letter-spacing:.02em; padding:0 14px 6px; }
      table.bf td{ background:var(--surface); padding:13px 14px; color:#D5DDE8;
        border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
      table.bf tr td:first-child{ border-radius:12px 0 0 12px; border-left:1px solid var(--line); }
      table.bf tr td:last-child{ border-radius:0 12px 12px 0; border-right:1px solid var(--line); }
      .chip{ display:inline-block; padding:3px 10px; border-radius:8px; font-size:.74rem; font-weight:600;
        color:var(--g); background:color-mix(in srgb, var(--g) 16%, transparent); }
      .catdot{ display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--c);
        margin-right:8px; vertical-align:middle; }

      /* ── Sidebar ── */
      [data-testid="stSidebar"]{ background:var(--bg2); border-right:1px solid var(--line); }
      [data-testid="stSidebar"] h3{ font-size:.78rem!important; letter-spacing:.12em; text-transform:uppercase;
        color:var(--faint)!important; font-weight:600; }
      .navlinks a{ display:block; padding:9px 13px; margin:5px 0; border-radius:12px; font-size:.9rem;
        font-weight:500; color:var(--muted); background:var(--surface); border:1px solid var(--line);
        transition:all .2s; }
      .navlinks a:hover{ color:var(--text); transform:translateX(3px);
        border-color:color-mix(in srgb, var(--accent) 45%, transparent); }

      /* ── Buttons ── */
      .stButton>button{ border-radius:12px; font-weight:600; letter-spacing:-.01em; transition:transform .15s, filter .2s; }
      .stButton>button:hover{ transform:translateY(-1px); filter:brightness(1.05); }

      /* ── Tabs (페이지 분리) ── */
      .stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--line); margin-bottom:22px; }
      .stTabs [data-baseweb="tab"]{ height:46px; padding:0 20px; background:transparent; color:var(--muted);
        font-weight:600; font-size:1rem; letter-spacing:-.01em; border-radius:10px 10px 0 0; }
      .stTabs [data-baseweb="tab"]:hover{ color:var(--text); background:rgba(255,255,255,.03); }
      .stTabs [aria-selected="true"]{ color:var(--text)!important; }
      .stTabs [data-baseweb="tab-highlight"]{ background:var(--accent)!important; height:3px; border-radius:3px 3px 0 0; }
      .stTabs [data-baseweb="tab-border"]{ background:transparent; }
      .tabcap{ color:var(--faint); font-size:.88rem; margin:0 0 18px; }
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
    analysis = str(meta.get("분석", "")) if meta else ""
    note = ("실시간 나라장터 데이터를 보안 키워드로 1차 선별했습니다 (AI 분류 미적용)."
            if "키워드" in analysis
            else "AI 1차 분석이며 최종 판단은 담당자가 검수합니다.")
    st.markdown(
        f'<div class="hero"><div class="eyebrow">🔒 PUBLIC SECTOR SECURITY SALES</div>'
        f'<h1>보안 영업 <span class="ac">Copilot</span></h1>'
        f'<p>나라장터 입찰공고 → 보안 분류 → 제품 매칭 → 영업 토킹포인트.<br>'
        f'{note} '
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

    tab0, tab1, tab2, tab3 = st.tabs([
        "🏠 메인",
        f"⭐ 영업 우선대상 {len(targets)}",
        f"🔗 연관 기회 {len(adj)}",
        f"📋 전체 브리핑 {len(items)}",
    ])

    with tab0:
        _hero(meta)
        _kpis(len(items), len(targets), len(adj), hot)

    with tab1:
        st.markdown('<div class="tabcap">직접 보안 · 우선순위 점수순</div>', unsafe_allow_html=True)
        if targets:
            st.markdown('<div class="grid">' + "".join(_deal_html(i) for i in targets) + "</div>",
                        unsafe_allow_html=True)
        else:
            st.caption("매칭된 영업 대상이 없습니다.")

    with tab2:
        st.markdown('<div class="tabcap">보안이 따라붙는 IT 사업 · 크로스셀 기회</div>', unsafe_allow_html=True)
        if adj:
            st.markdown('<div class="grid">' + "".join(_adj_html(i) for i in adj) + "</div>",
                        unsafe_allow_html=True)
        else:
            st.caption("연관 기회로 분류된 공고가 없습니다.")

    with tab3:
        st.markdown('<div class="tabcap">전체 공고 · 점수·등급·마감 한눈에</div>', unsafe_allow_html=True)
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



# 키워드 → 표시 카테고리 (AI 없이 결정론적 매핑). 앞쪽이 더 구체적.
_LIVE_CORE_CAT = [
    (("방화벽",), "방화벽"),
    (("백신", "EDR"), "백신/EDR"),
    (("보안관제", "관제", "SOC"), "보안관제(SOC)"),
    (("망분리",), "망분리"),
    (("접근통제", "IAM"), "접근통제(IAM)"),
    (("정보보호", "정보보안", "ISMS", "개인정보", "취약점", "모의해킹", "암호", "인증서", "컨설팅"),
     "정보보호 컨설팅"),
]
_LIVE_ADJ_CAT = [
    (("클라우드",), "클라우드 전환"),
    (("데이터센터",), "데이터센터"),
    (("네트워크", "서버"), "네트워크/인프라"),
    (("CCTV", "영상"), "통합관제/영상"),
    (("전자정부",), "전자정부"),
    (("홈페이지", "웹"), "홈페이지/웹"),
    (("스마트시티",), "스마트시티"),
    (("정보시스템", "정보화", "시스템 구축", "시스템 통합", "전산", "디지털"), "정보시스템 구축"),
]


def _live_items(bids: list[dict], scope: str = "all") -> list[dict]:
    """나라장터 실데이터를 AI 없이 보안 키워드로 1차 선별해 화면 아이템으로 변환.

    scope: "core"=직접 보안만, "all"=직접+연관(크로스셀).
    """
    import keywords as _kw

    out: list[dict] = []
    for b in bids:
        name = (b.get("공고명", "") or "").replace(" ", "")
        cat = grade = None
        for kws, c in _LIVE_CORE_CAT:
            if any(k.replace(" ", "") in name for k in kws):
                cat, grade = c, "영업대상"
                break
        if cat is None and any(k in name for k in _kw.CORE):
            cat, grade = "정보보호 컨설팅", "영업대상"
        if cat is None and scope != "core":
            for kws, c in _LIVE_ADJ_CAT:
                if any(k.replace(" ", "") in name for k in kws):
                    cat, grade = c, "연관기회"
                    break
            if cat is None and any(k in name for k in _kw.ADJACENT):
                cat, grade = "정보시스템 구축", "연관기회"
        if cat is None:
            continue
        out.append({
            "공고번호": b.get("공고번호", ""), "공고명": b.get("공고명", ""),
            "발주기관": b.get("공고기관", ""), "업무구분": b.get("업무구분", ""),
            "공고url": b.get("공고url", ""), "마감일시": b.get("마감일시", ""),
            "카테고리": cat, "등급": grade, "추천제품": [],
        })
    return out


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 실행 모드")
    mode = st.radio(
        "모드 선택",
        ["📁 저장된 브리핑 (무료)", "🔎 실시간 공고 (나라장터)", "⚡ 지금 분석 (API 키 필요)"],
        label_visibility="collapsed",
    )
    analyze = mode.startswith("⚡")
    livefetch = mode.startswith("🔎")

    if livefetch:
        st.divider()
        st.caption("나라장터에서 **오늘자 실데이터**를 가져와 보안 키워드로 1차 선별합니다. "
                   "AI 분류·토킹포인트는 적용하지 않아 추가 비용이 없습니다.")
        lf_division = st.selectbox("업무구분", list(narajangteo.BUSINESS_DIVISIONS),
                                   index=1, key="lf_div")
        lf_scope = st.radio("범위", ["보안 직접+연관", "보안 직접만"], index=0, key="lf_scope")
        lf_days = st.slider("최근 며칠", 3, 30, 14, key="lf_days")
        run = st.button("실시간 공고 불러오기", type="primary", use_container_width=True)
    elif analyze:
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
    st.markdown("### 🔑 상태")
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
if livefetch:
    if run:
        scope = "core" if lf_scope.startswith("보안 직접만") else "all"
        try:
            with st.spinner("나라장터에서 실시간 공고를 가져오는 중..."):
                _raw = narajangteo.search_bids(division=lf_division, keyword=None,
                                               days=lf_days, rows=100)
                _bids = [b.to_dict() for b in _raw]
        except RuntimeError as ex:
            st.error(str(ex)); st.stop()
        items = _live_items(_bids, scope=scope)
        if not items:
            st.warning("선별된 보안 관련 공고가 없습니다. 기간/업무구분을 넓혀보세요."); st.stop()
        st.info("실시간 나라장터 공고를 **보안 키워드로 1차 선별**한 결과입니다. "
                "AI 분류·제품 매칭·토킹포인트는 적용하지 않았습니다(추가 비용 없음). "
                "정밀 분석은 로컬에서 Anthropic 키와 함께 실행하세요.")
        from datetime import date as _date
        _meta = {"출처": "나라장터(조달청) 입찰공고정보서비스",
                 "생성일": _date.today().isoformat(), "분석": "키워드 선별(AI 미적용)"}
        render_briefing(items, _meta)
    else:
        _hero(None)
        st.info("왼쪽에서 업무구분·기간을 정하고 **실시간 공고 불러오기**를 눌러주세요. "
                "(나라장터 키만 있으면 동작 · 추가 비용 없음)")
elif not analyze:
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
