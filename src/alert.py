"""สถานะ alert: ราคาล่าสุดอยู่ในโซนซื้อระดับไหน"""
from datetime import datetime

STALE_DAYS = 7


def status(latest_price: float | None, price_date: str | None, zone_prices: dict | None, today: str) -> str:
    if latest_price is None or price_date is None:
        return "ไม่มีราคา"
    age = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(price_date, "%Y-%m-%d")).days
    if age > STALE_DAYS:
        return "ราคาเก่า"
    if not zone_prices:
        return "ไม่มีโซน"
    for level, label in (("level3", "โซน 3"), ("level2", "โซน 2"), ("level1", "โซน 1")):
        if latest_price <= zone_prices[level]:
            return label
    return "นอกโซน"
