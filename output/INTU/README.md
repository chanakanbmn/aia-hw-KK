# INTU (Intuit) — งานวิเคราะห์

สถานะ: draft · อัปเดต 2026-11-03 · กรอบวิเคราะห์ในคอร์ส ไม่ใช่คำแนะนำลงทุนส่วนบุคคล

| ไฟล์ | คืออะไร |
|---|---|
| `INTU-infographic.html` | infographic หน้าเดียว (overview, takeaways, ราคา, valuation, โซนราคา, งบ FY2026, bear case) + ส่วนพับได้ "เทียบงบ 5 ปี" เปิดในเบราว์เซอร์ได้เลย |
| `INTU-5yr.html` | เทียบงบรายปี FY2022–FY2026 (ปีบัญชีจบ 31 ก.ค.) พร้อมกราฟ สร้างด้วยสคริปต์จาก SEC companyfacts |
| `INTU.md` | โน้ตสรุปหน้าเดียว พร้อมที่มาของตัวเลข |
| `INTU-FACTS.md` | ตารางข้อเท็จจริง 130 แถว พร้อมไฟล์และตำแหน่งต้นทาง |
| `INTU-deepdive-2026-11-02.html` | บทความเชิงลึกฉบับเต็ม |
| `review/` | ผลตรวจตรรกะ (`INTU-critic.md`) และผลตรวจตัวเลข (`INTU-factcheck.md`) |
| `tools/build_5yr.py` | ดึงตัวเลขจาก `data/raw/INTU.json` สร้าง `INTU-5yr.html` และเติมตาราง/กราฟ FY2026 ราคา และส่วนเทียบ 5 ปีใน infographic รันซ้ำได้ |
| `tools/check_zones.py` | ตรวจซ้ำโซนราคาและมัลติเพิลสามฉากกับ `src/zones.py` และ `zones.json` |
| `ticker/` | หน้าติดตามราคาเทียบโซน 3/2/1 รันในเครื่องด้วย `python -I server.py` (ในโฟลเดอร์ ticker) แล้วเปิด http://127.0.0.1:8766 |

รันสคริปต์ (Windows):

```
"D:/Let's go/.venv/Scripts/python.exe" -I "D:/Let's go/homework/aia-hw-KK/output/INTU/tools/build_5yr.py"
"D:/Let's go/.venv/Scripts/python.exe" -I "D:/Let's go/homework/aia-hw-KK/output/INTU/tools/check_zones.py"
```

ที่มาของตัวเลข: เอกสารที่บริษัทยื่นต่อ SEC (10-K FY2026/FY2025, 10-Q, 8-K, DEF 14A) ผ่าน `INTU-FACTS.md` และ SEC companyfacts (`data/raw/INTU.json`) ราคาหุ้น 341.09 USD (ปิด 30 ต.ค. 2026) มาจาก Yahoo Finance แบบไม่เป็นทางการ [ยังไม่ยืนยัน] อัตราโต margin และมัลติเพิลของแต่ละฉากเป็นสมมติฐานผู้วิเคราะห์ [ยังไม่ยืนยัน]

ข้อควรระวัง: CFO และ FCF ตามงบ FY2026 สูงเพราะภาษีเงินสดจ่ายต่ำผิดปกติ ($281M เทียบ $1,408M ใน FY2025) จึงมีโซนสองชุด: ปรับภาษี (ค่าหลัก) และตามงบ (ข้อมูลเทียบ) ส่วนงานถูกจัดใหม่ใน 10-K FY2026 หน้าเทียบ 5 ปีจึงแสดงรายได้รวมเท่านั้น
