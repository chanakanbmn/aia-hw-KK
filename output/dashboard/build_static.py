"""สร้างหน้า dashboard แบบไฟล์นิ่ง (ไม่ต้องมีเซิร์ฟเวอร์) ให้คนอื่นเปิดดูได้ เช่นผ่าน GitHub Pages

รัน (จากโฟลเดอร์ repo): python -I output/dashboard/build_static.py
ได้: output/dashboard/public.html (ฝังข้อมูล ณ เวลาที่รัน) และ index.html ที่รากของ repo (หน้ารวมลิงก์ผลงานจาก landing.template)

ดึงราคาจาก Yahoo Finance แบบไม่เป็นทางการ 1 ครั้งตอนสร้างไฟล์ หน้าที่ได้ไม่เรียกเครือข่ายอีก (มี CSP ห้ามเชื่อมต่อ)
ข้อมูลเป็นภาพนิ่ง ณ เวลาที่รัน ต้องรันใหม่เมื่ออยากอัปเดต
"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))  # import server.py (ใช้ฟังก์ชันดึงราคาและจัดแถวร่วมกับ dashboard สด)
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from src.dashboard import group_rows, render_static  # noqa: E402

INDEX = (HERE / "landing.template").read_text(encoding="utf-8")  # หน้ารวมลิงก์ผลงาน (index.html ที่รากของ repo)


def main() -> None:
    watch = {e["ticker"]: e for e in server.load_watch()}
    rows = server.get_rows()
    for r in rows:
        inf = watch[r["ticker"]].get("infographic")
        r["infographic_url"] = inf or ""  # ลิงก์สัมพัทธ์จากโฟลเดอร์ output/dashboard/
    payload = {"rows": rows, "groups": group_rows(rows), "fetched": datetime.now().strftime("%Y-%m-%d %H:%M")}
    html = render_static((HERE / "dashboard.html").read_text(encoding="utf-8"), payload)
    (HERE / "public.html").write_text(html, encoding="utf-8")
    (ROOT / "index.html").write_text(INDEX, encoding="utf-8")
    print(f"สร้าง {HERE / 'public.html'} ({len(rows)} ตัว ข้อมูล ณ {payload['fetched']})")


if __name__ == "__main__":
    main()
