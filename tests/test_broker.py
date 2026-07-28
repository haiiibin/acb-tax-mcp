"""Tests for the broker-export normalizer."""

from __future__ import annotations

import json

import pytest

from acb_tax_mcp import server
from acb_tax_mcp.broker import normalize

RBC_STYLE = [
    {"Trade Date": "2024-01-15", "Activity Type": "Buy", "Symbol": "XEQT",
     "Quantity": "100", "Price": "$30.00", "Commission": "9.95", "Currency": "CAD",
     "Description": "ISHARES CORE EQUITY ETF"},
    {"Trade Date": "2024-02-20", "Activity Type": "Dividend", "Symbol": "XEQT",
     "Quantity": "", "Price": "", "Commission": "", "Currency": "CAD",
     "Description": "CASH DIV"},
    {"Trade Date": "2024-03-10", "Activity Type": "Sell", "Symbol": "XEQT",
     "Quantity": "-40", "Price": "33.50", "Commission": "(9.95)", "Currency": "CAD",
     "Description": "SOLD 40"},
    {"Trade Date": "2024-04-01", "Activity Type": "Deposit", "Symbol": "",
     "Quantity": "", "Price": "", "Commission": "", "Currency": "CAD",
     "Description": "CONTRIBUTION"},
    {"Trade Date": "2024-05-05", "Activity Type": "Reinvestment", "Symbol": "XEQT",
     "Quantity": "1.25", "Price": "32.00", "Commission": "0", "Currency": "CAD",
     "Description": "DRIP"},
]


def test_rbc_style_export():
    result = normalize(RBC_STYLE)
    assert result["counts"] == {"rows": 5, "trades": 3, "skipped": 2}

    buy, sell, drip = result["transactions"]
    assert buy["action"] == "buy" and buy["shares"] == 100.0 and buy["price"] == 30.0
    assert buy["commission"] == 9.95
    # signed quantity and parenthesized commission are cleaned on the sell
    assert sell["action"] == "sell" and sell["shares"] == 40.0 and sell["commission"] == 9.95
    # DRIP counts as a buy
    assert drip["action"] == "buy" and drip["shares"] == 1.25
    assert any("DRIP" in w or "reinvest" in w.lower() for w in result["warnings"])

    reasons = " ".join(s["reason"] for s in result["skipped"])
    assert "Dividend" in reasons and "Deposit" in reasons
    json.dumps(result)


def test_output_feeds_calculate_acb():
    trades = normalize(RBC_STYLE)["transactions"]
    result = server.calculate_acb(trades)
    assert result["dispositions"][0]["shares_sold"] == 40.0
    assert result["holdings"][0]["security"] == "XEQT"


def test_thousands_separator_and_alias_headers():
    rows = [
        {"Transaction Date": "2024/01/05", "Type": "You bought", "Ticker": "VTI",
         "Units": "1,000", "Unit Price": "205.10", "Fees": "1.00",
         "Currency": "USD", "Exchange Rate": "1.35"},
    ]
    result = normalize(rows)
    t = result["transactions"][0]
    assert t == {
        "date": "2024-01-05", "action": "buy", "security": "VTI", "shares": 1000.0,
        "price": 205.1, "commission": 1.0, "currency": "USD", "fx_rate": 1.35, "note": "",
    }


def test_missing_fx_on_foreign_trades_warns():
    rows = [
        {"Date": "2024-01-05", "Action": "buy", "Symbol": "VTI",
         "Quantity": "10", "Price": "200", "Currency": "USD"},
    ]
    result = normalize(rows)
    assert any("fx_rate" in w for w in result["warnings"])


def test_bad_trade_row_is_skipped_with_reason():
    rows = [
        {"Date": "2024-01-05", "Action": "buy", "Symbol": "AAA", "Quantity": "10", "Price": "10"},
        {"Date": "not-a-date", "Action": "buy", "Symbol": "AAA", "Quantity": "10", "Price": "10"},
    ]
    result = normalize(rows)
    assert result["counts"]["trades"] == 1
    assert result["counts"]["skipped"] == 1
    assert "date" in result["skipped"][0]["reason"].lower()


def test_unmappable_headers_raise():
    with pytest.raises(ValueError, match="Could not identify columns"):
        normalize([{"foo": 1, "bar": 2}])
    with pytest.raises(ValueError):
        normalize([])


def test_csv_path_input(tmp_path):
    csv = tmp_path / "activity.csv"
    csv.write_text(
        "Trade Date,Activity Type,Symbol,Quantity,Price,Commission\n"
        "2024-01-15,Buy,XEQT,100,30.00,9.95\n"
        "2024-02-20,Dividend,XEQT,,,\n",
        encoding="utf-8",
    )
    result = server.normalize_broker_csv(csv_path=str(csv))
    assert result["counts"]["trades"] == 1
    assert result["counts"]["skipped"] == 1


def test_missing_input_raises():
    with pytest.raises(ValueError):
        server.normalize_broker_csv()
