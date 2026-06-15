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
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
PORTAL = os.path.join(BASE, "portal")
STORE = os.path.join(BASE, "data", "tracking.json")
_lock = threading.Lock()
_VALID = {"status", "owner", "memo"}


def _load() -> dict:
    try:
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: dict) -> None:
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
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

    def do_GET(self):
        if self.path.split("?")[0] == "/api/tracking":
            with _lock:
                return self._json(200, _load())
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/tracking":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad json"})
        bid = str(payload.get("id", "")).strip()
        if not bid:
            return self._json(400, {"error": "id required"})
        with _lock:
            d = _load()
            cur = d.get(bid, {"status": "미정", "owner": "", "memo": ""})
            for k in _VALID:
                if k in payload and payload[k] is not None:
                    cur[k] = str(payload[k])[:300]
            d[bid] = cur
            _save(d)
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
