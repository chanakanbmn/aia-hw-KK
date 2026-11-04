"""สร้างหัวข้อ CAN SLIM ของ LRCX จาก tools/canslim.json แล้วใส่ใน LRCX-infographic.html
ระหว่าง <!--CANSLIM:START--> และ <!--CANSLIM:END--> (รันซ้ำได้ ไม่สร้างซ้ำ)

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/build_canslim.py
build_infographic.py เรียกไฟล์นี้ต่อท้ายอัตโนมัติ (หน้าถูกสร้างทั้งหน้า) จึงรันก่อนหรือหลัง build_5yr.py ก็ได้
ตัวเลขทุกตัวมาจาก canslim.json (ยกเว้นราคาซื้อหุ้นคืน Q1 FY2027 จาก LRCX-FACTS.md แถว 144)
CAN SLIM เป็นกรอบ momentum เสริม ไม่ใช่กรอบหลักและไม่ใช่คำแนะนำ
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INFO = HERE.parent / "LRCX-infographic.html"
D = json.loads((HERE / "canslim.json").read_text(encoding="utf-8"))
START, END = "<!--CANSLIM:START-->", "<!--CANSLIM:END-->"
CM = ' <span class="cm">[คำนวณ]</span>'
SEC = '<span class="warn">[แหล่งรอง ยังไม่ยืนยัน]</span>'
NUM = 7  # เลขหัวข้อ (Bear Case เป็น 8)


def pct(v, nd=1):
    return f"{v * 100:+.{nd}f}%".replace("-", "−")


def usd(v):
    return f"${v:,.2f}"


def build_block() -> str:
    c, n, s = D["C_quarter_eps"], D["N_price"], D["S_shares"]
    lsp, lnq = D["L_vs_sp500"], D["L_vs_nasdaq"]
    msp, mnq = D["M_sp500"], D["M_nasdaq"]
    asof = D["as_of"]

    # A: ปีบัญชีหลังแตกหุ้น FY2023-FY2026 (ตัดแถวซ้ำ) ใช้ 3 ปีล่าสุดตัดสิน
    seen, yrs = set(), []
    for r in D["A_annual_eps"]:
        if r["end"] >= "2023-06-01" and r["end"] not in seen:
            seen.add(r["end"])
            yrs.append(r)
    last3 = yrs[-3:]
    a_pass = all(r["growth"] is not None and r["growth"] >= 0.25 for r in last3)
    a_n_ok = sum(1 for r in last3 if r["growth"] >= 0.25)
    fy = lambda r: "FY" + r["end"][:4]
    a_txt = " · ".join(f'{fy(r)} ${r["eps"]:.2f} ({pct(r["growth"])})' for r in yrs)
    a_next = last3[-1]["eps"] * 1.25  # EPS FY2027 ที่ทำให้ FY2025-27 ผ่านครบ

    # N
    n_near = n["pct_from_high"] >= -0.15
    n_floor = n["high_52w"] * 0.85

    # S: ราคาซื้อคืน Q1 FY2027 (FACTS แถว 144)
    bb_cost, bb_sh = 1010711, 2344  # พัน USD / พันหุ้น
    bb_all = bb_cost / bb_sh

    # L
    l_ok = lsp["excess_12m"] > 0

    def mrow(name, m):
        a50 = "เหนือ" if m["above_ma50"] else "ต่ำกว่า"
        a200 = "เหนือ" if m["above_ma200"] else "ต่ำกว่า"
        return (f'{name} {m["last"]:,.0f}: {a50} MA50 ({m["ma50"]:,.0f}) · {a200} MA200 ({m["ma200"]:,.0f}) · '
                f'ห่างจุดสูง 52 สัปดาห์ {pct(m["pct_from_high"])}')

    m_ok = all(m["above_ma50"] and m["above_ma200"] for m in (msp, mnq))
    m_bad = not any(m["above_ma200"] for m in (msp, mnq))
    m_chip = ("✅", "good") if m_ok else (("❌", "bad") if m_bad else ("🟡", "warn"))

    c_ok = c["growth"] >= 0.25
    rows = [
        ("C", f'EPS GAAP diluted ไตรมาสล่าสุด Q1 FY2027 (จบ {c["period_end"]}) ${c["eps"]:.2f} เทียบ ${c["prior_eps"]:.2f} ปีก่อน '
              f'<span class="{"good" if c_ok else "bad"}">{pct(c["growth"])}</span> (เกณฑ์ ≥ +25%){CM}',
         ("✅", "good") if c_ok else ("❌", "bad")),
        ("A", f'EPS GAAP diluted รายปี (ฐานหลังแตกหุ้น 10:1 ต.ค. 2024): {a_txt} · 3 ปีล่าสุดผ่านเกณฑ์ ≥ +25% {a_n_ok} จาก 3 ปี '
              f'(<span class="bad">{fy(last3[0])} {pct(last3[0]["growth"])}</span> ไม่ผ่าน) ธุรกิจวัฏจักร ปีลบคั่นกลาง{CM}',
         ("✅", "good") if a_pass else ("🟡", "warn")),
        ("N", f'ปัจจัยใหม่: 10-K FY2026 ระบุผลิตภัณฑ์/เทคโนโลยีในตระกูล Akara (conductor etch รองรับ gate-all-around, DRAM, NAND), '
              f'Vantex (dielectric etch รุ่นล่าสุดของบริษัท), Aether (dry photoresist สำหรับ EUV), ALTUS Halo (โมลิบดีนัม) และโซลูชัน advanced packaging/HBM · '
              f'แต่ราคาปิด {usd(n["last"])} ห่างจากราคาปิดสูงสุด 52 สัปดาห์ {usd(n["high_52w"])} '
              f'<span class="{"good" if n_near else "bad"}">{pct(n["pct_from_high"])}</span> (เกณฑ์ภายใน 15%) '
              f'ขณะผลตอบแทน 12 เดือน {pct(n["ret_12m"])} ยังเป็นบวก{CM} {SEC}',
         ("✅", "good") if n_near else ("❌", "bad")),
        ("S", f'จำนวนหุ้นเฉลี่ย diluted Q1 FY2027 {s["latest"] / 1e6:,.1f}M เทียบ {s["year_ago"] / 1e6:,.1f}M '
              f'ปีก่อน ({pct(s["change"])} ลดลงเล็กน้อย){CM} · ซื้อหุ้นคืนทั้งไตรมาส 2,344 พันหุ้น ต้นทุนรวมต่อหุ้นราว ${bb_all:,.0f}{CM} '
              f'(รวม ASR) ส่วน $329.17 เป็นราคาเฉลี่ยของหุ้นที่ซื้อในตลาด 3 พันหุ้นเท่านั้น ไม่รวม ASR',
         ("✅", "good") if s["change"] < 0 else ("❌", "bad")),
        ("L", f'ผลตอบแทน 12 เดือนของหุ้น {pct(lsp["ret_12m_stock"])} เทียบ S&amp;P 500 {pct(lsp["ret_12m_index"])} '
              f'(ส่วนต่าง {lsp["excess_12m"]*100:+.1f} จุดเปอร์เซ็นต์) และ Nasdaq {pct(lnq["ret_12m_index"])} (ส่วนต่าง {lnq["excess_12m"]*100:+.1f} จุดเปอร์เซ็นต์){CM} '
              f'{SEC} <span class="warn">[RS rating ยังไม่ยืนยัน]</span>',
         ("✅", "good") if l_ok else ("❌", "bad")),
        ("I", 'ไม่ได้ดึง 13F สถาบัน [ยังไม่ยืนยัน] (DEF 14A ระบุ BlackRock 9.41% อ้าง 13G ณ 31 ธ.ค. 2023 เป็นข้อมูลเก่ากว่า 2.5 ปี ไม่ใช้เป็นสถานะปัจจุบัน)',
         ("⚪", "")),
        ("M", f'{mrow("S&amp;P 500", msp)}<br>{mrow("Nasdaq", mnq)}<br>ภาพรวม: {msp["trend"]} (ตัวเลขจาก canslim.json){CM} {SEC}',
         m_chip),
    ]
    tr = "\n".join(
        f'      <tr><td>{k}</td><td>{ev}</td><td class="{cl}">{ic}</td></tr>' if cl else
        f'      <tr><td>{k}</td><td>{ev}</td><td>{ic}</td></tr>' for k, ev, (ic, cl) in rows)

    res = {k: ic for k, _, (ic, _) in rows}
    summary = " ".join(f"{k} {res[k]}" for k in "CANSLIM")

    return f"""{START}
  <section class="card">
    <h2><span class="num">{NUM}</span>CAN SLIM</h2>
    <div class="warnbox" style="margin:0 0 10px;color:var(--mute);border-color:var(--line)">CAN SLIM เป็นกรอบ growth/momentum ใช้เสริม ไม่ใช่กรอบหลักของคอร์สและไม่ใช่คำแนะนำ ผลด้านล่างเป็นการประเมินตามเกณฑ์ ไม่ใช่สัญญาณซื้อหรือขาย · EPS เป็น GAAP diluted ปีบัญชีจบสิ้นเดือนมิถุนายน · <b>ข้อมูลราคาและดัชนีของหัวข้อนี้ ณ {asof}</b> (ปิด {usd(n["last"])}) ซึ่งต่างจากราคา 227.56 ณ 2 พ.ย. ที่ใช้ในหัวข้อ 3 และ 5 และจุดสูง 52 สัปดาห์ในหัวข้อนี้เป็นราคาปิดสูงสุด ({usd(n["high_52w"])}) จึงไม่เท่าตัวเลข 438.5 ของส่วนอื่น ไม่นำมาปนกัน</div>
    <table>
      <tr><th></th><th>หลักฐาน</th><th>ผล</th></tr>
{tr}
    </table>
    <ul>
      <li><b>สรุป CAN SLIM:</b> {summary} · ผ่านตามเกณฑ์ 3 ตัว (C, S, L) ผ่านบางส่วน 2 ตัว (A, M) ไม่ผ่าน 1 ตัว (N) และยังตรวจไม่ได้ 1 ตัว (I) ด้านกำไรไตรมาสล่าสุดและผลตอบแทนเทียบดัชนีเข้าเกณฑ์ แต่ราคาอยู่ห่างจุดสูง 52 สัปดาห์มาก ({pct(n["pct_from_high"])}) และต่ำกว่า MA50 ({n["ma50"]:,.2f}) กับ MA200 ({n["ma200"]:,.2f}) ของตัวเอง{CM} ธุรกิจเป็นวัฏจักร กำไรรายปีมีปีลบคั่น (FY2024) จึงไม่ผ่านเกณฑ์ A ครบ 3 ปี · เป็นการประเมินตามกรอบ momentum แยกจากกรอบ value ในหัวข้อ 4-5 ไม่ใช่สัญญาณ</li>
      <li><b>เงื่อนไขเปลี่ยนเป็นผ่าน:</b>
        <b>A</b> EPS FY2027 โตอย่างน้อย +25% (ราว {usd(a_next)} ขึ้นไป เทียบ ${last3[-1]["eps"]:.2f} ของ FY2026) เพื่อให้ FY2025–FY2027 ผ่านครบ 3 ปี{CM} ·
        <b>N</b> ราคาปิดกลับมาอยู่ภายใน 15% ของจุดสูง 52 สัปดาห์ (ราว {usd(n_floor)} ขึ้นไป ตามจุดสูงปัจจุบัน){CM} ·
        <b>M</b> S&amp;P 500 และ Nasdaq อยู่เหนือทั้ง MA50 และ MA200 พร้อมกัน (ตอนนี้เหนือเฉพาะ MA200) ·
        <b>I</b> ดึงข้อมูลถือครองสถาบันล่าสุด (13F) มาตรวจก่อน ยังให้ผลไม่ได้ ·
        C, S, L ผ่านอยู่แล้ว แต่ต้องตรวจซ้ำทุกไตรมาส (L จะไม่ผ่านถ้าผลตอบแทน 12 เดือนของหุ้นต่ำกว่าดัชนี)</li>
      <li><b>ข้อจำกัด:</b> เอกสารที่ยื่นไม่ระบุสาเหตุที่ราคาเปลี่ยน จึงไม่อธิบายสาเหตุของระยะห่างจากจุดสูง · 10-K ไม่ระบุวันเปิดตัวหรือรายได้แยกรายผลิตภัณฑ์ ตัว N จึงยืนยันได้เพียงว่าบริษัทระบุผลิตภัณฑ์เหล่านี้ในรายการสินค้า ไม่ได้ยืนยันว่าเป็นของใหม่ในปีนี้ และ 10-Q Q1 FY2027 ไม่พบการระบุชื่อตระกูลเหล่านี้ · ค่า EPS FY2022 และก่อนหน้าเป็นฐานก่อนแตกหุ้น 10:1 จึงไม่นำมาเทียบ อัตราโต FY2023 ใช้ตามที่คำนวณในไฟล์ canslim.json จากเอกสารฉบับเดียวกัน</li>
    </ul>
    <div class="src">[ที่มา: tools/canslim.json (สร้างจาก src/canslim.py ณ {asof}: EPS และจำนวนหุ้นจาก SEC companyfacts, ราคาและดัชนีจาก Yahoo Finance แบบไม่เป็นทางการ แหล่งรอง ยังไม่ยืนยัน) · ผลิตภัณฑ์: 10-K FY2026 Item 1 บรรทัด 188, 234, 244, 256, 272 (ไฟล์ .txt) · ซื้อหุ้นคืน: LRCX-FACTS.md แถว 144, 146 (10-Q Q1 FY2027) · DEF 14A 2026-09-24 (13G ณ 2023-12-31) · เกณฑ์ตามกรอบเดียวกับ BX.md หัวข้อ 4]</div>
  </section>
{END}"""


def inject(path: Path = INFO) -> None:
    t = path.read_text(encoding="utf-8")
    a, b = t.find(START), t.find(END)
    if a < 0 or b < 0 or b < a:
        raise SystemExit(f"ไม่พบเครื่องหมาย {START} ... {END} ใน {path.name} (รัน build_infographic.py ก่อน)")
    path.write_text(t[:a] + build_block() + t[b + len(END):], encoding="utf-8")
    print("ใส่ CAN SLIM ใน", path)




MD_START, MD_END = "<!--CANSLIM-MD:START-->", "<!--CANSLIM-MD:END-->"


def build_md() -> str:
    """หัวข้อ 4.1 CAN SLIM ใน LRCX.md (ตัวเลขจาก canslim.json เช่นเดียวกับหน้า infographic)"""
    c, n, s = D["C_quarter_eps"], D["N_price"], D["S_shares"]
    lsp, lnq, msp, mnq = D["L_vs_sp500"], D["L_vs_nasdaq"], D["M_sp500"], D["M_nasdaq"]
    seen, yrs = set(), []
    for r in D["A_annual_eps"]:
        if r["end"] >= "2023-06-01" and r["end"] not in seen:
            seen.add(r["end"])
            yrs.append(r)
    a_txt = " · ".join(f'FY{r["end"][:4]} ${r["eps"]:.2f} ({pct(r["growth"])})' for r in yrs)
    nz = yrs[-1]["eps"] * 1.25
    bb = 1010711 / 2344
    mm = lambda nm, m: (f'{nm} {m["last"]:,.0f} {"เหนือ" if m["above_ma50"] else "ต่ำกว่า"} MA50 ({m["ma50"]:,.0f}), '
                        f'{"เหนือ" if m["above_ma200"] else "ต่ำกว่า"} MA200 ({m["ma200"]:,.0f}), ห่างจุดสูง {pct(m["pct_from_high"])}')
    return f"""{MD_START}
## 4.1 CAN SLIM (กรอบ growth/momentum ใช้เสริม ไม่ใช่กรอบหลักของคอร์ส ไม่ใช่คำแนะนำ)

EPS เป็น GAAP diluted ปีบัญชีจบสิ้นเดือนมิถุนายน · ข้อมูลราคา/ดัชนีของหัวข้อนี้ ณ {D["as_of"]} (ปิด {usd(n["last"])}) คนละวันกับราคา 227.56 ณ 2 พ.ย. ที่ใช้ในหัวข้อ 3-4 และจุดสูง 52 สัปดาห์ตรงนี้เป็นราคาปิดสูงสุด {usd(n["high_52w"])} (ไม่ใช่ 438.5) · ราคาทุกตัวเป็นแหล่งรอง Yahoo [ยังไม่ยืนยัน] [ที่มา: tools/canslim.json]

| ตัวอักษร | หลักฐาน | ผล |
|---|---|---|
| C กำไรไตรมาสล่าสุด | Q1 FY2027 ${c["eps"]:.2f} เทียบ ${c["prior_eps"]:.2f} ({pct(c["growth"])}) เกณฑ์ ≥ +25% [คำนวณ] | ✅ ผ่าน |
| A กำไรรายปี | ฐานหลังแตกหุ้น 10:1: {a_txt} · 3 ปีล่าสุดผ่านเกณฑ์ ≥ +25% 2 จาก 3 ปี (FY2024 ติดลบ) [คำนวณ] | 🟡 ผ่านบางส่วน |
| N ของใหม่/ราคาใกล้จุดสูง | 10-K FY2026 ระบุตระกูล Akara, Vantex, Aether, ALTUS Halo และโซลูชัน advanced packaging/HBM [10-K FY2026 Item 1 บรรทัด 188, 234, 244, 256, 272] แต่ราคาปิด {usd(n["last"])} ห่างจุดสูง {pct(n["pct_from_high"])} (เกณฑ์ภายใน 15%) ขณะผลตอบแทน 12 เดือน {pct(n["ret_12m"])} [คำนวณ] | ❌ ไม่ผ่านด้านราคา |
| S อุปสงค์/อุปทานหุ้น | หุ้นเฉลี่ย diluted {s["latest"] / 1e6:,.1f}M เทียบ {s["year_ago"] / 1e6:,.1f}M ({pct(s["change"])}) · ซื้อคืน Q1 FY2027 ต้นทุนรวมต่อหุ้นราว ${bb:,.0f} (รวม ASR) ส่วน $329.17 เป็นหุ้นซื้อในตลาด 3 พันหุ้น ไม่รวม ASR [LRCX-FACTS.md แถว 144] | ✅ ลดลงเล็กน้อย |
| L ผู้นำ/ผู้ตาม | ผลตอบแทน 12 เดือน {pct(lsp["ret_12m_stock"])} เทียบ S&P 500 {pct(lsp["ret_12m_index"])} และ Nasdaq {pct(lnq["ret_12m_index"])} [คำนวณ] | ✅ เหนือดัชนี [RS rating ยังไม่ยืนยัน] |
| I สถาบันถือ | ไม่ได้ดึง 13F (BlackRock 9.41% ใน DEF 14A อ้าง 13G ณ 31 ธ.ค. 2023 เก่ากว่า 2.5 ปี ไม่ใช้) | ⚪ [ยังไม่ยืนยัน] |
| M ทิศทางตลาด | {mm("S&P 500", msp)}; {mm("Nasdaq", mnq)} | 🟡 ผสม |

**สรุป CAN SLIM:** C ✅ A 🟡 N ❌ S ✅ L ✅ I ⚪ M 🟡 ด้านกำไรไตรมาสล่าสุดและผลตอบแทนเทียบดัชนีเข้าเกณฑ์ แต่ราคาอยู่ห่างจุดสูงมากและกำไรรายปีมีปีลบคั่น (ธุรกิจวัฏจักร) เป็นการประเมินตามกรอบ momentum แยกจากกรอบ value ไม่ใช่สัญญาณซื้อขาย

**เงื่อนไขเปลี่ยนเป็นผ่าน:** A = EPS FY2027 โต ≥ +25% (ราว {usd(nz)} ขึ้นไป) · N = ราคาปิดอยู่ภายใน 15% ของจุดสูง (ราว {usd(n["high_52w"] * 0.85)} ขึ้นไป ตามจุดสูงปัจจุบัน) · M = S&P 500 และ Nasdaq เหนือทั้ง MA50 และ MA200 · I = ดึง 13F มาตรวจก่อน · เอกสารไม่ระบุสาเหตุที่ราคาเปลี่ยน จึงไม่อธิบายระยะห่างจากจุดสูง
{MD_END}
"""


def inject_md() -> None:
    p = HERE.parent / "LRCX.md"
    t = p.read_text(encoding="utf-8")
    a, b = t.find(MD_START), t.find(MD_END)
    if a >= 0 and b > a:
        t = t[:a] + build_md().rstrip("\n") + t[b + len(MD_END):]
    else:
        k = t.index("## 5. Bear case")
        t = t[:k] + build_md() + "\n" + t[k:]
    p.write_text(t, encoding="utf-8")
    print("ใส่ CAN SLIM ใน", p)


if __name__ == "__main__":
    inject()
    inject_md()
