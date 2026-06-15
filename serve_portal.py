# -*- coding: utf-8 -*-
"""영업부 포털 서버 (팀 공유 모드).

portal/ 정적 파일을 서빙하면서, 공고별 영업 트래킹(상태·담당자·메모)을
data/tracking.json 에 저장하는 공유 API(/api/tracking)를 제공한다.

- GET  /api/tracking            → 전체 트래킹 맵(JSON)
- POST /api/tracking            → {"id","status?","owner?","memo?"} 병합 저장

사용:
    python serve_portal.py            # http://localhost:4571
    python serve_portal.py --port 8000

정적만 필요하면 `python -m http.server --directory portal` 로도 동작한다.
이 경우 트래킹은 서버 대신 브라우저(localStorage)에 저장된다(팀 공유 X).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

BASE = os.path.dirname(os.path.abspath(__file__))
PORTAL = os.path.join(BASE, "portal")
STORE = os.path.join(BASE, "data", "tracking.json")
_lock = threading.Lock()
_VALID = {"status", "owner", "memo"}

# ── 보안 정책 상수 ──────────────────────────────────────────
MAX_BODY = 65536           # POST 본문 상한(64KB) — 단일 요청 메모리 고갈 방지
MAX_KEYS = 1000            # tracking.json 키 개수 상한 — 무한 증식 방지
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")   # 공고번호(id) 허용 형식
VALID_STATUS = {"미정", "검토", "제안", "수주", "보류"}  # script.js STATUSES와 동일
# CSRF: 단순요청으로는 붙일 수 없는 커스텀 헤더(고정 상수). script.js pushToServer와 일치.
PORTAL_TOKEN = "portal-sales-2026"
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")   # 제어문자 제거용


class CorruptStore(Exception):
    """tracking.json 이 존재하나 파싱 불가(손상)임을 알리는 sentinel 예외."""


def _warn(*parts) -> None:
    """콘솔 경고 출력. Windows cp949 등 비UTF-8 콘솔에서 인코딩 오류가
    요청 스레드를 죽이지 않도록 방어한다(경고는 best-effort)."""
    msg = "[serve_portal] WARNING: " + " ".join(str(p) for p in parts)
    try:
        print(msg)
    except Exception:  # noqa: BLE001 - 로깅 실패가 요청 처리를 막으면 안 됨
        try:
            print(msg.encode("ascii", "replace").decode("ascii"))
        except Exception:  # noqa: BLE001
            pass


def _strip_ctrl(s: str) -> str:
    return _CTRL_RE.sub("", s)


def _load() -> dict:
    """tracking.json 로드.

    - 파일 없음(FileNotFoundError) → 정상: 빈 {} 반환.
    - 파일은 있으나 JSON 파싱/형식 오류 → 손상: 손상본을 타임스탬프 백업 후
      CorruptStore 예외를 올린다(빈 {}로 오인해 덮어쓰지 않도록).
    """
    try:
        with open(STORE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (ValueError, OSError) as e:
        # 존재하는데 읽기/파싱 실패: 손상으로 간주. 원본을 보존 백업.
        try:
            backup = "%s.corrupt.%d.json" % (STORE, int(time.time()))
            os.replace(STORE, backup)
            _warn("tracking.json 손상 감지, 백업:", backup)
        except OSError as be:
            _warn("tracking.json 손상, 백업 실패:", be)
        raise CorruptStore(str(e)) from e
    if not isinstance(data, dict):
        # 최상위가 객체가 아니면 손상으로 처리(키 병합 불가).
        try:
            backup = "%s.corrupt.%d.json" % (STORE, int(time.time()))
            os.replace(STORE, backup)
            _warn("tracking.json 형식 오류(객체 아님), 백업:", backup)
        except OSError as be:
            _warn("tracking.json 형식 오류, 백업 실패:", be)
        raise CorruptStore("top-level is not an object")
    return data


def _save(d: dict) -> None:
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    # 저장 직전 기존 정상본을 1세대 백업(.bak)으로 복사해 둔다.
    if os.path.exists(STORE):
        try:
            shutil.copy2(STORE, STORE + ".bak")
        except OSError as e:
            _warn(".bak 백업 실패(저장은 계속):", e)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _self_origin(self) -> str:
        """요청 Host 기준 자기 자신 origin(scheme://host[:port])."""
        host = self.headers.get("Host", "")
        # HTTP 평문 서버이므로 scheme 은 http 고정.
        return "http://" + host if host else ""

    def _csrf_ok(self) -> bool:
        """동일 출처 검증: Origin 우선, 없으면 Referer 의 scheme+host 로 대조."""
        mine = self._self_origin()
        origin = self.headers.get("Origin")
        if origin:
            return bool(mine) and origin == mine
        referer = self.headers.get("Referer")
        if referer:
            r = urlsplit(referer)
            return bool(mine) and ("%s://%s" % (r.scheme, r.netloc)) == mine
        # Origin/Referer 둘 다 없음 → 토큰 검증에 의존(아래 do_POST).
        return True

    def do_GET(self):
        if self.path.split("?")[0] == "/api/tracking":
            with _lock:
                try:
                    return self._json(200, _load())
                except CorruptStore:
                    return self._json(
                        503, {"error": "tracking store corrupt; restore from backup"}
                    )
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/tracking":
            return self.send_error(404)

        # ── CSRF 방어 ──────────────────────────────────────
        # (1) 동일 출처 검증(Origin/Referer).
        if not self._csrf_ok():
            return self._json(403, {"error": "cross-origin forbidden"})
        # (2) 커스텀 헤더 강제(단순요청으로는 못 붙음).
        if self.headers.get("X-Portal-Token") != PORTAL_TOKEN:
            return self._json(403, {"error": "missing or invalid token"})
        # (3) 비단순요청 강제: JSON Content-Type 만 허용.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self._json(415, {"error": "content-type must be application/json"})

        # ── 본문 크기 제한(DoS 방어) ─────────────────────────
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            return self._json(400, {"error": "bad content-length"})
        if n > MAX_BODY:
            return self._json(413, {"error": "payload too large"})
        raw = self.rfile.read(min(n, MAX_BODY + 1)) if n > 0 else b"{}"
        if len(raw) > MAX_BODY:
            return self._json(413, {"error": "payload too large"})

        # ── 파싱 + 타입 검증 ────────────────────────────────
        try:
            payload = json.loads(raw or b"{}")
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "bad json"})
        if not isinstance(payload, dict):
            return self._json(400, {"error": "object required"})

        # ── id 형식 검증 ────────────────────────────────────
        bid = str(payload.get("id", "")).strip()
        if not ID_RE.match(bid):
            return self._json(400, {"error": "invalid id"})

        # ── 필드별 검증/정규화 ──────────────────────────────
        if "status" in payload and payload["status"] is not None:
            if str(payload["status"]) not in VALID_STATUS:
                return self._json(400, {"error": "invalid status"})
        _LIMITS = {"owner": 20, "memo": 200}

        with _lock:
            try:
                d = _load()
            except CorruptStore:
                # 손상 시 절대 _save 로 덮어쓰지 않는다.
                _warn("POST 거부: tracking.json 손상 상태")
                return self._json(
                    503, {"error": "tracking store corrupt; restore from backup"}
                )
            # 신규 키인데 개수 상한 초과면 거부.
            if bid not in d and len(d) >= MAX_KEYS:
                return self._json(400, {"error": "too many tracked items"})
            cur = d.get(bid, {"status": "미정", "owner": "", "memo": ""})
            for k in _VALID:
                if k in payload and payload[k] is not None:
                    val = str(payload[k])
                    if k in _LIMITS:
                        val = _strip_ctrl(val)[: _LIMITS[k]]
                    cur[k] = val
            d[bid] = cur
            try:
                _save(d)
            except OSError as e:
                _warn("저장 실패:", e)
                return self._json(500, {"error": "save failed"})
            return self._json(200, {"ok": True, "id": bid, "record": cur})

    def log_message(self, *args):  # 콘솔 소음 억제
        return


def main() -> None:
    ap = argparse.ArgumentParser(description="영업부 포털 (팀 공유) 서버")
    ap.add_argument("--port", type=int, default=4571)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    handler = partial(Handler, directory=PORTAL)
    srv = ThreadingHTTPServer((args.host, args.port), handler)
    print("영업부 포털(팀 공유) → http://%s:%d" % (args.host, args.port))
    print("트래킹 저장 위치:", STORE)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
