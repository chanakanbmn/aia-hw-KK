import json

import pytest

from src.dashboard import label_for, make_row, normalize_zones, resolve_path, sort_rows

TODAY = "2026-11-03"
Z = {"zone3_max": 100.0, "zone2_max": 130.0, "zone1_max": 200.0}


@pytest.mark.parametrize(
    "status,label,color",
    [
        ("โซน 3", "ซื้อ", "green"),
        ("โซน 2", "สนใจ", "yellow"),
        ("โซน 1", "รอ", "red"),
        ("นอกโซน", "รอ", "red"),
        ("ไม่มีราคา", None, "grey"),
        ("ราคาเก่า", None, "grey"),
        ("ไม่มีโซน", None, "grey"),
    ],
)
def test_label_for_every_status(status, label, color):
    assert label_for(status) == (label, color)


def test_normalize_inline_zones(tmp_path):
    assert normalize_zones({"zone3_max": 1, "zone2_max": 2, "zone1_max": 3}, tmp_path) == {
        "zone3_max": 1, "zone2_max": 2, "zone1_max": 3}


def test_normalize_simple_zones_file(tmp_path):
    (tmp_path / "z.json").write_text(json.dumps({"zones": Z}), encoding="utf-8")
    assert normalize_zones({"zones_file": "z.json"}, tmp_path) == Z


def test_normalize_intu_style_uses_adjusted_fcf(tmp_path):
    data = {"zones": {"adjusted_fcf": {"zone3_max": 214.7, "zone2_max": 432.0, "zone1_max": 729.9},
                      "reported_fcf": {"zone3_max": 297.0, "zone2_max": 593.6, "zone1_max": 1000.0}}}
    (tmp_path / "z.json").write_text(json.dumps(data), encoding="utf-8")
    assert normalize_zones({"zones_file": "z.json"}, tmp_path)["zone3_max"] == 214.7


def test_normalize_bx_style_buy_hold(tmp_path):
    (tmp_path / "z.json").write_text(json.dumps({"buy_max": 99, "hold_max": 150, "review_min": 165}), encoding="utf-8")
    # ≤ buy_max = ซื้อ, ≤ hold_max = สนใจ, เกินนั้น = รอ
    assert normalize_zones({"zones_file": "z.json"}, tmp_path) == {"zone3_max": 99, "zone2_max": 150, "zone1_max": 150}


def test_normalize_missing_file_returns_none(tmp_path):
    assert normalize_zones({"zones_file": "nope.json"}, tmp_path) is None


def test_make_row_zone2_is_yellow_with_gap_to_zone3():
    r = make_row({"ticker": "AAA", "name": "A"}, Z, 110.0, "2026-11-02", TODAY)
    assert (r["status"], r["label"], r["color"]) == ("โซน 2", "สนใจ", "yellow")
    assert r["gap_pct"] == pytest.approx(100.0 / 110.0 - 1)


def test_make_row_missing_price_is_grey():
    r = make_row({"ticker": "AAA", "name": "A"}, Z, None, None, TODAY)
    assert (r["label"], r["color"], r["gap_pct"]) == (None, "grey", None)


def test_make_row_stale_price_is_grey():
    r = make_row({"ticker": "AAA", "name": "A"}, Z, 90.0, "2026-10-01", TODAY)
    assert r["color"] == "grey"


def test_sort_rows_buy_first_grey_last():
    rows = [{"ticker": t, "label": l} for t, l in [("R", "รอ"), ("G", None), ("B", "ซื้อ"), ("I", "สนใจ")]]
    assert [r["ticker"] for r in sort_rows(rows)] == ["B", "I", "R", "G"]


def test_resolve_path_only_allows_known_routes(tmp_path):
    watch = [{"ticker": "NOW", "infographic": "info.html"}]
    (tmp_path / "info.html").write_text("x", encoding="utf-8")
    assert resolve_path("/infographic/NOW", watch, tmp_path) == tmp_path / "info.html"
    assert resolve_path("/infographic/XYZ", watch, tmp_path) is None
    assert resolve_path("/../../data/raw/NOW.json", watch, tmp_path) is None
    assert resolve_path("/infographic/..%2F..%2Fsecret", watch, tmp_path) is None
