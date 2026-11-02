"""คำนวณ EV/FCF, EV/Sales และโซนซื้อจากช่วง multiple ในอดีตของหุ้นตัวเอง"""
import statistics

from src.edgar import ttm_metrics

MIN_HISTORY = 8  # ไตรมาส ต่ำกว่านี้ไม่ตั้งโซน
PERCENTILES = {"level1": 25, "level2": 15, "level3": 5}


def _ev(price: float, shares: float, m: dict) -> float:
    # ถ้าไม่พบเงินสดหรือหนี้ใน XBRL ให้ถือว่า 0 (บริษัทที่ไม่มีหนี้มักไม่มี tag นี้)
    return price * shares + (m.get("debt") or 0) - (m.get("cash") or 0)


def multiples(price: float, shares: float, m: dict) -> dict:
    ev = _ev(price, shares, m)
    fcf, rev = m.get("fcf_after_sbc"), m.get("revenue")
    ev_fcf = ev / fcf if fcf and fcf > 0 else None
    ev_sales = ev / rev if rev and rev > 0 else None
    return {"ev_fcf": ev_fcf, "ev_sales": ev_sales, "basis": "ev_fcf" if ev_fcf is not None else "ev_sales"}


def buy_zones(history: list[float]) -> dict | None:
    if len(history) < MIN_HISTORY:
        return None
    cuts = statistics.quantiles(history, n=100, method="inclusive")
    return {k: cuts[p - 1] for k, p in PERCENTILES.items()}


def zones_to_price(zones: dict, m: dict, shares: float, basis: str) -> dict:
    denom = m["fcf_after_sbc"] if basis == "ev_fcf" else m["revenue"]
    adj = (m.get("debt") or 0) - (m.get("cash") or 0)
    return {k: (mult * denom - adj) / shares for k, mult in zones.items()}


def history_multiples(facts: dict, prices: list[tuple[str, float]], shares: float, basis: str) -> list[float]:
    """multiple ณ แต่ละวันที่มีราคา โดยใช้งบที่งวดจบก่อนวันนั้น ข้ามจุดที่คำนวณไม่ได้"""
    out = []
    for day, close in prices:
        m = ttm_metrics(facts, cutoff=day)
        if m["period_end"] is None:
            continue
        v = multiples(close, shares, m)[basis]
        if v is not None:
            out.append(v)
    return out
