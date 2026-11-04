"""ใส่หัวข้อ CAN SLIM ลง INTU-infographic.html และ INTU.md จาก tools/canslim.json

รัน (หลัง build_5yr.py): python -I output/INTU/tools/build_canslim.py
- infographic: แทนส่วนระหว่าง <!--CANSLIM:START--> และ <!--CANSLIM:END--> (ถ้ายังไม่มีมาร์กเกอร์ แทรกก่อนหัวข้อ Bear Case แล้วเลื่อนเลขหัวข้อ Bear Case เป็น 8)
- INTU.md: แทนส่วนระหว่าง <!--CANSLIM-MD:START--> และ <!--CANSLIM-MD:END--> (ท้ายไฟล์ ถ้ายังไม่มี)
ตัวเลข CAN SLIM มาจาก canslim.json ทั้งหมด ยกเว้นซื้อหุ้นคืน/ปันผล/EPS FY2026 ที่อ้าง INTU-FACTS.md
"""
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
D = json.loads((Path(__file__).with_name("canslim.json")).read_text(encoding="utf-8"))
INFO = OUT / "INTU-infographic.html"
MD = OUT / "INTU.md"
MINUS = "−"
SEC = "[แหล่งรอง ยังไม่ยืนยัน]"


def pct(v, d=1):
    s = f"{abs(v) * 100:.{d}f}%"
    return (MINUS + s) if v < 0 else ("+" + s)


def usd(v):
    return f"${v:,.2f}"


c, a, n, s_, ls, ln = D["C_quarter_eps"], D["A_annual_eps"], D["N_price"], D["S_shares"], D["L_vs_sp500"], D["L_vs_nasdaq"]
mS, mN = D["M_sp500"], D["M_nasdaq"]
asof = D["as_of"]
last3 = a[-3:]
a_ok = [x["growth"] >= 0.25 for x in last3]
a_txt = " · ".join(f"FY{x['end'][:4]} {pct(x['growth'])}" for x in last3)
a_res = "pass" if all(a_ok) else ("part" if any(a_ok) else "fail")
c_res = "pass" if c["growth"] >= 0.25 else "fail"
n_res = "pass" if n["pct_from_high"] >= -0.15 else "fail"  # ปัจจัยใหม่มีจริงตามที่บริษัทระบุ + ราคาภายใน 15%
s_res = "pass" if s_["change"] < 0 else "fail"
l_res = "pass" if ls["excess_12m"] > 0 else "fail"
m_all = [mS["above_ma50"] and mS["above_ma200"], mN["above_ma50"] and mN["above_ma200"]]
m_none = [not (mS["above_ma50"] or mS["above_ma200"]), not (mN["above_ma50"] or mN["above_ma200"])]
m_res = "pass" if all(m_all) else ("fail" if all(m_none) else "part")
EMO = {"pass": "✅", "part": "🟡", "fail": "❌", "na": "⚪"}
CLS = {"pass": "good", "part": "warn", "fail": "bad", "na": "na"}
thr_high = n["high_52w"] * 0.85
a_next = a[-1]["eps"] * 1.25


def ma(m, name):
    r50 = "เหนือ" if m["above_ma50"] else "ใต้"
    r200 = "เหนือ" if m["above_ma200"] else "ใต้"
    return (f"{name} {m['last']:,.2f} {r50} MA50 ({m['ma50']:,.2f}) และ{r200} MA200 ({m['ma200']:,.2f}) · "
            f"ห่างจุดสูง 52 สัปดาห์ {pct(m['pct_from_high'])} · 12 เดือน {pct(m['ret_12m'])}")


def word(res, part="ผ่านบางส่วน"):
    return {"pass": "ผ่าน", "part": part, "fail": "ไม่ผ่าน", "na": ""}[res]


rows = [
    ("C", "กำไรไตรมาสล่าสุด",
     f"EPS GAAP diluted ไตรมาส 4 FY2026 (จบ {c['period_end']}) {c['eps']:.2f} เทียบ {c['prior_eps']:.2f} ปีก่อน ({pct(c['growth'])}) "
     f"เกณฑ์ ≥ +25% · <b>derived</b> = ทั้งปีลบ 9 เดือน เป็นค่าประมาณเพราะจำนวนหุ้นเฉลี่ยต่างกัน ไม่ใช่ตัวเลข non-GAAP",
     c_res, word(c_res)),
    ("A", "กำไรรายปี",
     f"EPS GAAP diluted ปีบัญชีจบ 31 ก.ค.: {a_txt} (เกณฑ์ ≥ +25% ต่อปี ดู 3 ปีล่าสุด) · EPS FY2026 {a[-1]['eps']:.2f} [INTU-FACTS.md แถว 21]",
     a_res, word(a_res, "ผ่านบางส่วน (1 ใน 3 ปีถึงเกณฑ์)")),
    ("N", "ของใหม่/ราคาใกล้จุดสูง",
     "ปัจจัยใหม่ที่บริษัทระบุเองใน 10-K FY2026: ชุด AI agents และ AI-driven expert platform ที่ขยายใหม่ใน FY2026, Intuit Accountant Suite "
     "(แพลตฟอร์มจัดการสำนักงานบัญชีที่ฝัง Intuit Intelligence) [10-K FY2026 Item 1 Business บ.266, 316 ของไฟล์ .txt] "
     f"แต่ราคาปิด {usd(n['last'])} ห่างจากจุดสูง 52 สัปดาห์ {usd(n['high_52w'])} อยู่ {pct(n['pct_from_high'])} (เกณฑ์ภายใน 15%) {SEC}",
     n_res, "ไม่ผ่านด้านราคา" if n_res == "fail" else "ผ่าน"),
    ("S", "อุปสงค์/อุปทานหุ้น",
     f"หุ้นเฉลี่ย diluted ไตรมาส 3 FY2026 (จบ {s_['period_end']}) {s_['latest'] / 1e6:,.0f}M เทียบ {s_['year_ago'] / 1e6:,.0f}M ปีก่อน ({pct(s_['change'])}) · "
     "เงินสดซื้อหุ้นคืน FY2026 $5,412M และปันผลจ่าย $1,347M [INTU-FACTS.md แถว 70, 72]",
     s_res, "หนุน" if s_res == "pass" else "ไม่หนุน"),
    ("L", "ผู้นำ/ผู้ตาม",
     f"ผลตอบแทน 12 เดือนของหุ้น {pct(ls['ret_12m_stock'])} เทียบ S&amp;P 500 {pct(ls['ret_12m_index'])} (ต่างกัน {pct(ls['excess_12m'])} จุดเปอร์เซ็นต์) "
     f"· เทียบ Nasdaq {pct(ln['ret_12m_index'])} (ต่างกัน {pct(ln['excess_12m'])}) {SEC} [RS rating ยังไม่ยืนยัน]",
     l_res, "ตามหลังดัชนี" if l_res == "fail" else "นำดัชนี"),
    ("I", "สถาบันถือ", "ยังไม่ได้ดึงข้อมูล 13F ไม่ประเมิน", "na", "[ยังไม่ยืนยัน]"),
    ("M", "ทิศทางตลาด",
     f"{ma(mS, 'S&amp;P 500')}<br>{ma(mN, 'Nasdaq')} {SEC}",
     m_res, word(m_res, "ผสม (เหนือ MA200 แต่ใต้ MA50 ทั้งสองดัชนี)")),
]
RES = {r[0]: r[3] for r in rows}
n_pass = sum(v == "pass" for v in RES.values())
n_part = sum(v == "part" for v in RES.values())
n_fail = sum(v == "fail" for v in RES.values())

cond = [
    ("C", f"EPS GAAP diluted รายไตรมาสโต ≥ +25% เทียบไตรมาสเดียวกันปีก่อน (ไตรมาสล่าสุดที่คำนวณได้ {pct(c['growth'])})"),
    ("A", f"EPS GAAP diluted รายปีโต ≥ +25% ทุกปีในช่วง 3 ปีล่าสุด ตามการอ่านเข้มงวด FY2026 ไม่ถึงเกณฑ์ ({pct(a[-1]['growth'])}) จึงต้องรอ 3 ปีถัดไป ถ้าดูเฉพาะ FY2027 ต้องมี EPS ≥ {a_next:.2f} (= {a[-1]['eps']:.2f} × 1.25)"),
    ("N", f"ราคากลับมาอยู่ภายใน 15% จากจุดสูง 52 สัปดาห์ (≥ {usd(thr_high)} เมื่อจุดสูงเท่าเดิม) และยังมีปัจจัยใหม่จริง {SEC}"),
    ("L", f"ผลตอบแทน 12 เดือนของหุ้นสูงกว่า S&amp;P 500 (ตอนนี้ต่าง {pct(ls['excess_12m'])} จุด) และมี RS rating ทางการที่ตรวจแล้ว"),
    ("M", "S&amp;P 500 และ Nasdaq ราคาอยู่เหนือทั้ง MA50 และ MA200 (ตอนนี้ใต้ MA50 ทั้งสองดัชนี)"),
    ("I", "ดึงข้อมูล 13F ของสถาบันมาตรวจก่อนจึงประเมินได้"),
]

SUMMARY = (f"ผ่าน {n_pass} · ผ่านบางส่วน {n_part} · ไม่ผ่าน {n_fail} · ไม่ประเมิน 1 จาก 7 ตัวอักษร "
           f"กำไรไตรมาสล่าสุด ราคาเทียบจุดสูง และผลตอบแทนเทียบดัชนียังไม่ถึงเกณฑ์ momentum ส่วนจำนวนหุ้นลดลงตามเกณฑ์ S "
           f"เป็นการประเมินตามกรอบ ณ {asof} ไม่ใช่สัญญาณ และไม่แทนโซนราคา/valuation ในส่วนอื่น")


def build_html():
    tr = "".join(
        f'<tr><td><b>{k}</b> <small class="na">{lab}</small></td><td>{ev}</td>'
        f'<td><span class="chip {CLS[res]}">{EMO[res]}</span> <small class="na">{txt}</small></td></tr>'
        for k, lab, ev, res, txt in rows)
    lis = "".join(f"<li><b>{k}</b> {t}</li>" for k, t in cond)
    return f"""
  <!-- 7 -->
  <section class="card">
    <h2><span class="num">7</span>CAN SLIM</h2>
    <div class="legend">กรอบ growth/momentum แบบคลาสสิก ใช้เสริม ไม่ใช่กรอบหลักของคอร์ส และไม่ใช่คำแนะนำ · ผลเป็นการประเมินตามกรอบ ไม่ใช่สัญญาณ · EPS ในหัวข้อนี้เป็น <b>GAAP diluted</b> ไม่ใช่ non-GAAP · ข้อมูลราคาของหัวข้อนี้ ณ <b>{asof}</b> (Yahoo Finance รายวัน แหล่งรอง) ต่างจากราคา $341.09 ณ 30 ต.ค. 2026 ที่ใช้ในส่วนอื่นของหน้า ไม่ปนกัน</div>
    <table>
      <tr><th>ตัวอักษร</th><th>หลักฐาน</th><th>ผล</th></tr>
      {tr}
    </table>
    <ul>
      <li><b>สรุป CAN SLIM:</b> {SUMMARY}</li>
      <li><b>เงื่อนไขเปลี่ยนเป็นผ่าน (เฉพาะตัวอักษรที่ยังไม่ผ่านหรือยังไม่ประเมิน):</b></li>
    </ul>
    <ul style="margin-top:0">{lis}</ul>
    <div class="src">[ที่มา: tools/canslim.json สร้างจาก src/canslim.py ณ {asof} · ราคา/ดัชนี: Yahoo Finance แบบไม่เป็นทางการ แหล่งรอง ยังไม่ยืนยัน · EPS/จำนวนหุ้น: SEC companyfacts · C ไตรมาส 4 เป็นค่า derived · ซื้อหุ้นคืน/ปันผล: INTU-FACTS.md แถว 70, 72 · ผลิตภัณฑ์ใหม่: 10-K FY2026 Item 1 · ยังไม่ผ่าน check-jing]</div>
  </section>
"""


def build_md():
    def strip(t):
        return re.sub(r"<[^>]+>", "", t.replace("<br>", "; ")).replace("&amp;", "&")
    tb = "\n".join(f"| {k} {lab} | {strip(ev)} | {EMO[res]} {txt} |" for k, lab, ev, res, txt in rows)
    cl = "\n".join(f"- {k}: {strip(t)}" for k, t in cond)
    return f"""
## 8. CAN SLIM (กรอบ growth/momentum ใช้เสริม ไม่ใช่กรอบหลักของคอร์ส ไม่ใช่คำแนะนำ)

ข้อมูลราคา ณ {asof} (Yahoo Finance รายวัน แหล่งรอง [ยังไม่ยืนยัน]) ต่างจากราคา $341.09 ณ 30 ต.ค. 2026 ที่ใช้ในส่วน 3-4 · EPS เป็น GAAP diluted ไม่ใช่ non-GAAP · ปีบัญชีจบ 31 ก.ค.

| ตัวอักษร | หลักฐาน | ผล |
|---|---|---|
{tb}

**สรุป CAN SLIM:** {SUMMARY}

**เงื่อนไขเปลี่ยนเป็นผ่าน:**
{cl}

[ที่มา: output/INTU/tools/canslim.json (src/canslim.py, {asof}) · 10-K FY2026 Item 1 · INTU-FACTS.md แถว 70, 72 · สร้างโดย tools/build_canslim.py]
"""


def put_html(text):
    a, b = "<!--CANSLIM:START-->", "<!--CANSLIM:END-->"
    blk = a + build_html() + b
    if a in text and b in text:
        head, rest = text.split(a, 1)
        _, tail = rest.split(b, 1)
        return head + blk + tail
    anchor = '  <!-- 7 -->\n  <section class="card">\n    <h2><span class="num">7</span>Bear Case'
    assert anchor in text, "ไม่พบหัวข้อ Bear Case"
    new_anchor = anchor.replace("<!-- 7 -->", "<!-- 8 -->").replace('num">7<', 'num">8<')
    return text.replace(anchor, blk + "\n\n" + new_anchor)


def put_md(text):
    a, b = "<!--CANSLIM-MD:START-->", "<!--CANSLIM-MD:END-->"
    blk = a + build_md() + b
    if a in text and b in text:
        head, rest = text.split(a, 1)
        _, tail = rest.split(b, 1)
        return head + blk + tail
    return text.rstrip("\n") + "\n\n" + blk + "\n"


def main():
    INFO.write_text(put_html(INFO.read_text(encoding="utf-8")), encoding="utf-8")
    m = re.sub(r"^updated: .*$", f"updated: {asof}", MD.read_text(encoding="utf-8"), count=1, flags=re.M)
    MD.write_text(put_md(m), encoding="utf-8")
    print(" ".join(f"{k}={v}" for k, v in RES.items()))


if __name__ == "__main__":
    main()
