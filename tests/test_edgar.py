import copy

import pytest

from src.edgar import fetch_companyfacts, ttm_metrics


def _e(start, end, val, form):
    return {"start": start, "end": end, "val": val, "form": form}


def _inst(end, val, form="10-Q"):
    return {"end": end, "val": val, "form": form}


def make_facts():
    """FY2024 10-K + 10-Q 6 เดือน 2025 (ตัวเลขสะสมตั้งแต่ต้นปี) พร้อมรายการ 3 เดือนปนอยู่"""

    def flow(fy, h25, h24, q2=None):
        rows = [
            _e("2024-01-01", "2024-12-31", fy, "10-K"),
            _e("2025-01-01", "2025-06-30", h25, "10-Q"),
            _e("2024-01-01", "2024-06-30", h24, "10-Q"),
        ]
        if q2 is not None:
            rows.append(_e("2025-04-01", "2025-06-30", q2, "10-Q"))
        return {"units": {"USD": rows}}

    return {
        "cik": 123,
        "facts": {
            "us-gaap": {
                "NetCashProvidedByUsedInOperatingActivities": flow(1000, 700, 450, q2=400),
                "PaymentsToAcquirePropertyPlantAndEquipment": flow(100, 60, 40),
                "ShareBasedCompensation": flow(300, 200, 130),
                "Revenues": flow(5000, 3000, 2500, q2=1600),
                "CashAndCashEquivalentsAtCarryingValue": {
                    "units": {"USD": [_inst("2024-12-31", 700, "10-K"), _inst("2025-06-30", 800)]}
                },
                "LongTermDebt": {
                    "units": {"USD": [_inst("2025-06-30", 400)]}
                },
            }
        },
    }


def test_ttm_from_cumulative_10q():
    m = ttm_metrics(make_facts(), as_of="2026-11-02")
    assert m["ocf"] == 1250  # 1000 + 700 - 450 (ไม่ใช่ 400 ของไตรมาสเดียว)
    assert m["capex"] == 120
    assert m["sbc"] == 370
    assert m["fcf_after_sbc"] == 760
    assert m["revenue"] == 5500
    assert m["revenue_growth_yoy"] == pytest.approx(0.2)
    assert m["cash"] == 800
    assert m["debt"] == 400
    assert m["as_of"] == "2026-11-02"
    assert m["period_end"] == "2025-06-30"
    assert "CIK0000000123" in m["source_url"]


def test_ttm_when_latest_is_full_year():
    facts = make_facts()
    for tag in facts["facts"]["us-gaap"].values():
        rows = tag["units"]["USD"]
        tag["units"]["USD"] = [r for r in rows if r.get("form") == "10-K"]
    m = ttm_metrics(facts, as_of="2026-11-02")
    assert m["ocf"] == 1000
    assert m["fcf_after_sbc"] == 1000 - 100 - 300


def test_negative_fcf_kept_as_negative():
    facts = copy.deepcopy(make_facts())
    sbc = facts["facts"]["us-gaap"]["ShareBasedCompensation"]["units"]["USD"]
    for r in sbc:
        r["val"] *= 10
    m = ttm_metrics(facts, as_of="2026-11-02")
    assert m["fcf_after_sbc"] < 0


def test_missing_tag_returns_none():
    facts = copy.deepcopy(make_facts())
    del facts["facts"]["us-gaap"]["ShareBasedCompensation"]
    m = ttm_metrics(facts, as_of="2026-11-02")
    assert m["sbc"] is None
    assert m["fcf_after_sbc"] is None  # ไม่เดาว่า SBC = 0
    assert m["ocf"] == 1250


def test_missing_user_agent_raises(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        fetch_companyfacts("0000000123")


def test_cutoff_uses_only_periods_ending_on_or_before_cutoff():
    m = ttm_metrics(make_facts(), as_of="2026-11-02", cutoff="2024-12-31")
    assert m["period_end"] == "2024-12-31"
    assert m["fcf_after_sbc"] == 1000 - 100 - 300
    assert m["cash"] == 700
    assert m["debt"] is None


def test_shares_outstanding_latest():
    from src.edgar import shares_outstanding

    facts = make_facts()
    facts["facts"]["dei"] = {
        "EntityCommonStockSharesOutstanding": {
            "units": {"shares": [
                {"end": "2025-01-31", "val": 90, "form": "10-K"},
                {"end": "2025-07-31", "val": 100, "form": "10-Q"},
            ]}
        }
    }
    assert shares_outstanding(facts) == 100
    assert shares_outstanding(make_facts()) is None
