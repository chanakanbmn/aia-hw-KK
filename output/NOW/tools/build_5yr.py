"""สร้าง NOW-5yr.html และส่วนพับ "เทียบงบ 5 ปี" ใน NOW-infographic.html จาก companyfacts ของ SEC

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/NOW/tools/build_5yr.py
อ่าน:  data/raw/NOW.json (SEC companyfacts)  เขียน: output/NOW/NOW-5yr.html
        และแทนที่ข้อความระหว่าง <!--EXT5-START--> ... <!--EXT5-END--> ใน NOW-infographic.html (ถ้ามีไฟล์)

หลักการ: ตัวเลขทุกตัวมาจาก companyfacts เท่านั้น ห้ามกรอกมือ ถ้างวดไหนไม่มีให้เว้นว่าง (None) และบอก
- หุ้นแตก 5:1 ธ.ค. 2025 -> ไม่ใช้ EPS หรือจำนวนหุ้นข้ามฐาน ใช้ยอดรวมเงินดอลลาร์ที่ไม่ขึ้นกับจำนวนหุ้น
- แต่ละงวดเลือกค่าจากไฟล์ที่ยื่นล่าสุด (filed ใหม่สุด) เฉพาะ form 10-K / 10-Q
- LTM (12 เดือนถึง 30 ก.ย. 2026) = FY2025 - 9M2025 + 9M2026
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../aia-hw-KK
RAW = ROOT / "data" / "raw" / "NOW.json"
OUT_DIR = Path(__file__).resolve().parents[1]       # .../output/NOW
YEARS = [2021, 2022, 2023, 2024, 2025]
COLS = [str(y) for y in YEARS] + ["LTM"]
TAGS = {
    "rev": "RevenueFromContractWithCustomerExcludingAssessedTax",
    "ocf": "NetCashProvidedByUsedInOperatingActivities",
    "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
    "sbc": "ShareBasedCompensation",
    "opinc": "OperatingIncomeLoss",
    "ni": "NetIncomeLoss",
}
# ค่าที่ NOW-FACTS.md ลงไว้ (ล้านดอลลาร์) ใช้ตรวจว่าสคริปต์ดึงตรงกัน: (คีย์, ปี) -> ค่า
FACTS_CHECK = {
    ("rev", 2023): 8971, ("rev", 2024): 10984, ("rev", 2025): 13278,
    ("ocf", 2023): 3398, ("ocf", 2024): 4267, ("ocf", 2025): 5444,
    ("capex", 2023): 694, ("capex", 2024): 852, ("capex", 2025): 868,
    ("sbc", 2023): 1604, ("sbc", 2024): 1746, ("sbc", 2025): 1955,
    ("opinc", 2023): 762, ("opinc", 2024): 1364, ("opinc", 2025): 1824,
    ("ni", 2023): 1731, ("ni", 2024): 1425, ("ni", 2025): 1748,
    ("rev", "LTM"): 15431, ("ocf", "LTM"): 5334, ("capex", "LTM"): 584, ("ni", "LTM"): 1445,
}
GOLD, BLUE, GREEN = "#e8c26a", "#5fb3d9", "#6fcf97"

facts = json.loads(RAW.read_text(encoding="utf-8"))["facts"]["us-gaap"]


def pick(tag, start, end):
    """ค่า USD ของช่วง start..end จากไฟล์ที่ยื่นล่าสุด (10-K/10-Q) คืน (ล้านดอลลาร์, filed, form) หรือ None"""
    best = None
    for x in facts.get(tag, {}).get("units", {}).get("USD", []):
        if x.get("start") == start and x["end"] == end and x["form"] in ("10-K", "10-Q"):
            if best is None or x["filed"] > best["filed"]:
                best = x
    if best is None:
        return None
    return best["val"] / 1e6, best["filed"], best["form"]


def series(key):
    tag = TAGS[key]
    vals = []
    for y in YEARS:
        r = pick(tag, f"{y}-01-01", f"{y}-12-31")
        vals.append(r[0] if r else None)
    fy25 = vals[-1]
    a = pick(tag, "2025-01-01", "2025-09-30")
    b = pick(tag, "2026-01-01", "2026-09-30")
    vals.append(fy25 - a[0] + b[0] if None not in (fy25, a, b) else None)
    return vals


def sub(a, b):
    return [None if x is None or y is None else x - y for x, y in zip(a, b)]


def ratio(a, b):
    return [None if x is None or y in (None, 0) else x / y * 100 for x, y in zip(a, b)]


D = {k: series(k) for k in TAGS}
D["fcf"] = sub(D["ocf"], D["capex"])
D["fcf_sbc"] = sub(D["fcf"], D["sbc"])
D["fcf_m"] = ratio(D["fcf"], D["rev"])
D["fcf_sbc_m"] = ratio(D["fcf_sbc"], D["rev"])
D["sbc_pct"] = ratio(D["sbc"], D["rev"])
D["op_m"] = ratio(D["opinc"], D["rev"])

# ตรวจกับ NOW-FACTS.md ก่อนเขียนไฟล์
bad = []
for (k, c), v in FACTS_CHECK.items():
    i = COLS.index(str(c))
    got = D[k][i]
    if got is None or abs(got - v) > 0.5:
        bad.append((k, c, v, got))
if bad:
    print("ตัวเลขไม่ตรงกับ NOW-FACTS.md:", bad)
    sys.exit(1)
print("ตรวจกับ NOW-FACTS.md ผ่าน", len(FACTS_CHECK), "ค่า")
missing = [(k, COLS[i]) for k in TAGS for i, v in enumerate(D[k]) if v is None]
print("ค่าที่หาไม่ได้ใน companyfacts:", missing or "ไม่มี")


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
    ("rev", "รายได้รวม", "$M", f"us-gaap:{TAGS['rev']}", "up", False),
    ("ocf", "กระแสเงินสดจากการดำเนินงาน (OCF)", "$M", f"us-gaap:{TAGS['ocf']}", "up", False),
    ("capex", "Capex (ซื้อทรัพย์สินและอุปกรณ์)", "$M", f"us-gaap:{TAGS['capex']}", "cost", False),
    ("sbc", "ค่าตอบแทนเป็นหุ้น (SBC)", "$M", f"us-gaap:{TAGS['sbc']}", "cost", False),
    ("fcf", "FCF แบบง่าย (OCF − capex)", "$M", "คำนวณ: OCF − Capex", "up", False),
    ("fcf_sbc", "FCF หลังหัก SBC", "$M", "คำนวณ: FCF แบบง่าย − SBC", "up", False),
    ("opinc", "กำไรจากการดำเนินงาน", "$M", f"us-gaap:{TAGS['opinc']}", "up", False),
    ("ni", "กำไรสุทธิ", "$M", f"us-gaap:{TAGS['ni']}", "up", False),
    ("fcf_m", "FCF margin (FCF แบบง่าย ÷ รายได้)", "%", "คำนวณ", None, True),
    ("fcf_sbc_m", "FCF margin หลังหัก SBC", "%", "คำนวณ", None, True),
    ("sbc_pct", "SBC ÷ รายได้", "%", "คำนวณ", None, True),
    ("op_m", "Operating margin", "%", "คำนวณ", None, True),
]


def table_html():
    h = ['<table><tr><th>รายการ <small>(แท็กที่มา)</small></th>']
    h += [f'<th class="r">{y}</th>' for y in YEARS]
    h += ['<th class="r">LTM Q3\'26</th><th class="r">FY25 YoY</th><th class="r">CAGR 21→25</th></tr>']
    for key, label, unit, tag, kind, is_pct in ROWS:
        v = D[key]
        h.append(f'<tr><td>{escape(label)} <small>({unit})</small><br><small>{escape(tag)}</small></td>')
        h += [f'<td class="r">{pct(x) if is_pct else money(x)}</td>' for x in v]
        if is_pct:
            d = None if v[4] is None or v[3] is None else v[4] - v[3]
            h.append(f'<td class="r"><small>{"—" if d is None else f"{d:+.1f} จุด"}</small></td><td class="r">—</td>')
        else:
            h.append(f'<td class="r">{chip(chg(v[4], v[3]), kind)}</td><td class="r">{chip(cagr(v[4], v[0]), kind)}</td>')
        h.append("</tr>")
    h.append("</table>")
    return "".join(h)


def chart(title, series_list, fmt, unit, aria):
    """แท่งกลุ่ม 6 กลุ่ม (2021-2025 + LTM) series_list = [(ชื่อ, สี, [ค่า])] ค่า None = ว่าง"""
    W, L, R, T, B = 640, 44, 630, 22, 206
    allv = [x for _, _, vs in series_list for x in vs if x is not None]
    vmax, vmin = max(allv + [0]) * 1.12, min(allv + [0])
    span = (vmax - vmin) or 1
    y = lambda v: B - (v - vmin) / span * (B - T) + (B - (B - T)) * 0  # noqa: E731
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
        s.append(f'<text x="{gx:.1f}" y="224" text-anchor="middle" fill="#a89c80" font-size="11">'
                 f'{"LTM Q3\'26" if col == "LTM" else col}</text>')
        for si, (name, color, vs) in enumerate(series_list):
            v = vs[gi]
            x0 = gx - n * bw / 2 + si * bw
            if v is None:
                s.append(f'<text x="{x0 + bw / 2:.1f}" y="{base - 4:.1f}" text-anchor="middle" fill="#a89c80" font-size="9">—</text>')
                continue
            top, hgt = (y(v), base - y(v)) if v >= 0 else (base, y(v) - base)
            ltm = col == "LTM"
            extra = f' fill-opacity="0.45" stroke="{color}" stroke-dasharray="3 2"' if ltm else ' fill-opacity="1"'
            label = f"{name} {'LTM Q3' + chr(39) + '26' if ltm else col}: {fmt(v)}"
            s.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(hgt, 0.5):.1f}" rx="2" fill="{color}"{extra}>'
                     f'<title>{escape(label)}</title></rect>'
                     f'<text x="{x0 + bw / 2:.1f}" y="{(top - 4) if v >= 0 else (top + hgt + 11):.1f}" text-anchor="middle" fill="#f1ead8" font-size="9">{fmt(v)}</text>')
    s.append("</svg>")
    legend = "".join(f'<span><i style="background:{c}"></i>{escape(n_)}</span>' for n_, c, _ in series_list)
    return (f'<div class="x5h">{escape(title)}</div><div class="x5chart"><div class="x5legend">{legend}'
            f'<em>{escape(unit)} · แท่งจางประ = 12 เดือนถึง Q3 2026 (LTM)</em></div>{"".join(s)}</div>')


def charts_html():
    bn = lambda v: f"{v / 1000:.1f}"  # noqa: E731  ล้าน -> พันล้าน (แสดงผลเท่านั้น)
    pc = lambda v: f"{v:.0f}%"  # noqa: E731
    out = [
        chart("รายได้รวม", [("รายได้รวม", GOLD, D["rev"])], bn, "พันล้านดอลลาร์", "รายได้รวม"),
        chart("OCF, Capex และ SBC", [("OCF", GOLD, D["ocf"]), ("Capex", BLUE, D["capex"]), ("SBC", GREEN, D["sbc"])],
              bn, "พันล้านดอลลาร์", "OCF capex SBC"),
        chart("FCF แบบง่าย เทียบ FCF หลังหัก SBC", [("FCF แบบง่าย", GOLD, D["fcf"]), ("FCF หลังหัก SBC", BLUE, D["fcf_sbc"])],
              bn, "พันล้านดอลลาร์", "FCF"),
        chart("กำไรจากการดำเนินงาน เทียบ กำไรสุทธิ", [("กำไรจากการดำเนินงาน", GOLD, D["opinc"]), ("กำไรสุทธิ", BLUE, D["ni"])],
              bn, "พันล้านดอลลาร์", "กำไร"),
        chart("FCF margin", [("FCF margin", GOLD, D["fcf_m"]), ("หลังหัก SBC", BLUE, D["fcf_sbc_m"])],
              pc, "เปอร์เซ็นต์ของรายได้", "FCF margin"),
    ]
    return "".join(out)


def bullets():
    r, f, fs, o, sb = D["rev"], D["fcf"], D["fcf_sbc"], D["opinc"], D["sbc"]
    return [
        f"<b>รายได้โตต่อเนื่อง:</b> ${money(r[0])}M (2021) → ${money(r[4])}M (2025) CAGR 4 ปี {pct(cagr(r[4], r[0]))} · "
        f"LTM ${money(r[5])}M (รวมรายได้จากกิจการที่ซื้อในปี 2026 ซึ่งงบไม่แยกส่วนที่โตเอง)",
        f"<b>FCF แบบง่าย:</b> ${money(f[0])}M → ${money(f[4])}M (CAGR {pct(cagr(f[4], f[0]))}) · LTM ${money(f[5])}M "
        f"(margin {pct(D['fcf_m'][5])}) · <b>หลังหัก SBC:</b> ${money(fs[0])}M → ${money(fs[4])}M · LTM ${money(fs[5])}M "
        f"(margin {pct(D['fcf_sbc_m'][5])})",
        f"<b>SBC เป็นต้นทุนก้อนใหญ่:</b> {pct(D['sbc_pct'][0])} ของรายได้ (2021) → {pct(D['sbc_pct'][4])} (2025) → "
        f"{pct(D['sbc_pct'][5])} (LTM) ถ้าไม่หัก SBC FCF จะดูสูงกว่าที่เหลือจริงให้ผู้ถือหุ้น "
        f"(SBC 9M 2026 ในเอกสารยื่นขัดกันเอง 1,829 vs 1,846 ล้านดอลลาร์ ที่นี่ใช้ 1,829 จากกระแสเงินสด)",
        f"<b>กำไรจากการดำเนินงาน:</b> ${money(o[0])}M → ${money(o[4])}M · LTM ${money(o[5])}M "
        f"(margin {pct(D['op_m'][0])} → {pct(D['op_m'][4])} → {pct(D['op_m'][5])}) "
        f"· กำไรสุทธิถูกบิดเบือนจากรายการพิเศษ (ภาษีเป็นผลได้ FY2023 และกำไรจาก strategic investments 9M 2026) ใช้เทียบข้ามปีตรง ๆ ไม่ได้ "
        f"[ที่มา: NOW-FACTS.md ข้อควรระวังข้อ 4]",
        "<b>หุ้นแตก 5:1 (ธ.ค. 2025):</b> ตารางนี้จึงไม่มี EPS หรือจำนวนหุ้น ใช้เฉพาะยอดรวมเป็นดอลลาร์ "
        "[ที่มา: NOW-FACTS.md ข้อควรระวังข้อ 1]",
    ]


SRC_LINES = [
    "ที่มา: SEC companyfacts ของ ServiceNow (data/raw/NOW.json) หน่วยเดิมเป็นดอลลาร์เต็มจำนวน แปลงเป็นล้านดอลลาร์ด้วยสคริปต์ "
    "output/NOW/tools/build_5yr.py · แต่ละงวดเลือกค่าจากไฟล์ 10-K/10-Q ที่ยื่นล่าสุด · "
    "LTM = FY2025 − 9 เดือน 2025 + 9 เดือน 2026 (12 เดือนถึง 30 ก.ย. 2026) · CAGR คำนวณ 4 ปี (2021→2025) ไม่รวม LTM · "
    "FCF แบบง่ายเป็นนิยามของเราเอง ไม่ใช่ FCF นิยามบริษัท (บริษัทบวกกลับต้นทุนควบรวมและคำตัดสินคดี) "
    "· ตรวจสคริปต์กับค่าใน NOW-FACTS.md แล้ว (ผ่านทุกค่าที่ซ้ำกัน)",
    "ปี 2021–2022 ตัวเลขดอลลาร์รวมไม่ขึ้นกับการแตกหุ้น จึงเทียบข้ามปีได้ · ปี 2026 มีดีลใหญ่ (Armis, Veza) งวดเปรียบเทียบตรง ๆ จึงมีข้อจำกัด",
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
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:760px}
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
    lis = "".join(f"<li>{b}</li>" for b in bullets())
    srcs = "".join(f'<div class="src">{escape(t)}</div>' for t in SRC_LINES)
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NOW เทียบงบ 5 ปี</title>
<style>
{CSS_COMMON}</style></head><body><div class="wrap">
<h1>ServiceNow (NOW) — เทียบงบ 5 ปี</h1>
<div class="sub">ปีงบ 2021–2025 (สิ้นปี 31 ธ.ค.) และ 12 เดือนถึง 30 ก.ย. 2026 (LTM) · ตัวเลขจาก SEC companyfacts · สร้างด้วยสคริปต์ ไม่ได้กรอกมือ</div>
<span class="badge">สถานะ: draft</span><span class="badge">ไม่มี EPS/จำนวนหุ้น (หุ้นแตก 5:1)</span>

<section class="card"><h2>ภาพรวม</h2><ul>{lis}</ul></section>

<section class="card"><h2>ตารางเทียบ 5 ปี (ล้านดอลลาร์)</h2>{table_html()}
<div class="src"><span class="chip good">เขียว</span> เพิ่มขึ้น · <span class="chip bad">แดง</span> ลดลง · <span class="chip warn">เหลือง</span> ต้นทุนที่เพิ่ม (ไม่ตัดสินดีร้าย) · "—" = ไม่มีข้อมูลหรือคำนวณไม่ได้</div></section>

<section class="card"><h2>กราฟ</h2>{charts_html()}{srcs}</section>
</div></body></html>
"""


def ext_block():
    lis = "".join(f"<li>{b}</li>" for b in bullets())
    srcs = "".join(f'<div class="src">{escape(t)}</div>' for t in SRC_LINES[:2])
    return f"""<!--EXT5-START-->
  <details class="card x5">
    <summary><span class="num">+</span>เสริม: เทียบงบ 5 ปี (2021–2025 + LTM) พร้อมกราฟ <small>— คลิกเพื่อขยาย</small></summary>
    <ul>{lis}</ul>
    {table_html()}
    {charts_html()}
    {srcs}
    <div class="src">รายละเอียดเต็ม: <a href="NOW-5yr.html" style="color:var(--gold)">NOW-5yr.html</a></div>
  </details>
<!--EXT5-END-->"""


if __name__ == "__main__":
    (OUT_DIR / "NOW-5yr.html").write_text(page_5yr(), encoding="utf-8")
    print("เขียน", OUT_DIR / "NOW-5yr.html")
    info = OUT_DIR / "NOW-infographic.html"
    if info.exists():
        t = info.read_text(encoding="utf-8")
        a, b = t.find("<!--EXT5-START-->"), t.find("<!--EXT5-END-->")
        if a < 0 or b < 0:
            print("ไม่พบเครื่องหมาย EXT5 ใน NOW-infographic.html")
            sys.exit(1)
        info.write_text(t[:a] + ext_block() + t[b + len("<!--EXT5-END-->"):], encoding="utf-8")
        print("อัปเดตส่วนพับใน", info)
    print("LTM:", {k: round(D[k][5], 1) for k in D if D[k][5] is not None})
