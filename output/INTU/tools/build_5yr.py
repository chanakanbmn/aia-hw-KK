"""สร้างหน้าเทียบงบ 5 ปีของ INTU (FY2022-FY2026) จาก companyfacts.json ของ SEC

รัน (จากที่ไหนก็ได้):
    "D:/Let's go/.venv/Scripts/python.exe" -I "D:/Let's go/homework/aia-hw-KK/output/INTU/tools/build_5yr.py"

อ่าน : data/raw/INTU.json  (SEC companyfacts)
เขียน: output/INTU/INTU-5yr.html
       และแทนที่ส่วนระหว่าง <!--EXT5-START--> ... <!--EXT5-END--> ใน output/INTU/INTU-infographic.html (ถ้ามีไฟล์)

หลักการ: ตัวเลขทุกตัวในหน้าเทียบงบมาจาก JSON ด้วยโค้ดนี้เท่านั้น ไม่พิมพ์ตัวเลขด้วยมือ
ยกเว้นค่าคงที่ที่ระบุที่มาไว้ด้านล่าง (CHECK_FACTS ใช้ตรวจเทียบ INTU-FACTS.md, TAX_FY27_ESTIMATE_MUSD)
ถ้างวดไหนไม่มีข้อมูลใน JSON จะเว้นว่างและรายงานท้ายการรัน ไม่เดา
"""
import json
import math
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
ROOT = HERE.parents[2]  # .../aia-hw-KK
SRC = ROOT / "data" / "raw" / "INTU.json"
FY_LIST = [2022, 2023, 2024, 2025, 2026]
BASE_YEAR = 2021  # ใช้เป็นฐานคำนวณโต FY2022 เท่านั้น ไม่แสดงในตาราง
TODAY = "2026-11-03"

# ภาษีเงินสดที่บริษัทคาดจ่าย FY2027 "ประมาณ 2 พันล้านดอลลาร์" [ที่มา: INTU-FACTS.md แถว 60, INTU.md ส่วน 2]
TAX_FY27_ESTIMATE_MUSD = 2000

# ค่าที่ตรวจเทียบ INTU-FACTS.md (หน่วยล้านดอลลาร์) แถว #1,#2,#20,#53,#59,#62,#68,#69,#126
CHECK_FACTS = {
    ("rev", 2026): 21448, ("rev", 2025): 18831, ("rev", 2024): 16285, ("rev", 2023): 14368, ("rev", 2022): 12726,
    ("ni", 2023): 2384, ("cfo", 2023): 5046, ("sbc", 2023): 1712,
    ("taxpaid", 2026): 281, ("taxpaid", 2025): 1408, ("taxpaid", 2024): 1881,
    ("sbc", 2026): 2056, ("sbc", 2025): 1968, ("sbc", 2024): 1940,
    ("fcf", 2026): 8617, ("fcf", 2025): 6083, ("fcf", 2024): 4634,
    ("fcf_sbc", 2026): 6561, ("fcf_sbc", 2025): 4115, ("fcf_sbc", 2024): 2694,
}

TAGS = {
    "rev": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "opinc": ["OperatingIncomeLoss"],
    "ni": ["NetIncomeLoss"],
    "pretax": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "taxexp": ["IncomeTaxExpenseBenefit"],
    "taxpaid": ["IncomeTaxesPaidNet", "IncomeTaxesPaid"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "ppe": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "sw": ["PaymentsToDevelopSoftware", "CapitalizedComputerSoftwareAdditions"],
    "sbc": ["ShareBasedCompensation"],
}


# ---------------------------------------------------------------- ดึงข้อมูล
def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def annual(gaap, tags, year, notes):
    """ค่ารายปีบัญชี (สิ้น 31 ก.ค. ของ year) จาก 10-K: ลอง tag ตามลำดับ เลือกฉบับที่ยื่นล่าสุด"""
    for tag in tags:
        rows = [
            r for r in gaap.get(tag, {}).get("units", {}).get("USD", [])
            if r.get("form") == "10-K" and "start" in r and r["end"] == f"{year}-07-31"
            and 355 <= (_d(r["end"]) - _d(r["start"])).days <= 370
        ]
        if not rows:
            continue
        vals = {r["val"] for r in rows}
        if len(vals) > 1:
            notes.append(f"{tag} FY{year}: ค่าต่างกันระหว่างฉบับที่ยื่น {sorted(vals)} ใช้ฉบับล่าสุด")
        best = max(rows, key=lambda r: r["filed"])
        return {"val": best["val"], "tag": tag, "filed": best["filed"], "accn": best.get("accn")}
    return None


def load():
    facts = json.loads(SRC.read_text(encoding="utf-8"))
    gaap = facts["facts"]["us-gaap"]
    notes, raw = [], {}
    for key, tags in TAGS.items():
        for y in [BASE_YEAR] + FY_LIST:
            raw[(key, y)] = annual(gaap, tags, y, notes)
    return facts, raw, notes


def build_series(raw):
    """คืน dict key -> {year: ล้านดอลลาร์ หรือ None} และ dict ที่มา (tag) ต่อปี"""
    s, tags = {}, {}
    for key in TAGS:
        s[key] = {}
        tags[key] = {}
        for y in [BASE_YEAR] + FY_LIST:
            r = raw[(key, y)]
            s[key][y] = None if r is None else r["val"] / 1e6
            tags[key][y] = None if r is None else r["tag"]

    def sub(a, b):
        return None if a is None or b is None else a - b

    def add(a, b):
        return None if a is None or b is None else a + b

    def ratio(a, b):
        return None if a is None or b in (None, 0) else a / b

    s["capex"] = {y: add(s["ppe"][y], s["sw"][y]) for y in s["ppe"]}
    s["fcf"] = {y: sub(s["cfo"][y], s["capex"][y]) for y in s["ppe"]}
    s["fcf_sbc"] = {y: sub(s["fcf"][y], s["sbc"][y]) for y in s["ppe"]}
    for name, num in (("opm", "opinc"), ("nim", "ni"), ("cfom", "cfo"), ("fcfm", "fcf"), ("fcfsm", "fcf_sbc"), ("sbcm", "sbc")):
        s[name] = {y: (None if ratio(s[num][y], s["rev"][y]) is None else ratio(s[num][y], s["rev"][y]) * 100) for y in s["rev"]}
    s["etr"] = {y: (None if ratio(s["taxexp"][y], s["pretax"][y]) is None else ratio(s["taxexp"][y], s["pretax"][y]) * 100) for y in s["rev"]}
    s["cfo_ni"] = {y: ratio(s["cfo"][y], s["ni"][y]) for y in s["rev"]}
    s["cash_vs_exp"] = {y: (None if ratio(s["taxpaid"][y], s["taxexp"][y]) is None else ratio(s["taxpaid"][y], s["taxexp"][y]) * 100) for y in s["rev"]}
    s["rev_yoy"] = {}
    for y in FY_LIST:
        p = s["rev"][y - 1]
        s["rev_yoy"][y] = None if p is None or s["rev"][y] is None else (s["rev"][y] / p - 1) * 100
    return s, tags


def check_against_facts(s):
    bad = []
    for (k, y), want in CHECK_FACTS.items():
        got = s[k][y]
        if got is None or round(got) != want:
            bad.append(f"{k} FY{y}: JSON={got} FACTS={want}")
    return bad


# ---------------------------------------------------------------- จัดรูปแบบ
def n0(v):
    return "–" if v is None else f"{v:,.0f}"


def pct(v, d=1):
    return "–" if v is None else f"{v:.{d}f}%"


def x2(v):
    return "–" if v is None else f"{v:.2f}x"


def yoy(a, b):
    return None if a is None or b is None or b == 0 else (a / b - 1) * 100


def cagr(a, b, years):
    return None if a is None or b is None or a <= 0 or b <= 0 else ((a / b) ** (1 / years) - 1) * 100


def chip(v, mode="gb"):
    if v is None:
        return '<span class="na">–</span>'
    cls = "warn" if mode == "warn" else ("good" if v >= 0 else "bad")
    sign = "+" if v > 0 else ""
    return f'<span class="chip {cls}">{sign}{v:.1f}%</span>'


def cell(v, fmt=n0):
    if v is None:
        return '<td class="r na" title="ไม่มีข้อมูลใน companyfacts สำหรับงวดนี้">–</td>'
    return f'<td class="r">{fmt(v)}</td>'


# ---------------------------------------------------------------- กราฟ SVG
COLORS = ["#e8c26a", "#5fb3d9", "#6fcf97", "#eb7a6a", "#b39ddb"]


def nice_max(v, steps=4):
    if v <= 0:
        return 1.0
    raw = v / steps
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag * steps
    return 10 * mag * steps


def bar_chart(series, years, aria, fmt, label_fmt=None):
    """series: [(ชื่อ, สี, {year: value|None})]  fmt: จัดรูปป้ายแกน"""
    label_fmt = label_fmt or fmt
    W, H, L, R, TOP, BASE = 640, 250, 44, 630, 22, 206
    vals = [v for _, _, d in series for v in d.values() if v is not None]
    top = nice_max(max(vals) if vals else 1)
    ys = lambda v: BASE - (v / top) * (BASE - TOP)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{aria}" style="width:100%;height:auto">']
    for i in range(5):
        v = top * i / 4
        y = ys(v)
        out.append(f'<line x1="{L}" x2="{R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#3a2f17" stroke-width="1"/>')
        out.append(f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" fill="#a89c80" font-size="10">{fmt(v)}</text>')
    gw = (R - L) / len(years)
    n = len(series)
    bw = min(44, (gw - 24) / n)
    for gi, y in enumerate(years):
        gx = L + gi * gw
        start = gx + (gw - bw * n) / 2
        out.append(f'<text x="{gx + gw / 2:.1f}" y="224" text-anchor="middle" fill="#a89c80" font-size="11">FY{y}</text>')
        for si, (name, color, d) in enumerate(series):
            v = d.get(y)
            x = start + si * bw
            if v is None:
                out.append(f'<text x="{x + bw / 2:.1f}" y="{BASE - 6}" text-anchor="middle" fill="#a89c80" font-size="9">ไม่มีข้อมูล</text>')
                continue
            h = max((v / top) * (BASE - TOP), 0)
            out.append(
                f'<rect x="{x:.1f}" y="{BASE - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" rx="2" fill="{color}">'
                f'<title>{name} FY{y}: {label_fmt(v)}</title></rect>'
                f'<text x="{x + (bw - 2) / 2:.1f}" y="{BASE - h - 4:.1f}" text-anchor="middle" fill="#f1ead8" font-size="9">{label_fmt(v)}</text>'
            )
    out.append("</svg>")
    return "".join(out)


def line_chart(series, years, aria):
    W, H, L, R, TOP, BASE = 640, 250, 44, 630, 22, 206
    vals = [v for _, _, d in series for v in d.values() if v is not None]
    top = nice_max(max(vals), 4)
    ys = lambda v: BASE - (v / top) * (BASE - TOP)
    gw = (R - L) / len(years)
    xs = lambda i: L + gw * i + gw / 2
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{aria}" style="width:100%;height:auto">']
    for i in range(5):
        v = top * i / 4
        y = ys(v)
        out.append(f'<line x1="{L}" x2="{R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#3a2f17" stroke-width="1"/>')
        out.append(f'<text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" fill="#a89c80" font-size="10">{v:.0f}%</text>')
    for i, y in enumerate(years):
        out.append(f'<text x="{xs(i):.1f}" y="224" text-anchor="middle" fill="#a89c80" font-size="11">FY{y}</text>')
    for name, color, d in series:
        pts = [(xs(i), ys(d[y]), d[y], y) for i, y in enumerate(years) if d.get(y) is not None]
        if len(pts) > 1:
            out.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (color, " ".join(f"{x:.1f},{yy:.1f}" for x, yy, _, _ in pts)))
        for k, (x, yy, v, yr) in enumerate(pts):
            out.append(f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="3.5" fill="{color}"><title>{name} FY{yr}: {v:.1f}%</title></circle>')
            if k in (0, len(pts) - 1):
                out.append(f'<text x="{x:.1f}" y="{yy - 7:.1f}" text-anchor="middle" fill="{color}" font-size="9">{v:.1f}%</text>')
    out.append("</svg>")
    return "".join(out)


def legend(series, note, cls="legend"):
    items = "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c, _ in series)
    return f'<div class="{cls}">{items}<em>{note}</em></div>'


def chart_block(title, series, years, aria, fmt, note, src, kind="bar", cls="chart", lcls="legend", hcls=None, label_fmt=None):
    svg = line_chart(series, years, aria) if kind == "line" else bar_chart(series, years, aria, fmt, label_fmt)
    head = f'<div class="{hcls}">{title}</div>' if hcls else f"<h2>{title}</h2>"
    return f'{head}<div class="{cls}">{legend(series, note, lcls)}{svg}</div><div class="src">{src}</div>'


# ---------------------------------------------------------------- เนื้อหา
def src_of(tags, key):
    used = []
    for y in FY_LIST:
        t = tags[key][y]
        if t and t not in used:
            used.append(t)
    return " / ".join(used) if used else "ไม่พบ tag"


def table_rows(s, tags, compact=False):
    """แถวตารางหลัก: (ชื่อ, หน่วย, key, fmt, โหมด chip, ที่มา) """
    def row(label, unit, key, fmt=n0, mode="gb", with_growth=True, src=None):
        cells = "".join(cell(s[key][y], fmt) for y in FY_LIST)
        if with_growth:
            g = chip(yoy(s[key][2026], s[key][2025]), mode)
            c = chip(cagr(s[key][2026], s[key][2022], 4), mode)
        else:
            g = c = '<span class="na">–</span>'
        srcs = src if src is not None else src_of(tags, key)
        tail = "" if compact else f'<td class="tg">{srcs}</td>'
        return f'<tr><td>{label} <small>({unit})</small></td>{cells}<td class="r">{g}</td><td class="r">{c}</td>{tail}</tr>'

    R = []
    R.append(row("รายได้รวม", "$M", "rev"))
    R.append(row("กำไรจากการดำเนินงาน", "$M", "opinc"))
    R.append(row("กำไรสุทธิ", "$M", "ni"))
    R.append(row("เงินสดจากการดำเนินงาน (CFO)", "$M", "cfo"))
    R.append(row("ซื้อทรัพย์สินและอุปกรณ์ (PP&amp;E)", "$M", "ppe", mode="warn"))
    R.append(row("capitalized software", "$M", "sw", mode="warn"))
    R.append(row("capex รวม (PP&amp;E + capitalized software)", "$M", "capex", mode="warn", src="คำนวณ: ppe + sw"))
    R.append(row("FCF = CFO − capex รวม", "$M", "fcf", src="คำนวณ: cfo − capex รวม"))
    R.append(row("ค่าหุ้นพนักงาน (SBC)", "$M", "sbc", mode="warn"))
    R.append(row("FCF หลังหัก SBC", "$M", "fcf_sbc", src="คำนวณ: FCF − sbc"))
    R.append(row("ภาษีเงินได้ (ค่าใช้จ่าย)", "$M", "taxexp", mode="warn"))
    R.append(row("ภาษีเงินสดจ่ายสุทธิ", "$M", "taxpaid", mode="warn",
                 src="IncomeTaxesPaidNet (FY24–26) · IncomeTaxesPaid (FY22–23)"))
    if compact:
        return "".join(R)
    R.append(row("อัตรากำไรจากการดำเนินงาน", "%", "opm", pct, with_growth=False, src="คำนวณ: opinc ÷ rev"))
    R.append(row("อัตรากำไรสุทธิ", "%", "nim", pct, with_growth=False, src="คำนวณ: ni ÷ rev"))
    R.append(row("CFO ÷ รายได้", "%", "cfom", pct, with_growth=False, src="คำนวณ"))
    R.append(row("FCF ÷ รายได้", "%", "fcfm", pct, with_growth=False, src="คำนวณ"))
    R.append(row("FCF หลังหัก SBC ÷ รายได้", "%", "fcfsm", pct, with_growth=False, src="คำนวณ"))
    R.append(row("SBC ÷ รายได้", "%", "sbcm", pct, with_growth=False, src="คำนวณ"))
    R.append(row("อัตราภาษีที่แท้จริง (ภาษี ÷ กำไรก่อนภาษี)", "%", "etr", pct, with_growth=False,
                 src="คำนวณ: IncomeTaxExpenseBenefit ÷ IncomeLoss…BeforeIncomeTaxes…"))
    R.append(row("ภาษีเงินสดจ่าย ÷ ค่าใช้จ่ายภาษี", "%", "cash_vs_exp", pct, with_growth=False, src="คำนวณ"))
    R.append(row("CFO ÷ กำไรสุทธิ", "เท่า", "cfo_ni", x2, with_growth=False, src="คำนวณ"))
    return "".join(R)


def head_row(compact=False):
    th = "".join(f'<th class="r">FY{y}</th>' for y in FY_LIST)
    tail = "" if compact else "<th>ที่มา (tag ใน companyfacts)</th>"
    return f'<tr><th>รายการ</th>{th}<th class="r">FY26 YoY</th><th class="r">CAGR 22→26</th>{tail}</tr>'


def observations(s):
    r = s["rev"]
    items = [
        f"<li><b>รายได้โตทุกปี:</b> ${n0(r[2022])}M (FY2022) → ${n0(r[2026])}M (FY2026) CAGR {pct(cagr(r[2026], r[2022], 4))} ต่อปี "
        f"· YoY รายปี {', '.join(pct(s['rev_yoy'][y]) for y in FY_LIST)}</li>",
        f"<li><b>margin ดำเนินงาน:</b> {pct(s['opm'][2022])} (FY2022) → {pct(s['opm'][2026])} (FY2026) · "
        f"margin สุทธิ {pct(s['nim'][2022])} → {pct(s['nim'][2026])}</li>",
        f"<li><b>SBC:</b> ${n0(s['sbc'][2022])}M → ${n0(s['sbc'][2026])}M เพิ่มขึ้นในเชิงมูลค่า แต่สัดส่วนต่อรายได้ {pct(s['sbcm'][2022])} → {pct(s['sbcm'][2026])}</li>",
        f"<li><b>FCF หลังหัก SBC (ตามงบ):</b> ${n0(s['fcf_sbc'][2022])}M → ${n0(s['fcf_sbc'][2026])}M · "
        f"FY2026 ถูกยกด้วยภาษีเงินสดจ่ายต่ำผิดปกติ (ดูกล่องเตือนด้านบน) จึงไม่ควรอ่านเป็นการโตต่อเนื่อง</li>",
        f"<li><b>ภาษีเงินสดจ่ายเทียบค่าใช้จ่ายภาษี:</b> {', '.join(f'FY{y} {pct(s['cash_vs_exp'][y], 0)}' for y in FY_LIST)} "
        f"(FY2026 ต่ำสุดในช่วงนี้)</li>",
    ]
    return "<ul>" + "".join(items) + "</ul>"


def warn_box(s):
    adj_tax = TAX_FY27_ESTIMATE_MUSD - s["taxpaid"][2026]
    fcf_adj = s["fcf"][2026] - adj_tax
    fcf_adj_sbc = fcf_adj - s["sbc"][2026]
    return (
        '<div class="warnbox"><b>คำเตือน: CFO FY2026 สูงเพราะภาษีเงินสดจ่ายต่ำผิดปกติ</b> — '
        f'ภาษีเงินสดจ่ายสุทธิ ${n0(s["taxpaid"][2026])} ล้านดอลลาร์ เทียบ ${n0(s["taxpaid"][2025])} ใน FY2025 และ ${n0(s["taxpaid"][2024])} ใน FY2024 '
        f'[ที่มา: tag IncomeTaxesPaidNet ใน companyfacts] ขณะค่าใช้จ่ายภาษีในงบกำไรขาดทุน FY2026 คือ ${n0(s["taxexp"][2026])}M · '
        f'CFO ÷ กำไรสุทธิ = {x2(s["cfo_ni"][2026])} (FY2025: {x2(s["cfo_ni"][2025])}) · '
        'บริษัทอธิบายว่ากฎหมาย OBBBA คืนสิทธิหักค่า R&amp;D ทันที และคาดจะจ่ายภาษีราว 2 พันล้านดอลลาร์ใน FY2027 [ที่มา: INTU-FACTS.md แถว 60] '
        f'· ถ้าสมมติหักภาษีที่คาดเพิ่ม (2,000 − {n0(s["taxpaid"][2026])} = ${n0(adj_tax)}M) FCF FY2026 จะเป็น ${n0(fcf_adj)}M '
        f'และ ${n0(fcf_adj_sbc)}M หลังหัก SBC [คำนวณตามวิธีใน INTU.md ส่วน 2 · ตัวเลข 2,000 เป็นประมาณการปัดของบริษัท ไม่ใช่ตัวเลขจริง]</div>'
    )


CSS = """
:root{--bg:#0b0a08;--card:#16130d;--line:#3a2f17;--gold:#e8c26a;--gold2:#b8914a;--text:#f1ead8;--mute:#a89c80;--good:#6fcf97;--bad:#eb7a6a;--warn:#e8c26a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Segoe UI","Noto Sans Thai",system-ui,sans-serif;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto;padding:20px 16px 48px}
h1{margin:0;font-size:26px;color:var(--gold)}.sub{color:var(--mute);font-size:14px;margin:4px 0 12px}
.badge{display:inline-block;border:1px solid var(--gold2);color:var(--gold);border-radius:99px;padding:2px 10px;font-size:12px;margin:0 6px 4px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:14px;overflow-x:auto;min-width:0}
.card h2{margin:0 0 8px;font-size:17px;color:var(--gold)}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:760px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--gold2);font-weight:600}
.r{text-align:right;white-space:nowrap}small{color:var(--mute)}.na{color:var(--mute)}.tg{color:var(--mute);font-size:11px}
.chip{display:inline-block;border-radius:6px;padding:1px 7px;font-weight:700}
.chip.good{color:var(--good);background:rgba(111,207,151,.16)}.chip.bad{color:var(--bad);background:rgba(235,122,106,.16)}.chip.warn{color:var(--warn);background:rgba(232,194,106,.16)}
.src{color:var(--mute);font-size:11px;margin-top:8px}
ul{margin:6px 0 0;padding-left:18px}li{margin:4px 0;font-size:13px}
.chart{min-width:520px}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--mute);margin-bottom:4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}.legend em{margin-left:auto;font-style:normal}
.warnbox{border:1px dashed var(--bad);color:var(--bad);border-radius:10px;padding:8px 12px;font-size:12.5px;margin-top:12px}
"""


def page_5yr(s, tags, notes, missing):
    yrs = FY_LIST
    c = []
    c.append(chart_block(
        "รายได้รวม", [("รายได้รวม", COLORS[0], s["rev"])], yrs, "รายได้รวม", lambda v: f"{v / 1000:,.1f}",
        "พันล้านดอลลาร์ · ปีบัญชีสิ้น 31 ก.ค.", f"[ที่มา: companyfacts tag {src_of(tags, 'rev')}] · แสดงเฉพาะรวม ไม่แยกส่วนงาน (ส่วนงานถูกจัดใหม่ใน 10-K FY2026 เทียบข้ามฉบับไม่ได้)"))
    c.append(chart_block(
        "CFO เทียบ capex รวม (รวม capitalized software)",
        [("CFO", COLORS[0], s["cfo"]), ("capex รวม", COLORS[1], s["capex"])], yrs, "CFO และ capex",
        lambda v: f"{v / 1000:,.1f}", "พันล้านดอลลาร์ · แท่ง capex เล็กมากเทียบ CFO",
        "[ที่มา: tag NetCashProvidedByUsedInOperatingActivities, PaymentsToAcquirePropertyPlantAndEquipment, PaymentsToDevelopSoftware · capex รวมคำนวณ]",
        label_fmt=lambda v: f"{v / 1000:,.2f}" if v < 1000 else f"{v / 1000:,.1f}"))
    c.append(chart_block(
        "FCF เทียบ FCF หลังหัก SBC (ตามงบ)",
        [("FCF", COLORS[0], s["fcf"]), ("FCF หลังหัก SBC", COLORS[1], s["fcf_sbc"])], yrs, "FCF",
        lambda v: f"{v / 1000:,.1f}", "พันล้านดอลลาร์ · FY2026 ได้อานิสงส์ภาษีเงินสดจ่ายต่ำ",
        "[ที่มา: คำนวณ FCF = CFO − (PP&amp;E + capitalized software) · แถวตรวจเทียบ INTU-FACTS.md #68, #69 ตรงกันทั้ง FY2024–26]"))
    c.append(chart_block(
        "ค่าหุ้นพนักงาน (SBC)", [("SBC", COLORS[3], s["sbc"])], yrs, "SBC", lambda v: f"{v / 1000:,.2f}",
        "พันล้านดอลลาร์", f"[ที่มา: tag {src_of(tags, 'sbc')}]"))
    c.append(chart_block(
        "กำไรจากการดำเนินงานเทียบกำไรสุทธิ",
        [("กำไรจากการดำเนินงาน", COLORS[0], s["opinc"]), ("กำไรสุทธิ", COLORS[1], s["ni"])], yrs, "กำไร",
        lambda v: f"{v / 1000:,.1f}", "พันล้านดอลลาร์", "[ที่มา: tag OperatingIncomeLoss, NetIncomeLoss]"))
    c.append(chart_block(
        "Margin ต่าง ๆ (% ของรายได้)",
        [("กำไรดำเนินงาน", COLORS[0], s["opm"]), ("กำไรสุทธิ", COLORS[1], s["nim"]),
         ("FCF", COLORS[2], s["fcfm"]), ("FCF หลังหัก SBC", COLORS[3], s["fcfsm"])], yrs, "margin", None,
        "ป้ายแสดงปีแรกและปีล่าสุด วางเมาส์ดูค่าทุกจุด", "[ที่มา: คำนวณจากรายได้และรายการข้างต้น]", kind="line"))
    c.append(chart_block(
        "ภาษีเงินสดจ่ายเทียบค่าใช้จ่ายภาษี",
        [("ภาษีเงินสดจ่ายสุทธิ", COLORS[3], s["taxpaid"]), ("ค่าใช้จ่ายภาษี (งบกำไรขาดทุน)", COLORS[1], s["taxexp"])], yrs, "ภาษี",
        lambda v: f"{v:,.0f}", "ล้านดอลลาร์ · FY2026 ภาษีเงินสดจ่ายต่ำผิดปกติ",
        "[ที่มา: tag IncomeTaxesPaidNet (FY24–26) และ IncomeTaxesPaid (FY22–23), IncomeTaxExpenseBenefit]"))

    sections = "".join(f'<section class="card">{b}</section>' for b in c)
    miss = "<li>ไม่มีรายการใดขาดข้อมูลใน FY2022–FY2026</li>" if not missing else "".join(f"<li>{m}</li>" for m in missing)
    extra = "".join(f"<li>{n}</li>" for n in notes)
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>INTU เทียบงบ 5 ปี</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>Intuit (INTU) — เทียบงบ 5 ปี</h1>
<div class="sub">ปีบัญชี FY2022–FY2026 (สิ้นปีบัญชี 31 ก.ค. FY2026 = สิ้นสุด 31 ก.ค. 2026) · ตัวเลขดึงด้วยสคริปต์จาก SEC companyfacts</div>
<span class="badge">สถานะ: draft</span><span class="badge">สร้างเมื่อ {TODAY}</span><span class="badge">ไม่ใช่คำแนะนำลงทุน</span>

<section class="card"><h2>ภาพรวมจากตัวเลข 5 ปี</h2>
{warn_box(s)}
{observations(s)}
<div class="src">ทุกตัวเลขในหน้านี้คำนวณจากไฟล์ data/raw/INTU.json ด้วย output/INTU/tools/build_5yr.py (รันซ้ำได้) · ถ้างวดไหนไม่มีข้อมูลจะเว้นว่างเป็น "–" ไม่เดา</div></section>

<section class="card"><h2>ตารางเทียบ 5 ปี (หน่วย $M ยกเว้นระบุ)</h2>
<table>{head_row()}{table_rows(s, tags)}</table>
<div class="src"><span class="chip good">เขียว</span> เพิ่มขึ้น · <span class="chip bad">แดง</span> ลดลง · <span class="chip warn">เหลือง</span> รายการที่ "เพิ่ม/ลด" ไม่ได้แปลว่าดีหรือร้ายโดยตัวเอง (capex, SBC, ภาษี) · CAGR คำนวณ 4 ปี (FY2022→FY2026) · FY2022 YoY ใช้ฐาน FY2021 ใน JSON (ไม่แสดงในตาราง) · capex รวม = PP&amp;E + capitalized software ตามนิยามเดียวกับ INTU-FACTS.md แถว 68 (ต่างจากสูตร watchlist ใน src/ ที่นับเฉพาะ PP&amp;E)</div></section>

{sections}

<section class="card"><h2>ที่มาและข้อจำกัด</h2>
<ul>
<li><b>แหล่งข้อมูล:</b> SEC EDGAR companyfacts (CIK 0000896878) ไฟล์ data/raw/INTU.json · เลือกเฉพาะค่ารายปีจากฟอร์ม 10-K ที่งวดจบ 31 ก.ค. และถ้ามีหลายฉบับใช้ฉบับที่ยื่นล่าสุด</li>
<li><b>ส่วนงาน:</b> ไม่แสดงรายได้แยกส่วนงาน เพราะส่วนงานถูกจัดใหม่ใน 10-K FY2026 (ตัวเลข FY2025 ใน 10-K สองฉบับต่างกัน เทียบข้ามฉบับไม่ได้) [ที่มา: INTU-FACTS.md แถว 100]</li>
<li><b>ภาษีเงินสดจ่าย:</b> ใช้ tag IncomeTaxesPaidNet (FY2024–26) และ IncomeTaxesPaid (FY2022–23) สองtag นี้ตรงกันใน FY2024–25 ที่มีทั้งคู่</li>
<li><b>รายการที่ขาดข้อมูล:</b></li>{miss}
{('<li><b>หมายเหตุจากสคริปต์:</b></li>' + extra) if extra else ''}
<li>ยังไม่ผ่าน check-jing · กรอบวิเคราะห์ ไม่ใช่คำแนะนำลงทุนส่วนบุคคล · ราคาตลาดไม่เกี่ยวกับหน้านี้</li>
</ul></section>
</div></body></html>
"""


EXT_CSS_NOTE = ""


def ext5_block(s, tags):
    yrs = FY_LIST
    r = s["rev"]
    bullets = (
        "<ul>"
        f"<li><b>ธุรกิจโตต่อเนื่อง:</b> รายได้ ${n0(r[2022])}M (FY2022) → ${n0(r[2026])}M (FY2026) CAGR {pct(cagr(r[2026], r[2022], 4))} ต่อปี margin ดำเนินงาน {pct(s['opm'][2022])} → {pct(s['opm'][2026])}</li>"
        f"<li><b>FCF หลังหัก SBC ตามงบ:</b> ${n0(s['fcf_sbc'][2022])}M → ${n0(s['fcf_sbc'][2026])}M แต่ FY2026 ได้อานิสงส์ภาษีเงินสดจ่ายต่ำผิดปกติ (${n0(s['taxpaid'][2026])}M เทียบ ${n0(s['taxpaid'][2025])}M ใน FY2025)</li>"
        f"<li><b>SBC:</b> ${n0(s['sbc'][2022])}M → ${n0(s['sbc'][2026])}M สัดส่วนต่อรายได้ {pct(s['sbcm'][2022])} → {pct(s['sbcm'][2026])}</li>"
        "<li><b>ไม่แสดงรายได้แยกส่วนงานข้ามปี:</b> ส่วนงานถูกจัดใหม่ใน 10-K FY2026 เทียบข้ามฉบับไม่ได้</li>"
        "</ul>"
    )
    table = f'<table>{head_row(True)}{table_rows(s, tags, compact=True)}</table>'
    ch = []
    ch.append(chart_block("รายได้รวม", [("รายได้รวม", COLORS[0], s["rev"])], yrs, "รายได้รวม", lambda v: f"{v / 1000:,.1f}",
                          "พันล้านดอลลาร์", "", cls="x5chart", lcls="x5legend", hcls="x5h"))
    ch.append(chart_block("FCF เทียบ FCF หลังหัก SBC", [("FCF", COLORS[0], s["fcf"]), ("FCF หลังหัก SBC", COLORS[1], s["fcf_sbc"])], yrs, "FCF",
                          lambda v: f"{v / 1000:,.1f}", "พันล้านดอลลาร์", "", cls="x5chart", lcls="x5legend", hcls="x5h"))
    ch.append(chart_block("ภาษีเงินสดจ่ายเทียบค่าใช้จ่ายภาษี", [("ภาษีเงินสดจ่าย", COLORS[3], s["taxpaid"]), ("ค่าใช้จ่ายภาษี", COLORS[1], s["taxexp"])], yrs, "ภาษี",
                          lambda v: f"{v:,.0f}", "ล้านดอลลาร์", "", cls="x5chart", lcls="x5legend", hcls="x5h"))
    ch = [b.replace('<div class="src"></div>', "") for b in ch]
    return (
        '<details class="card x5">\n'
        '    <summary><span class="num">+</span>เสริม: เทียบงบ 5 ปี (FY2022–FY2026) พร้อมกราฟ <small>— คลิกเพื่อขยาย</small></summary>\n'
        f"    {bullets}\n    {table}\n"
        '    <div class="src"><span class="chip good">เขียว</span> เพิ่มขึ้น · <span class="chip bad">แดง</span> ลดลง · <span class="chip warn">เหลือง</span> รายการที่เพิ่ม/ลดไม่ได้แปลว่าดีหรือร้าย (capex, SBC, ภาษี) · CAGR 4 ปี FY2022→FY2026</div>\n'
        f'    {"".join(ch)}\n'
        '    <div class="src">[ที่มา: SEC companyfacts data/raw/INTU.json ดึงด้วย output/INTU/tools/build_5yr.py · tag ทุกแถวดูใน <a href="INTU-5yr.html" style="color:var(--gold)">INTU-5yr.html</a> · ยังไม่ผ่าน check-jing]</div>\n'
        "  </details>"
    )


def inject(info_path, block):
    text = info_path.read_text(encoding="utf-8")
    a, b = "<!--EXT5-START-->", "<!--EXT5-END-->"
    if a not in text or b not in text:
        return False
    head, rest = text.split(a, 1)
    _, tail = rest.split(b, 1)
    info_path.write_text(head + a + "\n" + block + "\n" + b + tail, encoding="utf-8")
    return True


def price_block():
    """กราฟราคาปิดรายไตรมาสจาก data/prices.csv (Yahoo แหล่งรอง [ยังไม่ยืนยัน])"""
    import csv
    rows = [(r["date"], float(r["close"])) for r in csv.DictReader(open(ROOT / "data" / "prices.csv", encoding="utf-8")) if r["ticker"] == "INTU"]
    W, H, L, R, T, B = 640, 170, 40, 630, 14, 140
    top = nice_max(max(v for _, v in rows))
    xs = lambda i: L + (R - L) * i / (len(rows) - 1)
    ys = lambda v: B - v / top * (B - T)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="ราคาปิดรายไตรมาส" style="width:100%;height:auto">']
    for i in range(5):
        v = top * i / 4
        o.append(f'<line x1="{L}" x2="{R}" y1="{ys(v):.1f}" y2="{ys(v):.1f}" stroke="#3a2f17"/><text x="{L-6}" y="{ys(v)+4:.1f}" text-anchor="end" fill="#a89c80" font-size="10">${v:,.0f}</text>')
    o.append('<polyline fill="none" stroke="#e8c26a" stroke-width="2" points="%s"/>' % " ".join(f"{xs(i):.1f},{ys(v):.1f}" for i, (_, v) in enumerate(rows)))
    for i, (d, v) in enumerate(rows):
        o.append(f'<circle cx="{xs(i):.1f}" cy="{ys(v):.1f}" r="3" fill="#e8c26a"><title>{d}: ${v:,.2f}</title></circle>')
    for i in (0, len(rows) - 1):
        o.append(f'<text x="{xs(i):.1f}" y="{ys(rows[i][1]) - 8:.1f}" text-anchor="middle" fill="#f1ead8" font-size="10">${rows[i][1]:,.2f}</text>')
    o.append(f'<text x="{L}" y="160" fill="#a89c80" font-size="10">{rows[0][0]}</text><text x="{R}" y="160" text-anchor="end" fill="#a89c80" font-size="10">{rows[-1][0]}</text></svg>')
    hi = max(rows, key=lambda r: r[1])
    last = rows[-1][1]
    ref = 498.92  # ราคาปิดอ้างอิงใน 10-K FY2026 (30 ม.ค. 2026) [ที่มา: INTU-FACTS.md แถว 120]
    txt = (f'<div class="kpis" style="margin-top:12px"><div class="kpi"><b class="bad">{(last/hi[1]-1)*100:.1f}%</b><span>จากจุดสูงสุดของราคาปิดรายไตรมาส ({hi[0]}: ${hi[1]:,.2f}) ในชุดข้อมูล {len(rows)} จุด</span></div>'
           f'<div class="kpi"><b class="bad">{(last/ref-1)*100:.1f}%</b><span>เทียบราคาปิดอ้างอิงใน 10-K FY2026 (30 ม.ค. 2026: ${ref})</span></div></div>')
    return "".join(o) + txt


def inject_price(info_path):
    text = info_path.read_text(encoding="utf-8")
    a, b = "<!--PRICE-START-->", "<!--PRICE-END-->"
    if a not in text:
        return False
    head, rest = text.split(a, 1)
    _, tail = rest.split(b, 1)
    info_path.write_text(head + a + price_block() + b + tail, encoding="utf-8")
    return True


# ค่าจาก INTU-FACTS.md (10-K FY2026 ฉบับเดียวกัน) ล้านดอลลาร์ ยกเว้น EPS: (FY2026, FY2025, แถว FACTS)
FACTS_ROWS = [
    ("EPS เจือจาง ($)", 16.46, 13.67, 21, "gb", "{:,.2f}"),
    ("Restructuring ($M)", 293, 15, 11, "warn", "{:,.0f}"),
    ("เงินสดซื้อหุ้นคืน ($M)", 5412, 2772, 70, "warn", "{:,.0f}"),
    ("เงินปันผลจ่ายเป็นเงินสด ($M)", 1347, 1189, 72, "warn", "{:,.0f}"),
]
SEG_ROWS = [
    ("Global Business Solutions", 12864, 11077, 95),
    ("Consumer (รวม TurboTax + Credit Karma + ProTax)", 8584, 7754, 96),
    ("QuickBooks Online", 5051, 4120, 98),
    ("TurboTax", 5296, 4933, 99),
    ("Credit Karma", 2641, 2200, 99),
]


def _splice(path, name, html):
    text = path.read_text(encoding="utf-8")
    a, b = f"<!--{name}-START-->", f"<!--{name}-END-->"
    if a not in text:
        return False
    head, rest = text.split(a, 1)
    _, tail = rest.split(b, 1)
    path.write_text(head + a + html + b + tail, encoding="utf-8")
    return True


def fy26_rows(s):
    out = []
    for label, key, mode, src in (("รายได้รวม ($M)", "rev", "gb", "tag Revenues"), ("กำไรจากการดำเนินงาน ($M)", "opinc", "gb", "tag OperatingIncomeLoss"),
                                  ("กำไรสุทธิ ($M)", "ni", "gb", "tag NetIncomeLoss"), ("CFO ($M)", "cfo", "gb", "tag NetCashProvidedByUsedInOperatingActivities"),
                                  ("ภาษีเงินสดจ่ายสุทธิ ($M)", "taxpaid", "warn", "tag IncomeTaxesPaidNet"), ("SBC ($M)", "sbc", "warn", "tag ShareBasedCompensation"),
                                  ("FCF = CFO − PP&amp;E − capitalized software ($M)", "fcf", "gb", "คำนวณ"), ("FCF หลังหัก SBC ($M)", "fcf_sbc", "gb", "คำนวณ")):
        out.append(f'<tr><td>{label} <small class="na">[{src}]</small></td><td class="r">{n0(s[key][2026])}</td><td class="r">{n0(s[key][2025])}</td><td class="r">{chip(yoy(s[key][2026], s[key][2025]), mode)}</td></tr>')
    for label, a, b, row, mode, f in FACTS_ROWS:
        out.append(f'<tr><td>{label} <small class="na">[INTU-FACTS.md แถว {row}]</small></td><td class="r">{f.format(a)}</td><td class="r">{f.format(b)}</td><td class="r">{chip(yoy(a, b), mode)}</td></tr>')
    out.append(f'<tr><td>CFO ÷ กำไรสุทธิ <small class="na">[คำนวณ]</small></td><td class="r">{x2(s["cfo_ni"][2026])}</td><td class="r">{x2(s["cfo_ni"][2025])}</td><td class="r"><span class="chip warn">สูงจากภาษีเงินสดจ่ายต่ำ</span></td></tr>')
    return "".join(out)


def seg_rows(s):
    out = ['<tr><th>ส่วนงาน/ผลิตภัณฑ์ ($M)</th><th class="r">FY2026</th><th class="r">FY2025</th><th class="r">เปลี่ยนแปลง</th></tr>']
    for label, a, b, row in SEG_ROWS:
        out.append(f'<tr><td>{label} <small class="na">[INTU-FACTS.md แถว {row}]</small></td><td class="r">{a:,}</td><td class="r">{b:,}</td><td class="r">{chip(yoy(a, b))}</td></tr>')
    return "".join(out)


def main():
    facts, raw, notes = load()
    s, tags = build_series(raw)
    bad = check_against_facts(s)
    missing = []
    labels = {"rev": "รายได้", "opinc": "กำไรดำเนินงาน", "ni": "กำไรสุทธิ", "cfo": "CFO", "ppe": "ซื้อ PP&E", "sw": "capitalized software",
              "sbc": "SBC", "taxexp": "ค่าใช้จ่ายภาษี", "taxpaid": "ภาษีเงินสดจ่าย", "pretax": "กำไรก่อนภาษี"}
    for k, lab in labels.items():
        ys = [y for y in FY_LIST if s[k][y] is None]
        if ys:
            missing.append(f"{lab} (tag {', '.join(TAGS[k])}): ไม่มีข้อมูล FY{', FY'.join(map(str, ys))}")
    (OUT_DIR / "INTU-5yr.html").write_text(page_5yr(s, tags, notes, missing), encoding="utf-8")
    info = OUT_DIR / "INTU-infographic.html"
    injected = inject(info, ext5_block(s, tags)) if info.exists() else False
    if info.exists():
        print("แทรกตาราง FY2026:", _splice(info, "FY26ROWS", fy26_rows(s)), _splice(info, "SEGROWS", seg_rows(s)))
    price_ok = inject_price(info) if info.exists() else False
    print("แทรกกราฟราคา:", price_ok)
    print(f"เขียน {OUT_DIR / 'INTU-5yr.html'}")
    print(f"แทรกส่วนเทียบ 5 ปีใน infographic: {injected}")
    print("ตรวจเทียบ INTU-FACTS.md:", "ตรงทุกรายการ" if not bad else bad)
    print("รายการที่ขาดข้อมูล:", missing or "ไม่มี")
    for n in notes:
        print("หมายเหตุ:", n)
    print("tag ที่ใช้ต่อปี:")
    for k in ("taxpaid", "sw"):
        print(" ", k, {y: tags[k][y] for y in FY_LIST})
    for k in ("rev", "opinc", "ni", "cfo", "ppe", "sw", "sbc", "taxexp", "taxpaid", "fcf", "fcf_sbc"):
        print(f"  {k:8}", {y: (None if s[k][y] is None else round(s[k][y])) for y in FY_LIST})
    if bad:
        raise SystemExit("ตัวเลขไม่ตรง INTU-FACTS.md")


if __name__ == "__main__":
    main()
