"""ใส่หัวข้อ CAN SLIM ลง NOW-infographic.html (ระหว่าง <!--CANSLIM:START--> และ <!--CANSLIM:END-->) จาก canslim.json

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/NOW/tools/build_canslim.py
รันซ้ำได้ ไม่สร้างซ้ำ และรันก่อนหรือหลัง build_5yr.py ก็ได้ (build_5yr.py แก้เฉพาะระหว่างเครื่องหมาย EXT5)
ตัวเลขทุกตัวมาจาก canslim.json หรือคำนวณจากมัน ห้ามกรอกมือ
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
D = json.loads((HERE / "canslim.json").read_text(encoding="utf-8"))
INFO = OUT / "NOW-infographic.html"
START, END = "<!--CANSLIM:START-->", "<!--CANSLIM:END-->"
MINUS = "\u2212"
SEC = "[แหล่งรอง ยังไม่ยืนยัน]"


def pct(x, d=1, sign=True):
    s = f"{abs(x) * 100:,.{d}f}%"
    if sign:
        return ("+" if x >= 0 else MINUS) + s
    return (MINUS if x < 0 else "") + s


def growth(x):
    return pct(x, 0 if abs(x) >= 1 else 1)


def usd(x):
    return f"${x:,.2f}"


c, a, n, s = D["C_quarter_eps"], D["A_annual_eps"], D["N_price"], D["S_shares"]
ls, ln, ms, mn = D["L_vs_sp500"], D["L_vs_nasdaq"], D["M_sp500"], D["M_nasdaq"]
asof = D["as_of"]
fy = {x["end"][:4]: x for x in a}
f23, f24, f25 = fy["2023"], fy["2024"], fy["2025"]
near_high = n["high_52w"] * 0.85          # ราคาที่ต้องถึงเพื่ออยู่ภายใน 15% ของจุดสูง
need_pct = near_high / n["last"] - 1       # ต้องขึ้นอีกเท่าไร
eps_need = c["eps"] * 1.25              # ไตรมาส 3 ปี 2027 เทียบฐาน Q3 2026


def side(m, name):
    ma50 = "เหนือ" if m["above_ma50"] else "ต่ำกว่า"
    ma200 = "เหนือ" if m["above_ma200"] else "ต่ำกว่า"
    return (f"{name} {ma50} MA50 และ{ma200} MA200 · ห่างจุดสูง 52 สัปดาห์ {pct(m['pct_from_high'])} · "
            f"12 เดือน {pct(m['ret_12m'])}")


rows = [
    ("C", f"EPS GAAP diluted ไตรมาส 3 ปี 2026 (จบ {c['period_end']}) {usd(c['eps'])} เทียบ {usd(c['prior_eps'])} ปีก่อน = "
          f"<span class=\"bad\">{pct(c['growth'])}</span> (เกณฑ์ ≥ +25%) · เป็น GAAP ไม่ใช่ non-GAAP · "
          "หน้านี้ไม่วิเคราะห์สาเหตุที่ EPS ลดลง", "bad", "❌"),
    ("A", f"EPS GAAP diluted รายปีหลังแตกหุ้น: FY2023 {usd(f23['eps'])} · FY2024 {usd(f24['eps'])} · FY2025 {usd(f25['eps'])} "
          f"อัตราโต {growth(f23['growth'])} / <span class=\"bad\">{growth(f24['growth'])}</span> / "
          f"<span class=\"bad\">{growth(f25['growth'])}</span> (เกณฑ์ ≥ +25% ต่อปี ทั้ง 3 ปี) · "
          f"FY2023 มีผลได้ภาษีครั้งเดียว (ปล่อย valuation allowance 723 ล้านดอลลาร์) ทำให้ FY2023 สูงและ FY2024 ต่ำเกินจริง", "bad", "❌"),
    ("N", f"ปัจจัยใหม่มีจริงตามที่บริษัทระบุ: ซื้อ Moveworks (15 ธ.ค. 2025), Veza (2 มี.ค. 2026), Armis (20 เม.ย. 2026) "
          f"และชุดเครื่องมือ AI Now Assist/AI agents ใน 10-K FY2025 แต่ราคา {usd(n['last'])} อยู่ห่างจุดสูง 52 สัปดาห์ "
          f"{usd(n['high_52w'])} ถึง <span class=\"bad\">{pct(n['pct_from_high'])}</span> (เกณฑ์ภายใน 15%) {SEC}", "bad", "❌"),
    ("S", f"จำนวนหุ้น (ตาม canslim.json) {s['latest'] / 1e6:,.1f} ล้านหุ้น เทียบ {s['year_ago'] / 1e6:,.1f} ล้านหุ้นปีก่อน = "
          f"<span class=\"warn\">{pct(s['change'], 2)}</span> ลดลงเล็กน้อย · 10-Q ระบุว่าไตรมาส 3 ไม่มีการซื้อคืนหุ้น "
          f"(ตัวเลขนับหุ้นของไฟล์นี้อาจต่างจากงบดุลใน NOW-FACTS.md แถว 109)", "warn", "🟡"),
    ("L", f"ผลตอบแทน 12 เดือนของหุ้น <span class=\"bad\">{pct(ls['ret_12m_stock'])}</span> เทียบ S&amp;P 500 {pct(ls['ret_12m_index'])} "
          f"ตามหลัง {abs(ls['excess_12m']) * 100:,.1f} จุดเปอร์เซ็นต์ (เทียบ Nasdaq {pct(ln['ret_12m_index'])} ตามหลัง "
          f"{abs(ln['excess_12m']) * 100:,.1f} จุด) · ยังไม่มี RS rating ทางการ [RS rating ยังไม่ยืนยัน] {SEC}", "bad", "❌"),
    ("I", "ยังไม่ได้ดึงข้อมูล 13F ของสถาบัน จึงไม่ตัดสิน [ยังไม่ยืนยัน]", "", "⚪"),
    ("M", f"{side(ms, 'S&amp;P 500')}<br>{side(mn, 'Nasdaq')}<br>ทั้งสองดัชนียืนเหนือ MA200 แต่ต่ำกว่า MA50 จึงอ่านเป็นสัญญาณผสม {SEC}",
     "warn", "🟡"),
]


def build():
    trs = "\n".join(
        f"      <tr><td>{k}</td><td>{ev}</td><td{(' class=\"' + cl + '\"') if cl else ''}>{mk}</td></tr>"
        for k, ev, cl, mk in rows
    )
    return f"""{START}
  <section class="card">
    <h2><span class="num">7</span>CAN SLIM</h2>
    <div class="legend">กรอบ momentum/growth แบบคลาสสิก ใช้เสริม ไม่ใช่กรอบหลัก และไม่ใช่คำแนะนำซื้อขาย · ข้อมูลราคาและดัชนีของหัวข้อนี้ ณ {asof} จากข้อมูลรายวัน Yahoo ซึ่งต่างวันจากราคา $105.12 (30 ต.ค.) ที่ใช้ในหัวข้ออื่นของหน้า จึงไม่นำมาปนกัน</div>
    <table>
      <tr><th></th><th>หลักฐาน</th><th>ผล</th></tr>
{trs}
    </table>
    <ul>
      <li><b>สรุป CAN SLIM:</b> ตามกรอบนี้ไม่ผ่านด้านกำไรและแรงราคา (C A N L ไม่ผ่าน, S และ M ผสม, I ยังไม่ตรวจ) เป็นการประเมินตามเกณฑ์ ไม่ใช่สัญญาณ และเป็นคนละมุมกับกรอบ value ของโซนราคาด้านบน</li>
      <li><b>เงื่อนไขเปลี่ยนเป็นผ่าน:</b>
        C = EPS GAAP รายไตรมาสโตเทียบปีก่อน ≥ +25% (เช่น Q3 ปี 2027 เทียบฐาน {usd(c['eps'])} ต้องไม่ต่ำกว่าราว {usd(eps_need)}) ·
        A = EPS รายปีโต ≥ +25% ต่อปีครบ 3 ปีล่าสุด (FY2025 อยู่ที่ {growth(f25['growth'])}) ·
        N = ราคาขึ้นมาอยู่ภายใน 15% ของจุดสูง 52 สัปดาห์ คือราว {usd(near_high)} ขึ้นไป (ต้องเพิ่มอีก {pct(need_pct, 0, False)} จาก {usd(n['last'])}) ·
        S = จำนวนหุ้นลดลงต่อเนื่องจากการซื้อคืนมากกว่าหุ้นที่ออกใหม่ ·
        L = ผลตอบแทน 12 เดือนไม่ต่ำกว่า S&amp;P 500 ({pct(ls['ret_12m_index'])} ณ วันนี้) ·
        I = ดึง 13F แล้วดูสถาบันถือเพิ่มหรือลด ·
        M = ทั้ง S&amp;P 500 และ Nasdaq ยืนเหนือทั้ง MA50 และ MA200</li>
      <li><b>ข้อควรระวัง:</b> EPS เป็น GAAP diluted ปรับหุ้นแตก 5:1 (ธ.ค. 2025) แล้ว แสดงเฉพาะ FY2023–FY2025 ฐานหลังแตก ไม่เทียบข้ามฐาน · อัตราโตมาจากเอกสารฉบับเดียวกัน (คำนวณใน canslim.json)</li>
    </ul>
    <div class="src">[ที่มา: output/NOW/tools/canslim.json (src/canslim.py ณ {asof}) · 10-K FY2025 และ 10-Q Q3 2026 (ผลิตภัณฑ์/ซื้อกิจการ) · NOW-FACTS.md แถว 28, 32, 33, 98-101, 109 · ราคา/ดัชนี: Yahoo Finance ไม่เป็นทางการ แหล่งรอง ยังไม่ยืนยัน]</div>
  </section>
{END}"""


def main():
    t = INFO.read_text(encoding="utf-8")
    block = build()
    a, b = t.find(START), t.find(END)
    if a >= 0 and b >= 0:
        t = t[:a] + block + t[b + len(END):]
    else:
        m = re.search(r'[ \t]*<section class="card">\s*<h2><span class="num">\d+</span>Bear Case</h2>', t)
        if not m:
            print("ไม่พบหัวข้อ Bear Case")
            sys.exit(1)
        t = t[:m.start()] + block + "\n\n" + t[m.start():]
    t = t.replace('<span class="num">7</span>Bear Case', '<span class="num">8</span>Bear Case')
    INFO.write_text(t, encoding="utf-8")
    print("อัปเดต CAN SLIM ใน", INFO)


if __name__ == "__main__":
    main()
