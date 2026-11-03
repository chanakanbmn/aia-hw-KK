"""สร้าง LRCX-5yr.html และส่วนพับ "เทียบงบ 5 ปี" ใน LRCX-infographic.html จาก companyfacts ของ SEC

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/build_5yr.py
อ่าน:  data/raw/LRCX.json (SEC companyfacts)  เขียน: output/LRCX/LRCX-5yr.html
        และแทนที่ข้อความระหว่าง <!--EXT5-START--> ... <!--EXT5-END--> ใน LRCX-infographic.html (ถ้ามีไฟล์)

หลักการ: ตัวเลขทุกตัวมาจาก companyfacts เท่านั้น ห้ามกรอกมือ ถ้างวดไหนไม่มีให้เว้นว่าง (None) และบอก
- ปีบัญชี LRCX จบวันอาทิตย์สุดท้ายของเดือนมิถุนายน (FY2026 = 30 มิ.ย. 2025 - 28 มิ.ย. 2026) ไม่ใช่ปีปฏิทิน
- หุ้นแตก 10:1 มีผล 2 ต.ค. 2024 -> ไม่ใช้ EPS หรือจำนวนหุ้นข้ามฐาน ใช้ยอดรวมเงินดอลลาร์
- แต่ละงวดเลือกค่าจากไฟล์ที่ยื่นล่าสุด (filed ใหม่สุด) เฉพาะ form 10-K / 10-Q
- LTM (12 เดือนถึง 27 ก.ย. 2026) = FY2026 - Q1 FY2026 + Q1 FY2027
"""
import json
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../aia-hw-KK
RAW = ROOT / "data" / "raw" / "LRCX.json"
OUT_DIR = Path(__file__).resolve().parents[1]       # .../output/LRCX
YEARS = [2022, 2023, 2024, 2025, 2026]
COLS = [f"FY{y}" for y in YEARS] + ["LTM"]
PERIOD = {  # ปีบัญชี -> (วันเริ่ม, วันจบ) ตาม companyfacts
    2022: ("2021-06-28", "2022-06-26"), 2023: ("2022-06-27", "2023-06-25"), 2024: ("2023-06-26", "2024-06-30"),
    2025: ("2024-07-01", "2025-06-29"), 2026: ("2025-06-30", "2026-06-28"),
}
Q1_PREV = ("2025-06-30", "2025-09-28")   # Q1 FY2026
Q1_CUR = ("2026-06-29", "2026-09-27")    # Q1 FY2027
FLOW = {
    "rev": "RevenueFromContractWithCustomerExcludingAssessedTax",
    "gp": "GrossProfit",
    "opinc": "OperatingIncomeLoss",
    "ni": "NetIncomeLoss",
    "ocf": "NetCashProvidedByUsedInOperatingActivities",
    "capex": "PaymentsToAcquireProductiveAssets",
    "sbc": "ShareBasedCompensation",
    "buyback": "PaymentsForRepurchaseOfCommonStock",
    "div": "PaymentsOfDividends",
}
INSTANT = {"inv": "InventoryNet", "ar": "AccountsReceivableNetCurrent"}
# ค่าที่ LRCX-FACTS.md ลงไว้ (ล้านดอลลาร์) ใช้ตรวจว่าสคริปต์ดึงตรงกัน: (คีย์, คอลัมน์) -> ค่า
FACTS_CHECK = {
    ("rev", "FY2022"): 17227.039, ("rev", "FY2023"): 17428.516, ("rev", "FY2024"): 14905.386,
    ("rev", "FY2025"): 18435.591, ("rev", "FY2026"): 23232.690,
    ("gp", "FY2024"): 7052.791, ("gp", "FY2026"): 11725.308,
    ("opinc", "FY2022"): 5381.822, ("opinc", "FY2026"): 8199.795,
    ("ni", "FY2023"): 4510.931, ("ni", "FY2026"): 7265.396,
    ("ocf", "FY2022"): 3099.674, ("ocf", "FY2023"): 5178.938, ("ocf", "FY2024"): 4652.269,
    ("ocf", "FY2025"): 6173.264, ("ocf", "FY2026"): 5857.657,
    ("capex", "FY2022"): 546.034, ("capex", "FY2026"): 966.405,
    ("sbc", "FY2022"): 259.064, ("sbc", "FY2026"): 386.381,
    ("buyback", "FY2022"): 3865.663, ("buyback", "FY2026"): 3851.343,
    ("div", "FY2022"): 815.290, ("div", "FY2026"): 1270.635,
    ("inv", "FY2022"): 3966.294, ("inv", "FY2026"): 4276.111, ("ar", "FY2022"): 4313.818, ("ar", "FY2026"): 5339.682,
    ("inv", "LTM"): 4550.544, ("ar", "LTM"): 5658.379,
    ("fcf", "FY2026"): 4891.252, ("fcf_sbc", "FY2026"): 4504.871, ("fcf", "FY2022"): 2553.640,
}
GOLD, BLUE, GREEN = "#e8c26a", "#5fb3d9", "#6fcf97"

facts = json.loads(RAW.read_text(encoding="utf-8"))["facts"]["us-gaap"]


def _best(tag, start, end):
    best = None
    for x in facts.get(tag, {}).get("units", {}).get("USD", []):
        if x.get("start") == start and x["end"] == end and x["form"] in ("10-K", "10-Q"):
            if best is None or x["filed"] > best["filed"]:
                best = x
    return best


def pick(tag, start, end):
    """ค่า USD ของช่วง start..end จากไฟล์ที่ยื่นล่าสุด คืนล้านดอลลาร์ หรือ None"""
    b = _best(tag, start, end)
    return None if b is None else b["val"] / 1e6


def pick_inst(tag, end):
    best = None
    for x in facts.get(tag, {}).get("units", {}).get("USD", []):
        if "start" not in x and x["end"] == end and x["form"] in ("10-K", "10-Q"):
            if best is None or x["filed"] > best["filed"]:
                best = x
    return None if best is None else best["val"] / 1e6


def series(key):
    tag = FLOW[key]
    vals = [pick(tag, *PERIOD[y]) for y in YEARS]
    q_prev, q_cur = pick(tag, *Q1_PREV), pick(tag, *Q1_CUR)
    fy26 = vals[-1]
    vals.append(fy26 - q_prev + q_cur if None not in (fy26, q_prev, q_cur) else None)
    return vals


def iseries(key):
    tag = INSTANT[key]
    vals = [pick_inst(tag, PERIOD[y][1]) for y in YEARS]
    vals.append(pick_inst(tag, Q1_CUR[1]))
    return vals


def sub(a, b):
    return [None if x is None or y is None else x - y for x, y in zip(a, b)]


def ratio(a, b):
    return [None if x is None or y in (None, 0) else x / y * 100 for x, y in zip(a, b)]


D = {k: series(k) for k in FLOW}
D.update({k: iseries(k) for k in INSTANT})
D["fcf"] = sub(D["ocf"], D["capex"])
D["fcf_sbc"] = sub(D["fcf"], D["sbc"])
D["ret"] = [None if a is None or b is None else a + b for a, b in zip(D["buyback"], D["div"])]
D["gm"] = ratio(D["gp"], D["rev"])
D["op_m"] = ratio(D["opinc"], D["rev"])
D["fcf_m"] = ratio(D["fcf"], D["rev"])
D["fcf_sbc_m"] = ratio(D["fcf_sbc"], D["rev"])
D["sbc_pct"] = ratio(D["sbc"], D["rev"])
D["ret_pct_fcf"] = ratio(D["ret"], D["fcf"])

# ตรวจกับ LRCX-FACTS.md ก่อนเขียนไฟล์
bad = []
for (k, c), v in FACTS_CHECK.items():
    got = D[k][COLS.index(c)]
    if got is None or abs(got - v) > 0.5:
        bad.append((k, c, v, got))
if bad:
    print("ตัวเลขไม่ตรงกับ LRCX-FACTS.md:", bad)
    sys.exit(1)
print("ตรวจกับ LRCX-FACTS.md ผ่าน", len(FACTS_CHECK), "ค่า")
missing = [(k, COLS[i]) for k in D for i, v in enumerate(D[k]) if v is None]
print("ค่าที่หาไม่ได้ใน companyfacts:", missing or "ไม่มี")
days24 = (date.fromisoformat(PERIOD[2024][1]) - date.fromisoformat(PERIOD[2024][0])).days + 1
print("FY2024 ยาว", days24, "วัน =", days24 / 7, "สัปดาห์")


def money(v):
    return "—" if v is None else f"{v:,.0f}"


def pct(v):
    return "—" if v is None else f"{v:.1f}%"


def chg(a, b):
    return None if a is None or b is None or b <= 0 else (a / b - 1) * 100


def cagr(a, b, n=4):
    return None if a is None or b is None or a <= 0 or b <= 0 else ((a / b) ** (1 / n) - 1) * 100


def chip(v, kind="up"):
    """kind: up = ค่าเพิ่มคือดี, cost = ค่าเพิ่มไม่ตัดสินดีร้าย (เหลือง)"""
    if v is None:
        return "—"
    cls = "warn" if kind == "cost" else ("good" if v >= 0 else "bad")
    return f'<span class="chip {cls}">{v:+.1f}%</span>'


ROWS = [
    # key, ป้ายแถว, หน่วย, tag ที่มา, kind, เป็นเปอร์เซ็นต์หรือไม่
    ("rev", "รายได้รวม", "$M", f"us-gaap:{FLOW['rev']}", "up", False),
    ("gp", "กำไรขั้นต้น", "$M", f"us-gaap:{FLOW['gp']}", "up", False),
    ("opinc", "กำไรจากการดำเนินงาน", "$M", f"us-gaap:{FLOW['opinc']}", "up", False),
    ("ni", "กำไรสุทธิ", "$M", f"us-gaap:{FLOW['ni']}", "up", False),
    ("ocf", "กระแสเงินสดจากการดำเนินงาน (OCF)", "$M", f"us-gaap:{FLOW['ocf']}", "up", False),
    ("capex", "Capex (ซื้อทรัพย์สินและสินทรัพย์ไม่มีตัวตน)", "$M", f"us-gaap:{FLOW['capex']}", "cost", False),
    ("sbc", "ค่าตอบแทนเป็นหุ้น (SBC)", "$M", f"us-gaap:{FLOW['sbc']}", "cost", False),
    ("fcf", "FCF แบบง่าย (OCF − capex)", "$M", "คำนวณ: OCF − Capex", "up", False),
    ("fcf_sbc", "FCF หลังหัก SBC", "$M", "คำนวณ: FCF แบบง่าย − SBC", "up", False),
    ("buyback", "ซื้อหุ้นคืน (เงินสดจ่าย)", "$M", f"us-gaap:{FLOW['buyback']}", "cost", False),
    ("div", "เงินปันผลจ่าย", "$M", f"us-gaap:{FLOW['div']}", "cost", False),
    ("inv", "สินค้าคงคลัง (สิ้นงวด)", "$M", f"us-gaap:{INSTANT['inv']}", "cost", False),
    ("ar", "ลูกหนี้การค้า (สิ้นงวด)", "$M", f"us-gaap:{INSTANT['ar']}", "cost", False),
    ("gm", "Gross margin (กำไรขั้นต้น ÷ รายได้)", "%", "คำนวณ", None, True),
    ("op_m", "Operating margin", "%", "คำนวณ", None, True),
    ("fcf_m", "FCF margin (FCF แบบง่าย ÷ รายได้)", "%", "คำนวณ", None, True),
    ("fcf_sbc_m", "FCF margin หลังหัก SBC", "%", "คำนวณ", None, True),
    ("sbc_pct", "SBC ÷ รายได้", "%", "คำนวณ", None, True),
    ("ret_pct_fcf", "(ซื้อหุ้นคืน + ปันผล) ÷ FCF แบบง่าย", "%", "คำนวณ", None, True),
]
LAB = {"LTM": "LTM Q1'27"}


def table_html():
    h = ['<table><tr><th>รายการ <small>(แท็กที่มา)</small></th>']
    h += [f'<th class="r">{c}</th>' for c in COLS[:-1]]
    h += ['<th class="r">LTM Q1\'27</th><th class="r">FY24 YoY</th><th class="r">FY26 YoY</th><th class="r">CAGR 22→26</th></tr>']
    for key, label, unit, tag, kind, is_pct in ROWS:
        v = D[key]
        h.append(f'\n<tr><td>{escape(label)} <small>({unit})</small><br><small>{escape(tag)} · YoY/CAGR [คำนวณ]</small></td>')
        h += [f'<td class="r">{pct(x) if is_pct else money(x)}</td>' for x in v]
        if is_pct:
            d24 = None if v[2] is None or v[1] is None else v[2] - v[1]
            d26 = None if v[4] is None or v[3] is None else v[4] - v[3]
            f = lambda d: "—" if d is None else f"{d:+.1f} จุด"  # noqa: E731
            h.append(f'<td class="r"><small>{f(d24)}</small></td><td class="r"><small>{f(d26)}</small></td><td class="r">—</td>')
        else:
            h.append(f'<td class="r">{chip(chg(v[2], v[1]), kind)}</td><td class="r">{chip(chg(v[4], v[3]), kind)}</td>'
                     f'<td class="r">{chip(cagr(v[4], v[0]), kind)}</td>')
        h.append("</tr>")
    h.append("</table>")
    return "".join(h)


def chart(title, series_list, fmt, unit, aria):
    """แท่งกลุ่ม 6 กลุ่ม (FY2022-FY2026 + LTM) series_list = [(ชื่อ, สี, [ค่า])] ค่า None = ว่าง"""
    W, L, R, T, B = 640, 44, 630, 22, 206
    allv = [x for _, _, vs in series_list for x in vs if x is not None]
    vmax, vmin = max(allv + [0]) * 1.12, min(allv + [0])
    span = (vmax - vmin) or 1
    y = lambda v: B - (v - vmin) / span * (B - T)  # noqa: E731
    base = y(0)
    n = len(series_list)
    gw = (R - L) / 6
    bw = min(32.0, (gw - 16) / n)
    s = [f'<svg viewBox="0 0 {W} 250" role="img" aria-label="{escape(aria)}" style="width:100%;height:auto">']
    for i in range(5):
        v = vmin + span * i / 4
        yy = B - (B - T) * i / 4
        s.append(f'<line x1="{L}" x2="{R}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#3a2f17" stroke-width="1"/>'
                 f'<text x="{L - 6}" y="{yy + 4:.1f}" text-anchor="end" fill="#a89c80" font-size="10">{fmt(v)}</text>')
    for gi, col in enumerate(COLS):
        gx = L + gw * gi + gw / 2
        s.append(f'<text x="{gx:.1f}" y="224" text-anchor="middle" fill="#a89c80" font-size="11">{LAB.get(col, col)}</text>')
        for si, (name, color, vs) in enumerate(series_list):
            v = vs[gi]
            x0 = gx - n * bw / 2 + si * bw
            if v is None:
                s.append(f'<text x="{x0 + bw / 2:.1f}" y="{base - 4:.1f}" text-anchor="middle" fill="#a89c80" font-size="9">—</text>')
                continue
            top, hgt = (y(v), base - y(v)) if v >= 0 else (base, y(v) - base)
            ltm = col == "LTM"
            extra = f' fill-opacity="0.45" stroke="{color}" stroke-dasharray="3 2"' if ltm else ' fill-opacity="1"'
            label = f"{name} {LAB.get(col, col)}: {fmt(v)}"
            s.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(hgt, 0.5):.1f}" rx="2" fill="{color}"{extra}>'
                     f'<title>{escape(label)}</title></rect>'
                     f'<text x="{x0 + bw / 2:.1f}" y="{(top - 4) if v >= 0 else (top + hgt + 11):.1f}" text-anchor="middle" fill="#f1ead8" font-size="9">{fmt(v)}</text>')
    s.append("</svg>")
    legend = "".join(f'<span><i style="background:{c}"></i>{escape(n_)}</span>' for n_, c, _ in series_list)
    return (f'\n<!-- [คำนวณ] พิกัดกราฟ -->\n<div class="x5h">{escape(title)}</div><div class="x5chart"><div class="x5legend">{legend}'
            f'<em>{escape(unit)} · แท่งจางประ = 12 เดือนถึง Q1 FY2027 (LTM)</em></div>\n{"".join(s)}\n</div>')


def charts_html():
    bn = lambda v: f"{v / 1000:.1f}"  # noqa: E731  ล้าน -> พันล้าน (แสดงผลเท่านั้น)
    pc = lambda v: f"{v:.0f}%"  # noqa: E731
    return "".join([
        chart("รายได้รวม (สังเกตปี FY2024 ที่ลดลง)", [("รายได้รวม", GOLD, D["rev"])], bn, "พันล้านดอลลาร์", "รายได้รวม"),
        chart("OCF, Capex และ SBC", [("OCF", GOLD, D["ocf"]), ("Capex", BLUE, D["capex"]), ("SBC", GREEN, D["sbc"])],
              bn, "พันล้านดอลลาร์", "OCF capex SBC"),
        chart("FCF แบบง่าย เทียบ FCF หลังหัก SBC", [("FCF แบบง่าย", GOLD, D["fcf"]), ("FCF หลังหัก SBC", BLUE, D["fcf_sbc"])],
              bn, "พันล้านดอลลาร์", "FCF"),
        chart("กำไรจากการดำเนินงาน เทียบ กำไรสุทธิ", [("กำไรจากการดำเนินงาน", GOLD, D["opinc"]), ("กำไรสุทธิ", BLUE, D["ni"])],
              bn, "พันล้านดอลลาร์", "กำไร"),
        chart("FCF margin", [("FCF margin", GOLD, D["fcf_m"]), ("หลังหัก SBC", BLUE, D["fcf_sbc_m"])],
              pc, "เปอร์เซ็นต์ของรายได้", "FCF margin"),
        chart("ซื้อหุ้นคืน + ปันผล เทียบ FCF แบบง่าย", [("ซื้อหุ้นคืน + ปันผล", GREEN, D["ret"]), ("FCF แบบง่าย", GOLD, D["fcf"])],
              bn, "พันล้านดอลลาร์", "ซื้อหุ้นคืนและปันผลเทียบ FCF"),
        chart("สินค้าคงคลังและลูกหนี้ (สิ้นงวด)", [("สินค้าคงคลัง", BLUE, D["inv"]), ("ลูกหนี้การค้า", GOLD, D["ar"])],
              bn, "พันล้านดอลลาร์", "สินค้าคงคลังและลูกหนี้"),
    ])


def bullets():
    r, f, fs, o, sb = D["rev"], D["fcf"], D["fcf_sbc"], D["opinc"], D["sbc"]
    return [
        f"<b>นี่คือธุรกิจวัฏจักร:</b> รายได้ ${money(r[0])}M (FY2022) → ${money(r[1])}M → <b>${money(r[2])}M (FY2024, {chip(chg(r[2], r[1]))})</b> → "
        f"${money(r[3])}M → ${money(r[4])}M (FY2026, {chip(chg(r[4], r[3]))}) · CAGR 4 ปี ฐาน FY2022→FY2026 {pct(cagr(r[4], r[0]))} ซ่อนการตกและการดีดกลับ (ไม่ปนกับ CAGR 5 ปีฐาน FY2021 ที่ 9.7% ซึ่ง FY2021 ไม่อยู่ในตารางนี้) · "
        f"LTM ${money(r[5])}M · FY2024 ยาว 53 สัปดาห์ (เทียบ FY อื่น 52 สัปดาห์) YoY ของ FY2024 และ FY2025 ในตารางนี้ไม่ได้ปรับตามจำนวนสัปดาห์ [คำนวณ จากวันเริ่ม-จบงวดใน companyfacts]",
        f"<b>FCF แบบง่ายแกว่งแรงกว่ารายได้:</b> ${money(f[0])}M (FY2022, margin {pct(D['fcf_m'][0])}) → ${money(f[4])}M (FY2026, margin {pct(D['fcf_m'][4])}) · "
        f"LTM ${money(f[5])}M (margin {pct(D['fcf_m'][5])}) · <b>หลังหัก SBC:</b> LTM ${money(fs[5])}M (margin {pct(D['fcf_sbc_m'][5])}) · "
        f"FY2026 OCF ({money(D['ocf'][4])}M) ต่ำกว่า FY2025 ({money(D['ocf'][3])}M) ทั้งที่กำไรสุทธิโต [ที่มา: LRCX-FACTS.md แถว 65]",
        f"<b>SBC เล็กเมื่อเทียบ FCF:</b> {pct(D['sbc_pct'][5])} ของรายได้ใน LTM ({money(sb[5])}M) คิดเป็น {pct(sb[5] / f[5] * 100)} ของ FCF แบบง่าย "
        f"จึงตัวเลขก่อนและหลังหัก SBC ต่างกันไม่มาก [คำนวณ: SBC ÷ FCF แบบง่าย]",
        f"<b>Margin:</b> gross margin {pct(D['gm'][0])} → {pct(D['gm'][4])} (FY2026) → {pct(D['gm'][5])} (LTM) · operating margin "
        f"{pct(D['op_m'][0])} → {pct(D['op_m'][4])} → {pct(D['op_m'][5])} (LTM มี Q1 FY2027 ที่สูงเป็นพิเศษ ใช้เป็นฐานทั้งปีไม่ได้)",
        f"<b>เงินคืนผู้ถือหุ้น:</b> ซื้อหุ้นคืน + ปันผล FY2026 = ${money(D['ret'][4])}M เทียบ FCF แบบง่าย ${money(f[4])}M ({pct(D['ret_pct_fcf'][4])}) · "
        f"FY2022 {pct(D['ret_pct_fcf'][0])} (ซื้อหุ้นคืนมากกว่า FCF ในปีที่ FCF ต่ำ)",
        f"<b>สินค้าคงคลังและลูกหนี้:</b> สินค้าคงคลัง ${money(D['inv'][0])}M (FY2022) → ${money(D['inv'][4])}M (FY2026, {chip(chg(D['inv'][4], D['inv'][0]), 'cost')}) เทียบรายได้ที่โต {pct(chg(r[4], r[0]))} ในช่วงเดียวกัน · "
        f"ลูกหนี้ ${money(D['ar'][3])}M → ${money(D['ar'][4])}M ในปี FY2026 ({chip(chg(D['ar'][4], D['ar'][3]), 'cost')}) เร็วกว่ารายได้ที่โต {pct(chg(r[4], r[3]))}",
        "<b>หุ้นแตก 10:1 (2 ต.ค. 2024):</b> ตารางนี้จึงไม่มี EPS หรือจำนวนหุ้น (ปี FY2022 มีเฉพาะฐานก่อนแตก) ใช้เฉพาะยอดรวมเป็นดอลลาร์ "
        "[ที่มา: LRCX-FACTS.md แถว 38-51]",
        "<b>ปีบัญชีจบสิ้นเดือนมิถุนายน:</b> FY2026 = 30 มิ.ย. 2025 ถึง 28 มิ.ย. 2026 · Q1 FY2027 = 29 มิ.ย. ถึง 27 ก.ย. 2026 ไม่ตรงกับปีปฏิทิน",
    ]


SRC_LINES = [
    "ที่มา: SEC companyfacts ของ Lam Research (data/raw/LRCX.json) หน่วยเดิมเป็นดอลลาร์เต็มจำนวน แปลงเป็นล้านดอลลาร์ด้วยสคริปต์ "
    "output/LRCX/tools/build_5yr.py · แต่ละงวดเลือกค่าจากไฟล์ 10-K/10-Q ที่ยื่นล่าสุด · "
    "LTM = FY2026 − Q1 FY2026 + Q1 FY2027 (12 เดือนถึง 27 ก.ย. 2026) · สินค้าคงคลังและลูกหนี้ในคอลัมน์ LTM คือยอด ณ 27 ก.ย. 2026 · "
    "CAGR คำนวณ 4 ปี (FY2022→FY2026) ไม่รวม LTM · FCF แบบง่ายเป็นนิยามของเราเอง ไม่ใช่นิยามบริษัท · "
    "ตรวจสคริปต์กับค่าใน LRCX-FACTS.md แล้ว (ผ่านทุกค่าที่ซ้ำกัน)",
    "รายการ capex ใช้ tag PaymentsToAcquireProductiveAssets ซึ่งรวมสินทรัพย์ไม่มีตัวตน (ตามชื่อ tag ใน FACTS แถว 53) · "
    "ตัวเลขทั้งหมดเป็นงบที่ยื่นต่อ SEC ไม่ใช่ราคาตลาด จึงไม่มีป้ายแหล่งรอง",
    "สถานะ draft · กรอบวิเคราะห์ ไม่ใช่คำแนะนำลงทุนส่วนบุคคล",
]

CSS_COMMON = """:root{--bg:#0b0a08;--card:#16130d;--line:#3a2f17;--gold:#e8c26a;--gold2:#b8914a;--text:#f1ead8;--mute:#a89c80;--good:#6fcf97;--bad:#eb7a6a;--warn:#e8c26a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Segoe UI","Noto Sans Thai",system-ui,sans-serif;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto;padding:20px 16px 48px}
h1{margin:0;font-size:26px;color:var(--gold)}.sub{color:var(--mute);font-size:14px;margin:4px 0 12px}
.badge{display:inline-block;border:1px solid var(--gold2);color:var(--gold);border-radius:99px;padding:2px 10px;font-size:12px;margin:0 6px 4px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:14px;overflow-x:auto;min-width:0}
.card h2{margin:0 0 8px;font-size:17px;color:var(--gold)}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:860px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--gold2);font-weight:600}
.r{text-align:right;white-space:nowrap}small{color:var(--mute)}
.chip{display:inline-block;border-radius:6px;padding:1px 7px;font-weight:700}
.chip.good{color:var(--good);background:rgba(111,207,151,.16)}.chip.bad{color:var(--bad);background:rgba(235,122,106,.16)}.chip.warn{color:var(--warn);background:rgba(232,194,106,.16)}
.src{color:var(--mute);font-size:11px;margin-top:8px}
ul{margin:6px 0 0;padding-left:18px}li{margin:4px 0;font-size:13px}
.x5h{margin:16px 0 2px;font-size:14px;font-weight:600;color:var(--gold2)}
.x5chart{min-width:520px}.x5legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--mute);margin-bottom:4px}
.x5legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}.x5legend em{margin-left:auto;font-style:normal}
"""


def page_5yr():
    lis = "\n".join(f"<li>{b} [คำนวณ]</li>" for b in bullets())
    srcs = "\n".join(f'<div class="src">{escape(t)} [คำนวณ]</div>' for t in SRC_LINES)
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LRCX เทียบงบ 5 ปี</title>
<style>
{CSS_COMMON}</style></head><body><div class="wrap">
<h1>Lam Research (LRCX) — เทียบงบ 5 ปี</h1>
<div class="sub">ปีงบ FY2022–FY2026 (ปีบัญชีจบสิ้นเดือนมิถุนายน ไม่ใช่ปีปฏิทิน) และ 12 เดือนถึง 27 ก.ย. 2026 (LTM) · ตัวเลขจาก SEC companyfacts · สร้างด้วยสคริปต์ ไม่ได้กรอกมือ</div>
<span class="badge">สถานะ: draft</span><span class="badge">ปีบัญชีจบ มิ.ย.</span><span class="badge">ไม่มี EPS/จำนวนหุ้น (หุ้นแตก 10:1 ต.ค. 2024)</span>

<section class="card"><h2>ภาพรวม</h2><ul>\n{lis}\n</ul></section>

<section class="card"><h2>ตารางเทียบ 5 ปี (ล้านดอลลาร์)</h2>{table_html()}
<div class="src"><span class="chip good">เขียว</span> เพิ่มขึ้น · <span class="chip bad">แดง</span> ลดลง · <span class="chip warn">เหลือง</span> ต้นทุน/ยอดคงค้างที่เพิ่ม (ไม่ตัดสินดีร้าย) · "—" = ไม่มีข้อมูลหรือคำนวณไม่ได้</div></section>

<section class="card"><h2>กราฟ</h2>{charts_html()}{srcs}</section>
</div></body></html>
"""


def ext_block():
    lis = "\n".join(f"<li>{b} [คำนวณ]</li>" for b in bullets())
    srcs = "\n".join(f'<div class="src">{escape(t)} [คำนวณ]</div>' for t in SRC_LINES[:2])
    return f"""<!--EXT5-START-->
  <details class="card x5">
    <summary><span class="num">+</span>เสริม: เทียบงบ 5 ปี (FY2022–FY2026 + LTM) พร้อมกราฟ <small>— คลิกเพื่อขยาย · ปีบัญชีจบสิ้นเดือนมิถุนายน</small></summary>
    <ul>\n{lis}\n</ul>
    {table_html()}
    {charts_html()}
    {srcs}
    <div class="src">รายละเอียดเต็ม: <a href="LRCX-5yr.html" style="color:var(--gold)">LRCX-5yr.html</a></div>
  </details>
<!--EXT5-END-->"""


if __name__ == "__main__":
    (OUT_DIR / "LRCX-5yr.html").write_text(page_5yr(), encoding="utf-8")
    print("เขียน", OUT_DIR / "LRCX-5yr.html")
    info = OUT_DIR / "LRCX-infographic.html"
    if info.exists():
        t = info.read_text(encoding="utf-8")
        a, b = t.find("<!--EXT5-START-->"), t.find("<!--EXT5-END-->")
        if a < 0 or b < 0:
            print("ไม่พบเครื่องหมาย EXT5 ใน LRCX-infographic.html")
            sys.exit(1)
        info.write_text(t[:a] + ext_block() + t[b + len("<!--EXT5-END-->"):], encoding="utf-8")
        print("อัปเดตส่วนพับใน", info)
    print("LTM:", {k: round(D[k][5], 1) for k in D if D[k][5] is not None})
