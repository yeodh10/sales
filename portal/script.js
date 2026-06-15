/* =============================================================================
   보안 영업부 · 코파일럿 포털 — vanilla JS
   데이터: window.PORTAL_DATA (data.js)
   스코어링: sales/scoring.py 로직을 그대로 이식 (적합도 + 카테고리 가중 + 마감 임박도)
   ========================================================================== */
(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DATA = window.PORTAL_DATA || { bids: [], products: [], total: 0, refDate: '2026-06-15' };

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function stripEx(s) { return String(s || '').replace(/^\(예시\)\s*/, ''); }
  function parseDate(s) {
    if (!s) return null;
    var m = String(s).match(/(\d{4})-(\d{2})-(\d{2})/);
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
      { n: soon, label: 'D-7 임박', foot: '영업대상·연관기회' }
    ];
    document.getElementById('kpi-row').innerHTML = items.map(function (k) {
      return '<div class="kpi" role="listitem"><div class="kpi-num">' +
        '<span class="' + (k.grad ? 'grad' : '') + '" data-count="' + k.n + '">0</span></div>' +
        '<div class="kpi-label">' + esc(k.label) + '</div>' +
        '<div class="kpi-foot">' + esc(k.foot) + '</div></div>';
    }).join('');
  }

  /* ---------- Board ---------- */
  var boardBids = DATA.bids.filter(function (b) { return b.grade !== '제외'; });
  var state = { grade: '전체', category: '전체', q: '', sort: 'score', status: '전체' };

  /* ---------- tracking (localStorage: 영업 상태·담당자·메모) ---------- */
  var TRACK_KEY = 'salesportal.tracking.v1';
  var STATUSES = ['미정', '검토', '제안', '수주', '보류'];
  var TRACK = (function () { try { return JSON.parse(localStorage.getItem(TRACK_KEY)) || {}; } catch (e) { return {}; } })();
  function saveTrack() { try { localStorage.setItem(TRACK_KEY, JSON.stringify(TRACK)); } catch (e) {} }
  function getTrack(id) { return TRACK[id] || { status: '미정', owner: '', memo: '' }; }
  function setTrack(id, patch) {
    var t = getTrack(id);
    TRACK[id] = {
      status: patch.status != null ? patch.status : t.status,
      owner: patch.owner != null ? patch.owner : t.owner,
      memo: patch.memo != null ? patch.memo : t.memo
    };
    saveTrack();
  }
  function trackRowHTML(id) {
    var t = getTrack(id);
    var opts = STATUSES.map(function (s) {
      return '<option value="' + s + '"' + (s === t.status ? ' selected' : '') + '>' + s + '</option>';
    }).join('');
    return '<div class="bid-track" data-id="' + esc(id) + '">' +
      '<select class="track-status" data-v="' + esc(t.status) + '" aria-label="영업 상태">' + opts + '</select>' +
      '<input class="track-owner" type="text" value="' + esc(t.owner) + '" placeholder="담당자" aria-label="담당자" autocomplete="off" maxlength="20">' +
      '<input class="track-memo" type="text" value="' + esc(t.memo) + '" placeholder="메모" aria-label="메모" autocomplete="off" maxlength="200">' +
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

    var copyBtn = note ? '<button class="copy-btn" type="button" data-copy="' + esc(note) + '">멘트 복사</button>' : '<span></span>';

    return '<article class="bid-card reveal">' +
      '<div class="bid-top">' +
        '<div class="bid-score score--' + s.tier.cls + '"><span class="num">' + s.score + '</span><small>' + s.tier.label + '</small></div>' +
        '<div class="bid-headings">' +
          '<div class="bid-badges">' +
            '<span class="badge badge--' + gradeCls(b.grade) + '">' + esc(b.grade) + '</span>' +
            '<span class="badge badge--cat">' + esc(b.category) + '</span>' +
          '</div>' +
          '<h3 class="bid-title"><a href="' + esc(b.url) + '" target="_blank" rel="noopener noreferrer">' + esc(b.name) + ' <span class="sr-only">(새 탭에서 열림)</span></a></h3>' +
          '<p class="bid-org">' + esc(b.org) + (b.type ? ' · ' + esc(b.type) : '') + '</p>' +
        '</div>' +
      '</div>' +
      '<div class="bid-deadline">마감 <span class="dday dday--' + dd.cls + '">' + dd.label + '</span> <span class="dl-date">' + fmtDate(b.deadline) + '</span></div>' +
      body +
      '<div class="bid-foot">' +
        '<a class="bid-link" href="' + esc(b.url) + '" target="_blank" rel="noopener noreferrer">공고 보기 →</a>' +
        copyBtn +
      '</div>' +
      trackRowHTML(b.id) +
    '</article>';
  }

  function filteredBoard() {
    var q = state.q.trim().toLowerCase();
    var list = boardBids.filter(function (b) {
      if (state.grade !== '전체' && b.grade !== state.grade) return false;
      if (state.category !== '전체' && b.category !== state.category) return false;
      if (state.status !== '전체' && getTrack(b.id).status !== state.status) return false;
      if (q && (b.name + ' ' + b.org).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    list.sort(function (a, c) {
      if (state.sort === 'deadline') {
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

  function renderBoard() {
    var list = filteredBoard();
    var grid = document.getElementById('board-grid');
    var empty = document.getElementById('board-empty');
    var count = document.getElementById('board-count');
    grid.innerHTML = list.map(bidCardHTML).join('');
    empty.hidden = list.length > 0;
    count.textContent = '총 ' + list.length + '건' +
      (state.grade !== '전체' || state.category !== '전체' || state.q ? ' (필터 적용)' : '') +
      ' · 점수 높은 순으로 먼저 움직이세요';
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

    // events
    document.getElementById('grade-filter').addEventListener('click', function (e) {
      var btn = e.target.closest('.chip'); if (!btn) return;
      state.grade = btn.getAttribute('data-grade');
      this.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('chip--active', c === btn); });
      renderBoard();
    });
    sel.addEventListener('change', function () { state.category = this.value; renderBoard(); });
    document.getElementById('board-sort').addEventListener('change', function () { state.sort = this.value; renderBoard(); });
    document.getElementById('board-status').addEventListener('change', function () { state.status = this.value; renderBoard(); });
    var si = document.getElementById('board-search');
    var t;
    si.addEventListener('input', function () {
      clearTimeout(t); var v = this.value; t = setTimeout(function () { state.q = v; renderBoard(); }, 160);
    });
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
  document.addEventListener('change', function (e) {
    var sel = e.target.closest('.track-status'); if (!sel) return;
    var row = sel.closest('.bid-track'); if (!row) return;
    setTrack(row.getAttribute('data-id'), { status: sel.value });
    sel.setAttribute('data-v', sel.value);
    if (state.status !== '전체') renderBoard();
  });
  document.addEventListener('input', function (e) {
    var row = e.target.closest('.bid-track'); if (!row) return;
    var id = row.getAttribute('data-id');
    if (e.target.classList.contains('track-owner')) setTrack(id, { owner: e.target.value });
    else if (e.target.classList.contains('track-memo')) setTrack(id, { memo: e.target.value });
  });

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
})();
