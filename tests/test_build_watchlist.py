import json

from src.build_watchlist import build
from tests.test_edgar import make_facts


def _setup(tmp_path, price_rows):
    facts = make_facts()
    facts["facts"]["dei"] = {
        "EntityCommonStockSharesOutstanding": {"units": {"shares": [{"end": "2025-07-31", "val": 100, "form": "10-Q"}]}}
    }
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "AAA.json").write_text(json.dumps(facts), encoding="utf-8")
    (tmp_path / "tickers.csv").write_text("ticker,cik\nAAA,123\nBBB,456\n", encoding="utf-8")
    header = "ticker,date,close,source_url,as_of\n"
    (tmp_path / "prices.csv").write_text(header + price_rows, encoding="utf-8")
    return tmp_path


def _quarters():
    rows = []
    for i, day in enumerate(
        ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]
    ):
        rows.append(f"AAA,{day},{10 + i},https://example.test/p,2026-11-02\n")
    return "".join(rows)


def test_html_contains_source_link_for_every_row(tmp_path):
    d = _setup(tmp_path, _quarters())
    build(str(d / "tickers.csv"), str(d / "prices.csv"), str(d / "out"), raw_dir=str(d / "raw"), today="2026-11-02")
    html = (d / "out" / "watchlist.html").read_text(encoding="utf-8")
    assert html.count("<tr data-ticker=") == 2
    assert "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json" in html
    assert "https://example.test/p" in html
    assert (d / "out" / "data.csv").exists()


def test_missing_price_row_renders_without_crash(tmp_path):
    d = _setup(tmp_path, _quarters())  # BBB ไม่มีทั้งราคาและงบ
    build(str(d / "tickers.csv"), str(d / "prices.csv"), str(d / "out"), raw_dir=str(d / "raw"), today="2026-11-02")
    html = (d / "out" / "watchlist.html").read_text(encoding="utf-8")
    row = html.split('data-ticker="BBB"')[1].split("</tr>")[0]
    assert "ไม่มีราคา" in row
