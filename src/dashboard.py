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


ZONE_KEYS = {"โซน 3": "z3", "โซน 2": "z2", "โซน 1": "z1", "นอกโซน": "out"}


def zone_key_for(st: str) -> str:
    """คีย์สีพื้นหลัง: z3 เขียว, z2 เหลือง, z1 ส้ม, out แดง, none เทา"""
    return ZONE_KEYS.get(st, "none")


def spark_change(closes: list[float]) -> float | None:
    if len(closes) < 2 or not closes[0]:
        return None
    return closes[-1] / closes[0] - 1


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


def make_row(entry: dict, zones: dict | None, price: float | None, price_date: str | None, today: str,
             spark: list[float] | None = None) -> dict:
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
        "zone_key": zone_key_for(st),
        "spark": spark or [],
        "spark_change": spark_change(spark or []),
        "gap_pct": gap,
        "sector": entry.get("sector", "อื่น ๆ"),
        "has_infographic": bool(entry.get("infographic")),
        "note": entry.get("note", ""),
    }


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: ORDER.get(r["label"], 3))


def group_rows(rows: list[dict]) -> list[dict]:
    """จัดเป็นกลุ่มตาม sector เรียง sector ตามลำดับที่ปรากฏก่อน และเรียงหุ้นในกลุ่มตามป้าย"""
    order: list[str] = []
    by_sector: dict[str, list[dict]] = {}
    for r in rows:
        sec = r.get("sector", "อื่น ๆ")
        if sec not in by_sector:
            order.append(sec)
            by_sector[sec] = []
        by_sector[sec].append(r)
    groups = []
    for sec in order:
        members = sort_rows(by_sector[sec])
        counts = {"ซื้อ": 0, "สนใจ": 0, "รอ": 0, "ไม่มีข้อมูล": 0}
        for r in members:
            counts[r["label"] or "ไม่มีข้อมูล"] += 1
        groups.append({"sector": sec, "rows": members, "counts": counts})
    return groups


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
