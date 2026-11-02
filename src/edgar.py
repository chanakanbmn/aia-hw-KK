"""ดึงงบจาก SEC EDGAR (companyfacts) และคำนวณตัวเลข 12 เดือนย้อนหลัง (TTM)"""
import os
from datetime import date, datetime

import requests

FORMS = ("10-K", "10-Q")

OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities"]
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
SBC_TAGS = ["ShareBasedCompensation"]
REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
]
CASH_TAGS = ["CashAndCashEquivalentsAtCarryingValue"]
DEBT_TAGS = ["LongTermDebt", "LongTermDebtNoncurrent", "ConvertibleNotesPayableNoncurrent"]


def fetch_companyfacts(cik: str) -> dict:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError(
            "ต้องตั้งตัวแปร SEC_USER_AGENT (ชื่อและอีเมลติดต่อตามที่ SEC กำหนด) ก่อนดึงข้อมูล"
        )
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
    resp = requests.get(url, headers={"User-Agent": ua}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _rows(facts: dict, tags: list[str]) -> list[dict]:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        rows = [r for r in gaap.get(tag, {}).get("units", {}).get("USD", []) if r.get("form") in FORMS]
        if rows:
            return rows
    return []


def _near(rows: list[dict], start: date, end: date, days: int = 10):
    for r in rows:
        if "start" in r and abs((_d(r["start"]) - start).days) <= days and abs((_d(r["end"]) - end).days) <= days:
            return r
    return None


def _latest_period(rows: list[dict]):
    """รายการล่าสุดที่ไม่ใช่ไตรมาสเดี่ยวซ้อนอยู่ใน YTD: จบล่าสุด และระยะยาวที่สุด"""
    flows = [r for r in rows if "start" in r]
    if not flows:
        return None
    return max(flows, key=lambda r: (r["end"], (_d(r["end"]) - _d(r["start"])).days))


def _ttm(rows: list[dict], latest) -> int | None:
    if not rows or latest is None:
        return None
    start, end = _d(latest["start"]), _d(latest["end"])
    if (end - start).days >= 350:
        return latest["val"]
    prior_start = start.replace(year=start.year - 1)
    prior_end = end.replace(year=end.year - 1)
    prior = _near(rows, prior_start, prior_end)
    fy_end_guess = start  # ปีบัญชีเต็มที่จบก่อนงวดสะสมปัจจุบันเริ่ม
    fy = None
    for r in rows:
        if "start" in r and (_d(r["end"]) - _d(r["start"])).days >= 350 and abs((_d(r["end"]) - fy_end_guess).days) <= 10 + 1:
            fy = r
    if prior is None or fy is None:
        return None
    return fy["val"] + latest["val"] - prior["val"]


def _instant(facts: dict, tags: list[str]):
    rows = _rows(facts, tags)
    if not rows:
        return None
    return max(rows, key=lambda r: r["end"])["val"]


def _cut(facts: dict, cutoff: str) -> dict:
    """สำเนา facts ที่เหลือเฉพาะรายการที่งวดจบ ณ หรือก่อนวัน cutoff"""
    gaap = {
        tag: {"units": {u: [r for r in rows if r["end"] <= cutoff] for u, rows in body.get("units", {}).items()}}
        for tag, body in facts.get("facts", {}).get("us-gaap", {}).items()
    }
    return {**facts, "facts": {**facts.get("facts", {}), "us-gaap": gaap}}


def shares_outstanding(facts: dict):
    rows = [
        r
        for r in facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    ]
    if rows:
        return max(rows, key=lambda r: r["end"])["val"]
    # บริษัทหลายคลาสหุ้นไม่มีค่ารวมใน dei ใช้ค่าเฉลี่ยถ่วงน้ำหนักแบบ diluted ของงวดล่าสุดแทน
    w = facts.get("facts", {}).get("us-gaap", {}).get("WeightedAverageNumberOfDilutedSharesOutstanding", {}).get("units", {}).get("shares", [])
    w = [r for r in w if r.get("form") in FORMS]
    return max(w, key=lambda r: r["end"])["val"] if w else None


def ttm_metrics(facts: dict, as_of: str | None = None, cutoff: str | None = None) -> dict:
    if cutoff:
        facts = _cut(facts, cutoff)
    ocf_rows = _rows(facts, OCF_TAGS)
    latest = _latest_period(ocf_rows)

    def ttm(tags):
        # ใช้งวดล่าสุดเดียวกับ OCF เพื่อให้ตัวเลขเทียบกันได้ ลอง tag ถัดไปถ้า tag แรกไม่มีงวดนี้
        for tag in tags:
            rows = _rows(facts, [tag])
            match = _near(rows, _d(latest["start"]), _d(latest["end"])) if latest and rows else None
            v = _ttm(rows, match)
            if v is not None:
                return v
        return None

    ocf, capex, sbc, revenue = ttm(OCF_TAGS), ttm(CAPEX_TAGS), ttm(SBC_TAGS), ttm(REVENUE_TAGS)

    fcf = None
    if None not in (ocf, capex, sbc):
        fcf = ocf - capex - sbc

    # โตเทียบงวดเดียวกันของปีก่อน (YTD ปีนี้ / YTD ปีก่อน) ไม่ใช่ TTM ต่อ TTM
    growth = None
    for tag in REVENUE_TAGS if latest else []:
        rev_rows = _rows(facts, [tag])
        cur = _near(rev_rows, _d(latest["start"]), _d(latest["end"])) if rev_rows else None
        prev = _near(
            rev_rows,
            _d(latest["start"]).replace(year=_d(latest["start"]).year - 1),
            _d(latest["end"]).replace(year=_d(latest["end"]).year - 1),
        ) if cur else None
        if cur and prev and prev["val"]:
            growth = cur["val"] / prev["val"] - 1
            break

    cik = facts.get("cik")
    return {
        "ocf": ocf,
        "capex": capex,
        "sbc": sbc,
        "fcf_after_sbc": fcf,
        "revenue": revenue,
        "revenue_growth_yoy": growth,
        "cash": _instant(facts, CASH_TAGS),
        "debt": _instant(facts, DEBT_TAGS),
        "period_end": latest["end"] if latest else None,
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json" if cik is not None else None,
        "as_of": as_of or date.today().isoformat(),
    }
