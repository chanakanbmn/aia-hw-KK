"""สร้าง output/watchlist.html และ output/data.csv จากงบ SEC และ data/prices.csv"""
import csv
import html
import json
import os
from datetime import date

from src.alert import status
from src.edgar import shares_outstanding, ttm_metrics
from src.zones import buy_zones, history_multiples, multiples, zones_to_price


def _read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _row(ticker: str, raw_dir: str, prices: list[dict], today: str) -> dict:
    row = {"ticker": ticker, "status": None, "source_urls": []}
    prices = sorted(prices, key=lambda r: r["date"])
    latest = prices[-1] if prices else None
    row["price"] = float(latest["close"]) if latest else None
    row["price_date"] = latest["date"] if latest else None
    if latest:
        row["source_urls"].append(latest["source_url"])

    path = os.path.join(raw_dir, f"{ticker}.json")
    facts = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    zone_prices = None
    if facts:
        m = ttm_metrics(facts, as_of=today)
        row.update({k: m[k] for k in ("fcf_after_sbc", "revenue_growth_yoy")})
        row["source_urls"].insert(0, m["source_url"])
        shares = shares_outstanding(facts)
        if shares and row["price"] is not None:
            cur = multiples(row["price"], shares, m)
            row.update(cur)
            hist = history_multiples(facts, [(p["date"], float(p["close"])) for p in prices], shares, cur["basis"])
            zones = buy_zones(hist)
            if zones:
                zone_prices = zones_to_price(zones, m, shares, cur["basis"])
                row.update({f"zone_{k}": v for k, v in zone_prices.items()})
    row["status"] = status(row["price"], row["price_date"], zone_prices, today)
    return row


def _fmt(v, nd=2):
    return "-" if v is None else f"{v:,.{nd}f}"


COLS = [
    ("ticker", "หุ้น"), ("fcf_after_sbc", "FCF หลังหัก SBC"), ("revenue_growth_yoy", "โตเทียบปีก่อน"),
    ("ev_fcf", "EV/FCF"), ("ev_sales", "EV/Sales"), ("basis", "ใช้ตัววัด"),
    ("zone_level1", "โซน 1 (ราคา)"), ("zone_level2", "โซน 2"), ("zone_level3", "โซน 3"),
    ("price", "ราคาล่าสุด"), ("price_date", "วันที่ราคา"), ("status", "สถานะ"),
]


def build(tickers_csv: str, prices_csv: str, out_dir: str, raw_dir: str = "data/raw", today: str | None = None) -> None:
    today = today or date.today().isoformat()
    prices = _read_csv(prices_csv) if os.path.exists(prices_csv) else []
    rows = []
    for t in _read_csv(tickers_csv):
        tk = t["ticker"]
        rows.append(_row(tk, raw_dir, [p for p in prices if p["ticker"] == tk], today))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "data.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([c for c, _ in COLS] + ["source_urls"])
        for r in rows:
            w.writerow([r.get(c) for c, _ in COLS] + [" | ".join(r["source_urls"])])

    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in COLS) + "<th>ที่มา</th>"
    body = []
    for r in rows:
        cells = []
        for c, _ in COLS:
            v = r.get(c)
            if c == "revenue_growth_yoy" and v is not None:
                cells.append(f"<td>{v:.1%}</td>")
            elif isinstance(v, float):
                cells.append(f"<td>{_fmt(v)}</td>")
            else:
                cells.append(f"<td>{html.escape(str(v)) if v is not None else '-'}</td>")
        links = " ".join(f'<a href="{html.escape(u)}">[{i + 1}]</a>' for i, u in enumerate(r["source_urls"])) or "-"
        body.append(f'<tr data-ticker="{html.escape(r["ticker"])}">{"".join(cells)}<td>{links}</td></tr>')
    page = f"""<!doctype html><html lang="th"><meta charset="utf-8"><title>Watchlist โซนซื้อ</title>
<style>body{{font-family:sans-serif;margin:2rem}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:right}}</style>
<h1>Watchlist โซนซื้อ (หุ้นซอฟต์แวร์/ไซเบอร์)</h1>
<p>สร้างเมื่อ {today} · ราคาที่ยังไม่เช็กกับแหล่งสด [ยังไม่ยืนยัน]</p>
<table><tr>{head}</tr>{"".join(body)}</table>
<h2>วิธีคำนวณและข้อจำกัด</h2>
<ul>
<li>FCF = เงินสดจากการดำเนินงาน − capex − ค่าหุ้นพนักงาน (SBC) แบบ 12 เดือนย้อนหลัง จากงบใน SEC EDGAR</li>
<li>โซนซื้อ = multiple ล่างสุด 25% / 15% / 5% ของช่วงราคาที่ใส่ไว้ ใช้จำนวนหุ้นล่าสุดกับราคาย้อนหลังทุกจุด และงบที่งวดจบก่อนวันนั้น (ประมาณการ)</li>
<li>หุ้นที่ FCF ติดลบใช้ EV/Sales แทน (ดูคอลัมน์ "ใช้ตัววัด")</li>
</ul></html>"""
    with open(os.path.join(out_dir, "watchlist.html"), "w", encoding="utf-8") as f:
        f.write(page)
