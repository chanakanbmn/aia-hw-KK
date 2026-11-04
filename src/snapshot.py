"""ภาพนิ่ง (snapshot) ของคำแนะนำโซนซื้อ ณ วันหนึ่ง และเปรียบเทียบกับราคาจริงภายหลัง

สร้าง:    python -m src.snapshot create
เปรียบเทียบ: python -m src.snapshot compare output/snapshots/2026-11-04.csv

snapshot เก็บเป็น CSV ที่ไม่ถูกเขียนทับ (สร้างใหม่ถ้าสมมติฐานเปลี่ยน) ไม่มีข้อมูลพอร์ตหรือต้นทุนของผู้ใช้
ราคามาจาก Yahoo Finance แบบไม่เป็นทางการ (แหล่งรอง) [ยังไม่ยืนยัน]
"""
import csv
import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from src.alert import status
from src.dashboard import make_row, normalize_zones

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "output" / "dashboard"
SNAP_DIR = ROOT / "output" / "snapshots"

FIELDS = [
    "snapshot_date", "ticker", "name", "sector", "price", "price_date",
    "zone3_max", "zone2_max", "zone1_max", "status", "label",
    "scenario_bad", "scenario_base", "scenario_good", "scenario_kind",
    "sp500", "sp500_date", "git_commit", "source",
]
NUMERIC = ("price", "zone3_max", "zone2_max", "zone1_max", "scenario_bad", "scenario_base", "scenario_good", "sp500")
SOURCE = "ราคา Yahoo Finance แบบไม่เป็นทางการ [ยังไม่ยืนยัน] · โซนจาก output/dashboard/watchlist.json"


def make_rows(entries: list[dict], prices: dict, sp500: tuple, asof: str, commit: str) -> list[dict]:
    rows = []
    for e in entries:
        price, price_date = prices.get(e["ticker"], (None, None))
        zones = e.get("_zones")
        base = make_row(e, zones, price, price_date, asof)
        sc = e.get("_scenarios") or {}
        rows.append({
            "snapshot_date": asof, "ticker": e["ticker"], "name": e.get("name", e["ticker"]),
            "sector": e.get("sector", "อื่น ๆ"),
            "price": "" if price is None else price, "price_date": price_date or "",
            "zone3_max": zones["zone3_max"] if zones else "", "zone2_max": zones["zone2_max"] if zones else "",
            "zone1_max": zones["zone1_max"] if zones else "",
            "status": base["status"], "label": base["label"] or "",
            "scenario_bad": sc.get("bad", ""), "scenario_base": sc.get("base", ""), "scenario_good": sc.get("good", ""),
            "scenario_kind": sc.get("kind", ""),
            "sp500": sp500[0], "sp500_date": sp500[1], "git_commit": commit, "source": SOURCE,
        })
    return rows


def write_snapshot(path, rows: list[dict]) -> None:
    # โหมด "x": ไม่เขียนทับไฟล์เดิม เพื่อให้ snapshot เก่าไม่ถูกแก้ภายหลัง
    with open(path, "x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _parse(row: dict) -> dict:
    out = dict(row)
    for k in NUMERIC:
        v = row.get(k)
        out[k] = float(v) if v not in (None, "") else None
    return out


def read_snapshot(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return [_parse(r) for r in csv.DictReader(f)]


def _first_at_or_below(path: list[tuple], limit):
    if limit is None:
        return None
    for d, c in path:
        if c <= limit:
            return d
    return None


def compare(snapshot: list[dict], paths: dict, index_path: list[tuple], today: str) -> list[dict]:
    results = []
    idx_now = index_path[-1][1] if index_path else None
    for s in snapshot:
        start = s["price_date"] or s["snapshot_date"]  # ราคาล่าสุดตอนทำ snapshot อาจเป็นของวันก่อนหน้า
        since = [(d, c) for d, c in paths.get(s["ticker"], []) if d >= start]
        then = s["price"]
        now = since[-1][1] if since else None
        levels = None
        if s["zone3_max"] is not None:
            levels = {"level3": s["zone3_max"], "level2": s["zone2_max"], "level1": s["zone1_max"]}  # โซนที่ล็อกไว้ ไม่คำนวณใหม่
        status_now = status(now, since[-1][0] if since else None, levels, today)
        ret = now / then - 1 if now is not None and then else None
        idx_ret = idx_now / s["sp500"] - 1 if idx_now is not None and s["sp500"] else None
        z3 = _first_at_or_below(since, s["zone3_max"])
        z2 = _first_at_or_below(since, s["zone2_max"])
        z1 = _first_at_or_below(since, s["zone1_max"])
        results.append({
            "ticker": s["ticker"], "snapshot_date": s["snapshot_date"], "today": today,
            "price_then": then, "price_now": now, "return": ret,
            "index_return": idx_ret, "excess": None if ret is None or idx_ret is None else ret - idx_ret,
            "min_price": min((c for _, c in since), default=None), "max_price": max((c for _, c in since), default=None),
            "status_then": s["status"], "status_now": status_now,
            "entered_zone3": z3 is not None, "first_zone3_date": z3,
            "entered_zone2": z2 is not None, "first_zone2_date": z2,
            "entered_zone1": z1 is not None, "first_zone1_date": z1,
            "scenario_bad": s["scenario_bad"], "scenario_base": s["scenario_base"], "scenario_good": s["scenario_good"],
            "scenario_kind": s["scenario_kind"],
        })
    return results


def _pct(v):
    return "-" if v is None else f"{v * 100:+.1f}%"


def _num(v):
    return "-" if v is None else f"{v:,.2f}"


def render_markdown(results: list[dict]) -> str:
    snap, today = results[0]["snapshot_date"], results[0]["today"]
    lines = [
        f"# เทียบคำแนะนำโซนซื้อ: snapshot {snap} กับ {today}", "",
        "ใช้โซนที่ล็อกไว้ใน snapshot ไม่คำนวณใหม่ ราคา Yahoo แหล่งรอง [ยังไม่ยืนยัน] ไม่ใช่คำแนะนำลงทุน", "",
        "| หุ้น | ราคาตอนนั้น | ราคาตอนนี้ | ผลตอบแทน | S&P 500 | ส่วนต่าง | ต่ำสุด–สูงสุด | สถานะตอนนั้น → ตอนนี้ | เข้าโซน 3 | เข้าโซน 2 |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for r in results:
        rng = f"{_num(r['min_price'])}–{_num(r['max_price'])}" if r["min_price"] is not None else "-"
        lines.append(
            f"| {r['ticker']} | {_num(r['price_then'])} | {_num(r['price_now'])} | {_pct(r['return'])} | {_pct(r['index_return'])} | "
            f"{_pct(r['excess'])} | {rng} | {r['status_then']} → {r['status_now']} | "
            f"{r['first_zone3_date'] or 'ไม่เข้า'} | {r['first_zone2_date'] or 'ไม่เข้า'} |")
    lines += ["", "ข้อควรระวัง: ช่วงสั้นและมีหุ้นไม่กี่ตัว ผลเป็นบทเรียน ไม่ใช่ข้อพิสูจน์ว่าโซนใช้ได้ ต้องเทียบกับ S&P 500 ช่วงเดียวกัน "
              "และตรวจเงื่อนไขเปลี่ยนใจในโน้ตของแต่ละหุ้นด้วยมือ (cRPO, margin, คดี ฯลฯ) ตัวเลขงบจริงที่ออกใหม่เทียบกับสามฉากที่ตั้งไว้ต้องดูเอง", ""]
    return "\n".join(lines)


def fetch_history(symbol: str, rng: str = "1y") -> list[tuple]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol)}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.load(resp)["chart"]["result"][0]
    out = [(datetime.fromtimestamp(t, timezone.utc).date().isoformat(), round(c, 4))
           for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    return sorted(out)


def scenarios_from_zones_file(entry: dict) -> dict | None:
    f = entry.get("zones_file")
    if not f:
        return None
    data = json.loads((DASH / f).read_text(encoding="utf-8"))
    sc = data.get("scenarios")
    if sc:
        keys = ("bad", "base", "good")
        if not any(k in sc for k in keys):
            return None
        return {"bad": sc.get("bad"), "base": sc.get("base"), "good": sc.get("good"), "kind": str(sc.get("note", ""))[:200]}
    if "bear" in data:  # แบบ BX
        return {"bad": data["bear"], "base": data.get("base"), "good": data.get("bull"), "kind": "มูลค่าต่อหุ้นตาม BX.md (bear/base/bull)"}
    return None


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def cmd_create() -> Path:
    stocks = json.loads((DASH / "watchlist.json").read_text(encoding="utf-8"))["stocks"]
    entries, prices = [], {}
    for e in stocks:
        entries.append({**e, "_zones": normalize_zones(e, DASH), "_scenarios": scenarios_from_zones_file(e)})
        try:
            d, c = fetch_history(e["ticker"], "5d")[-1]
            prices[e["ticker"]] = (c, d)
        except Exception:
            pass  # ดึงไม่ได้ = เว้นว่าง ไม่เดา
    sp_d, sp_c = fetch_history("^GSPC", "5d")[-1]
    asof = date.today().isoformat()
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAP_DIR / f"{asof}.csv"
    write_snapshot(path, make_rows(entries, prices, (sp_c, sp_d), asof, _git_commit()))
    return path


def cmd_compare(snapshot_path: str) -> Path:
    snap = read_snapshot(snapshot_path)
    paths = {}
    for s in snap:
        try:
            paths[s["ticker"]] = fetch_history(s["ticker"], "2y")
        except Exception:
            pass
    index = [(d, c) for d, c in fetch_history("^GSPC", "2y") if d >= (snap[0]["sp500_date"] or snap[0]["snapshot_date"])]
    today = date.today().isoformat()
    md = render_markdown(compare(snap, paths, index, today))
    out = SNAP_DIR / f"compare-{snap[0]['snapshot_date']}-to-{today}.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "create":
        print(cmd_create())
    elif len(sys.argv) >= 3 and sys.argv[1] == "compare":
        cmd_compare(sys.argv[2])
    else:
        print(__doc__)
