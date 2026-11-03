"""คำนวณตัวเลขที่ใช้ใน LRCX.md / LRCX-infographic.html (ไม่ต้องคำนวณมือ)

รัน:  "D:/Let's go/.venv/Scripts/python.exe" -I output/LRCX/tools/calc_lrcx.py
อ่าน:  data/raw/LRCX.json, data/prices.csv, src/zones.py (ผ่าน src/edgar.py)   เขียน: output/LRCX/tools/calc_lrcx.json

ค่าตั้งต้นจากตาราง LRCX-FACTS.md (แถวที่ระบุ) และราคา 227.56 (แหล่งรอง Yahoo [ยังไม่ยืนยัน])
สมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน]: คิดลด 10% โตระยะยาว 3% และพารามิเตอร์ของสามฉาก
"""
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.edgar import shares_outstanding, ttm_metrics  # noqa: E402
from src.zones import buy_zones, history_multiples, multiples, zones_to_price  # noqa: E402

PRICE = 227.56          # FACTS แถว 181 (แหล่งรอง ยังไม่ยืนยัน)
HIGH52 = 438.5          # ข้อมูลรายวัน Yahoo ตามผู้ใช้ (แหล่งรอง ยังไม่ยืนยัน)
DISC, TERM = 0.10, 0.03
raw = json.loads((ROOT / "data" / "raw" / "LRCX.json").read_text(encoding="utf-8"))
m = ttm_metrics(raw, as_of="2026-11-03")
sh = shares_outstanding(raw)
mc = PRICE * sh
ev = mc + m["debt"] - m["cash"]
fcf_b = m["fcf_after_sbc"]
fcf_a = m["ocf"] - m["capex"]
out = {"price": PRICE, "high52": HIGH52, "below_high_pct": (PRICE / HIGH52 - 1) * 100,
       "shares": sh, "mcap": mc, "debt": m["debt"], "cash": m["cash"], "ev": ev,
       "revenue_ltm": m["revenue"], "ocf_ltm": m["ocf"], "capex_ltm": m["capex"], "sbc_ltm": m["sbc"],
       "fcf_a": fcf_a, "fcf_b": fcf_b, "growth_yoy": m["revenue_growth_yoy"]}
out["ev_fcf_a"], out["ev_fcf_b"], out["ev_sales"] = ev / fcf_a, ev / fcf_b, ev / m["revenue"]
out["fcf_a_margin"], out["fcf_b_margin"] = fcf_a / m["revenue"] * 100, fcf_b / m["revenue"] * 100
out["sbc_pct_fcf"] = m["sbc"] / fcf_a * 100


def req_growth(fcf0, value, r=DISC, tg=TERM, n=10):
    """FCF ต้องโตปีละกี่ % นาน n ปี แล้วโตต่อเนื่อง tg ตลอดไป เพื่อให้มูลค่าปัจจุบันเท่า value"""
    def pv(g):
        s, f = 0.0, fcf0
        for t in range(1, n + 1):
            f *= 1 + g
            s += f / (1 + r) ** t
        return s + f * (1 + tg) / (r - tg) / (1 + r) ** n
    lo, hi = -0.5, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if pv(mid) < value:
            lo = mid
        else:
            hi = mid
    return mid * 100


out["rdcf_a"], out["rdcf_b"] = req_growth(fcf_a, ev), req_growth(fcf_b, ev)
out["sens"] = {k: [[req_growth(f, ev, r, tg) for tg in (0.02, 0.03, 0.04)] for r in (0.08, 0.10, 0.12)]
               for k, f in (("a", fcf_a), ("b", fcf_b))}

# --- โซน (รันซ้ำด้วย src/zones.py) ---
px = [(r["date"], float(r["close"])) for r in csv.DictReader(open(ROOT / "data" / "prices.csv", encoding="utf-8")) if r["ticker"] == "LRCX"]
cur = multiples(PRICE, sh, m)
hist = history_multiples(raw, px, sh, cur["basis"])
zz = zones_to_price(buy_zones(hist), m, sh, cur["basis"])
q = statistics.quantiles(hist, n=4, method="inclusive")
out["zones"] = {"z1": zz["level1"], "z2": zz["level2"], "z3": zz["level3"], "basis": cur["basis"],
                "ev_fcf_now": cur["ev_fcf"], "n": len(hist), "min": min(hist), "q1": q[0], "median": q[1], "q3": q[2], "max": max(hist)}

# --- ข้อมูลวัฏจักรจาก FACTS (USD) ---
REV = {"FY2021": 14626150000, "FY2022": 17227039000, "FY2023": 17428516000, "FY2024": 14905386000, "FY2025": 18435591000, "FY2026": 23232690000}
OCF = {"FY2021": 3588163000, "FY2022": 3099674000, "FY2023": 5178938000, "FY2024": 4652269000, "FY2025": 6173264000, "FY2026": 5857657000}
CAP = {"FY2021": 349096000, "FY2022": 546034000, "FY2023": 501568000, "FY2024": 396670000, "FY2025": 759186000, "FY2026": 966405000}
fy = list(REV)
out["rev_yoy"] = {fy[i]: (REV[fy[i]] / REV[fy[i - 1]] - 1) * 100 for i in range(1, 6)}
out["fcf_a_margin_fy"] = {k: (OCF[k] - CAP[k]) / REV[k] * 100 for k in fy}
out["rev_fy24_vs_fy23"] = out["rev_yoy"]["FY2024"]
out["rev_cagr_5y"] = ((REV["FY2026"] / REV["FY2021"]) ** (1 / 5) - 1) * 100

Q_REV_Q1 = 8219418
# --- สามฉาก 3 ปี (12 เดือนถึง ก.ย. 2029) ---
NETCASH = m["cash"] - m["debt"]
SC = {"bad": (-16.0, 12.0, min(hist)), "base": (8.0, 22.0, statistics.median(hist)), "good": (12.0, 28.0, q[2])}
out["scenarios"] = {}
for k, (g, mg, mult) in SC.items():
    rev3 = m["revenue"] * (1 + g / 100) ** 3
    fa = rev3 * mg / 100
    fb = fa - m["sbc"]            # SBC คงที่ตามดอลลาร์ 12 เดือนล่าสุด
    ps = lambda f: (f * mult + NETCASH) / sh  # noqa: E731  ถือเงินสดสุทธิและจำนวนหุ้นคงที่
    out["scenarios"][k] = {"g": g, "margin": mg, "mult": mult, "rev3": rev3, "fcf_a3": fa, "fcf_b3": fb,
                           "ps_a": ps(fa), "ps_b": ps(fb), "vs_price_a": (ps(fa) / PRICE - 1) * 100,
                           "vs_price_b": (ps(fb) / PRICE - 1) * 100}
out["netcash"] = NETCASH
# ฉากฐานเทียบ run-rate รายได้ไตรมาสล่าสุด x 4 และฉากแย่ที่ไม่ซ้อนมัลติเพิลต่ำสุด (ใช้มัธยฐานแทน)
out["runrate_rev"] = Q_REV_Q1 * 4 * 1000
out["base_rev3_vs_runrate"] = (out["scenarios"]["base"]["rev3"] / out["runrate_rev"] - 1) * 100
_b = out["scenarios"]["bad"]
_fb = _b["fcf_b3"]
out["bad_median_mult_ps_b"] = (_fb * statistics.median(hist) + NETCASH) / sh
out["bad_median_mult_ps_a"] = (_b["fcf_a3"] * statistics.median(hist) + NETCASH) / sh
out["rev_cagr_4y"] = ((REV["FY2026"] / REV["FY2022"]) ** (1 / 4) - 1) * 100
FCFA = {k: (OCF[k] - CAP[k]) for k in fy}
SBCV = {"FY2022": 259064000, "FY2026": 386381000}
out["fcfa_cagr_4y"] = ((FCFA["FY2026"] / FCFA["FY2022"]) ** 0.25 - 1) * 100
out["fcfb_cagr_4y"] = (((FCFA["FY2026"] - SBCV["FY2026"]) / (FCFA["FY2022"] - SBCV["FY2022"])) ** 0.25 - 1) * 100
out["fy24_yoy_per_week"] = ((REV["FY2024"] / 53) / (REV["FY2023"] / 52) - 1) * 100
# ซื้อหุ้นคืน: ต้นทุนรวมต่อหุ้น (ตลาด+ASR) เทียบเฉพาะหุ้นตลาด
out["bb_fy26_avg_cost"] = 3474460 / 23400
out["bb_q1_total_cost_per_sh"] = 1010711 / 2344
out["bb_q1_total_vs_price"] = (PRICE / out["bb_q1_total_cost_per_sh"] - 1) * 100
out["bb_fy26_avg_vs_price"] = (PRICE / out["bb_fy26_avg_cost"] - 1) * 100
out["bb_q4_vs_price"] = (PRICE / 325.14 - 1) * 100
out["asr_shares_q1"] = 2344 - 3
out["q1fy26_fcf_margin"] = (1778964 - 185121) / 5324173 * 100
out["q1fy27_fcf_margin_chk"] = (3497652 - 257697) / 8219418 * 100
out["q2q4fy26_fcf_margin"] = ((OCF["FY2026"] - CAP["FY2026"]) / 1000 - (1778964 - 185121)) / (REV["FY2026"] / 1000 - 5324173) * 100
out["debt_date_gap_pct_ev"] = (3735444 - 3722061) * 1000 / ev * 100
out["rpo_qoq"] = (2661231 / 2433996 - 1) * 100
out["rpo_yoy"] = (2661231 / 2769203 - 1) * 100

# --- งบ Q1 FY2027 vs Q1 FY2026 (พัน USD ตามงบ FACTS แถว 25-32, 55-60, 74-75, 93-94, 114-118, 140-141) ---
Q = {  # รายการ: (Q1FY27, Q1FY26)
    "rev": (8219418, 5324173), "gp": (4298853, 2684879), "op": (3283727, 1829088), "ni": (2753138, 1568660),
    "ocf": (3497652, 1778964), "capex": (257697, 185121), "sbc": (114696, 97241),
    "systems": (5732907, 3547565), "support": (2486511, 1776608), "china": (2885608, 2282573),
    "rd": (666398, 576446), "sga": (348728, 279345), "buyback": (1024965, 975791), "div": (325402, 291981),
    "ar": (5658379, 3633034), "inv": (4550544, 4095054)}
out["q"] = {k: {"cur": a, "prev": b, "chg": (a / b - 1) * 100} for k, (a, b) in Q.items()}
for k in ("fcf_a", "fcf_b"):
    sub = (lambda d: d["ocf"] - d["capex"]) if k == "fcf_a" else (lambda d: d["ocf"] - d["capex"] - d["sbc"])
    a, b = sub({x: Q[x][0] for x in Q}), sub({x: Q[x][1] for x in Q})
    out["q"][k] = {"cur": a, "prev": b, "chg": (a / b - 1) * 100}
out["q_gm"] = (Q["gp"][0] / Q["rev"][0] * 100, Q["gp"][1] / Q["rev"][1] * 100)
out["q_om"] = (Q["op"][0] / Q["rev"][0] * 100, Q["op"][1] / Q["rev"][1] * 100)
out["q_qoq_rev"] = (8219418 / 6722238 - 1) * 100
out["dso"] = (Q["ar"][0] / Q["rev"][0] * 91, Q["ar"][1] / Q["rev"][1] * 91)   # วันขาย ~ AR / รายได้ไตรมาส x 91 วัน (วิธีคิดของเรา)
# ซื้อหุ้นคืน + ปันผล เทียบ FCF
bb_ltm = 3851343 - 975791 + 1024965
dv_ltm = 1270635 - 291981 + 325402
out["bb_ltm"], out["div_ltm"] = bb_ltm * 1000, dv_ltm * 1000
out["ret_over_fcf_a"] = (bb_ltm + dv_ltm) * 1000 / fcf_a * 100
out["ret_over_fcf_b"] = (bb_ltm + dv_ltm) * 1000 / fcf_b * 100
out["bb_fy26_over_fcf_a"] = 3851343 / (OCF["FY2026"] / 1000 - CAP["FY2026"] / 1000) * 100
out["bb_fy26_plus_div_over_fcf_a"] = (3851343 + 1270635) / (OCF["FY2026"] / 1000 - CAP["FY2026"] / 1000) * 100
out["bb_vs_price"] = {"q1fy27": (PRICE / 329.17 - 1) * 100, "may_jun26": (PRICE / 370.15 - 1) * 100}
out["china_share"] = {"q1fy27": Q["china"][0] / Q["rev"][0] * 100, "q1fy26": Q["china"][1] / Q["rev"][1] * 100}
out["purchase_obl_chg"] = (1481195 / 1036227 - 1) * 100
out["ar_fy26_vs_fy25"] = (5339682 / 3378071 - 1) * 100
out["inv_q1_vs_rev"] = (Q["inv"][0] / 4307991 - 1) * 100
out["netdebt_note"] = {"cash_9_27": 7437384, "debt_6_28": 3722061}
out["cash_over_mcap"] = m["cash"] / mc * 100

# FY2026 (บริษัทรายงาน) ช่วงโซนเทียบ: ส่วนต่างโซน 1 กับราคา
out["price_over_z1"] = (PRICE / zz["level1"] - 1) * 100
out["drop_to_z1"] = (1 - zz["level1"] / PRICE) * 100


# --- มุมที่ไม่ตรงกัน: ถ้าเอา Q1 FY2027 คูณ 4 (สมมติว่าอัตราไตรมาสนี้คงที่ ซึ่งเป็นวัฏจักรจึงไม่ควรเชื่อ) ---
out["ann_q1_fcf_a"] = out["q"]["fcf_a"]["cur"] * 4 * 1000
out["ann_q1_fcf_b"] = out["q"]["fcf_b"]["cur"] * 4 * 1000
out["ev_over_ann_a"] = ev / out["ann_q1_fcf_a"]
out["ev_over_ann_b"] = ev / out["ann_q1_fcf_b"]
out["q1_fcf_a_margin"] = out["q"]["fcf_a"]["cur"] / Q["rev"][0] * 100
out["fy26_op_margin"] = 8199795000 / REV["FY2026"] * 100
out["fy26_fcf_b"] = OCF["FY2026"] - CAP["FY2026"] - 386381000
out["fy26_fcf_b_margin"] = out["fy26_fcf_b"] / REV["FY2026"] * 100
out["ev_over_fy26_fcf_a"] = ev / (OCF["FY2026"] - CAP["FY2026"])
out["ev_over_fy26_fcf_b"] = ev / out["fy26_fcf_b"]
out["fy26_ar_over_rev_pct"] = 5339682000 / REV["FY2026"] * 100

(ROOT / "output" / "LRCX" / "tools" / "calc_lrcx.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
