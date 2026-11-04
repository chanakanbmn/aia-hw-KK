import pytest

from src.canslim import (
    annual_eps,
    latest_quarter_eps,
    market_state,
    price_stats,
    relative_strength,
    shares_trend,
)


def _row(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form}


def facts_with(tag_rows, tag="EarningsPerShareDiluted", unit="USD/shares"):
    return {"facts": {"us-gaap": {tag: {"units": {unit: tag_rows}}}}}


def test_latest_quarter_eps_from_three_month_rows():
    f = facts_with([
        _row("2026-07-01", "2026-09-30", 1.50, "2026-10-28"),
        _row("2025-07-01", "2025-09-30", 1.00, "2026-10-28"),
        _row("2026-04-01", "2026-06-30", 1.20, "2026-07-23"),
    ])
    q = latest_quarter_eps(f)
    assert q == {"period_end": "2026-09-30", "eps": 1.50, "prior_eps": 1.00, "growth": pytest.approx(0.5), "derived": False}


def test_latest_quarter_eps_derives_q4_from_year_minus_nine_months():
    # ไตรมาส 4 ไม่มีใน 10-Q: Q4 = ทั้งปี − 9 เดือน (ประมาณ เพราะจำนวนหุ้นเฉลี่ยต่างกัน)
    f = facts_with([
        _row("2025-08-01", "2026-04-30", 9.0, "2026-05-20"),   # 9 เดือน FY26
        _row("2024-08-01", "2025-04-30", 8.0, "2025-05-22"),   # 9 เดือน FY25
        _row("2025-08-01", "2026-07-31", 12.0, "2026-09-09", "10-K"),  # FY26
        _row("2024-08-01", "2025-07-31", 10.0, "2025-09-03", "10-K"),  # FY25
        _row("2026-02-01", "2026-04-30", 3.0, "2026-05-20"),   # Q3 FY26 (3 เดือน)
    ])
    q = latest_quarter_eps(f)
    assert q["derived"] is True
    assert q["period_end"] == "2026-07-31"
    assert q["eps"] == pytest.approx(3.0)        # 12 − 9
    assert q["prior_eps"] == pytest.approx(2.0)  # 10 − 8
    assert q["growth"] == pytest.approx(0.5)


def test_annual_eps_uses_latest_filed_value_after_split_restatement():
    f = facts_with([
        _row("2024-01-01", "2024-12-31", 20.0, "2025-02-01", "10-K"),   # ก่อนแตกหุ้น
        _row("2024-01-01", "2024-12-31", 4.0, "2026-02-01", "10-K"),    # ปรับย้อนหลัง 5:1
        _row("2025-01-01", "2025-12-31", 5.0, "2026-02-01", "10-K"),
    ])
    a = annual_eps(f)
    assert [(x["end"], x["eps"]) for x in a] == [("2024-12-31", 4.0), ("2025-12-31", 5.0)]
    assert a[1]["growth"] == pytest.approx(0.25)
    assert a[0]["growth"] is None


def test_annual_eps_empty_when_tag_missing():
    assert annual_eps({"facts": {"us-gaap": {}}}) == []


def test_price_stats_high_low_and_moving_averages():
    closes = [float(x) for x in range(1, 301)]  # ขึ้นทุกวัน 300 วัน
    s = price_stats(closes)
    assert s["last"] == 300.0
    assert s["high_52w"] == 300.0 and s["pct_from_high"] == 0.0
    assert s["ma50"] == pytest.approx(sum(range(251, 301)) / 50)
    assert s["ma200"] == pytest.approx(sum(range(101, 301)) / 200)
    assert s["above_ma50"] and s["above_ma200"]
    assert s["ret_12m"] == pytest.approx(300 / 48 - 1)  # 252 วันทำการก่อนหน้า = ราคา 48


def test_price_stats_short_history_returns_none_for_ma200():
    s = price_stats([10.0] * 60)
    assert s["ma200"] is None and s["above_ma200"] is None


def test_relative_strength_is_return_difference():
    stock = [100.0] * 252 + [150.0]
    index = [100.0] * 252 + [110.0]
    rs = relative_strength(stock, index)
    assert rs["ret_12m_stock"] == pytest.approx(0.5)
    assert rs["ret_12m_index"] == pytest.approx(0.1)
    assert rs["excess_12m"] == pytest.approx(0.4)


def test_market_state_uptrend_vs_downtrend():
    up = market_state([float(x) for x in range(1, 301)])
    assert up["trend"] == "ขาขึ้น"
    down = market_state([float(x) for x in range(300, 0, -1)])
    assert down["trend"] == "ขาลง"


def test_shares_trend_compares_latest_with_year_ago():
    f = facts_with([
        _row("2026-07-01", "2026-09-30", 98.0, "2026-10-28"),
        _row("2025-07-01", "2025-09-30", 100.0, "2026-10-28"),
    ], tag="WeightedAverageNumberOfDilutedSharesOutstanding", unit="shares")
    t = shares_trend(f)
    assert t["change"] == pytest.approx(-0.02)


def test_annual_growth_uses_comparatives_from_the_same_filing_not_mixed_split_bases():
    # FY2022 ยังเป็นฐานก่อนแตกหุ้น (33.0) แต่ FY2023 ถูกปรับย้อนหลังเป็นฐานหลังแตก (3.32)
    f = facts_with([
        _row("2022-07-01", "2023-06-25", 33.2, "2023-08-10", "10-K"),
        _row("2021-06-28", "2022-06-26", 33.0, "2023-08-10", "10-K"),
        _row("2022-07-01", "2023-06-25", 3.32, "2025-08-11", "10-K"),
    ])
    a = {x["end"]: x for x in annual_eps(f)}
    assert a["2023-06-25"]["eps"] == pytest.approx(3.32)
    assert a["2023-06-25"]["growth"] == pytest.approx(33.2 / 33.0 - 1)  # ไม่ใช่ 3.32/33.0 − 1 = −90%
