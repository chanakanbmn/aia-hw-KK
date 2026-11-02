import pytest

from src.zones import buy_zones, history_multiples, multiples, zones_to_price
from tests.test_edgar import make_facts

M = {"fcf_after_sbc": 760, "revenue": 5500, "cash": 800, "debt": 400}


def test_multiples_basic():
    r = multiples(10.0, 100, M)  # market cap 1000, EV = 1000 + 400 - 800 = 600
    assert r["ev_fcf"] == pytest.approx(600 / 760)
    assert r["ev_sales"] == pytest.approx(600 / 5500)
    assert r["basis"] == "ev_fcf"


def test_negative_fcf_falls_back_to_ev_sales():
    r = multiples(10.0, 100, {**M, "fcf_after_sbc": -50})
    assert r["ev_fcf"] is None
    assert r["basis"] == "ev_sales"


def test_zones_ordered_level1_gt_level2_gt_level3():
    z = buy_zones([float(x) for x in range(10, 50)])
    assert z["level1"] > z["level2"] > z["level3"]


def test_history_too_short_returns_none():
    assert buy_zones([1.0] * 7) is None


def test_zones_to_price_round_trips():
    zones = {"level1": 0.5, "level2": 0.4, "level3": 0.3}
    prices = zones_to_price(zones, M, 100, "ev_fcf")
    for key, mult in zones.items():
        assert multiples(prices[key], 100, M)["ev_fcf"] == pytest.approx(mult)


def test_history_multiples_uses_fundamentals_known_at_each_date():
    hist = history_multiples(make_facts(), [("2024-12-31", 10.0)], 100, "ev_fcf")
    # FCF ณ สิ้นปี 2024 = 600, EV = 1000 + 0 - 700 = 300
    assert hist == [pytest.approx(0.5)]


def test_history_multiples_skips_undefined_points():
    # ไม่มีงวดที่จบก่อน cutoff -> ข้ามจุดนั้น ไม่ crash
    assert history_multiples(make_facts(), [("2020-01-01", 10.0)], 100, "ev_fcf") == []
