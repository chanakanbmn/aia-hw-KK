# Software Buy-Zone Watchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง watchlist หน้าเดียวที่บอกว่าหุ้นซอฟต์แวร์/ไซเบอร์ 6 ตัวอยู่ในโซนซื้อหรือไม่ โดยทุกตัวเลขย้อนไปถึงเอกสาร SEC ได้

**Architecture:** สคริปต์ Python เล็กๆ แยกตามหน้าที่: ดึงงบจาก SEC EDGAR → คำนวณ metric และโซนซื้อ → เทียบราคา → สร้าง HTML ราคาตลาดอ่านจาก `data/prices.csv` ที่ผู้เรียนกรอกเอง (พร้อมแหล่งและวันที่) เพื่อไม่ผูกกับแหล่งราคาที่ยังไม่ได้เลือก

**Tech Stack:** Python 3 (ใช้ venv ของ workspace `D:\Let's go\.venv` ห้ามเรียก `python` ลอยๆ เพราะเครื่องนี้เคยติดตั้ง Python เองโดยไม่ถาม), `requests`, `pytest`, HTML ล้วน

**Spec:** `spec.md`

## Global Constraints

- repo เป็น Public: ห้ามมี key, token, อีเมล, พอร์ตจริง ค่า User-Agent ของ EDGAR อ่านจากตัวแปรสภาพแวดล้อม `SEC_USER_AGENT` ห้ามเขียนลงไฟล์
- ทุกตัวเลขต้องมี `source_url` และ `as_of` (วันที่ดึง) หาไม่ได้ให้เว้นว่าง ห้ามเดา
- ราคาที่ยังไม่ยืนยันติดป้าย `[ยังไม่ยืนยัน]`
- FCF = เงินสดจากการดำเนินงาน − capex − SBC (ทุกตัวเลขมาจากงบกระแสเงินสดใน 10-K/10-Q)
- ผลงานอยู่ใน `output/` ตามกติกาของ repo
- โซนซื้อ = ล่างสุด 25% ของช่วง multiple 3–5 ปีของหุ้นตัวเอง แบ่ง 3 ระดับ (เกณฑ์นี้เป็นการเลือกของผู้ช่วย ผู้เรียนยังไม่ยืนยัน)
- ตอบ/เขียนเอกสารเป็นภาษาไทย; commit ข้อความ `รอบ N: ทำอะไร` และมี entry คู่กันใน `prompts.md`

## Review Focus

1. หุ้นที่ FCF หลังหัก SBC เป็นลบ (น่าจะเจอกับ S, KVYO, ZETA [ยังไม่ยืนยัน]): EV/FCF ไม่นิยาม ต้องตกไปใช้ EV/Sales และบอกชัดว่าใช้ตัวไหน ไม่ error ไม่โชว์ตัวเลขลบเป็นโซน
2. XBRL แต่ละบริษัทใช้ tag ต่างกัน หรือบางไตรมาสไม่มี: ต้องระบุว่า "ไม่พบ" แทนการเดาหรือเอา 0
3. 10-Q รายงานกระแสเงินสดแบบสะสมตั้งแต่ต้นปี ไม่ใช่รายไตรมาส: TTM ต้องคำนวณถูก
4. `data/prices.csv` ขาดบางตัวหรือราคาเก่าเกิน 7 วัน: แสดง "ไม่มีราคา" หรือคำเตือนว่าราคาเก่า ไม่ crash ไม่บอกว่าอยู่ในโซน
5. `SEC_USER_AGENT` ไม่ได้ตั้ง: ต้องหยุดพร้อมข้อความชัดเจน ไม่ยิง request ที่ถูกบล็อก

---

### Task 1: ดึงงบจาก EDGAR และคำนวณ TTM

**Files:**
- Create: `src/edgar.py`, `tests/test_edgar.py`, `tests/fixtures/companyfacts_sample.json`
- Create: `data/tickers.csv` (คอลัมน์ `ticker,cik`; ผู้ช่วยหา CIK จาก EDGAR และตรวจกับผู้เรียน)

**Interfaces:**
- Produces:
  - `fetch_companyfacts(cik: str) -> dict` (อ่าน `SEC_USER_AGENT`, raise `RuntimeError` ถ้าไม่ได้ตั้ง)
  - `ttm_metrics(facts: dict) -> dict` คืน `{"ocf","capex","sbc","fcf_after_sbc","revenue","revenue_growth_yoy","cash","debt","source_url","as_of"}` ค่าที่ไม่พบเป็น `None`

- [ ] **Step 1: เขียน test ที่ล้มก่อน** ใน `tests/test_edgar.py`: `test_ttm_from_cumulative_10q` (fixture มี 10-K + 10-Q สะสม คาด `fcf_after_sbc` ตรงกับเลขที่คำนวณมือจาก fixture), `test_negative_fcf_kept_as_negative`, `test_missing_tag_returns_none`, `test_missing_user_agent_raises`
- [ ] **Step 2: รัน** `.venv\Scripts\python -m pytest tests/test_edgar.py -v` คาดว่า FAIL (ยังไม่มีโมดูล)
- [ ] **Step 3: implement `fetch_companyfacts` และ `ttm_metrics` ใน `src/edgar.py`** TTM = ปีเต็มล่าสุด + สะสมงวดปัจจุบัน − สะสมงวดเดียวกันปีก่อน ใช้ tag ของ us-gaap ที่ตรงกับ OCF, capex, SBC, รายได้, เงินสด, หนี้ และคืน `None` เมื่อไม่พบ
- [ ] **Step 4: รัน test อีกครั้ง** คาด PASS
- [ ] **Step 5: ดึงจริง 6 ตัว** บันทึก JSON ดิบลง `data/raw/<TICKER>.json` (ไฟล์สาธารณะจาก SEC ไม่ใช่ข้อมูลที่ซื้อมา) เปิดดูว่ามีหุ้นตัวไหนได้ `None` แล้วจดลง `PROJECT_MEMORY.md`
- [ ] **Step 6: เพิ่ม entry ใน `prompts.md` แล้ว commit** `รอบ 1: ดึงงบ EDGAR และคำนวณ FCF หลังหัก SBC`

### Task 2: Multiple และโซนซื้อ

**Files:**
- Create: `src/zones.py`, `tests/test_zones.py`, `data/prices.csv` (คอลัมน์ `ticker,date,close,source_url,as_of`; ผู้เรียนกรอก ราคาย้อนหลังแบบสิ้นไตรมาส 3–5 ปี และราคาล่าสุด)

**Interfaces:**
- Consumes: `ttm_metrics` จาก Task 1
- Produces:
  - `multiples(price: float, shares: float, m: dict) -> dict` คืน `{"ev_fcf": float | None, "ev_sales": float | None, "basis": "ev_fcf" | "ev_sales"}`
  - `buy_zones(history: list[float]) -> dict` คืน `{"level1","level2","level3"}` เป็นค่า multiple (level1 = เปอร์เซ็นไทล์ 25, level2 = 15, level3 = 5)
  - `zones_to_price(zones: dict, m: dict, shares: float) -> dict` แปลงโซนเป็นราคา

- [ ] **Step 1: เขียน test ที่ล้ม:** `test_negative_fcf_falls_back_to_ev_sales` (basis = "ev_sales"), `test_zones_ordered_level1_gt_level2_gt_level3`, `test_history_too_short_returns_none` (ต่ำกว่า 8 ไตรมาสไม่ตั้งโซน)
- [ ] **Step 2: รันให้เห็น FAIL**
- [ ] **Step 3: implement ทั้งสามฟังก์ชันใน `src/zones.py`** ใช้ `statistics.quantiles` หรือ numpy percentile
- [ ] **Step 4: รันให้ PASS**
- [ ] **Step 5: `prompts.md` + commit** `รอบ 2: คำนวณ multiple และโซนซื้อ`

### Task 3: สถานะ alert

**Files:**
- Create: `src/alert.py`, `tests/test_alert.py`

**Interfaces:**
- Consumes: `zones_to_price` จาก Task 2
- Produces: `status(latest_price: float | None, price_date: str | None, zone_prices: dict, today: str) -> str` คืนหนึ่งใน `"นอกโซน" | "โซน 1" | "โซน 2" | "โซน 3" | "ไม่มีราคา" | "ราคาเก่า"`

- [ ] **Step 1: test ที่ล้ม:** `test_price_at_level2_returns_zone2`, `test_none_price_returns_no_price`, `test_price_older_than_7_days_returns_stale`
- [ ] **Step 2: รัน FAIL → Step 3: implement `status` ใน `src/alert.py` → Step 4: รัน PASS**
- [ ] **Step 5: `prompts.md` + commit** `รอบ 3: สถานะ alert ตามโซนซื้อ`

### Task 4: หน้า watchlist HTML

**Files:**
- Create: `src/build_watchlist.py`, `tests/test_build_watchlist.py`
- Output: `output/watchlist.html`, `output/data.csv`

**Interfaces:**
- Consumes: Tasks 1–3
- Produces: `build(tickers_csv: str, prices_csv: str, out_dir: str) -> None` เขียนตาราง 6 แถว คอลัมน์: ticker, FCF หลังหัก SBC, อัตราโต, EV/FCF, EV/Sales, basis, โซน 1/2/3 เป็นราคา, ราคาล่าสุด+วันที่, สถานะ, ลิงก์ที่มา

- [ ] **Step 1: test ที่ล้ม:** `test_html_contains_source_link_for_every_row`, `test_missing_price_row_renders_without_crash`
- [ ] **Step 2: รัน FAIL → Step 3: implement `build` → Step 4: รัน PASS**
- [ ] **Step 5: เปิด `output/watchlist.html` ในเบราว์เซอร์ จับภาพหน้าจอลง `output/watchlist.png`**
- [ ] **Step 6: ตรวจกฎ Public** ไม่มีอีเมล/token/พอร์ตจริงใน `data/`, `output/`, `src/` (`grep -ri "@" src data output` ต้องไม่เจออีเมลจริง)
- [ ] **Step 7: `prompts.md` + commit** `รอบ 4: watchlist HTML 6 ตัว`

### Task 5: Deep dive เต็ม 2 ตัว

**Files:**
- Output: `output/deepdive-<TICKER>.html` ×2

- [ ] **Step 1: เลือก 2 ตัวร่วมกับผู้เรียน** (ผู้ช่วยยังไม่ได้เลือก)
- [ ] **Step 2: ใช้ skill `stock-deepdive-lite:fetch` แล้ว `stock-deepdive-lite:deepdive` ต่อตัว** จากนั้นให้ agent `stock-deepdive-lite:factcheck` ตรวจตัวเลขก่อนติดสถานะ verified
- [ ] **Step 3: ตรวจว่า FCF และ multiple ในรายงานตรงกับ watchlist** ถ้าไม่ตรงให้หาสาเหตุก่อนส่ง
- [ ] **Step 4: `prompts.md` + `PROJECT_MEMORY.md` (บทเรียน อย่างน้อย 1 ข้อ) + commit** `รอบ 5: deep dive 2 ตัว`

### Task 6: ปิดงานก่อนส่ง

**Files:**
- Modify: `README.md` (ตารางหัวเรื่อง), `help.md` (3 ข้อ)

- [ ] **Step 1: กรอกตารางบนสุดใน `README.md`** แล้วลบหัวข้อ "วิธีใช้ template นี้"
- [ ] **Step 2: เขียน `help.md` 3 ข้อจากสิ่งที่ติดจริง**
- [ ] **Step 3: ไล่ "เช็กก่อนส่ง" ใน README ทีละข้อ** แล้ว push เมื่อผู้เรียนสั่งเท่านั้น
