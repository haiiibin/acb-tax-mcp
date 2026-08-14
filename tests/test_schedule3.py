"""Tests for the schedule3 per-security aggregation."""

from __future__ import annotations

import pytest

from acb_tax_mcp import acb

TXNS = [
    # XEQT: bought twice (2023, 2024), sold once in 2024 with commission
    {"date": "2023-03-01", "action": "buy", "security": "XEQT", "shares": 100, "price": 25.00, "commission": 9.95},
    {"date": "2024-02-01", "action": "buy", "security": "XEQT", "shares": 100, "price": 30.00, "commission": 9.95},
    {"date": "2024-06-01", "action": "sell", "security": "XEQT", "shares": 50, "price": 32.00, "commission": 9.95},
    # VFV: sold across two years
    {"date": "2023-01-15", "action": "buy", "security": "VFV", "shares": 40, "price": 100.00},
    {"date": "2023-11-01", "action": "sell", "security": "VFV", "shares": 10, "price": 110.00},
    {"date": "2024-03-01", "action": "sell", "security": "VFV", "shares": 10, "price": 120.00},
]


def test_rows_aggregate_per_security_for_the_year():
    result = acb.schedule3(TXNS, tax_year=2024)
    assert [r["security"] for r in result["rows"]] == ["VFV", "XEQT"]

    xeqt = next(r for r in result["rows"] if r["security"] == "XEQT")
    # Gross proceeds: 50 * 32.00 = 1600.00 (commission NOT deducted here)
    assert xeqt["proceeds_of_disposition"] == pytest.approx(1600.00)
    assert xeqt["outlays_and_expenses"] == pytest.approx(9.95)
    # ACB pool: (100*25 + 9.95) + (100*30 + 9.95) = 5519.90 over 200 shares
    assert xeqt["adjusted_cost_base"] == pytest.approx(5519.90 / 200 * 50, abs=0.01)
    # Gain = gross - acb - outlays
    expected_gain = 1600.00 - (5519.90 / 200 * 50) - 9.95
    assert xeqt["gain_or_loss"] == pytest.approx(expected_gain, abs=0.01)
    assert xeqt["number_of_shares"] == pytest.approx(50)
    assert xeqt["acquisition_years"] == [2023, 2024]


def test_year_filter_and_available_years():
    result = acb.schedule3(TXNS, tax_year=2023)
    assert result["available_years"] == [2023, 2024]
    assert [r["security"] for r in result["rows"]] == ["VFV"]
    vfv = result["rows"][0]
    assert vfv["proceeds_of_disposition"] == pytest.approx(1100.00)

    empty = acb.schedule3(TXNS, tax_year=2020)
    assert empty["rows"] == []


def test_totals_equal_sum_of_rows():
    result = acb.schedule3(TXNS)  # all years
    for key in (
        "proceeds_of_disposition",
        "adjusted_cost_base",
        "outlays_and_expenses",
        "gain_or_loss",
    ):
        assert result["totals"][key] == pytest.approx(sum(r[key] for r in result["rows"]), abs=0.01)


def test_gain_matches_capital_gains_math():
    """Row gains must equal the sum of per-disposition capital gains."""
    full = acb.compute(acb.parse_transactions(TXNS))
    by_security: dict[str, float] = {}
    for d in full["dispositions"]:
        by_security[d["security"]] = by_security.get(d["security"], 0.0) + d["capital_gain"]

    result = acb.schedule3(TXNS)
    for row in result["rows"]:
        assert row["gain_or_loss"] == pytest.approx(by_security[row["security"]], abs=0.01)


def test_superficial_loss_flows_into_rows():
    txns = [
        {"date": "2024-01-02", "action": "buy", "security": "TSLA", "shares": 10, "price": 100.00},
        {"date": "2024-06-01", "action": "sell", "security": "TSLA", "shares": 10, "price": 50.00},
        # Repurchase within 30 days => the loss is superficial
        {"date": "2024-06-15", "action": "buy", "security": "TSLA", "shares": 10, "price": 55.00},
    ]
    result = acb.schedule3(txns, tax_year=2024)
    row = result["rows"][0]
    assert row["superficial_loss_denied"] == pytest.approx(500.00)
    assert row["gain_or_loss"] == pytest.approx(0.00)
