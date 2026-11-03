"""dashboard หุ้นที่สนใจ: ราคาปัจจุบันเทียบโซน พร้อมป้าย ซื้อ/สนใจ/รอ

รัน (จากโฟลเดอร์ repo): python -I output/dashboard/server.py  แล้วเปิด http://127.0.0.1:8770
ฟังเฉพาะ 127.0.0.1 ไม่มี token ข้อมูลที่ออกจากเครื่องมีแค่คำขอราคาไป Yahoo Finance (แบบไม่เป็นทางการ)
"""
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # ราก repo เพื่อ import src/
from src.dashboard import group_rows, make_row, normalize_zones, resolve_path  # noqa: E402

PORT = 8770
CACHE_SECONDS = 60
_cache = {"at": 0.0, "rows": None}


def load_watch() -> list[dict]:
    return json.loads((HERE / "watchlist.json").read_text(encoding="utf-8"))["stocks"]


def fetch_price(ticker: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=3mo"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.load(resp)["chart"]["result"][0]
    meta = result["meta"]
    day = datetime.fromtimestamp(meta["regularMarketTime"], timezone.utc).date().isoformat()
    closes = [round(c, 2) for c in result["indicators"]["quote"][0]["close"] if c is not None]  # ราคาปิดรายวัน 3 เดือน
    return float(meta["regularMarketPrice"]), day, closes


def get_rows() -> list[dict]:
    if _cache["rows"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
        return _cache["rows"]
    rows = []
    for e in load_watch():
        try:
            price, day, closes = fetch_price(e["ticker"])
        except Exception:
            price, day, closes = None, None, []  # ดึงไม่ได้ = สีเทา ไม่เดา
        rows.append(make_row(e, normalize_zones(e, HERE), price, day, date.today().isoformat(), spark=closes))
    _cache.update(at=time.time(), rows=rows)
    return _cache["rows"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/rows":
            rows = get_rows()
            body = {"rows": rows, "groups": group_rows(rows), "fetched": datetime.now().strftime("%Y-%m-%d %H:%M")}
            self._send(200, json.dumps(body, ensure_ascii=False), "application/json; charset=utf-8")
        else:
            f = resolve_path(path, load_watch(), HERE)
            if f:
                self._send(200, f.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"dashboard: http://127.0.0.1:{PORT}  (กด Ctrl+C เพื่อหยุด)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
