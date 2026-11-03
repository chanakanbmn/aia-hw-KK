"""เซิร์ฟเวอร์ ticker ในเครื่อง: เสิร์ฟ ticker.html และ /api/price (ดึงราคาจาก Yahoo Finance แบบไม่เป็นทางการ)

รัน: python -I server.py (ในโฟลเดอร์ ticker/)  แล้วเปิด http://127.0.0.1:8768
"""
import json
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
PORT = 8768
CACHE_SECONDS = 30
_cache = {"at": 0.0, "data": None}


def load_zones():
    return json.loads((HERE / "zones.json").read_text(encoding="utf-8"))


def fetch_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        meta = json.load(resp)["chart"]["result"][0]["meta"]
    return {
        "ticker": ticker,
        "price": meta["regularMarketPrice"],
        "prev_close": meta.get("chartPreviousClose"),
        "high_52w": meta.get("fiftyTwoWeekHigh"),
        "low_52w": meta.get("fiftyTwoWeekLow"),
        "market_time": meta.get("regularMarketTime"),
        "source": "Yahoo Finance (ไม่เป็นทางการ) [ยังไม่ยืนยัน]",
        "fetched_at": int(time.time()),
    }


def get_price():
    now = time.time()
    if _cache["data"] is None or now - _cache["at"] > CACHE_SECONDS:
        _cache["data"] = fetch_price(load_zones()["ticker"])
        _cache["at"] = now
    return _cache["data"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "ticker.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/zones":
            self._send(200, json.dumps(load_zones(), ensure_ascii=False).encode(), "application/json")
        elif self.path == "/api/price":
            try:
                self._send(200, json.dumps(get_price()).encode(), "application/json")
            except Exception as exc:  # ส่งข้อผิดพลาดจริงให้หน้าเว็บแสดง ไม่เงียบ
                self._send(502, json.dumps({"error": str(exc)}).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"ticker: http://127.0.0.1:{PORT}  (กด Ctrl+C เพื่อหยุด)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
