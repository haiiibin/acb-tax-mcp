"""Regression tests for real-world input traps: blank CSV cells, missing FX,
messy dates. These paths are what spreadsheet exports actually look like."""

from __future__ import annotations

import pytest

from acb_tax_mcp import acb, server
from acb_tax_mcp.models import parse_transaction


def test_blank_optional_cells_in_csv(tmp_path):
    # fx_rate/commission columns exist but are blank for CAD trades: must not crash.
    csv = tmp_path / "trades.csv"
    csv.write_text(
        "date,action,security,shares,price,commission,fx_rate,note\n"
        "2024-01-01,buy,XYZ,100,10,,,\n"
        "2024-03-01,sell,XYZ,100,15,9.99,,\n",
        encoding="utf-8",
    )
    r = server.calculate_acb(csv_path=str(csv))
    d = r["dispositions"][0]
    assert d["capital_gain"] == 490.01  # 1490.01 proceeds - 1000 ACB
    assert d["note"] == ""


def test_blank_required_cell_raises_clear_error():
    with pytest.raises(ValueError, match="'price' is required"):
        parse_transaction(
            {"date": "2024-01-01", "action": "buy", "security": "X", "shares": 10, "price": ""}
        )
    with pytest.raises(ValueError, match="'shares' is required"):
        parse_transaction(
            {"date": "2024-01-01", "action": "buy", "security": "X", "shares": None, "price": 5}
        )


def test_negative_commission_rejected():
    with pytest.raises(ValueError, match="commission"):
        parse_transaction(
            {"date": "2024-01-01", "action": "buy", "security": "X",
             "shares": 10, "price": 5, "commission": -1}
        )


def test_foreign_currency_without_fx_warns():
    txns = [
        {"date": "2024-01-01", "action": "buy", "security": "AAPL",
         "shares": 10, "price": 100, "currency": "USD"},
        {"date": "2024-03-01", "action": "sell", "security": "AAPL",
         "shares": 10, "price": 120, "currency": "USD"},
    ]
    r = acb.compute(txns)
    assert any("fx_rate is 1" in w and "AAPL" in w for w in r["warnings"])
    # only one warning per security/currency pair, not one per trade
    assert sum("fx_rate is 1" in w for w in r["warnings"]) == 1


def test_foreign_currency_with_fx_does_not_warn():
    txns = [
        {"date": "2024-01-01", "action": "buy", "security": "AAPL",
         "shares": 10, "price": 100, "currency": "USD", "fx_rate": 1.35},
    ]
    r = acb.compute(txns)
    assert not any("fx_rate" in w for w in r["warnings"])


def test_datetime_style_dates_parse():
    t = parse_transaction(
        {"date": "2024-01-01 09:30:00", "action": "buy", "security": "X",
         "shares": 1, "price": 1}
    )
    assert t.date.isoformat() == "2024-01-01"
    t2 = parse_transaction(
        {"date": "2024-01-01T09:30:00", "action": "buy", "security": "X",
         "shares": 1, "price": 1}
    )
    assert t2.date.isoformat() == "2024-01-01"


def test_json_transactions_file(tmp_path):
    import json

    f = tmp_path / "trades.json"
    f.write_text(json.dumps([
        {"date": "2024-01-01", "action": "buy", "security": "XYZ", "shares": 100, "price": 10},
        {"date": "2024-03-01", "action": "sell", "security": "XYZ", "shares": 100, "price": 15},
    ]), encoding="utf-8")
    r = server.calculate_acb(csv_path=str(f))
    assert r["dispositions"][0]["capital_gain"] == 500.0
