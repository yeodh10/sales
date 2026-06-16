/* =============================================================================
   보안 영업부 · 코파일럿 포털 — vanilla JS
   데이터: window.PORTAL_DATA (data.js)
   스코어링: sales/scoring.py 로직을 그대로 이식 (적합도 + 카테고리 가중 + 마감 임박도)
   ========================================================================== */
(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // 데이터 로드 실패(undefined/형식 이상)와 정상 빈 데이터(bids:[])를 구분
  var DATA_OK = !!(window.PORTAL_DATA && Array.isArray(window.PORTAL_DATA.bids));
  var DATA = DATA_OK ? window.PORTAL_DATA : { bids: [], products: [], total: 0, refDate: '2026-06-15' };

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function stripEx(s) { return String(s || '').replace(/^\(예시\)\s*/, ''); }
  function safeUrl(u) {
    var s = String(u == null ? '' : u).trim();
    return /^https?:\/\//i.test(s) ? s : '#';
  }
  function parseDate(s) {
    if (!s) return null;
    var m = String(s).replace(/[./]/g, '-').match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (!m) return null;
    return new Date(+m[1], +m[2] - 1, +m[3]);
  }
  var TODAY = parseDate(DATA.refDate) || new Date(2026, 5, 15);
  function daysLeft(deadline) {
    var d = parseDate(deadline);
    if (!d) return null;
    return Math.round((d - TODAY) / 86400000);
  }
  function fmtDate(s) {
    var d = parseDate(s);
    if (!d) return '미정';
    return (d.getMonth() + 1) + '월 ' + d.getDate() + '일';
  }

  /* ---------- scoring (이식: scoring.py) ---------- */
  var GRADE_FIT = { '영업대상': 35, '연관기회': 18, '보안주제/매칭약함': 12, '제외': 0 };
  var CATEGORY_WEIGHT = {
    '보안관제(SOC)': 20, '정보보호 컨설팅': 18, '접근통제(IAM)': 16, '망분리': 15,
    '방화벽': 15, '네트워크 보안': 15, '백신/EDR': 13, '보안 유지관리': 14, 'OT 보안': 8,
    '보안 교육': 6, '보안 거버넌스': 9, '인프라': 6, '보안 행사': 4,
    '클라우드 전환': 14, '데이터센터': 13, '네트워크/인프라': 13, '정보시스템 구축': 12,
    '전자정부': 11, '통합관제/영상': 8, '홈페이지/웹': 9, '스마트시티': 9
  };
  function deadlineScore(dleft) {
    if (dleft === null) return 12;
    if (dleft < 0) return 0;
    if (dleft <= 3) return 18;
    if (dleft <= 21) return 30;
    if (dleft <= 45) return 20;
    return 12;
  }
  function tierOf(score, expired) {
    if (expired) return { cls: 'expired', label: '마감' };
    if (score >= 72) return { cls: 'hot', label: '핫' };
    if (score >= 58) return { cls: 'watch', label: '주목' };
    if (score >= 40) return { cls: 'review', label: '검토' };
    return { cls: 'low', label: '후순위' };
  }
  function scoreBid(b) {
    var dleft = daysLeft(b.deadline);
    var expired = dleft !== null && dleft < 0;
    if (b.grade === '제외') return { score: 0, dleft: dleft, expired: expired, tier: tierOf(0, expired) };
    var fit = Math.min((GRADE_FIT[b.grade] || 0) + Math.min((b.products || []).length, 2) * 7, 49);
    var cat = CATEGORY_WEIGHT[b.category] != null ? CATEGORY_WEIGHT[b.category] : 10;
    var total = fit + cat + deadlineScore(dleft);
    if (expired) total = Math.min(total, 30);
    total = Math.max(0, Math.min(100, total));
    return { score: total, dleft: dleft, expired: expired, tier: tierOf(total, expired) };
  }

  // annotate
  DATA.bids.forEach(function (b) { b._s = scoreBid(b); });

  function gradeCls(g) {
    return g === '영업대상' ? 'target' : g === '연관기회' ? 'related' : 'weak';
  }
  function ddayInfo(s) {
    if (s.dleft === null) return { cls: 'none', label: '미정' };
    if (s.dleft < 0) return { cls: 'none', label: '마감' };
    if (s.dleft <= 3) return { cls: 'urgent', label: 'D-' + s.dleft };
    if (s.dleft <= 7) return { cls: 'soon', label: 'D-' + s.dleft };
    return { cls: '', label: 'D-' + s.dleft };
  }

  /* ---------- KPIs ---------- */
  function renderKPIs() {
    var bids = DATA.bids;
    var sec = bids.filter(function (b) { return b.security; }).length;
    var target = bids.filter(function (b) { return b.grade === '영업대상'; }).length;
    var related = bids.filter(function (b) { return b.grade === '연관기회'; }).length;
    var soon = bids.filter(function (b) {
      return (b.grade === '영업대상' || b.grade === '연관기회') && b._s.dleft !== null && b._s.dleft >= 0 && b._s.dleft <= 7;
    }).length;

    var items = [
      { n: DATA.total || bids.length, label: '수집 공고', foot: '나라장터 신규' },
      { n: sec, label: '보안 공고', foot: 'AI 보안 분류' },
      { n: target, label: '영업대상', foot: '제품 직접 매칭', grad: true },
      { n: related, label: '연관기회', foot: '크로스셀 후보' },
      { n: soon, label: 'D-7 임박', foot: '클릭 시 임박 공고만', action: 'urgent' }
    ];
    document.getElementById('kpi-row').innerHTML = items.map(function (k) {
      var inner = '<div class="kpi-num">' +
        '<span class="' + (k.grad ? 'grad' : '') + '" data-count="' + k.n + '">0</span></div>' +
        '<div class="kpi-label">' + esc(k.label) + '</div>' +
        '<div class="kpi-foot">' + esc(k.foot) + '</div>';
      if (k.action === 'urgent') {
        return '<button class="kpi kpi--action" type="button" data-action="urgent" aria-pressed="false">' + inner + '</button>';
      }
      return '<div class="kpi" role="listitem">' + inner + '</div>';
    }).join('');
  }

  /* ---------- Board ---------- */
  var boardBids = DATA.bids.filter(function (b) { return b.grade !== '제외'; });
  var state = { grade: '전체', category: '전체', q: '', sort: 'score', status: '전체', owner: '전체', urgent: false };

  /* ---------- tracking (localStorage: 영업 상태·담당자·메모) ---------- */
  var TRACK_KEY = 'salesportal.tracking.v1';
  var STATUSES = ['미정', '검토', '제안', '수주', '보류'];
  var TRACK = (function () { try { return JSON.parse(localStorage.getItem(TRACK_KEY)) || {}; } catch (e) { return {}; } })();
  var TRACK_API = '/api/tracking';   // 팀 공유 서버(serve_portal.py). 없으면 로컬(localStorage) 모드.
  // CSRF 비단순요청 강제용 토큰(브라우저가 보내므로 비밀이 아님).
  // 서버는 config.PORTAL_TOKEN(.env PORTAL_TOKEN)에서 읽으므로, 서버 쪽 토큰을
  // 기본값에서 바꾸면 아래 값도 같은 값으로 맞춰야 한다(불일치 시 403).
  var PORTAL_TOKEN = 'portal-sales-2026';
  var SERVER = false;           // syncFromServer 성공 시 true
  var SERVER_READY = false;     // 서버 가용성 확정 여부(성공/실패 모두 확정)
  var pending = {};             // id -> 누적 patch (서버 미확정 또는 전송 실패분)
  var edited = {};              // id -> true (사용자가 로컬에서 편집): 머지 시 보존
  function saveTrack() { try { localStorage.setItem(TRACK_KEY, JSON.stringify(TRACK)); } catch (e) {} }
  function getTrack(id) { return TRACK[id] || { status: '미정', owner: '', memo: '' }; }
  function setTrack(id, patch) {
    var t = getTrack(id);
    TRACK[id] = {
      status: patch.status != null ? patch.status : t.status,
      owner: patch.owner != null ? patch.owner : t.owner,
      memo: patch.memo != null ? patch.memo : t.memo
    };
    edited[id] = true;
    saveTrack();
    pushToServer(id, patch);
  }
  function updateMode() {
    var el = document.getElementById('track-mode');
    if (!el) return;
    el.innerHTML = SERVER
      ? '🟢 <strong>팀 공유 모드</strong> — 상태·담당자·메모가 서버에 저장되어 팀원과 공유됩니다.'
      : '💼 상태·담당자·메모는 이 <strong>브라우저(기기)</strong>에 저장됩니다. 팀 공유가 필요하면 serve_portal.py 로 실행하세요.';
  }
  // fetch + 타임아웃/취소
  function fetchT(url, opts, ms) {
    opts = opts || {};
    if (typeof AbortController === 'function') {
      var ac = new AbortController();
      var to = setTimeout(function () { ac.abort(); }, ms);
      opts.signal = ac.signal;
      return fetch(url, opts).then(
        function (r) { clearTimeout(to); return r; },
        function (e) { clearTimeout(to); throw e; }
      );
    }
    return fetch(url, opts);
  }
  // 안전한 attribute selector escape
  function cssEsc(v) { return (window.CSS && CSS.escape) ? CSS.escape(v) : String(v).replace(/["\\]/g, '\\$&'); }
  function trackRow(id) { return document.querySelector('.bid-track[data-id="' + cssEsc(id) + '"]'); }
  // 활성 편집 요소의 포커스/선택영역 기억 → 재렌더 후 복원
  function captureFocus() {
    var a = document.activeElement;
    if (!a || !a.closest) return null;
    var row = a.closest('.bid-track'); if (!row) return null;
    var cls = a.classList.contains('track-status') ? 'track-status'
      : a.classList.contains('track-owner') ? 'track-owner'
      : a.classList.contains('track-memo') ? 'track-memo' : null;
    if (!cls) return null;
    var snap = { id: row.getAttribute('data-id'), cls: cls };
    if (typeof a.selectionStart === 'number') { snap.s = a.selectionStart; snap.e = a.selectionEnd; }
    return snap;
  }
  function restoreFocus(snap) {
    if (!snap) return;
    var row = trackRow(snap.id); if (!row) return;
    var el = row.querySelector('.' + snap.cls); if (!el) return;
    try {
      el.focus();
      if (snap.s != null && typeof el.setSelectionRange === 'function') el.setSelectionRange(snap.s, snap.e);
    } catch (e) { /* noop */ }
  }
  function isEditingTrack() {
    var a = document.activeElement;
    return !!(a && a.closest && a.closest('.bid-track'));
  }
  // 저장 상태 시각 피드백 (해당 카드 트래킹 행)
  function setSaveState(id, kind, text) {
    if (!SERVER && kind !== 'err') return;
    var row = trackRow(id); if (!row) return;
    var el = row.querySelector('.track-saved');
    if (!el) { el = document.createElement('span'); el.className = 'track-saved'; el.setAttribute('role', 'status'); row.appendChild(el); }
    el.classList.remove('is-ok', 'is-pending', 'is-err');
    if (kind) el.classList.add('is-' + kind);
    el.textContent = text || '';
  }
  function queuePatch(id, patch) {
    var p = pending[id] || (pending[id] = {});
    if (patch.status != null) p.status = patch.status;
    if (patch.owner != null) p.owner = patch.owner;
    if (patch.memo != null) p.memo = patch.memo;
  }
  function syncFromServer() {
    if (!window.fetch) { SERVER_READY = true; return; }
    fetchT(TRACK_API, { cache: 'no-store' }, 5000)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        SERVER = true; SERVER_READY = true;
        if (d && typeof d === 'object') {
          // 병합: 로컬 편집분(edited)·미전송분(pending)은 보존, 그 외만 서버값 적용
          Object.keys(d).forEach(function (k) {
            if (edited[k] || pending[k]) return;
            TRACK[k] = d[k];
          });
          saveTrack();
        }
        updateMode();
        // 입력 중이면 재렌더 보류(다음 blur까지). 그 외엔 포커스 보존하며 재렌더.
        if (!isEditingTrack()) {
          var snap = captureFocus();
          renderBoard();
          restoreFocus(snap);
        }
        flushPending();
      })
      .catch(function () {
        // 타임아웃/서버 없음 → 로컬 모드 확정 폴백
        SERVER = false; SERVER_READY = true; updateMode();
      });
  }
  function flushPending() {
    if (!SERVER) return;
    Object.keys(pending).forEach(function (id) {
      var patch = pending[id];
      delete pending[id];
      pushToServer(id, patch);
    });
  }
  function pushToServer(id, patch) {
    if (!window.fetch) return;
    // 서버 가용성 미확정이면 큐에 쌓고 sync 성공 후 flush
    if (!SERVER_READY) { queuePatch(id, patch); return; }
    if (!SERVER) return; // 로컬 모드 확정 → POST 불필요(localStorage에 이미 저장)
    var body = { id: id };
    if (patch.status != null) body.status = patch.status;
    if (patch.owner != null) body.owner = patch.owner;
    if (patch.memo != null) body.memo = patch.memo;
    setSaveState(id, 'pending', '저장 중…');
    fetchT(TRACK_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Portal-Token': PORTAL_TOKEN },
      body: JSON.stringify(body)
    }, 8000)
      .then(function (r) {
        if (r && r.ok) { setSaveState(id, 'ok', '저장됨 ✓'); }
        else { queuePatch(id, patch); setSaveState(id, 'err', '저장 실패—재시도'); }
      })
      .catch(function () {
        queuePatch(id, patch); setSaveState(id, 'err', '저장 실패—재시도');
      });
  }
  function trackRowHTML(id, name) {
    var t = getTrack(id);
    var nm = esc(stripEx(name || ''));
    var opts = STATUSES.map(function (s) {
      return '<option value="' + s + '"' + (s === t.status ? ' selected' : '') + '>' + s + '</option>';
    }).join('');
    return '<div class="bid-track" data-id="' + esc(id) + '" role="group" aria-label="' + nm + ' 영업 관리">' +
      '<select class="track-status" data-v="' + esc(t.status) + '" aria-label="' + nm + ' 영업 상태">' + opts + '</select>' +
      '<input class="track-owner" type="text" value="' + esc(t.owner) + '" placeholder="담당자" aria-label="' + nm + ' 담당자" autocomplete="off" maxlength="20">' +
      '<input class="track-memo" type="text" value="' + esc(t.memo) + '" placeholder="메모" aria-label="' + nm + ' 메모" autocomplete="off" maxlength="200">' +
    '</div>';
  }

  function bidCardHTML(b) {
    var s = b._s, dd = ddayInfo(s);
    var prodTags = (b.products || []).map(function (p) {
      return '<span class="tag">' + esc(stripEx(p)) + '</span>';
    }).join('');
    var body = '';
    if (prodTags) {
      body += '<div class="bid-products">' + prodTags + '</div>';
    } else if (b.crosssell) {
      body += '<div class="bid-products"><span class="tag tag--cross">크로스셀</span></div>';
    }
    var note = b.talk ? b.talk : (b.crosssell || '');
    if (note) body += '<p class="bid-talk">' + esc(note) + '</p>';
    // AI 판단근거
    if (b.reason) body += '<p class="bid-reason"><b>근거</b> · ' + esc(b.reason) + '</p>';
    // 제품 — 매칭이유
    var matches = b.match || [];
    if (matches.length) {
      var prods = b.products || [];
      var items = matches.map(function (m, i) {
        var p = stripEx(prods[i] || '');
        return '<li>' + (p ? '<b>' + esc(p) + '</b> — ' : '') + esc(m) + '</li>';
      }).join('');
      body += '<details class="bid-match"><summary>매칭 근거</summary><ul>' + items + '</ul></details>';
    }

    var copyBtn = note ? '<button class="copy-btn" type="button" data-copy="' + esc(note) + '">멘트 복사</button>' : '<span></span>';
    var titleUrl = safeUrl(b.url);
    var titleA = titleUrl === '#'
      ? '<span class="bid-title-text">' + esc(b.name) + '</span>'
      : '<a href="' + esc(titleUrl) + '" target="_blank" rel="noopener noreferrer">' + esc(b.name) + ' <span class="sr-only">(새 탭에서 열림)</span></a>';

    return '<article class="bid-card reveal">' +
      '<div class="bid-top">' +
        '<div class="bid-score score--' + s.tier.cls + '"><span class="num">' + s.score + '</span><small>' + s.tier.label + '</small></div>' +
        '<div class="bid-headings">' +
          '<div class="bid-badges">' +
            '<span class="badge badge--' + gradeCls(b.grade) + '">' + esc(b.grade) + '</span>' +
            '<span class="badge badge--cat">' + esc(b.category) + '</span>' +
          '</div>' +
          '<h3 class="bid-title">' + titleA + '</h3>' +
          '<p class="bid-org">' + esc(b.org) + (b.type ? ' · ' + esc(b.type) : '') + '</p>' +
        '</div>' +
      '</div>' +
      '<div class="bid-deadline">마감 <span class="dday dday--' + dd.cls + '">' + dd.label + '</span> <span class="dl-date">' + fmtDate(b.deadline) + '</span></div>' +
      body +
      '<div class="bid-foot">' +
        (titleUrl === '#'
          ? '<span class="bid-link bid-link--off" aria-disabled="true" title="유효한 공고 링크가 없습니다">공고 링크 없음</span>'
          : '<a class="bid-link" href="' + esc(titleUrl) + '" target="_blank" rel="noopener noreferrer">공고 보기 →</a>') +
        copyBtn +
      '</div>' +
      trackRowHTML(b.id, b.name) +
    '</article>';
  }

  function urgentActive() { return state.urgent || state.sort === 'urgent'; }
  function filteredBoard() {
    var q = state.q.trim().toLowerCase();
    var urgent = urgentActive();
    var list = boardBids.filter(function (b) {
      if (state.grade !== '전체' && b.grade !== state.grade) return false;
      if (state.category !== '전체' && b.category !== state.category) return false;
      var tk = getTrack(b.id);
      if (state.status !== '전체' && tk.status !== state.status) return false;
      if (state.owner !== '전체' && tk.owner !== state.owner) return false;
      if (urgent) { var dl = b._s.dleft; if (dl === null || dl < 0 || dl > 7) return false; }
      if (q) {
        var hay = (b.name + ' ' + b.org + ' ' + (b.category || '') + ' ' +
          (b.products || []).join(' ') + ' ' + (b.reason || '') + ' ' + (b.crosssell || '') +
          ' ' + (tk.memo || '') + ' ' + (tk.owner || '')).toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
    var byDeadline = state.sort === 'deadline' || urgent;
    list.sort(function (a, c) {
      if (byDeadline) {
        var da = a._s.dleft, dc = c._s.dleft;
        var va = da === null || da < 0 ? 99999 : da;
        var vc = dc === null || dc < 0 ? 99999 : dc;
        if (va !== vc) return va - vc;
        return c._s.score - a._s.score;
      }
      return c._s.score - a._s.score;
    });
    return list;
  }

  function filtersActive() {
    return state.grade !== '전체' || state.category !== '전체' || state.status !== '전체' ||
      state.owner !== '전체' || urgentActive() || !!state.q;
  }
  function renderBoard() {
    var list = filteredBoard();
    var grid = document.getElementById('board-grid');
    var empty = document.getElementById('board-empty');
    var count = document.getElementById('board-count');
    var snap = captureFocus();
    grid.innerHTML = list.map(bidCardHTML).join('');
    empty.hidden = list.length > 0;
    if (list.length === 0) {
      count.textContent = filtersActive()
        ? '조건에 맞는 공고가 없습니다 · 필터를 조정해 보세요'
        : '표시할 공고가 없습니다';
    } else {
      count.textContent = '총 ' + list.length + '건' +
        (filtersActive() ? ' (필터 적용)' : '') +
        (state.sort === 'deadline' || urgentActive() ? ' · 마감 임박순' : ' · 점수 높은 순으로 먼저 움직이세요');
    }
    renderStatusSummary();
    restoreFocus(snap);
    observeReveals();
  }

  function setupBoardControls() {
    // grade chips
    var grades = ['전체', '영업대상', '연관기회', '보안주제/매칭약함'];
    var counts = {};
    boardBids.forEach(function (b) { counts[b.grade] = (counts[b.grade] || 0) + 1; });
    counts['전체'] = boardBids.length;
    document.getElementById('grade-filter').innerHTML = grades.map(function (g) {
      var n = counts[g] || 0;
      var label = g === '보안주제/매칭약함' ? '매칭약함' : g;
      return '<button class="chip' + (g === '전체' ? ' chip--active' : '') + '" type="button" data-grade="' + esc(g) + '">' +
        esc(label) + '<span class="chip-n">' + n + '</span></button>';
    }).join('');

    // category select
    var cats = {};
    boardBids.forEach(function (b) { if (b.category) cats[b.category] = (cats[b.category] || 0) + 1; });
    var catKeys = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; });
    var sel = document.getElementById('board-category');
    sel.innerHTML = '<option value="전체">전체 카테고리</option>' + catKeys.map(function (c) {
      return '<option value="' + esc(c) + '">' + esc(c) + ' (' + cats[c] + ')</option>';
    }).join('');

    refreshOwnerOptions();

    // events
    document.getElementById('grade-filter').addEventListener('click', function (e) {
      var btn = e.target.closest('.chip'); if (!btn) return;
      state.grade = btn.getAttribute('data-grade');
      this.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('chip--active', c === btn); });
      renderBoard();
    });
    sel.addEventListener('change', function () { state.category = this.value; renderBoard(); });
    document.getElementById('board-sort').addEventListener('change', function () {
      state.sort = this.value;
      if (state.sort !== 'urgent') state.urgent = false; // 명시적 정렬 선택 시 KPI 임박 토글 해제
      renderBoard();
    });
    document.getElementById('board-status').addEventListener('change', function () { state.status = this.value; renderBoard(); });
    var ownerSel = document.getElementById('board-owner');
    if (ownerSel) ownerSel.addEventListener('change', function () { state.owner = this.value; renderBoard(); });
    var si = document.getElementById('board-search');
    var t;
    si.addEventListener('input', function () {
      clearTimeout(t); var v = this.value; t = setTimeout(function () { state.q = v; renderBoard(); }, 160);
    });
    var exportBtn = document.getElementById('board-export');
    if (exportBtn) exportBtn.addEventListener('click', exportCSV);
  }

  // 담당자 옵션 갱신(담당자 입력값이 바뀌면 재호출). 현재 선택값이 사라지면 '전체'로.
  function refreshOwnerOptions() {
    var ownerSel = document.getElementById('board-owner');
    if (!ownerSel) return;
    var set = {};
    boardBids.forEach(function (b) { var o = getTrack(b.id).owner; if (o) set[o] = true; });
    var owners = Object.keys(set).sort();
    if (state.owner !== '전체' && !set[state.owner]) state.owner = '전체';
    ownerSel.innerHTML = '<option value="전체">전체 담당자</option>' + owners.map(function (o) {
      return '<option value="' + esc(o) + '"' + (o === state.owner ? ' selected' : '') + '>' + esc(o) + '</option>';
    }).join('');
  }

  function syncStatusSelect() {
    var ss = document.getElementById('board-status');
    if (ss && ss.value !== state.status) ss.value = state.status;
  }

  /* ---------- 상태별 파이프라인 요약 ---------- */
  function renderStatusSummary() {
    var wrap = document.getElementById('status-summary');
    if (!wrap) return;
    var counts = {};
    boardBids.forEach(function (b) { var s = getTrack(b.id).status || '미정'; counts[s] = (counts[s] || 0) + 1; });
    wrap.innerHTML = STATUSES.map(function (s) {
      var on = state.status === s;
      return '<button class="chip' + (on ? ' chip--active' : '') + '" type="button" data-status="' + esc(s) + '" aria-pressed="' + (on ? 'true' : 'false') + '">' +
        esc(s) + '<span class="chip-n">' + (counts[s] || 0) + '</span></button>';
    }).join('');
  }

  /* ---------- CSV 내보내기 (현재 필터된 목록 + 트래킹) ---------- */
  function exportCSV() {
    var list = filteredBoard();
    var header = ['점수', '등급', '카테고리', '공고명', '발주기관', '마감일', 'D-day', '상태', '담당자', '메모', 'URL'];
    function cell(v) { return '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'; }
    var rows = [header.map(cell).join(',')];
    list.forEach(function (b) {
      var tk = getTrack(b.id), dd = ddayInfo(b._s);
      rows.push([
        b._s.score, b.grade, b.category, stripEx(b.name), b.org,
        (parseDate(b.deadline) ? b.deadline : '미정'), dd.label,
        tk.status || '미정', tk.owner || '', tk.memo || '', (b.url || '')
      ].map(cell).join(','));
    });
    var csv = rows.join('\r\n');
    try {
      var blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = '보안공고_' + (DATA.refDate || '목록') + '.csv';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    } catch (e) { /* noop */ }
  }

  /* ---------- Category distribution (security bids) ---------- */
  function renderDist() {
    var cats = {};
    DATA.bids.filter(function (b) { return b.security; }).forEach(function (b) {
      var c = b.category || '기타'; cats[c] = (cats[c] || 0) + 1;
    });
    var keys = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; });
    var max = keys.length ? cats[keys[0]] : 1;
    document.getElementById('dist-list').innerHTML = keys.map(function (c) {
      var w = Math.round((cats[c] / max) * 100);
      return '<div class="dist-row reveal"><span class="dist-name">' + esc(c) + '</span>' +
        '<span class="dist-track"><span class="dist-fill" data-w="' + w + '"></span></span>' +
        '<span class="dist-count"><b>' + cats[c] + '</b>건</span></div>';
    }).join('');
    // animate widths
    requestAnimationFrame(function () {
      document.querySelectorAll('#dist-list .dist-fill').forEach(function (el) {
        el.style.setProperty('--w', el.getAttribute('data-w') + '%');
      });
    });
    observeReveals();
  }

  /* ---------- Products ---------- */
  function renderProducts() {
    document.getElementById('product-grid').innerHTML = (DATA.products || []).map(function (p) {
      var feats = (p.features || []).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('');
      var fits = (p.fits || []).slice(0, 4).map(esc).join(' · ');
      return '<article class="product-card reveal">' +
        '<span class="product-cat">' + esc(p.category) + '</span>' +
        '<h3 class="product-name">' + esc(stripEx(p.name)) + '</h3>' +
        '<ul class="feature-list">' + feats + '</ul>' +
        (fits ? '<p class="bid-org">적합 요구 · ' + fits + '</p>' : '') +
        '<p class="product-diff"><b>차별점</b> ' + esc(p.diff) + '</p>' +
      '</article>';
    }).join('');
    observeReveals();
  }

  /* ---------- Talking points ---------- */
  var talkBids = DATA.bids.filter(function (b) { return b.talk && b.talk.length; });
  var talkState = '전체';
  function renderTalks() {
    var list = talkState === '전체' ? talkBids : talkBids.filter(function (b) { return b.category === talkState; });
    document.getElementById('talk-grid').innerHTML = list.map(function (b) {
      var prod = (b.products || []).map(stripEx).join(', ');
      function row(lbl, val) { return val ? '<div class="talk-step"><span class="lbl">' + lbl + '</span><span class="val">' + esc(val) + '</span></div>' : ''; }
      return '<article class="talk-card reveal">' +
        '<div class="talk-head"><span class="badge badge--cat">' + esc(b.category) + '</span>' +
          (prod ? '<span class="talk-prod">' + esc(prod) + '</span>' : '') + '</div>' +
        '<div class="talk-flow">' + row('고객 요구', b.need) + row('우리 강점', b.strength) + row('차별점', b.diff) + '</div>' +
        '<p class="talk-quote">' + esc(b.talk) + '</p>' +
        '<div class="talk-foot"><span class="bid-org">' + esc(b.org) + '</span>' +
          '<button class="copy-btn" type="button" data-copy="' + esc(b.talk) + '">멘트 복사</button></div>' +
      '</article>';
    }).join('');
    observeReveals();
  }
  function setupTalkFilter() {
    var cats = {};
    talkBids.forEach(function (b) { cats[b.category] = (cats[b.category] || 0) + 1; });
    var keys = ['전체'].concat(Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; }));
    var wrap = document.getElementById('talk-filter');
    wrap.innerHTML = keys.map(function (c) {
      var n = c === '전체' ? talkBids.length : cats[c];
      return '<button class="chip' + (c === '전체' ? ' chip--active' : '') + '" type="button" data-cat="' + esc(c) + '">' +
        esc(c) + '<span class="chip-n">' + n + '</span></button>';
    }).join('');
    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('.chip'); if (!btn) return;
      talkState = btn.getAttribute('data-cat');
      this.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('chip--active', c === btn); });
      renderTalks();
    });
  }

  /* ---------- copy (event delegation) ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.copy-btn'); if (!btn) return;
    var text = btn.getAttribute('data-copy') || '';
    var done = function () {
      var orig = btn.textContent;
      btn.classList.add('is-copied'); btn.textContent = '복사됨 ✓';
      setTimeout(function () { btn.classList.remove('is-copied'); btn.textContent = orig; }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else { fallbackCopy(text, done); }
  });
  function fallbackCopy(text, cb) {
    try {
      var ta = document.createElement('textarea'); ta.value = text;
      ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta);
      ta.select(); document.execCommand('copy'); document.body.removeChild(ta); cb();
    } catch (e) { /* noop */ }
  }

  /* ---------- tracking edits (event delegation) ---------- */
  // 로컬(TRACK+localStorage)만 즉시 갱신, 서버 POST는 분리
  function setTrackLocal(id, patch) {
    var t = getTrack(id);
    TRACK[id] = {
      status: patch.status != null ? patch.status : t.status,
      owner: patch.owner != null ? patch.owner : t.owner,
      memo: patch.memo != null ? patch.memo : t.memo
    };
    edited[id] = true;
    saveTrack();
  }
  // 메모/담당자 입력 디바운스: id별 타이머 + 누적 patch
  var pushTimers = {};
  var pushPatch = {};
  function debouncePush(id, patch) {
    var p = pushPatch[id] || (pushPatch[id] = {});
    if (patch.owner != null) p.owner = patch.owner;
    if (patch.memo != null) p.memo = patch.memo;
    clearTimeout(pushTimers[id]);
    pushTimers[id] = setTimeout(function () { flushPush(id); }, 500);
  }
  function flushPush(id) {
    clearTimeout(pushTimers[id]); delete pushTimers[id];
    var p = pushPatch[id]; delete pushPatch[id];
    if (p) pushToServer(id, p);
  }

  document.addEventListener('change', function (e) {
    var sel = e.target.closest('.track-status'); if (!sel) return;
    var row = sel.closest('.bid-track'); if (!row) return;
    var id = row.getAttribute('data-id');
    // status는 즉시 반영(로컬+서버)
    setTrackLocal(id, { status: sel.value });
    pushToServer(id, { status: sel.value });
    sel.setAttribute('data-v', sel.value);
    // 상태 필터가 걸려 카드가 빠져야 하면 해당 노드만 제거(전면 재렌더 회피 → 포커스 보존)
    if (state.status !== '전체' && state.status !== sel.value) {
      row.parentNode && row.parentNode.removeChild(row);
      var grid = document.getElementById('board-grid');
      var remain = grid ? grid.querySelectorAll('.bid-card').length : 0;
      var empty = document.getElementById('board-empty');
      var count = document.getElementById('board-count');
      if (empty) empty.hidden = remain > 0;
      if (count) count.textContent = remain === 0
        ? '조건에 맞는 공고가 없습니다 · 필터를 조정해 보세요'
        : '총 ' + remain + '건 (필터 적용)' +
          (state.sort === 'deadline' || urgentActive() ? ' · 마감 임박순' : ' · 점수 높은 순으로 먼저 움직이세요');
    }
    renderStatusSummary();
  });
  document.addEventListener('input', function (e) {
    var row = e.target.closest('.bid-track'); if (!row) return;
    var id = row.getAttribute('data-id');
    if (e.target.classList.contains('track-owner')) { setTrackLocal(id, { owner: e.target.value }); debouncePush(id, { owner: e.target.value }); }
    else if (e.target.classList.contains('track-memo')) { setTrackLocal(id, { memo: e.target.value }); debouncePush(id, { memo: e.target.value }); }
  });
  // blur 시 마지막 값 강제 flush + 담당자 옵션/요약 갱신
  document.addEventListener('focusout', function (e) {
    var row = e.target.closest && e.target.closest('.bid-track'); if (!row) return;
    var id = row.getAttribute('data-id');
    if (pushTimers[id] != null) flushPush(id);
    if (e.target.classList.contains('track-owner')) refreshOwnerOptions();
  });

  // 상태 요약 칩 클릭 → 상태 필터 토글
  (function () {
    var wrap = document.getElementById('status-summary');
    if (!wrap) return;
    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('.chip[data-status]'); if (!btn) return;
      var s = btn.getAttribute('data-status');
      state.status = (state.status === s) ? '전체' : s; // 같은 칩 재클릭 시 해제
      syncStatusSelect();
      renderBoard();
    });
  })();

  // KPI 'D-7 임박' 클릭 → 임박 공고만 보기 토글
  (function () {
    var kpiRow = document.getElementById('kpi-row');
    if (!kpiRow) return;
    kpiRow.addEventListener('click', function (e) {
      var btn = e.target.closest('.kpi--action[data-action="urgent"]'); if (!btn) return;
      state.urgent = !state.urgent;
      btn.setAttribute('aria-pressed', state.urgent ? 'true' : 'false');
      var sortSel = document.getElementById('board-sort');
      if (sortSel) sortSel.value = state.urgent ? 'urgent' : (state.sort === 'urgent' ? 'score' : state.sort);
      if (!state.urgent && state.sort === 'urgent') state.sort = 'score';
      renderBoard();
      var board = document.getElementById('board');
      if (board) {
        var top = board.getBoundingClientRect().top + (window.scrollY || window.pageYOffset) - headerH() - 12;
        window.scrollTo({ top: Math.max(top, 0), behavior: prefersReduced ? 'auto' : 'smooth' });
      }
    });
  })();

  /* ---------- reveal + counters observers ---------- */
  var revealObs = null;
  if (!prefersReduced && 'IntersectionObserver' in window) {
    revealObs = new IntersectionObserver(function (ents, o) {
      ents.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('is-visible'); o.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
  }
  function observeReveals() {
    var els = document.querySelectorAll('.reveal:not(.is-visible)');
    if (!revealObs) { els.forEach(function (e) { e.classList.add('is-visible'); }); return; }
    els.forEach(function (e) { revealObs.observe(e); });
  }

  function animateCount(el) {
    var target = parseFloat(el.getAttribute('data-count')); if (isNaN(target)) return;
    if (prefersReduced) { el.textContent = target.toLocaleString('ko-KR'); return; }
    var dur = 1100, start = null;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1), eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString('ko-KR');
      if (p < 1) requestAnimationFrame(step); else el.textContent = target.toLocaleString('ko-KR');
    }
    requestAnimationFrame(step);
  }
  function observeCounters() {
    var els = document.querySelectorAll('[data-count]');
    if (prefersReduced || !('IntersectionObserver' in window)) {
      els.forEach(function (e) { e.textContent = (parseFloat(e.getAttribute('data-count')) || 0).toLocaleString('ko-KR'); });
      return;
    }
    var co = new IntersectionObserver(function (ents, o) {
      ents.forEach(function (en) { if (en.isIntersecting) { animateCount(en.target); o.unobserve(en.target); } });
    }, { threshold: 0.5 });
    els.forEach(function (e) { co.observe(e); });
  }

  /* ---------- header / nav / scroll ---------- */
  var header = document.getElementById('site-header');
  var navToggle = document.getElementById('nav-toggle');
  var navLinks = [].slice.call(document.querySelectorAll('.nav-link'));
  var toTop = document.getElementById('to-top');

  function closeNav() {
    header.classList.remove('nav-open');
    if (navToggle) { navToggle.setAttribute('aria-expanded', 'false'); navToggle.setAttribute('aria-label', '메뉴 열기'); }
  }
  if (navToggle) navToggle.addEventListener('click', function () {
    var open = !header.classList.contains('nav-open');
    header.classList.toggle('nav-open', open);
    navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    navToggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  });
  navLinks.forEach(function (l) { l.addEventListener('click', closeNav); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeNav(); });

  var spy = navLinks.map(function (l) {
    var href = l.getAttribute('href') || '';
    if (href.charAt(0) !== '#' || href.length < 2) return null;
    var sec = document.getElementById(href.slice(1));
    return sec ? { link: l, sec: sec } : null;
  }).filter(Boolean);

  function headerH() { return (header && header.offsetHeight) || 64; }
  function onScrollRAF() {
    var y = window.scrollY || window.pageYOffset;
    header.classList.toggle('scrolled', y > 8);
    if (toTop) toTop.classList.toggle('is-visible', y > 500);
    var doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    doc.style.setProperty('--scroll-progress', max > 0 ? (y / max).toFixed(4) : '0');
    // scrollspy
    var probe = headerH() + 28, cur = spy.length ? spy[0].link : null;
    for (var i = 0; i < spy.length; i++) {
      if (spy[i].sec.getBoundingClientRect().top - probe <= 0) cur = spy[i].link;
    }
    if (window.innerHeight + y >= doc.scrollHeight - 4 && spy.length) cur = spy[spy.length - 1].link;
    navLinks.forEach(function (l) {
      var on = l === cur; l.classList.toggle('active', on);
      if (on) l.setAttribute('aria-current', 'true'); else l.removeAttribute('aria-current');
    });
  }
  var ticking = false;
  function onScroll() { if (ticking) return; ticking = true; requestAnimationFrame(function () { onScrollRAF(); ticking = false; }); }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', function () { if (window.innerWidth > 860) closeNav(); onScroll(); }, { passive: true });

  // smooth anchor with header offset
  [].slice.call(document.querySelectorAll('a[href^="#"]')).forEach(function (l) {
    l.addEventListener('click', function (e) {
      var href = l.getAttribute('href'); if (!href || href === '#') return;
      var target = document.getElementById(href.slice(1)); if (!target) return;
      e.preventDefault(); closeNav();
      var top = target.getBoundingClientRect().top + (window.scrollY || window.pageYOffset) - headerH() - 12;
      window.scrollTo({ top: Math.max(top, 0), behavior: prefersReduced ? 'auto' : 'smooth' });
    });
  });
  if (toTop) toTop.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: prefersReduced ? 'auto' : 'smooth' });
  });

  /* ---------- meta lines ---------- */
  function setText(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
  setText('ref-line', '오늘 기준 ' + (DATA.refDate || '—'));
  setText('src-line', '출처 ' + (DATA.source || '나라장터') + ' · 수집 ' + (DATA.generatedAt || '—'));
  setText('foot-ref', DATA.generatedAt || '—');
  setText('year', String(new Date().getFullYear()));

  /* ---------- init ---------- */
  renderKPIs();
  setupBoardControls();
  renderBoard();
  renderDist();
  renderProducts();
  setupTalkFilter();
  renderTalks();
  observeReveals();
  observeCounters();
  onScrollRAF();
  updateMode();
  syncFromServer();
})();
