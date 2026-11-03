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


from src.dashboard import zone_key_for  # noqa: E402


@pytest.mark.parametrize(
    "st,key",
    [("โซน 3", "z3"), ("โซน 2", "z2"), ("โซน 1", "z1"), ("นอกโซน", "out"),
     ("ไม่มีราคา", "none"), ("ราคาเก่า", "none"), ("ไม่มีโซน", "none")],
)
def test_zone_key_for_each_status(st, key):
    assert zone_key_for(st) == key


def test_make_row_has_zone_key_and_spark_passthrough():
    r = make_row({"ticker": "AAA"}, Z, 110.0, "2026-11-02", TODAY, spark=[1.0, 2.0, 3.0])
    assert r["zone_key"] == "z2"
    assert r["spark"] == [1.0, 2.0, 3.0]


def test_make_row_spark_defaults_to_empty_list():
    assert make_row({"ticker": "AAA"}, Z, 110.0, "2026-11-02", TODAY)["spark"] == []


def test_spark_change_pct():
    from src.dashboard import spark_change

    assert spark_change([100.0, 110.0]) == pytest.approx(0.10)
    assert spark_change([100.0]) is None
    assert spark_change([]) is None


from src.dashboard import group_rows  # noqa: E402


def _r(ticker, sector, label):
    return {"ticker": ticker, "sector": sector, "label": label}


def test_group_rows_keeps_sector_order_of_first_appearance():
    rows = [_r("A", "ซอฟต์แวร์", "รอ"), _r("B", "การเงิน", "ซื้อ"), _r("C", "ซอฟต์แวร์", "สนใจ")]
    groups = group_rows(rows)
    assert [g["sector"] for g in groups] == ["ซอฟต์แวร์", "การเงิน"]


def test_group_rows_sorts_within_sector_by_label():
    rows = [_r("A", "S", "รอ"), _r("B", "S", None), _r("C", "S", "ซื้อ"), _r("D", "S", "สนใจ")]
    assert [r["ticker"] for r in group_rows(rows)[0]["rows"]] == ["C", "D", "A", "B"]


def test_group_rows_counts_labels_and_unknown():
    rows = [_r("A", "S", "ซื้อ"), _r("B", "S", "สนใจ"), _r("C", "S", "รอ"), _r("D", "S", "รอ"), _r("E", "S", None)]
    assert group_rows(rows)[0]["counts"] == {"ซื้อ": 1, "สนใจ": 1, "รอ": 2, "ไม่มีข้อมูล": 1}


def test_make_row_sector_defaults_to_other():
    assert make_row({"ticker": "AAA"}, Z, 110.0, "2026-11-02", TODAY)["sector"] == "อื่น ๆ"
    assert make_row({"ticker": "AAA", "sector": "ซอฟต์แวร์"}, Z, 110.0, "2026-11-02", TODAY)["sector"] == "ซอฟต์แวร์"
