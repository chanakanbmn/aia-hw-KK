"""ตรรกะของ dashboard: แปลงโซนจากไฟล์หลายแบบ จับคู่สถานะเป็นป้ายและสี และเลือกไฟล์ที่อนุญาตให้เสิร์ฟ"""
import json
from pathlib import Path

from src.alert import status

# กฎของผู้ใช้: โซน 3 = ซื้อ, โซน 2 = สนใจ, โซน 1 และนอกโซน = รอ
LABELS = {
    "โซน 3": ("ซื้อ", "green"),
    "โซน 2": ("สนใจ", "yellow"),
    "โซน 1": ("รอ", "red"),
    "นอกโซน": ("รอ", "red"),
}
ORDER = {"ซื้อ": 0, "สนใจ": 1, "รอ": 2, None: 3}
KEYS = ("zone3_max", "zone2_max", "zone1_max")


def label_for(st: str) -> tuple[str | None, str]:
    return LABELS.get(st, (None, "grey"))


def normalize_zones(entry: dict, base_dir: Path) -> dict | None:
    if all(k in entry for k in KEYS):
        return {k: entry[k] for k in KEYS}
    path = Path(base_dir) / entry.get("zones_file", "")
    if not entry.get("zones_file") or not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    zones = data.get("zones", {})
    if "adjusted_fcf" in zones:
        zones = zones["adjusted_fcf"]
    if all(k in zones for k in KEYS):
        return {k: zones[k] for k in KEYS}
    if "buy_max" in data and "hold_max" in data:
        # แบบ BX: ≤ buy_max = ซื้อ, ≤ hold_max = สนใจ, เกินนั้น = รอ
        return {"zone3_max": data["buy_max"], "zone2_max": data["hold_max"], "zone1_max": data["hold_max"]}
    return None


def make_row(entry: dict, zones: dict | None, price: float | None, price_date: str | None, today: str) -> dict:
    levels = {f"level{k[4]}": v for k, v in zones.items()} if zones else None  # src/alert.py ใช้ชื่อ level1-3
    st = status(price, price_date, levels, today)
    label, color = label_for(st)
    # ระยะห่างไปโซนที่ดีกว่าถัดไป (ติดลบ = ราคาต้องลงอีกกี่ %)
    target = {"รอ": "zone2_max", "สนใจ": "zone3_max"}.get(label)
    gap = zones[target] / price - 1 if target and zones and price else None
    return {
        "ticker": entry["ticker"],
        "name": entry.get("name", entry["ticker"]),
        "price": price,
        "price_date": price_date,
        "zones": zones,
        "status": st,
        "label": label,
        "color": color,
        "gap_pct": gap,
        "has_infographic": bool(entry.get("infographic")),
        "note": entry.get("note", ""),
    }


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: ORDER.get(r["label"], 3))


def resolve_path(url_path: str, watch: list[dict], base_dir: Path) -> Path | None:
    """เสิร์ฟเฉพาะ infographic ที่อยู่ใน watchlist ไม่รับ path อื่น"""
    prefix = "/infographic/"
    if not url_path.startswith(prefix):
        return None
    ticker = url_path[len(prefix):]
    for e in watch:
        if e["ticker"] == ticker and e.get("infographic"):
            p = (Path(base_dir) / e["infographic"]).resolve()
            return p if p.is_file() else None
    return None
