"""สร้าง LRCX-infographic.html (ส่วนหลัก 7 หัวข้อ) จาก tools/calc_lrcx.json แล้วเรียก build_5yr.py เติมส่วนพับ

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/calc_lrcx.py
      "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/build_infographic.py
      "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/build_5yr.py
ตัวเลขที่คำนวณทุกตัวมาจาก calc_lrcx.json ไม่กรอกมือ ทุกบรรทัดที่มีตัวเลขคำนวณมีป้าย [คำนวณ]
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "LRCX-infographic.html"
C = json.loads((HERE / "calc_lrcx.json").read_text(encoding="utf-8"))
Z, S, Q = C["zones"], C["scenarios"], C["q"]
CM = ' <span class="cm">[คำนวณ]</span>'
PRICE_TAG = '<span class="warn">[ยังไม่ยืนยัน]</span>'
PT = '<span class="warn">[ราคา 227.56 แหล่งรอง Yahoo 2 พ.ย. 2026 ยังไม่ยืนยัน]</span>'
HT = '[แหล่งรอง Yahoo ข้อมูลรายวัน ยังไม่ยืนยัน]'


def M(v):          # ดอลลาร์เต็ม -> $xM
    return f"${v / 1e6:,.0f}M"


def B(v):
    return f"${v / 1e9:,.1f}B"


def qm(k, which="cur"):   # พัน USD -> $xM
    return f"${Q[k][which] / 1000:,.0f}M"


def chip(v, kind="up", nd=1):
    cls = "warn" if kind == "cost" else ("good" if v >= 0 else "bad")
    return f'<span class="chip {cls}">{v:+.{nd}f}%</span>'


def qrow(label, k, kind="up"):
    return (f'<tr><td>{label}</td><td class="r">{qm(k)}</td><td class="r">{qm(k, "prev")}</td>'
            f'<td class="r">{chip(Q[k]["chg"], kind)}{CM}</td></tr>')


eps_chg = (2.19 / 1.24 - 1) * 100
rpo_chg = (2661231 / 2769203 - 1) * 100
sh_chg = (1255768 / 1269313 - 1) * 100
sens = C["sens"]
q1_margin_prev = C["q1fy26_fcf_margin"]


def sens_table(key):
    rows = ""
    for i, r in enumerate((8, 10, 12)):
        rows += f'<tr><td>คิดลด {r}%</td>' + "".join(
            f'<td class="r{" hl" if (r == 10 and tg == 3) else ""}">{sens[key][i][j]:.1f}%</td>' for j, tg in enumerate((2, 3, 4))) + f'</tr>\n'
    return rows


def sc_row(name, cls, k, cond):
    s = S[k]
    return (f'<tr><td class="{cls}"><b>{name}</b></td><td>โต {s["g"]:+.0f}%/ปี · FCF margin {s["margin"]:.0f}% · EV/FCF {s["mult"]:.1f}x{CM}</td>'
            f'<td class="r"><b>~${s["ps_a"]:,.0f}</b></td><td class="r"><b>~${s["ps_b"]:,.0f}</b></td><td>{cond}</td></tr>')


def zone_bar():
    mx = 240.0
    z3, z2, z1 = Z["z3"], Z["z2"], Z["z1"]
    return (f'<div class="zone">'
            f'<div style="flex:{z3:.2f};background:var(--good)">โซน 3 ≤ ${z3:.2f}</div>'
            f'<div style="flex:{z2 - z3:.2f};background:var(--gold)"></div>'
            f'<div style="flex:{z1 - z2:.2f};background:#e29a5a"></div>'
            f'<div style="flex:{mx - z1:.2f};background:var(--bad)">นอกโซน &gt; ${z1:.2f}</div></div>\n'
            f'<div class="pin"><span style="left:{C["price"] / mx * 100:.1f}%">▲ ${C["price"]:.2f} [ยังไม่ยืนยัน] = นอกโซน</span></div>'
            f'<div class="src" style="margin-top:0">สีในแถบหมายถึงตำแหน่งเทียบอดีตของหุ้นเอง (เขียว = อยู่ในระดับมัลติเพิลล่างของช่วงที่เคยเป็น, แดง = สูงกว่าขอบโซน 1) ไม่ได้บอกว่าถูกหรือแพงในแง่สัมบูรณ์</div>')


HTML = f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lam Research LRCX Infographic</title>
<style>
:root{{--bg:#0b0a08;--card:#16130d;--line:#3a2f17;--gold:#e8c26a;--gold2:#b8914a;--text:#f1ead8;--mute:#a89c80;--good:#6fcf97;--bad:#eb7a6a;--warn:#e8c26a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:"Segoe UI","Noto Sans Thai",system-ui,sans-serif;line-height:1.55}}
.wrap{{max-width:1000px;margin:0 auto;padding:20px 16px 48px}}
h1{{margin:0;font-size:28px;color:var(--gold);letter-spacing:.5px}}
.sub{{color:var(--mute);margin:4px 0 12px;font-size:14px}}
.badge{{display:inline-block;border:1px solid var(--gold2);color:var(--gold);border-radius:99px;padding:2px 10px;font-size:12px;margin:0 6px 4px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:14px;overflow-x:auto;min-width:0}}
.card h2{{margin:0 0 10px;font-size:17px;color:var(--gold)}}
.card h3{{margin:14px 0 4px;font-size:14px;color:var(--gold2)}}
.num{{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--gold);color:#000;font-weight:700;font-size:13px;margin-right:8px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}}
.kpi{{border:1px solid var(--line);border-radius:10px;padding:10px;text-align:center}}
.kpi b{{display:block;font-size:22px;color:var(--gold)}}
.kpi span{{font-size:12px;color:var(--mute)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{color:var(--gold2);font-weight:600}}
.r{{text-align:right}}
td.hl{{background:rgba(232,194,106,.18);font-weight:700}}
.good{{color:var(--good)}}.bad{{color:var(--bad)}}.warn{{color:var(--warn)}}
.chip{{display:inline-block;border-radius:6px;padding:1px 8px;font-weight:700}}
.chip.good{{background:rgba(111,207,151,.16)}}.chip.bad{{background:rgba(235,122,106,.16)}}.chip.warn{{background:rgba(232,194,106,.16)}}
.cm{{color:var(--mute);font-size:10px;font-weight:400}}
.src{{color:var(--mute);font-size:11px;margin-top:8px}}
.zone{{display:flex;border-radius:8px;overflow:hidden;height:34px;font-size:12px;font-weight:600;color:#000;margin:10px 0 4px}}
.zone div{{display:flex;align-items:center;justify-content:center;white-space:nowrap}}
.pin{{position:relative;height:22px}}
.pin span{{position:absolute;transform:translateX(-50%);font-size:12px;color:var(--gold);white-space:nowrap}}
ul{{margin:6px 0 0;padding-left:18px}}
li{{margin:4px 0;font-size:13px}}
.price{{font-size:44px;font-weight:700;line-height:1.1}}
.warnbox{{border:1px dashed var(--bad);color:var(--bad);border-radius:10px;padding:8px 12px;font-size:12px;margin-top:12px}}
.legend{{font-size:12px;color:var(--mute);margin-bottom:8px}}
/*EXT5CSS*/
.x5>summary{{cursor:pointer;list-style:none;font-size:17px;color:var(--gold);font-weight:600}}
.x5>summary::-webkit-details-marker{{display:none}}
.x5[open]>summary{{margin-bottom:10px}}
.x5 small{{color:var(--mute);font-weight:400;font-size:12px}}
.x5 table{{min-width:860px;margin-top:10px}}
.x5 .x5h{{margin:16px 0 2px;font-size:14px;font-weight:600;color:var(--gold2)}}
.x5chart{{min-width:520px}}
.x5legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--mute);margin-bottom:4px}}
.x5legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}}
.x5legend em{{margin-left:auto;font-style:normal}}
/*EXT5CSSEND*/
</style>
</head>
<body>
<div class="wrap">
  <h1>Lam Research (LRCX)</h1>
  <div class="sub">อัปเดต 2026-11-03 · ข้อมูลงบ Q1 FY2027 (ไตรมาสที่จบ 27 ก.ย. 2026, 10-Q ยื่น 22 ต.ค. 2026) · ปีบัญชีจบสิ้นเดือนมิถุนายน</div>
  <span class="badge">สถานะ: draft</span><span class="badge">ราคา: แหล่งรอง [ยังไม่ยืนยัน]</span><span class="badge">หุ้นแตก 10:1 ต.ค. 2024</span><span class="badge">ธุรกิจวัฏจักร</span>

  <section class="card">
    <h2><span class="num">1</span>Company Overview</h2>
    <ul>
      <li><b>ทำอะไร:</b> ผู้จัดหาอุปกรณ์และบริการสำหรับโรงงานผลิตเวเฟอร์ชิป (wafer fabrication equipment) ส่วนงานรายงานส่วนเดียว รายได้แยกเป็น Systems (ขายเครื่อง) กับ Customer support-related (บริการ/อะไหล่/อัปเกรด) ใน Q1 FY2027: {qm("systems")} กับ {qm("support")} จากรวม {qm("rev")}</li>
      <li><b>ขนาด (12 เดือนถึง 27 ก.ย. 2026):</b> รายได้ {M(C["revenue_ltm"])} · OCF − capex {M(C["fcf_a"])} ·  หลังหัก SBC {M(C["fcf_b"])}{CM} · พนักงานประจำราว 23,300 คน</li>
      <li><b>ปลายทางของเครื่อง (เฉพาะอุปกรณ์+อัปเกรด) Q1 FY2027:</b> Foundry 46% / Memory 46% / Logic-IDM 8% (Q1 FY2026: 60 / 34 / 6)</li>
      <li><b>ภูมิภาค:</b> รายได้จีน 35% ของ Q1 FY2027 (34% ของ FY2026, 42% ของ FY2024) · รายได้นอกสหรัฐฯ 92% ของ Q1 FY2027</li>
      <li><b>ลูกค้า:</b> เอกสารเอ่ยชื่อ Micron, Samsung Electronics, SK hynix, TSMC เป็นลูกค้าสำคัญ และ FY2026 มีลูกค้า 4 รายที่ซื้อ ≥10% ของรายได้ (16%, 15%, 12%, 12%) เอกสารไม่ระบุว่าสัดส่วนไหนเป็นของรายใด จึงไม่จับคู่</li>
      <li><b>ข้อควรระวัง:</b> หุ้นแตก 10:1 มีผล 2 ต.ค. 2024 จึงไม่เทียบ EPS หรือจำนวนหุ้นข้ามฐานก่อน/หลังแตก · FY2026 = 30 มิ.ย. 2025 ถึง 28 มิ.ย. 2026</li>
    </ul>
    <div class="src">[ที่มา: LRCX-FACTS.md แถว 29, 58, 60, 74-77, 92, 95, 98-99, 101-102, 160 · 10-K FY2026, 10-Q Q1 FY2027]</div>
  </section>

  <section class="card">
    <h2><span class="num">2</span>Key Takeaways</h2>
    <ul>
      <li><b>สรุป:</b> Q1 FY2027 รายได้ {qm("rev")} โต {chip(Q["rev"]["chg"])}{CM} จาก Q1 FY2026 และโต {C["q_qoq_rev"]:.1f}% จากไตรมาสก่อน{CM} FCF แบบง่ายของไตรมาส {qm("fcf_a")} (margin {C["q1_fcf_a_margin"]:.1f}%){CM}</li>
      <li><b>ราคา:</b> ${C["price"]:.2f} {PRICE_TAG} ต่ำกว่าจุดสูง 52 สัปดาห์ $438.5 {HT} อยู่ {abs(C["below_high_pct"]):.1f}%{CM} {PT} นี่คือข้อเท็จจริงของตัวเลขเท่านั้น เอกสารที่บริษัทยื่นไม่ระบุสาเหตุของการเคลื่อนไหวราคา</li>
      <li><b>ความไม่แน่นอนหลัก:</b> FCF ที่ใช้ตั้งมูลค่าอยู่ใกล้ช่วงสูงของวัฏจักรหรือไม่ FCF margin แบบง่ายรายปีเคยอยู่ที่ {C["fcf_a_margin_fy"]["FY2022"]:.1f}% (FY2022) ถึง {C["fcf_a_margin_fy"]["FY2025"]:.1f}% (FY2025) และ {C["fcf_a_margin_fy"]["FY2026"]:.1f}% (FY2026){CM} เทียบกับ Q1 FY2027 ที่ {C["q1_fcf_a_margin"]:.1f}%{CM}</li>
      <li><b>ตำแหน่งตามกติกาโซน:</b> ราคาอยู่นอกโซน (ขอบโซน 1 = ${Z["z1"]:.2f}) ซึ่งเทียบมัลติเพิลปัจจุบัน {Z["ev_fcf_now"]:.1f}x กับมัธยฐาน {Z["median"]:.1f}x ของ {Z["n"]} ไตรมาสของตัวเอง ไม่ได้บอกว่าแพงหรือถูกในแง่สัมบูรณ์ (ดูหัวข้อ 5)</li>
      <li><b>เงื่อนไขที่ต้องตรวจทุกไตรมาส</b> (เกณฑ์เป็นสมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน]): รายได้รายไตรมาสลดลงเทียบไตรมาสก่อนสองไตรมาสติด (วันนี้ +{C["q_qoq_rev"]:.1f}%; เป็นตัวชี้วัดล้าหลัง จึงใช้ร่วมกับ RPO และสินค้าคงคลัง) · RPO เทียบปีก่อนติดลบลึกกว่าวันนี้ ({C["rpo_yoy"]:.1f}%) ขณะรายได้ยังโต (RPO ณ 27 ก.ย. 2026 สูงกว่า ณ 28 มิ.ย. 2026 {C["rpo_qoq"]:+.1f}%){CM} · gross margin ไตรมาสต่ำกว่า 50% (วันนี้ {C["q_gm"][0]:.1f}%, ปีก่อน {C["q_gm"][1]:.1f}%) · สัดส่วนรายได้จีนเกิน 40% (วันนี้ 35%; ระดับ FY2024 คือ 42%) · ข้อจำกัดส่งออกใหม่ที่บริษัทเปิดเผย (นับเป็นข้อของมันเอง ไม่ต้องรอสัดส่วนจีนเปลี่ยน) · วันเก็บลูกหนี้โดยประมาณเกิน 70 วัน (วันนี้ {C["dso"][0]:.1f}){CM} · สินค้าคงคลัง YoY โตเร็วกว่ารายได้ YoY สองไตรมาสติด (วันนี้ +{Q["inv"]["chg"]:.1f}% เทียบรายได้ +{Q["rev"]["chg"]:.1f}% จึงยังไม่เข้าเงื่อนไข){CM} · เมื่อเงื่อนไขใดเกิด: ทบทวนอัตราโตและ margin ของฉากฐานให้ต่ำลง และดูฉากแย่เป็นข้อมูลประกอบมากขึ้น ไม่ใช่สัญญาณซื้อขาย</li>
      <li><b>ที่ยังขาด:</b> ราคาแหล่งที่สอง · ไกด์ไลน์ผู้บริหารและประมาณการนักวิเคราะห์ (8-K 21 ต.ค. 2026 ไม่แนบ press release) · ขนาด WFE ทั้งตลาดเป็นดอลลาร์ · ผลกระทบข้อจำกัดส่งออกเป็นดอลลาร์ (เอกสารไม่ให้ตัวเลข) · backlog (เอกสารไม่รายงาน) · ผู้ถือหุ้นใหญ่ใน DEF 14A เป็นข้อมูลเก่า</li>
    </ul>
    <div class="warnbox">กรอบวิเคราะห์ตามสมมติฐานที่ระบุ ใช้ในคอร์ส ไม่ใช่คำแนะนำลงทุนส่วนบุคคล · ไม่ใช่การชี้นำให้ซื้อหรือขาย</div>
    <div class="src">[ที่มา: LRCX.md · LRCX-FACTS.md แถว 29, 58, 95, 167, 181 · ตัวเลขคำนวณจาก tools/calc_lrcx.py]</div>
  </section>

  <section class="card">
    <h2><span class="num">3</span>ราคาปัจจุบัน</h2>
    <div><span class="price">${C["price"]:.2f}</span> {PRICE_TAG} <span style="font-size:13px;color:var(--mute)">ปิด 2 พ.ย. 2026 · แหล่งรอง Yahoo</span></div>
    <div class="kpis" style="margin-top:12px">
      <div class="kpi"><b>~{B(C["mcap"])}</b><span>มูลค่าตลาด [ยังไม่ยืนยัน]{CM}<br>({C["price"]:.2f} × {C["shares"] / 1e6:,.1f}M หุ้น)</span></div>
      <div class="kpi"><b>~{B(C["ev"])}</b><span>EV [ยังไม่ยืนยัน]{CM}<br>(บวกหนี้ {B(C["debt"])} ลบเงินสด {B(C["cash"])})</span></div>
      <div class="kpi"><b class="bad">{C["below_high_pct"]:.1f}%</b><span>จากจุดสูง 52 สัปดาห์ $438.5<br>[ยังไม่ยืนยัน แหล่งรอง]{CM}</span></div>
      <div class="kpi"><b>$329.17</b><span>ราคาเฉลี่ยหุ้นที่ซื้อในตลาด Q1 FY2027 (3 พันหุ้น 29 มิ.ย.–26 ก.ค. 2026 ไม่รวม ASR)<br>{PT}<br>ราคาปัจจุบันต่ำกว่า {abs(C["bb_vs_price"]["q1fy27"]):.1f}%{CM}</span></div>
      <div class="kpi"><b>$370.15</b><span>ราคาเฉลี่ยหุ้นที่ซื้อในตลาด 25 พ.ค.–28 มิ.ย. 2026 (397 พันหุ้น ไม่รวม ASR)<br>{PT}<br>ต่ำกว่า {abs(C["bb_vs_price"]["may_jun26"]):.1f}%{CM}</span></div>
      <div class="kpi"><b>~${C["bb_q1_total_cost_per_sh"]:,.0f}</b><span>ต้นทุนรวมต่อหุ้น Q1 FY2027 รวมส่วน ASR (2,344 พันหุ้น)<br>[คำนวณ: 1,010,711k ÷ 2,344k]<br>{PT}<br>ราคาปัจจุบันต่ำกว่า {abs(C["bb_q1_total_vs_price"]):.1f}%{CM}</span></div>
      <div class="kpi"><b>~${C["bb_fy26_avg_cost"]:,.1f}</b><span>ต้นทุนต่อหุ้นทั้งปี FY2026 (23,400 พันหุ้น)<br>[คำนวณ: 3,474,460k ÷ 23,400k] ราคาปัจจุบันสูงกว่า {C["bb_fy26_avg_vs_price"]:.1f}%{CM}<br>{PT}</span></div>
    </div>
    <ul>
      <li><b>อ่านราคาซื้อหุ้นคืนให้ถูก:</b> $329.17 และ $370.15 เป็นราคาเฉลี่ยของหุ้นที่ซื้อในตลาดเท่านั้น (10-Q เขียนว่าไม่รวมผลของ ASR) ไม่ใช่ราคาเฉลี่ยทั้งไตรมาส · ส่วนที่บริษัทจ่ายผ่าน ASR ($1.00B ส่งมอบแรก 2,341 พันหุ้น) ไม่มีราคาแยก ต้นทุนรวมต่อหุ้น Q1 FY2027 ประมาณ ${C["bb_q1_total_cost_per_sh"]:,.0f} [คำนวณ] · ราคาเฉลี่ยรายไตรมาสของ FY2026 คือ 105.67 / 153.62 / 210.57 / 325.14 (ต่ำกว่าราคาปัจจุบัน 3 ไตรมาสแรก, สูงกว่าไตรมาสที่ 4) และทั้งปี ~${C["bb_fy26_avg_cost"]:,.1f} [คำนวณ] ไม่ใช่ $325.14 ({PT}) ข้อมูลนี้ไม่ใช้สรุปว่าการซื้อคืนถูกหรือแพงกว่าราคาปัจจุบัน · ราคาเฉลี่ยรายวัน ก.ค.–ก.ย. 2026 ตามแหล่งรองราว 315 [ยังไม่ยืนยัน]</li>
      <li>เอกสารที่บริษัทยื่นไม่ระบุสาเหตุที่ราคาเปลี่ยน หน้านี้จึงไม่เขียนสาเหตุ</li>
    </ul>
    <div class="src">ราคาปิด 2 พ.ย. 2026 [ที่มา: Yahoo Finance แหล่งรอง ผู้ใช้ให้มา · ยังไม่ยืนยัน] · หุ้นคงค้าง 1,249.171M (ปก 10-Q) · หนี้ตามบัญชี ณ 28 มิ.ย. 2026 เงินสด ณ 27 ก.ย. 2026 คนละวัน (ตามที่ src/edgar.py เลือกค่าล่าสุดของแต่ละรายการ) ถ้าใช้หนี้ ณ 27 ก.ย. ($3,735M) EV ต่างเพียง {C["debt_date_gap_pct_ev"]:.3f}%{CM} · งบดุล 27 ก.ย. 2026 ไม่มีเงินลงทุนระยะสั้นแยก (เงินสด+ลูกหนี้+สินค้าคงคลัง+อื่น ๆ = สินทรัพย์หมุนเวียนรวม) · ดูราคาล่าสุดด้วย ticker/ (รันเซิร์ฟเวอร์ในเครื่อง) · [ที่มา: LRCX-FACTS.md แถว 123, 143-144, 149, 181-183]</div>
  </section>

  <section class="card">
    <h2><span class="num">4</span>Valuation</h2>
    <div class="kpis">
      <div class="kpi"><b>{C["ev_fcf_a"]:.1f}x</b><span>EV/FCF (ไม่หัก SBC){CM}</span></div>
      <div class="kpi"><b>{C["ev_fcf_b"]:.1f}x</b><span>EV/FCF (หลังหัก SBC){CM}</span></div>
      <div class="kpi"><b>{C["ev_sales"]:.1f}x</b><span>EV/Sales เทียบรายได้โต {C["growth_yoy"] * 100:.1f}% (Q1 YoY){CM}</span></div>
      <div class="kpi"><b class="warn">{C["rdcf_a"]:.1f}% / {C["rdcf_b"]:.1f}%</b><span>Reverse DCF: FCF ต้องโตต่อปี 10 ปี<br>ไม่หัก / หลังหัก SBC{CM}</span></div>
      <div class="kpi"><b class="warn">{C["fcfa_cagr_4y"]:.1f}% / {C["fcfb_cagr_4y"]:.1f}%</b><span>FCF จริง CAGR 4 ปี FY2022→26<br>ไม่หัก / หลังหัก SBC{CM}<br>(ฐาน FY2022 margin ต่ำ 14.8%)</span></div>
    </div>
    <div class="warnbox" style="border-color:var(--warn);color:var(--warn)">สมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน]: อัตราคิดลด 10% · โตระยะยาว 3% · อัตราโต FCF margin และ EV/FCF ของทุกฉากด้านล่าง ไม่ใช่ข้อมูลจากบริษัท · ทุกค่าอิงราคา ${C["price"]:.2f} {PT}</div>
    <h3>มุมที่ 1-2: EV/FCF และ EV/Sales (ฐาน 12 เดือนถึง 27 ก.ย. 2026)</h3>
    <ul>
      <li>FCF ไม่หัก SBC {M(C["fcf_a"])} (margin {C["fcf_a_margin"]:.1f}%) · หลังหัก SBC {M(C["fcf_b"])} (margin {C["fcf_b_margin"]:.1f}%){CM} SBC เป็นราว {C["sbc_pct_fcf"]:.1f}% ของ FCF แบบง่าย{CM} ต่างกันไม่มาก</li>
      <li>EV/Sales {C["ev_sales"]:.1f}x ไม่มีเกณฑ์ว่าถูกหรือแพง และไม่มีหุ้นคู่เทียบในชุดข้อมูลนี้ จึงใช้เป็นข้อมูลประกอบเท่านั้น</li>
    </ul>
    <h3>มุมที่ 3: Reverse DCF ภายใต้สมมติฐาน ราคานี้สอดคล้องกับ FCF ที่โตต่อปีเท่าไร (10 ปี แล้วโต 3% ตลอดไป)</h3>
    <table>
      <tr><th>ตาราง: โตต่อปีที่ต้องการ</th><th class="r" colspan="3">ไม่หัก SBC (โตระยะยาว 2% / 3% / 4%)</th></tr>
{sens_table("a")}    </table>
    <table style="margin-top:8px">
      <tr><th>ตาราง: โตต่อปีที่ต้องการ</th><th class="r" colspan="3">หลังหัก SBC (โตระยะยาว 2% / 3% / 4%)</th></tr>
{sens_table("b")}    </table>
    <div class="src">ช่องเน้น = ค่าฐาน (คิดลด 10%, โตระยะยาว 3%) · วิธีคิด: หาอัตราโต g ที่ทำให้ผลรวมมูลค่าปัจจุบันของ FCF 10 ปี + มูลค่าปลายทาง เท่ากับ EV ณ ราคานี้ [คำนวณ ด้วย tools/calc_lrcx.py] · ผลไวต่อสมมติฐานทั้งสอง</div>
    <h3>สามฉาก (มอง 12 เดือนถึง ก.ย. 2029 จากฐานปัจจุบัน ไม่ใช่ราคาเป้าหมาย ไม่มีน้ำหนักความน่าจะเป็น)</h3>
    <table>
      <tr><th>ฉาก</th><th>โต / FCF margin / EV/FCF (สมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน])</th><th class="r">ต่อหุ้น ก่อนหัก SBC</th><th class="r">ต่อหุ้น หลังหัก SBC</th><th>เงื่อนไขที่ยังไม่เกิด</th></tr>
{sc_row("ดี", "good", "good", f"รายได้โตต่อเนื่อง 3 ปีโดยไม่มีปีลดลง (เคยโตสูงสุดรายปี {C['rev_yoy']['FY2026']:.1f}% ใน FY2026){CM} margin ใกล้ระดับสูงสุดที่เคยเกิด ({C['fcf_a_margin_fy']['FY2025']:.1f}% FY2025){CM} มัลติเพิลเท่าควอร์ไทล์บนของช่วงตัวเอง")}
{sc_row("ฐาน", "warn", "base", f"โต 8% ใกล้ CAGR 4 ปี FY2022→26 ({C['rev_cagr_4y']:.1f}%, ฐานตรงกับตารางพับ 5 ปี){CM} ทำให้รายได้ปี 2029 = {B(S['base']['rev3'])} ใกล้เคียง (ไม่ต่ำกว่า) รายได้ไตรมาสล่าสุด x 4 = {B(C['runrate_rev'])} ({C['base_rev3_vs_runrate']:+.1f}%){CM} · FCF margin 22% ใกล้ FY2026 ({C['fcf_a_margin_fy']['FY2026']:.1f}%) ซึ่งถูกลูกหนี้กด (ดูหัวข้อ 7) · มัลติเพิลเท่ามัธยฐานของช่วงตัวเอง")}
{sc_row("แย่", "bad", "bad", f"ปีลดลงต่อเนื่อง 3 ปีที่แรงกว่า FY2024 ({C['rev_fy24_vs_fy23']:.1f}%){CM} margin ต่ำกว่าปีต่ำสุด ({C['fcf_a_margin_fy']['FY2022']:.1f}% FY2022){CM} และต่ำกว่า LTM ({C['fcf_a_margin']:.1f}%){CM} มัลติเพิลเท่าค่าต่ำสุดของช่วงตัวเอง ({Z['min']:.1f}x) <b>ซ้อนกัน:</b> ค่าต่ำสุดของมัลติเพิลกับ margin ต่ำสุดตั้งพร้อมกัน ทั้งที่ในประวัติมัลติเพิลสูงสุดเกิดตอน FCF ต่ำ")}
    </table>
    <ul>
      <li><b>ฉากต่อหุ้นไม่ใช่ราคาเป้าหมาย</b> ไม่มีน้ำหนักความน่าจะเป็น เป็นผลของสมมติฐานที่ตั้งเอง ตัวเลขทั้งหมดอิงจำนวนหุ้น ({C["shares"] / 1e6:,.1f}M) และเงินสดสุทธิ ({B(C["netcash"])}){CM} คงที่ ซึ่งไม่ตรงความจริง (บริษัทซื้อหุ้นคืนและจ่ายผู้ถือหุ้นต่อเนื่อง) ทิศของความคลาดเคลื่อน: เงินสดจาก FCF 3 ปีไม่ถูกบวกเข้ามูลค่า และจำนวนหุ้นที่ลดลงจากการซื้อคืนไม่ถูกนับ (สองข้อนี้กดทุกฉากลง) ส่วนการเทียบมูลค่าปี 2029 กับราคาวันนี้โดยไม่คิดลดเวลาทำให้ฉากดูสูงกว่ามูลค่าปัจจุบัน</li>
      <li><b>ฉากฐานหลังปรับ:</b> ครั้งแรกตั้งโต 5% ต่อปี ให้รายได้ปี 2029 ราว $30.2B ซึ่งต่ำกว่ารายได้ไตรมาสล่าสุด x 4 ({B(C["runrate_rev"])}) จึงไม่ใช่ฐานกลาง ๆ ปรับเป็นโต {S["base"]["g"]:.0f}% (ใกล้ CAGR 4 ปี {C["rev_cagr_4y"]:.1f}%) ได้รายได้ปี 2029 {B(S["base"]["rev3"])}{CM} CAGR 5 ปี FY2021→26 ({C["rev_cagr_5y"]:.1f}%) เป็นคนละฐานปี ไม่นำมาปนกัน · มัลติเพิลของฉากมาจากรอบวัฏจักรเดียวและ {Z["n"]} ไตรมาส ซึ่งเป็นตัวอย่างเล็ก</li>
      <li>วิธีคิด: รายได้ LTM × (1+โต)^3 × FCF margin × EV/FCF บวกเงินสดสุทธิ หารจำนวนหุ้น · คอลัมน์หลังหัก SBC ตรึง SBC ที่ {M(C["sbc_ltm"])} ต่อปีทุกฉาก (ไม่ลดตามรายได้) [คำนวณ ด้วย tools/calc_lrcx.py] · มัลติเพิลของฉากมาจากช่วงของตัวเอง (ควอร์ไทล์ล่าง/มัธยฐาน/ควอร์ไทล์บนของ {Z["n"]} ไตรมาสที่วัด EV/FCF หลังหัก SBC) ใช้กับ FCF ทั้งสองนิยาม</li>
      <li>ฉากแย่แย่กว่าปีที่แย่สุดในข้อมูลทั้งอัตราโต (FY2024 {C["rev_fy24_vs_fy23"]:.1f}% ปีเดียว เทียบ {S["bad"]["g"]:.0f}% ต่อปี 3 ปีติด){CM} และ margin และแย่กว่าตัวเลขล่าสุด ทั้งสามค่าตั้งให้เลวพร้อมกัน และซ้อนมัลติเพิลต่ำสุดกับ margin ต่ำสุดพร้อมกัน (ถ้าใช้มัธยฐาน {Z["median"]:.1f}x แทน ฉากแย่ได้ ~${C["bad_median_mult_ps_a"]:,.0f} / ~${C["bad_median_mult_ps_b"]:,.0f}{CM}) จึงเป็นขอบล่างของการทดสอบ ไม่ใช่การทำนาย margin 12% ไม่มีเหตุผลเชิงกลไกรองรับ เป็นค่าที่ตั้งให้ต่ำกว่าปีต่ำสุด</li>
    </ul>
    <h3>จุดที่มุมต่าง ๆ ไม่ตรงกัน</h3>
    <ul>
      <li><b>ตัวหารของ FCF เลือกแล้วคำตอบเปลี่ยน:</b> EV/FCF (ไม่หัก SBC) = {C["ev_over_fy26_fcf_a"]:.1f}x ถ้าใช้ FY2026 · {C["ev_fcf_a"]:.1f}x ถ้าใช้ LTM · {C["ev_over_ann_a"]:.1f}x ถ้าเอา FCF Q1 FY2027 คูณ 4{CM} ตัวสุดท้ายสมมติว่าอัตรานี้คงที่ ซึ่งสวนกับธรรมชาติวัฏจักร ไม่ควรเชื่อเป็นฐาน ขณะที่ {C["ev_over_fy26_fcf_a"]:.1f}x (FY2026) ก็ไม่ควรเชื่อเป็นฐานเช่นกัน เพราะ FCF FY2026 ถูกลูกหนี้กด (OCF ลดเพราะลูกหนี้เพิ่มราว $1.96B ตามบริษัท) ทั้งสองตัวใช้ข้อจำกัดชุดเดียวกัน</li>
      <li><b>Reverse DCF กับประวัติการเติบโต:</b> ราคานี้สอดคล้องกับ FCF ที่โตราว {C["rdcf_a"]:.0f}–{C["rdcf_b"]:.0f}% ต่อปีนาน 10 ปีตามสมมติฐาน ขณะที่รายได้ 5 ปี (FY2021→FY2026) โตเฉลี่ย {C["rev_cagr_5y"]:.1f}% ต่อปี{CM} และมีปีที่ลดลง {C["rev_fy24_vs_fy23"]:.1f}% ตัวเทียบที่ตรงกว่าคือ FCF จริง: CAGR 4 ปี FY2022→26 = {C["fcfa_cagr_4y"]:.1f}% (ไม่หัก SBC) / {C["fcfb_cagr_4y"]:.1f}% (หลังหัก SBC){CM} ซึ่งใกล้ {C["rdcf_a"]:.1f}% / {C["rdcf_b"]:.1f}% ที่ราคานี้ต้องการ แต่ฐาน FY2022 เป็นจุดต่ำ (FCF margin {C["fcf_a_margin_fy"]["FY2022"]:.1f}%) จึงทำให้ CAGR สูงเกินจริง ส่วนตัวเทียบรายได้ทำให้ช่องว่างดูกว้างกว่า (รายได้ CAGR {C["rev_cagr_4y"]:.1f}% ฐาน FY2022 และ {C["rev_cagr_5y"]:.1f}% ฐาน FY2021 สองช่วงนี้ไม่ปนกัน) · FY2024 ยาว 53 สัปดาห์ ตัวเลข YoY {C["rev_fy24_vs_fy23"]:.1f}% ไม่ได้ปรับตามจำนวนสัปดาห์ (ถ้าปรับเป็นรายสัปดาห์ {C["fy24_yoy_per_week"]:.1f}%{CM})</li>
      <li><b>ฉากฐานกับราคา:</b> ฉากฐาน ~${S["base"]["ps_a"]:,.0f} ต่ำกว่าราคา ${C["price"]:.2f} {PT} ขณะฉากดี ~${S["good"]["ps_a"]:,.0f} สูงกว่า ราคาจึงอยู่ระหว่างสองฉาก เกิดจากมัลติเพิลของฉากอิงช่วงอดีตของตัวเองซึ่งเป็นช่วงที่ FCF ต่ำ (และมาจากรอบวัฏจักรเดียว 21 ไตรมาส) ไม่ใช่การบอกว่าราคาผิด</li>
      <li><b>ก่อน/หลังหัก SBC แทบไม่ขัดกัน:</b> {C["ev_fcf_a"]:.1f}x กับ {C["ev_fcf_b"]:.1f}x{CM} ต่างจากบริษัทที่ SBC สูง คำถามหลักของ LRCX จึงเป็นเรื่องวัฏจักรของ FCF ไม่ใช่นิยาม SBC</li>
    </ul>
    <div class="src">[ที่มา: LRCX.md หัวข้อ 3 · LRCX-FACTS.md แถว 5-6, 61-62, 147-149 · คำนวณด้วย output/LRCX/tools/calc_lrcx.py · ราคา ${C["price"]:.2f} แหล่งรอง ยังไม่ยืนยัน]</div>
  </section>

  <section class="card">
    <h2><span class="num">5</span>โซนราคา</h2>
{zone_bar()}
    <table>
      <tr><th>โซน</th><th>ราคา</th><th>ความหมาย</th></tr>
      <tr><td>โซน 3</td><td>≤ ${Z["z3"]:.2f}</td><td>EV/FCF หลังหัก SBC เท่าระดับล่างสุด 5% ของช่วง {Z["n"]} ไตรมาสของตัวเอง</td></tr>
      <tr><td>โซน 2</td><td>≤ ${Z["z2"]:.2f}</td><td>ล่างสุด 15%</td></tr>
      <tr><td>โซน 1</td><td>≤ ${Z["z1"]:.2f}</td><td>ล่างสุด 25%</td></tr>
      <tr><td>นอกโซน (ตอนนี้)</td><td>&gt; ${Z["z1"]:.2f}</td><td>สูงกว่าทุกระดับ · ราคาปัจจุบันสูงกว่าขอบโซน 1 อยู่ {C["price_over_z1"]:.1f}%{CM} {PT}</td></tr>
    </table>
    <ul>
      <li>ปัจจุบัน EV/FCF หลังหัก SBC {Z["ev_fcf_now"]:.1f}x เทียบช่วงตัวเอง {Z["min"]:.1f}x–{Z["max"]:.1f}x (มัธยฐาน {Z["median"]:.1f}x ควอร์ไทล์ {Z["q1"]:.1f}x / {Z["q3"]:.1f}x){CM}</li>
      <li><b>ทำไมโซนต่ำมาก:</b> ขอบโซนคือราคาที่ทำให้มัลติเพิลเท่า {Z["q1"]:.1f}x (โซน 1) ต่อ FCF หลังหัก SBC ปัจจุบัน {M(C["fcf_b"])} · FCF โตเร็ว (Q1 FY2027 {qm("fcf_b")} เทียบ {qm("fcf_b", "prev")} ปีก่อน) ขณะที่ช่วงอดีต 21 ไตรมาสส่วนใหญ่เป็นช่วงที่ FCF ต่ำกว่านี้และมัลติเพิลต่ำกว่า จึงต้องลดราคาลง {C["drop_to_z1"]:.1f}% ถึงจะเข้าโซน 1{CM} {PT}</li>
      <li><b>อ่านให้ถูก:</b> สถานะ "นอกโซน" ไม่ได้บอกว่าแพงหรือถูกในแง่สัมบูรณ์ เป็นการเทียบกับอดีตของตัวเอง ซึ่งเป็นช่วงวัฏจักรที่ FCF ต่ำ ถ้า FCF ปัจจุบันยั่งยืนมัลติเพิลปัจจุบันจะดูสูงเกินจริงน้อยลง ถ้า FCF ปัจจุบันเป็นยอดวัฏจักรจะเป็นตรงข้าม เอกสารไม่ตอบข้อนี้</li>
      <li>ข้อจำกัด: ใช้จำนวนหุ้นล่าสุดกับราคาย้อนหลัง · ราคาย้อนหลังเป็นราคาปิดสิ้นไตรมาสจากแหล่งรอง · จุดสูงสุด {Z["max"]:.1f}x คือจุดราคาสิ้น มิ.ย. 2026 ที่คำนวณจากงบ 12 เดือนก่อนหน้า · ไม่ใช่คำแนะนำ</li>
    </ul>
    <div class="src">สเกลแถบ $0–$240 เป็นสัดส่วนจริงของราคา (โซน 2 และ 1 แคบจึงไม่มีตัวอักษร ดูตาราง) · [ที่มา: LRCX.md หัวข้อ 4 · กติกาโซนจาก src/zones.py (รันซ้ำแล้ว) และ data/prices.csv · ราคา: ยังไม่ยืนยัน]</div>
  </section>

  <section class="card">
    <h2><span class="num">6</span>งบไตรมาสล่าสุด (Q1 FY2027 เทียบ Q1 FY2026)</h2>
    <div class="legend"><span class="chip good">เขียว</span> = ดีขึ้น/เป็นบวก YoY · <span class="chip bad">แดง</span> = ลดลง/เป็นลบ YoY · <span class="chip warn">เหลือง</span> = ต้นทุน/ยอดคงค้างที่เพิ่ม (ไม่ตัดสิน)</div>
    <table>
      <tr><th>รายการ</th><th class="r">Q1 FY27</th><th class="r">Q1 FY26</th><th class="r">เปลี่ยนแปลง</th></tr>
{qrow("รายได้รวม", "rev")}
{qrow("Systems revenue", "systems")}
{qrow("Customer support-related revenue", "support")}
{qrow("รายได้จากจีน (35% ของไตรมาส, ปีก่อน 43%)", "china")}
{qrow("กำไรขั้นต้น", "gp")}
<tr><td>Gross margin (Q1 FY27 บริษัทรายงาน 52.3%)</td><td class="r">{C["q_gm"][0]:.1f}%</td><td class="r">{C["q_gm"][1]:.1f}%</td><td class="r"><span class="chip good">{C["q_gm"][0] - C["q_gm"][1]:+.1f} จุด</span>{CM}</td></tr>
{qrow("กำไรจากการดำเนินงาน", "op")}
<tr><td>Operating margin</td><td class="r">{C["q_om"][0]:.1f}%</td><td class="r">{C["q_om"][1]:.1f}%</td><td class="r"><span class="chip good">{C["q_om"][0] - C["q_om"][1]:+.1f} จุด</span>{CM}</td></tr>
{qrow("กำไรสุทธิ", "ni")}
<tr><td>EPS diluted (ฐานหลังแตกหุ้นทั้งสองงวด)</td><td class="r">$2.19</td><td class="r">$1.24</td><td class="r"><span class="chip good">{eps_chg:+.1f}%</span>{CM}</td></tr>
{qrow("R&amp;D", "rd", "cost")}
{qrow("SG&amp;A", "sga", "cost")}
{qrow("SBC", "sbc", "cost")}
{qrow("OCF", "ocf")}
{qrow("Capex", "capex", "cost")}
{qrow("FCF แบบง่าย (OCF − capex)", "fcf_a")}
{qrow("FCF หลังหัก SBC", "fcf_b")}
{qrow("ซื้อหุ้นคืน (รวมภาษีสรรพสามิต)", "buyback", "cost")}
{qrow("เงินปันผลจ่าย", "div", "cost")}
    </table>
    <div style="margin-top:12px;font-weight:600;color:var(--gold2);font-size:13px">สถานะสะสมและงบดุล</div>
    <table>
      <tr><td>รายได้ Q1 FY27 เทียบ Q4 FY26 ($6,722M)</td><td class="r"><span class="chip good">+{C["q_qoq_rev"]:.1f}%</span>{CM}</td></tr>
      <tr><td>ลูกหนี้การค้า 27 ก.ย. 2026 เทียบ 28 ก.ย. 2025</td><td class="r">{qm("ar")} vs {qm("ar", "prev")} <span class="chip warn">{Q["ar"]["chg"]:+.1f}% ใกล้เคียงรายได้ไตรมาส</span>{CM} · วันเก็บเงินโดยประมาณ {C["dso"][0]:.1f} vs {C["dso"][1]:.1f} วัน{CM}</td></tr>
      <tr><td>สินค้าคงคลัง 27 ก.ย. 2026 เทียบ 28 ก.ย. 2025</td><td class="r">{qm("inv")} vs {qm("inv", "prev")} <span class="chip warn">{Q["inv"]["chg"]:+.1f}% ช้ากว่ารายได้</span>{CM} · ณ 28 มิ.ย. 2026 $4,276M</td></tr>
      <tr><td>RPO 27 ก.ย. 2026 เทียบ 28 ก.ย. 2025</td><td class="r">$2,661M vs $2,769M <span class="chip bad">{rpo_chg:+.1f}%</span>{CM}</td></tr>
      <tr><td>เงินสด / หนี้ (ตามบัญชี)</td><td class="r">$7,437M / $3,722M (Senior Notes par $3,750M ณ 28 มิ.ย. 2026)</td></tr>
      <tr><td>วงเงินซื้อหุ้นคืนคงเหลือ · ASR ก.ย. 2026</td><td class="r">$3,032M · $1.00B (ส่งมอบแรก 75% คาดจบ ธ.ค. 2026)</td></tr>
      <tr><td>หุ้นเฉลี่ย diluted Q1 FY27 vs Q1 FY26</td><td class="r">1,255.8M vs 1,269.3M <span class="chip good">{sh_chg:+.1f}%</span>{CM}</td></tr>
    </table>
    <div class="src">สีเขียว/แดงตามทิศทาง YoY เท่านั้น · % และอัตราส่วนคำนวณจากตัวเลขในงบ · วันเก็บเงินโดยประมาณ = ลูกหนี้ ÷ รายได้ไตรมาส × 91 วัน (วิธีของเรา ไม่ใช่ตัวเลขบริษัท) · RPO ลดลงขณะรายได้โต ความหมายเอกสารไม่อธิบายในส่วนที่อ่าน (RPO เป็นยอดสัญญาที่ยังไม่รับรู้ ไม่ใช่ backlog ทั้งหมด)<br>[ที่มา: LRCX-FACTS.md แถว 25-32, 46-47, 50, 55-60, 74-75, 93-95, 110, 112, 114-118, 120, 123-124, 139-141, 144-146, 156 · 10-Q Q1 FY2027]</div>
  </section>

  <section class="card">
    <h2><span class="num">7</span>Bear Case</h2>
    <ul>
      <li><b>วัฏจักรการลงทุนอุปกรณ์ผลิตชิป:</b> 10-K (Item 1A) ระบุเองว่าอุตสาหกรรมอุปกรณ์ผลิตชิป "subject to variability and periods of rapid growth or decline" ในข้อมูลของเรา รายได้ FY2024 ลดลง {abs(C["rev_fy24_vs_fy23"]):.1f}% จาก FY2023{CM} และ FCF margin FY2022 ต่ำเหลือ {C["fcf_a_margin_fy"]["FY2022"]:.1f}%{CM} Item 1A ยังระบุผลที่ตามมาของขาลง เช่น สำรองลูกหนี้ สำรองสินค้าคงคลังล้าสมัย การด้อยค่า goodwill และภาระจากสินค้าที่สั่งซื้อไว้ล่วงหน้า</li>
      <li><b>รายได้จีนและข้อจำกัดส่งออก:</b> จีน 34% ของ FY2026 และ 35% ของ Q1 FY2027 (FY2024: 42%) 10-K ระบุว่าการขายในจีน "likely to be materially and adversely affected" จากข้อกำหนดใบอนุญาตส่งออกและมาตรการภาครัฐ เอกสารไม่ให้ตัวเลขดอลลาร์ของผลกระทบ จึงไม่ประเมิน</li>
      <li><b>ลูกค้ากระจุกตัว:</b> 4 รายซื้อ ≥10% ของรายได้ FY2026 (16/15/12/12%) · ลูกหนี้ ณ 28 มิ.ย. 2026 มี 5 รายที่ ≥10% (20/16/15/11/10%) · Item 1A: "actions of even one customer" ทำให้ผลแปรปรวนได้ ไม่จับคู่ตัวเลขกับรายชื่อลูกค้า</li>
      <li><b>เงินสดจากการดำเนินงานผันผวนเทียบกำไร:</b> FY2026 กำไรสุทธิโต 35.6% แต่ OCF ต่ำกว่า FY2025 เพราะลูกหนี้เพิ่มราว 1.96 พันล้านดอลลาร์ และ deferred profit ลด (ตามที่บริษัทอธิบาย) ลูกหนี้ ณ 28 มิ.ย. 2026 เพิ่ม {C["ar_fy26_vs_fy25"]:.1f}% จาก ณ 29 มิ.ย. 2025{CM}</li>
      <li><b>ภาระผูกพันซื้อและสินค้าคงคลัง:</b> ภาระผูกพันซื้อ $1,481M ณ 28 มิ.ย. 2026 เทียบ $1,036M ปีก่อน {chip(C["purchase_obl_chg"], "cost")}{CM} สินค้าคงคลัง $4,551M ณ 27 ก.ย. 2026 ถ้ารายได้ลดลงแบบ FY2024 ทั้งสองรายการเป็นภาระ (เป็นการอ่านเชิงกลไก ไม่ใช่ข้อมูลที่เอกสารระบุเป็นตัวเลข)</li>
      <li><b>การซื้อหุ้นคืน + ปันผล เทียบ FCF:</b> FY2026 = {C["bb_fy26_plus_div_over_fcf_a"]:.1f}% ของ FCF แบบง่ายของปีนั้น (ซื้อคืนอย่างเดียว {C["bb_fy26_over_fcf_a"]:.1f}%){CM} ใน LTM = {C["ret_over_fcf_a"]:.1f}%{CM} ต้นทุนซื้อคืนต่อหุ้นทั้งปี FY2026 ~${C["bb_fy26_avg_cost"]:,.1f} และ Q1 FY2027 (รวม ASR) ~${C["bb_q1_total_cost_per_sh"]:,.0f}{CM} ($325.14 คือราคาเฉลี่ยของไตรมาสจบ 28 มิ.ย. 2026 ไตรมาสเดียว และ $329.17 คือราคาเฉพาะหุ้นตลาด 3 พันหุ้นที่ไม่รวม ASR) ไม่ใช้เทียบหาว่าซื้อแพงหรือถูกกว่าราคาปัจจุบัน {PT}</li>
      <li><b>RPO ลดลงขณะรายได้โต:</b> RPO $2,661M ณ 27 ก.ย. 2026 เทียบ $2,769M ปีก่อน ({C["rpo_yoy"]:+.1f}%){CM} เป็นตัวชี้วัดล่วงหน้าตัวเดียวในชุดข้อมูลที่เป็นแดง ขณะรายได้โต {Q["rev"]["chg"]:.1f}% เอกสารไม่อธิบาย (RPO ไม่ใช่ backlog ทั้งหมด) จึงตีความไม่ได้ว่าบอกอะไร แต่ไม่ควรถูกทิ้ง ใช้เป็นเงื่อนไขตรวจ (หัวข้อ 2) ทั้งนี้ RPO ณ 27 ก.ย. 2026 สูงกว่า ณ 28 มิ.ย. 2026 {C["rpo_qoq"]:+.1f}%{CM}</li>
      <li><b>ต้นทุนและมาตรการการค้า:</b> 10-K ระบุว่าภาษีนำเข้าเหล็กและอะลูมิเนียมเพิ่มต้นทุนการผลิตและกด margin ใน FY2026 (ไม่ให้ตัวเลข)</li>
      <li><b>ความเอียงของฐานตัวเลขล่าสุด:</b> FCF margin Q1 FY2027 {C["q1_fcf_a_margin"]:.1f}% เทียบ FY2026 {C["fcf_a_margin_fy"]["FY2026"]:.1f}%{CM} LTM นำ Q1 FY2027 (margin {C["q1_fcf_a_margin"]:.1f}%) เข้ามาแทน Q1 FY2026 (margin {q1_margin_prev:.1f}% ซึ่งไม่ต่ำ){CM} ไตรมาสที่ต่ำคือ Q2–Q4 FY2026 รวมกัน ({C["q2q4fy26_fcf_margin"]:.1f}%){CM} ไตรมาสที่เข้ามาสูงกว่าค่าเฉลี่ยรายปี FY2026 ไม่ทราบว่าระดับนี้คงอยู่หรือไม่ ส่วน FY2026 เองถูกลูกหนี้กด (OCF ลดเพราะลูกหนี้เพิ่มราว $1.96B ตามบริษัท) จึงเป็นฐานต่ำของฉากฐาน 22%</li>
    </ul>
    <h3>ฝั่งหนุน (เท่าที่หลักฐานในเอกสารมี ให้สมดุลกับฝั่งความเสี่ยง วัฏจักรมีทั้งขาลงและขาขึ้น)</h3>
    <ul>
      <li><b>Margin ขยับขึ้น:</b> gross margin {C["q_gm"][0]:.1f}% เทียบ {C["q_gm"][1]:.1f}% และ operating margin {C["q_om"][0]:.1f}% เทียบ {C["q_om"][1]:.1f}% (Q1 FY27 เทียบ Q1 FY26){CM}</li>
      <li><b>รายได้โตทั้งสองสาย:</b> Systems {chip(Q["systems"]["chg"])} และ Customer support-related {chip(Q["support"]["chg"])} (เอกสารไม่ได้ระบุว่าสายบริการลดความผันผวนได้เท่าไร){CM}</li>
      <li><b>เงินสดสุทธิเป็นบวก:</b> เงินสด {B(C["cash"])} เทียบหนี้ตามบัญชี {B(C["debt"])} (คนละวันที่) เงินสดสุทธิ {B(C["netcash"])}{CM} · หุ้นเฉลี่ย diluted ลดลง {abs(sh_chg):.1f}% YoY{CM}</li>
      <li><b>FCF margin รายปีไม่เคยต่ำกว่า {C["fcf_a_margin_fy"]["FY2022"]:.1f}% ใน FY2021–FY2026</b> (ต่ำสุดคือ FY2022) และ Q1 FY27 {C["q1_fcf_a_margin"]:.1f}%{CM}</li>
      <li><b>ที่หาไม่ได้:</b> เอกสารที่ยื่นไม่ให้ไกด์ไลน์ผู้บริหาร backlog หรือขนาด WFE จึงไม่มีหลักฐานโดยตรงว่า FCF ระดับนี้จะคงอยู่ ฝั่งหนุนจึงเป็นตัวเลขย้อนหลัง ไม่ใช่เหตุผลล่วงหน้า</li>
    </ul>
    <div class="src" style="margin-top:12px">ฉากต่อหุ้นทั้งสาม (ก่อนหัก SBC / หลังหัก SBC · ไม่ใช่ราคาเป้าหมาย): ดี ~${S["good"]["ps_a"]:,.0f} / ~${S["good"]["ps_b"]:,.0f} · ฐาน ~${S["base"]["ps_a"]:,.0f} / ~${S["base"]["ps_b"]:,.0f} · แย่ ~${S["bad"]["ps_a"]:,.0f} / ~${S["bad"]["ps_b"]:,.0f} (ฉากแย่ซ้อนมัลติเพิลต่ำสุดกับ margin ต่ำสุด ดูหัวข้อ 4){CM}</div>
    <div class="src">ฉากแย่เป็นสมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน] ตั้ง 3 ค่าให้แย่พร้อมกัน (ซ้อนมัลติเพิลต่ำสุดกับ margin ต่ำสุด) เป็นขอบล่างของการทดสอบ · อ่านหมวด Item 1A ของ 10-K FY2026 แล้ว หัวข้อความเสี่ยงที่บริษัทเรียงไว้คือเทคโนโลยี การแข่งขัน วัฏจักรอุตสาหกรรม ลูกค้ากระจุก ฯลฯ ที่นี่ไม่จัดอันดับความเสี่ยง · ผู้ถือหุ้นใหญ่ DEF 14A (BlackRock 9.41% อ้าง 13G ณ 31 ธ.ค. 2023) เป็นข้อมูลเก่า ไม่ใช้เป็นสถานะปัจจุบัน<br>[ที่มา: LRCX-FACTS.md แถว 65, 92, 95, 99, 101-102, 106, 114-115, 108-110, 131-132, 142-144, 161, 163, 167, 176 · 10-K FY2026 Item 1A]</div>
  </section>
<!--EXT5-START-->
<!--EXT5-END-->
</div>
</body>
</html>
"""
OUT.write_text(HTML, encoding="utf-8")
print("เขียน", OUT)
