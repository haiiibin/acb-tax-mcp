"""Tests for the superficial-loss (CRA 30-day / 61-day window) rule."""

from __future__ import annotations

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


def test_full_superficial_loss_deferred_into_acb():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8),
                     tx("2024-02-10", "buy", "AAA", 100, 8)])
    d = r["dispositions"][0]
    assert d["is_superficial_loss"] is True
    assert d["gain_before_superficial"] == -200.0
    assert d["superficial_loss_denied"] == 200.0
    assert d["capital_gain"] == 0.0
    # denied loss is added to the ACB of the repurchased shares
    h = r["holdings"][0]
    assert h["total_acb"] == 1000.0
    assert h["acb_per_share"] == 10.0


def test_deferred_loss_realized_on_later_sale():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8),
                     tx("2024-02-10", "buy", "AAA", 100, 8),
                     tx("2024-06-01", "sell", "AAA", 100, 12)])
    second = r["dispositions"][1]
    assert second["capital_gain"] == 200.0  # 1200 proceeds - 1000 ACB
    # the deferred loss simply shifted timing; net for the year is +200
    assert r["summary"]["by_tax_year"][0]["net_capital_gain"] == 200.0


def test_partial_superficial_loss():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8),
                     tx("2024-02-10", "buy", "AAA", 40, 8)])
    d = r["dispositions"][0]
    assert d["superficial_loss_denied"] == 80.0   # 40% of the 200 loss
    assert d["capital_gain"] == -120.0
    h = r["holdings"][0]
    assert h["shares"] == 40.0
    assert h["total_acb"] == 400.0
    assert h["acb_per_share"] == 10.0


def test_loss_with_no_rebuy_is_allowed():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8)])
    d = r["dispositions"][0]
    assert d["is_superficial_loss"] is False
    assert d["capital_gain"] == -200.0


def test_rebuy_outside_window_is_allowed():
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8),
                     tx("2024-04-01", "buy", "AAA", 100, 8)])  # > 30 days later
    assert r["dispositions"][0]["is_superficial_loss"] is False


def test_rebuy_then_sold_out_before_window_end_is_allowed():
    # Substitute shares not held at the end of the window -> not superficial.
    r = acb.compute([tx("2024-01-01", "buy", "AAA", 100, 10),
                     tx("2024-02-01", "sell", "AAA", 100, 8),
                     tx("2024-02-10", "buy", "AAA", 100, 8),
                     tx("2024-02-15", "sell", "AAA", 100, 7)])
    assert r["dispositions"][0]["is_superficial_loss"] is False


def test_rebuy_before_sale_within_window_is_superficial():
    r = acb.compute([tx("2024-01-05", "buy", "AAA", 100, 10),
                     tx("2024-01-20", "buy", "AAA", 100, 8),
                     tx("2024-02-01", "sell", "AAA", 100, 8)])
    assert r["dispositions"][0]["is_superficial_loss"] is True
