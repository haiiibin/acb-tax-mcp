"""Tests that the MCP server registers tools with clean, usable descriptions."""

from __future__ import annotations

import json

from acb_tax_mcp import server

EXPECTED = {"calculate_acb", "acb_summary", "capital_gains_report", "check_superficial_losses"}


def _tools():
    return server.mcp._tool_manager.list_tools()


def test_all_tools_registered():
    assert EXPECTED <= {t.name for t in _tools()}


def test_descriptions_clean_and_injected():
    by_name = {t.name: t.description for t in _tools()}
    for name, desc in by_name.items():
        assert desc and desc.strip(), f"{name} has an empty description"
        assert "{tx_shape}" not in desc, f"{name} still has the unfilled placeholder"
    # the shared transaction-shape note was injected
    assert "date (YYYY-MM-DD)" in by_name["calculate_acb"]


def test_tool_calls_serializable():
    txns = [
        {"date": "2024-01-01", "action": "buy", "security": "AAA", "shares": 100, "price": 10},
        {"date": "2024-03-01", "action": "sell", "security": "AAA", "shares": 100, "price": 15},
    ]
    for fn in (server.calculate_acb, server.acb_summary, server.check_superficial_losses):
        result = fn(txns)
        assert isinstance(result, dict)
        json.dumps(result)

    report = server.capital_gains_report(2024, txns)
    assert report["tax_year"] == 2024
    assert len(report["dispositions"]) == 1
    assert report["summary"]["net_capital_gain"] == 500.0
    json.dumps(report)


def test_csv_path_input(tmp_path):
    csv = tmp_path / "trades.csv"
    csv.write_text(
        "date,action,security,shares,price\n"
        "2024-01-01,buy,AAA,100,10\n"
        "2024-03-01,sell,AAA,100,15\n",
        encoding="utf-8",
    )
    result = server.calculate_acb(csv_path=str(csv))
    assert result["dispositions"][0]["capital_gain"] == 500.0


def test_missing_input_raises():
    import pytest

    with pytest.raises(ValueError):
        server.calculate_acb()
