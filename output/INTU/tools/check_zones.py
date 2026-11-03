"""ตรวจซ้ำโซนและมัลติเพิลฉากของ INTU ให้ตรงกับ zones.json / INTU.md

รัน: "D:/Let's go/.venv/Scripts/python.exe" -I output/INTU/tools/check_zones.py
ใช้ src/edgar.py และ src/zones.py ของ repo (กฎ watchlist) กับ data/raw/INTU.json และ data/prices.csv
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src import zones as Z  # noqa: E402
from src.edgar import shares_outstanding, ttm_metrics  # noqa: E402

facts = json.loads((ROOT / "data/raw/INTU.json").read_text(encoding="utf-8"))
m = ttm_metrics(facts)
sh = shares_outstanding(facts)
prices = [(r["date"], float(r["close"])) for r in csv.DictReader(open(ROOT / "data/prices.csv", encoding="utf-8")) if r["ticker"] == "INTU"]
hist = Z.history_multiples(facts, prices, sh, "ev_fcf")
mult = Z.buy_zones(hist)
rep = Z.zones_to_price(mult, m, sh, "ev_fcf")
# ฐานปรับภาษี: FCF หลังหัก SBC 4,842 = 8,617 - (2,000 - 281) - 2,056  (2,000 = ประมาณการภาษีเงินสด FY2027 ของบริษัท)
fcf = m["ocf"] / 1e6 - m["capex"] / 1e6 - 46 - (2000 - 281) - m["sbc"] / 1e6  # 46 = capitalized software FY2026
adj = Z.zones_to_price(mult, {**m, "fcf_after_sbc": fcf * 1e6}, sh, "ev_fcf")
zj = json.loads((ROOT / "output/INTU/ticker/zones.json").read_text(encoding="utf-8"))["zones"]
print(f"หุ้น {sh:,.0f} · มัลติเพิลโซน1/2/3 = {mult['level1']:.2f}/{mult['level2']:.2f}/{mult['level3']:.2f} · ประวัติ {len(hist)} จุด ช่วง {min(hist):.1f}-{max(hist):.1f}")
ok = True
for name, got, key in (("reported", rep, "reported_fcf"), ("adjusted", adj, "adjusted_fcf")):
    for lvl, k in (("level3", "zone3_max"), ("level2", "zone2_max"), ("level1", "zone1_max")):
        match = round(got[lvl], 1) == zj[key][k]
        ok &= match
        print(f"  {name} {k}: คำนวณ {got[lvl]:.1f} / zones.json {zj[key][k]} {'ตรง' if match else 'ไม่ตรง'}")
print(f"FCF ปรับภาษีหลังหัก SBC = {fcf:,.0f} (zones.json {zj['adjusted_fcf']['fcf_musd']})")
ok &= round(fcf) == zj["adjusted_fcf"]["fcf_musd"]
# สามฉาก FY2029: EV = ราคา x หุ้นหน้าปก + หนี้ตามบัญชี 7,669 - เงินสดและเงินลงทุน 7,200 [INTU.md ส่วน 2-3]
ev = 341.09 * sh / 1e6 + 7669 - 7200
rev26, want = 21448, {"good": (0.14, 0.30, 9.6), "base": (0.10, 0.274, 11.7), "bad": (0.05, 0.19, 19.4)}
for k, (g, mg, x) in want.items():
    op = rev26 * (1 + g) ** 3 * mg
    got = ev / op
    match = round(got, 1) == x
    ok &= match
    print(f"  ฉาก {k}: กำไรดำเนินงาน FY2029 {op:,.0f} · EV {ev:,.0f} ÷ = {got:.2f}x (เอกสาร {x}x) {'ตรง' if match else 'ไม่ตรง'}")
print("ผลรวม:", "ตรงทั้งหมด" if ok else "มีรายการไม่ตรง")
