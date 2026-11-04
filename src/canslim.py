"""ตัวเลขสำหรับ CAN SLIM: EPS รายไตรมาส/รายปี แนวโน้มราคา ความแข็งแรงเทียบดัชนี และทิศทางตลาด

EPS และจำนวนหุ้นมาจาก companyfacts (SEC) ส่วนราคามาจาก Yahoo Finance (แหล่งรอง ไม่เป็นทางการ)
รัน: python -m src.canslim NOW   พิมพ์ JSON ออก stdout
"""
import json
import sys
import urllib.request
from datetime import date, datetime

EPS_TAG = "EarningsPerShareDiluted"
SHARES_TAG = "WeightedAverageNumberOfDilutedSharesOutstanding"
TRADING_DAYS_YEAR = 252


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _days(r: dict) -> int:
    return (_d(r["end"]) - _d(r["start"])).days


def _rows(facts: dict, tag: str) -> list[dict]:
    units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    rows = [r for body in units.values() for r in body if "start" in r]
    # ช่วงเวลาเดียวกันอาจถูกรายงานหลายฉบับ (เช่น ปรับย้อนหลังหลังหุ้นแตก) ใช้ฉบับที่ยื่นล่าสุด
    latest: dict[tuple, dict] = {}
    for r in rows:
        key = (r["start"], r["end"])
        if key not in latest or r["filed"] > latest[key]["filed"]:
            latest[key] = r
    return list(latest.values())


def _near(rows, start, end, tol=10):
    for r in rows:
        if abs((_d(r["start"]) - start).days) <= tol and abs((_d(r["end"]) - end).days) <= tol:
            return r
    return None


def _shift_year(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # 29 ก.พ.
        return d.replace(year=d.year - 1, day=28)


def latest_quarter_eps(facts: dict) -> dict | None:
    rows = _rows(facts, EPS_TAG)
    quarters = [r for r in rows if 80 <= _days(r) <= 100]
    years = [r for r in rows if 350 <= _days(r) <= 380]
    nine = [r for r in rows if 260 <= _days(r) <= 285]
    last_q = max(quarters, key=lambda r: r["end"]) if quarters else None
    last_fy = max(years, key=lambda r: r["end"]) if years else None

    # ถ้าปีบัญชีล่าสุดจบหลังไตรมาสล่าสุดที่รายงานเดี่ยว: ไตรมาส 4 = ทั้งปี − 9 เดือน (ประมาณ)
    if last_fy and (not last_q or last_fy["end"] > last_q["end"]):
        def q4(fy):
            ytd = None
            for r in nine:
                if abs((_d(r["start"]) - _d(fy["start"])).days) <= 5 and 80 <= (_d(fy["end"]) - _d(r["end"])).days <= 100:
                    ytd = r
            return fy["val"] - ytd["val"] if ytd else None

        prior_fy = _near(years, _shift_year(_d(last_fy["start"])), _shift_year(_d(last_fy["end"])), tol=10)
        cur = q4(last_fy)
        prev = q4(prior_fy) if prior_fy else None
        if cur is None:
            return None
        return {"period_end": last_fy["end"], "eps": cur, "prior_eps": prev,
                "growth": (cur / prev - 1) if prev else None, "derived": True}

    if not last_q:
        return None
    prior = _near(quarters, _shift_year(_d(last_q["start"])), _shift_year(_d(last_q["end"])))
    prev = prior["val"] if prior else None
    return {"period_end": last_q["end"], "eps": last_q["val"], "prior_eps": prev,
            "growth": (last_q["val"] / prev - 1) if prev and prev > 0 else None, "derived": False}


def _raw_rows(facts: dict, tag: str) -> list[dict]:
    units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    return [r for body in units.values() for r in body if "start" in r]


def annual_eps(facts: dict) -> list[dict]:
    """EPS รายปี (ค่าล่าสุดที่ยื่น) และอัตราโตที่คำนวณจากตัวเลขเปรียบเทียบในเอกสารฉบับเดียวกัน

    ใช้ฉบับเดียวกันเพื่อไม่ให้ปนฐานก่อน/หลังหุ้นแตก (ปีเก่าอาจไม่ถูกปรับย้อนหลัง)
    """
    raw = [r for r in _raw_rows(facts, EPS_TAG) if 350 <= _days(r) <= 380]
    out = []
    for r in sorted(_rows(facts, EPS_TAG), key=lambda r: r["end"]):
        if not 350 <= _days(r) <= 380:
            continue
        # คู่ (ปีนี้, ปีก่อน) ที่อยู่ในเอกสารฉบับเดียวกัน เลือกฉบับที่ยื่นล่าสุดที่มีทั้งสองปี
        best = None
        for cn in raw:
            if cn["end"] != r["end"]:
                continue
            for cp in raw:
                if cp["filed"] == cn["filed"] and abs((_d(cp["end"]) - _shift_year(_d(r["end"]))).days) <= 10:
                    if best is None or cn["filed"] > best[0]["filed"]:
                        best = (cn, cp)
        growth = (best[0]["val"] / best[1]["val"] - 1) if best and best[1]["val"] and best[1]["val"] > 0 else None
        out.append({"end": r["end"], "eps": r["val"], "growth": growth})
    return out


def shares_trend(facts: dict) -> dict | None:
    rows = [r for r in _rows(facts, SHARES_TAG) if 80 <= _days(r) <= 100]
    if not rows:
        return None
    last = max(rows, key=lambda r: r["end"])
    prior = _near(rows, _shift_year(_d(last["start"])), _shift_year(_d(last["end"])))
    return {"period_end": last["end"], "latest": last["val"], "year_ago": prior["val"] if prior else None,
            "change": (last["val"] / prior["val"] - 1) if prior and prior["val"] else None}


def _ma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else None


def price_stats(closes: list[float]) -> dict:
    last = closes[-1]
    window = closes[-TRADING_DAYS_YEAR:]
    high, low = max(window), min(window)
    ma50, ma200 = _ma(closes, 50), _ma(closes, 200)
    ret = closes[-1] / closes[-TRADING_DAYS_YEAR - 1] - 1 if len(closes) > TRADING_DAYS_YEAR else None
    return {"last": last, "high_52w": high, "low_52w": low, "pct_from_high": last / high - 1,
            "ma50": ma50, "ma200": ma200,
            "above_ma50": None if ma50 is None else last > ma50,
            "above_ma200": None if ma200 is None else last > ma200,
            "ret_12m": ret}


def relative_strength(stock: list[float], index: list[float]) -> dict:
    s, i = price_stats(stock)["ret_12m"], price_stats(index)["ret_12m"]
    return {"ret_12m_stock": s, "ret_12m_index": i,
            "excess_12m": None if s is None or i is None else s - i}


def market_state(index: list[float]) -> dict:
    s = price_stats(index)
    if s["ma50"] is not None and s["ma200"] is not None:
        trend = "ขาขึ้น" if s["last"] > s["ma50"] > s["ma200"] else ("ขาลง" if s["last"] < s["ma50"] < s["ma200"] else "ผสม")
    else:
        trend = "ข้อมูลไม่พอ"
    return {**s, "trend": trend}


def fetch_daily(symbol: str, rng: str = "2y") -> list[float]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol)}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        q = json.load(resp)["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return [c for c in q if c is not None]


def build(ticker: str, raw_dir: str = "data/raw") -> dict:
    facts = json.load(open(f"{raw_dir}/{ticker}.json", encoding="utf-8"))
    stock, spx, ndx = fetch_daily(ticker), fetch_daily("^GSPC"), fetch_daily("^IXIC")
    return {
        "ticker": ticker,
        "as_of": date.today().isoformat(),
        "source_prices": "Yahoo Finance แบบไม่เป็นทางการ (แหล่งรอง) [ยังไม่ยืนยัน]",
        "C_quarter_eps": latest_quarter_eps(facts),
        "A_annual_eps": annual_eps(facts),
        "N_price": price_stats(stock),
        "S_shares": shares_trend(facts),
        "L_vs_sp500": relative_strength(stock, spx),
        "L_vs_nasdaq": relative_strength(stock, ndx),
        "M_sp500": market_state(spx),
        "M_nasdaq": market_state(ndx),
    }


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=2))
