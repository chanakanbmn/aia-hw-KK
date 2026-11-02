from src.alert import status

Z = {"level1": 100.0, "level2": 80.0, "level3": 60.0}
TODAY = "2026-11-02"


def test_price_above_level1_is_outside():
    assert status(120.0, "2026-11-01", Z, TODAY) == "นอกโซน"


def test_price_at_level2_returns_zone2():
    assert status(80.0, "2026-11-01", Z, TODAY) == "โซน 2"


def test_price_between_levels_takes_shallowest_matching():
    assert status(90.0, "2026-11-01", Z, TODAY) == "โซน 1"
    assert status(50.0, "2026-11-01", Z, TODAY) == "โซน 3"


def test_none_price_returns_no_price():
    assert status(None, None, Z, TODAY) == "ไม่มีราคา"


def test_price_older_than_7_days_returns_stale():
    assert status(70.0, "2026-10-20", Z, TODAY) == "ราคาเก่า"


def test_no_zones_returns_no_zone():
    assert status(70.0, "2026-11-01", None, TODAY) == "ไม่มีโซน"
