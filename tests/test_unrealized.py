"""Tests for the unrealized_gains tool."""

from __future__ import annotations

import json

import pytest

from acb_tax_mcp import server

TXNS = [
    {"date": "2024-01-01", "action": "buy", "security": "XEQT", "shares": 100, "price": 30},
    {"date": "2024-02-01", "action": "buy", "security": "XEQT", "shares": 100, "price": 34},
    {
        "date": "2024-03-01",
        "action": "buy",
        "security": "VTI",
        "shares": 10,
        "price": 200,
        "currency": "USD",
        "fx_rate": 1.35,
    },
]


def test_basic_unrealized_gain():
    result = server.unrealized_gains({"XEQT": 35, "VTI": {"price": 220, "fx_rate": 1.40}}, TXNS)
    by_sec = {p["security"]: p for p in result["positions"]}

    xeqt = by_sec["XEQT"]
    assert xeqt["total_acb"] == 6400.0
    assert xeqt["market_value"] == 7000.0  # 200 shares * $35
    assert xeqt["unrealized_gain"] == 600.0
    assert xeqt["unrealized_gain_pct"] == pytest.approx(9.38, abs=0.01)

    vti = by_sec["VTI"]
    assert vti["total_acb"] == 2700.0  # 10 * 200 * 1.35
    assert vti["market_value"] == 3080.0  # 10 * 220 * 1.40
    assert vti["unrealized_gain"] == 380.0

    totals = result["totals"]
    assert totals["total_acb"] == 9100.0
    assert totals["market_value"] == 10080.0
    assert totals["unrealized_gain"] == 980.0
    assert result["missing_prices"] == []
    json.dumps(result)


def test_missing_price_excluded_from_totals():
    result = server.unrealized_gains({"XEQT": 35}, TXNS)
    assert result["missing_prices"] == ["VTI"]
    assert {p["security"] for p in result["positions"]} == {"XEQT"}
    assert result["totals"]["total_acb"] == 6400.0
    assert any("VTI" in w for w in result["warnings"])


def test_price_for_unheld_security_warns():
    result = server.unrealized_gains({"XEQT": 35, "VTI": 220, "ZZZ": 1}, TXNS)
    assert any("ZZZ" in w for w in result["warnings"])


def test_case_insensitive_price_keys():
    result = server.unrealized_gains({"xeqt": 35, "vti": 220}, TXNS)
    assert {p["security"] for p in result["positions"]} == {"XEQT", "VTI"}


def test_invalid_prices_raise():
    with pytest.raises(ValueError):
        server.unrealized_gains({}, TXNS)
    with pytest.raises(ValueError):
        server.unrealized_gains({"XEQT": "not-a-number"}, TXNS)
    with pytest.raises(ValueError):
        server.unrealized_gains({"XEQT": -1}, TXNS)
    with pytest.raises(ValueError):
        server.unrealized_gains({"XEQT": {"fx_rate": 1.35}}, TXNS)
    with pytest.raises(ValueError):
        server.unrealized_gains({"XEQT": {"price": 35, "fx_rate": 0}}, TXNS)


def test_sold_out_position_not_reported():
    txns = TXNS + [
        {"date": "2024-06-01", "action": "sell", "security": "VTI", "shares": 10, "price": 210,
         "currency": "USD", "fx_rate": 1.36},
    ]
    result = server.unrealized_gains({"XEQT": 35, "VTI": 220}, txns)
    assert {p["security"] for p in result["positions"]} == {"XEQT"}
