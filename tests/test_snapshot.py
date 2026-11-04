import csv

import pytest

from src.snapshot import FIELDS, compare, make_rows, read_snapshot, write_snapshot

Z = {"zone3_max": 100.0, "zone2_max": 130.0, "zone1_max": 200.0}
ENTRY = {"ticker": "AAA", "name": "A Corp", "sector": "ซอฟต์แวร์"}


def _rows(price=120.0, price_date="2026-11-04", scenarios=None, zones=Z):
    return make_rows(
        entries=[{**ENTRY, "_zones": zones, "_scenarios": scenarios}],
        prices={"AAA": (price, price_date)},
        sp500=(5000.0, "2026-11-04"),
        asof="2026-11-04",
        commit="abc1234",
    )


def test_make_rows_has_all_fields_and_correct_label():
    r = _rows()[0]
    assert set(FIELDS) <= set(r)
    assert r["ticker"] == "AAA" and r["snapshot_date"] == "2026-11-04"
    assert r["price"] == 120.0 and r["status"] == "โซน 2" and r["label"] == "สนใจ"
    assert (r["zone3_max"], r["zone2_max"], r["zone1_max"]) == (100.0, 130.0, 200.0)
    assert r["sp500"] == 5000.0 and r["git_commit"] == "abc1234"


def test_make_rows_keeps_scenarios_when_given():
    r = _rows(scenarios={"bad": 60, "base": 130, "good": 200, "kind": "ต่อหุ้นก่อนหัก SBC"})[0]
    assert (r["scenario_bad"], r["scenario_base"], r["scenario_good"]) == (60, 130, 200)
    assert r["scenario_kind"] == "ต่อหุ้นก่อนหัก SBC"


def test_make_rows_missing_price_gives_blank_label_not_crash():
    r = make_rows([{**ENTRY, "_zones": Z, "_scenarios": None}], {}, (5000.0, "2026-11-04"), "2026-11-04", "abc")[0]
    assert r["price"] == "" and r["label"] == "" and r["status"] == "ไม่มีราคา"


def test_write_snapshot_refuses_to_overwrite(tmp_path):
    p = tmp_path / "2026-11-04.csv"
    write_snapshot(p, _rows())
    with pytest.raises(FileExistsError):
        write_snapshot(p, _rows())


def test_snapshot_round_trips_through_csv(tmp_path):
    p = tmp_path / "s.csv"
    write_snapshot(p, _rows())
    back = read_snapshot(p)
    assert back[0]["ticker"] == "AAA" and back[0]["price"] == 120.0 and back[0]["zone2_max"] == 130.0


def _path(*pairs):
    return [(d, c) for d, c in pairs]


def test_compare_return_excess_and_zone_entry():
    snap = read_snapshot_rows(_rows())
    paths = {"AAA": _path(("2026-11-04", 120.0), ("2026-12-01", 95.0), ("2027-01-15", 140.0), ("2027-02-04", 250.0))}
    index = _path(("2026-11-04", 5000.0), ("2027-02-04", 5250.0))
    r = compare(snap, paths, index, today="2027-02-04")[0]
    assert r["return"] == pytest.approx(250 / 120 - 1)
    assert r["index_return"] == pytest.approx(0.05)
    assert r["excess"] == pytest.approx(250 / 120 - 1 - 0.05)
    assert r["min_price"] == 95.0 and r["max_price"] == 250.0
    assert r["entered_zone3"] is True and r["first_zone3_date"] == "2026-12-01"
    assert r["entered_zone2"] is True
    assert r["status_then"] == "โซน 2" and r["status_now"] == "นอกโซน"  # ใช้โซนที่ล็อกไว้ ไม่คำนวณใหม่


def test_compare_never_entered_zone():
    snap = read_snapshot_rows(_rows(price=190.0))
    paths = {"AAA": _path(("2026-11-04", 190.0), ("2027-02-04", 210.0))}
    r = compare(snap, paths, _path(("2026-11-04", 5000.0), ("2027-02-04", 5000.0)), today="2027-02-04")[0]
    assert r["entered_zone3"] is False and r["first_zone3_date"] is None
    assert r["entered_zone1"] is True and r["first_zone1_date"] == "2026-11-04"  # 190 ≤ โซน 1 (200) ตั้งแต่วัน snapshot


def test_compare_missing_history_returns_none_values():
    snap = read_snapshot_rows(_rows())
    r = compare(snap, {}, _path(("2026-11-04", 5000.0), ("2027-02-04", 5250.0)), today="2027-02-04")[0]
    assert r["return"] is None and r["excess"] is None and r["status_now"] == "ไม่มีราคา"


def test_compare_only_counts_prices_on_or_after_snapshot_date():
    snap = read_snapshot_rows(_rows())
    paths = {"AAA": _path(("2026-10-01", 50.0), ("2026-11-04", 120.0), ("2027-02-04", 125.0))}  # 50 ก่อน snapshot ต้องไม่นับ
    r = compare(snap, paths, _path(("2026-11-04", 5000.0), ("2027-02-04", 5000.0)), today="2027-02-04")[0]
    assert r["min_price"] == 120.0 and r["entered_zone3"] is False


def read_snapshot_rows(rows):
    """แปลงผลของ make_rows ให้อยู่ในรูปเดียวกับที่ read_snapshot คืน (ผ่านไฟล์ CSV จริง)"""
    import io

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    buf.seek(0)
    from src.snapshot import _parse

    return [_parse(r) for r in csv.DictReader(buf)]


def test_compare_counts_prices_from_the_snapshot_price_date_not_the_run_date():
    # snapshot สร้างวันที่ 11-04 แต่ราคาล่าสุดที่มีตอนนั้นเป็นของ 11-03 (ตลาดยังไม่ปิดวันที่ 11-04)
    snap = read_snapshot_rows(_rows(price=120.0, price_date="2026-11-03"))
    paths = {"AAA": _path(("2026-11-03", 120.0))}  # มีแค่จุดของวันที่ใน snapshot (เทียบทันทีหลังสร้าง)
    r = compare(snap, paths, _path(("2026-11-03", 5000.0)), today="2026-11-04")[0]
    assert r["price_now"] == 120.0 and r["return"] == pytest.approx(0.0)
