"""ดึง companyfacts ของทุกตัวใน data/tickers.csv ลง data/raw/<TICKER>.json

ต้องตั้ง SEC_USER_AGENT ก่อน (ชื่อและอีเมลติดต่อตามที่ SEC กำหนด)
ถ้าคอลัมน์ cik ว่าง จะหาจากไฟล์ company_tickers.json ของ SEC
"""
import csv
import json
import os

import requests

from src.edgar import fetch_companyfacts


def _lookup_ciks(tickers: list[str]) -> dict[str, str]:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError("ต้องตั้งตัวแปร SEC_USER_AGENT ก่อนดึงข้อมูล")
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": ua}, timeout=30)
    r.raise_for_status()
    table = {v["ticker"].upper(): str(v["cik_str"]) for v in r.json().values()}
    return {t: table[t] for t in tickers if t in table}


def main(tickers_csv: str = "data/tickers.csv", raw_dir: str = "data/raw") -> None:
    with open(tickers_csv, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    missing = [r["ticker"] for r in rows if not r["cik"]]
    found = _lookup_ciks(missing) if missing else {}
    os.makedirs(raw_dir, exist_ok=True)
    for r in rows:
        cik = r["cik"] or found.get(r["ticker"])
        if not cik:
            print(f"ไม่พบ CIK ของ {r['ticker']} ข้าม")
            continue
        facts = fetch_companyfacts(cik)
        with open(os.path.join(raw_dir, f"{r['ticker']}.json"), "w", encoding="utf-8") as out:
            json.dump(facts, out)
        print(f"ดึง {r['ticker']} (CIK {cik}) แล้ว")


if __name__ == "__main__":
    main()
