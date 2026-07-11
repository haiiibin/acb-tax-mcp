"""Known-answer tests for the average-cost ACB and capital-gains engine."""

from __future__ import annotations

import json

from acb_tax_mcp import acb


def tx(date, action, security, shares, price, commission=0, fx_rate=1):
    return {
        "date": date,
        "action": action,
        "security": security,
        "shares": shares,
        "price": price,
        "commission": commission,
        "fx_rate": fx_rate,
    }


def test_simple_gain():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-03-01", "sell", "AAA", 100, 15)])
    assert r["dispositions"][0]["capital_gain"] == 500.0
    assert r["holdings"] == []
    json.dumps(r)


def test_average_cost():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "buy", "AAA", 100, 20),
                     tx("2024-03-01", "sell", "AAA", 100, 25)])
    d = r["dispositions"][0]
    assert d["acb"] == 1500.0
    assert d["capital_gain"] == 1000.0
    h = r["holdings"][0]
    assert (h["security"], h["shares"], h["total_acb"], h["acb_per_share"]) == ("AAA", 100.0, 1500.0, 15.0)


def test_commission_in_and_out():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10, commission=10),
                     tx("2024-03-01", "sell", "AAA", 100, 15, commission=5)])
    d = r["dispositions"][0]
    assert d["acb"] == 1010.0
    assert d["proceeds"] == 1495.0
    assert d["outlays"] == 5.0
    assert d["capital_gain"] == 485.0


def test_fx_conversion_to_cad():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10, fx_rate=1.35),
                     tx("2024-03-01", "sell", "AAA", 100, 12, fx_rate=1.40)])
    d = r["dispositions"][0]
    assert d["acb"] == 1350.0
    assert d["proceeds"] == 1680.0
    assert d["capital_gain"] == 330.0


def test_multiple_securities_pooled_separately():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 10, 100),
                     tx("2024-01-01", "buy", "BBB", 10, 50),
                     tx("2024-06-01", "sell", "AAA", 10, 120)])
    secs = {h["security"] for h in r["holdings"]}
    assert secs == {"BBB"}
    assert r["dispositions"][0]["capital_gain"] == 200.0


def test_oversell_is_flagged_and_clamped():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 50, 10),
                     tx("2024-03-01", "sell", "AAA", 100, 12)])
    assert r["warnings"]
    d = r["dispositions"][0]
    assert d["shares_sold"] == 50.0
    assert d["proceeds"] == 600.0
    assert d["capital_gain"] == 100.0
    assert r["holdings"] == []


def test_year_summary_and_taxable_gain():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-03-01", "sell", "AAA", 100, 15)])
    y = r["summary"]["by_tax_year"][0]
    assert y["tax_year"] == 2024
    assert y["net_capital_gain"] == 500.0
    assert y["taxable_capital_gain"] == 250.0
    assert r["summary"]["inclusion_rate"] == 0.5


def test_transactions_sorted_by_date():
    # Provided out of order; engine should sort chronologically.
    r = acb.compute([tx("2024-03-01", "sell", "AAA", 100, 15),
                     tx("2024-01-01", "buy", "AAA", 100, 10)])
    assert r["dispositions"][0]["capital_gain"] == 500.0
