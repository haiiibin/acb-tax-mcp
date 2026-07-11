"""Adjusted cost base (ACB) and capital-gains engine (Canadian rules).

Implements the CRA average-cost method: all shares of a security held in an
account share one pooled ACB, and a disposition realizes a gain/loss against the
*average* cost per share (not FIFO or specific-lot). Also detects superficial
losses under the 61-day (30 before / 30 after) rule and defers the denied loss
into the ACB of the substitute shares.

Every public function returns JSON-safe primitives (floats rounded to cents,
ISO date strings).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from acb_tax_mcp.models import Transaction, parse_transactions

# CRA superficial-loss window: 30 calendar days before and after the disposition.
WINDOW_DAYS = 30
# Capital gains inclusion rate (portion of a net gain that is taxable).
INCLUSION_RATE = Decimal("0.5")

_CENT = Decimal("0.01")
_QTY = Decimal("0.000001")


def _money(d: Decimal) -> float:
    return float(Decimal(d).quantize(_CENT, rounding=ROUND_HALF_UP))


def _qty(d: Decimal) -> float:
    return float(Decimal(d).quantize(_QTY, rounding=ROUND_HALF_UP))


def _sorted(txns: list[Transaction]) -> list[Transaction]:
    # Stable sort by date; ties keep input order (secondary key = original index).
    return [t for _, t in sorted(enumerate(txns), key=lambda p: (p[1].date, p[0]))]


def _shares_held_through(txns: list[Transaction], security: str, cutoff: date) -> Decimal:
    """Net shares of ``security`` held after all transactions dated <= cutoff."""
    held = Decimal(0)
    for t in txns:
        if t.security != security or t.date > cutoff:
            continue
        held += t.shares if t.action == "buy" else -t.shares
    return held


def _shares_acquired_in_window(
    txns: list[Transaction], security: str, start: date, end: date
) -> Decimal:
    """Shares of ``security`` bought within [start, end] (substitute property)."""
    total = Decimal(0)
    for t in txns:
        if t.security == security and t.action == "buy" and start <= t.date <= end:
            total += t.shares
    return total


def _superficial_fraction(
    txns: list[Transaction], sale: Transaction, shares_sold: Decimal
) -> Decimal:
    """Fraction of a loss that is superficial, per the CRA least-of-three test.

    fraction = min(shares sold, shares acquired in the 61-day window, shares still
    held at the end of the window) / shares sold.
    """
    start = sale.date - timedelta(days=WINDOW_DAYS)
    end = sale.date + timedelta(days=WINDOW_DAYS)
    acquired = _shares_acquired_in_window(txns, sale.security, start, end)
    held_at_end = _shares_held_through(txns, sale.security, end)
    if acquired <= 0 or held_at_end <= 0 or shares_sold <= 0:
        return Decimal(0)
    least = min(shares_sold, acquired, held_at_end)
    frac = least / shares_sold
    return min(frac, Decimal(1))


def compute(transactions) -> dict:
    """Run the full ACB / capital-gains calculation.

    Accepts a list of transaction dicts (or :class:`Transaction` objects) and
    returns holdings, per-disposition details, per-year summaries and warnings.
    """
    if transactions and isinstance(transactions[0], Transaction):
        txns = list(transactions)
    else:
        txns = parse_transactions(transactions)
    txns = _sorted(txns)

    state: dict[str, dict[str, Decimal]] = {}
    dispositions: list[dict] = []
    warnings: list[str] = []

    # Foreign-currency trades without an FX rate silently produce CAD-wrong
    # numbers; that is the worst failure mode for a tax tool, so warn loudly.
    flagged_fx: set[tuple[str, str]] = set()
    for t in txns:
        if t.currency != "CAD" and t.fx_rate == 1 and (t.security, t.currency) not in flagged_fx:
            flagged_fx.add((t.security, t.currency))
            warnings.append(
                f"{t.security}: trades are in {t.currency} but fx_rate is 1; amounts are "
                f"being treated as CAD. Supply the transaction-date CAD exchange rate "
                f"per trade or the ACB and gains will be wrong."
            )

    for t in txns:
        st = state.setdefault(t.security, {"shares": Decimal(0), "acb": Decimal(0)})

        if t.action == "buy":
            st["acb"] += t.cad_book_cost
            st["shares"] += t.shares
            continue

        # sell
        if t.shares > st["shares"]:
            warnings.append(
                f"{t.date.isoformat()} {t.security}: sold {t.shares} shares but only "
                f"{st['shares']} were held; treating the sale as disposing of all held shares."
            )
            shares_sold = st["shares"]
        else:
            shares_sold = t.shares

        if st["shares"] <= 0:
            warnings.append(
                f"{t.date.isoformat()} {t.security}: sale with no shares held; skipped."
            )
            continue

        acb_per_share = st["acb"] / st["shares"]
        acb_of_sold = acb_per_share * shares_sold
        # Scale proceeds/outlays if we clamped an oversell.
        scale = shares_sold / t.shares
        proceeds = t.cad_proceeds * scale
        outlays = t.cad_outlays * scale
        raw_gain = proceeds - acb_of_sold

        denied = Decimal(0)
        if raw_gain < 0:
            frac = _superficial_fraction(txns, t, shares_sold)
            denied = (-raw_gain) * frac  # positive magnitude of the deferred loss

        # Remove sold shares from the pool.
        st["acb"] -= acb_of_sold
        st["shares"] -= shares_sold
        # A superficial loss is denied and added to the ACB of the substitute shares.
        if denied > 0:
            st["acb"] += denied

        allowable_gain = raw_gain + denied  # loss moved toward zero by the denied part
        dispositions.append(
            {
                "date": t.date.isoformat(),
                "security": t.security,
                "shares_sold": _qty(shares_sold),
                "proceeds": _money(proceeds),
                "acb": _money(acb_of_sold),
                "outlays": _money(outlays),
                "gain_before_superficial": _money(raw_gain),
                "superficial_loss_denied": _money(denied),
                "capital_gain": _money(allowable_gain),
                "is_superficial_loss": denied > 0,
                "note": t.note,
            }
        )

    holdings = []
    for security, st in sorted(state.items()):
        if st["shares"] <= 0:
            continue
        acb = st["acb"]
        shares = st["shares"]
        holdings.append(
            {
                "security": security,
                "shares": _qty(shares),
                "total_acb": _money(acb),
                "acb_per_share": _money(acb / shares) if shares else 0.0,
            }
        )

    summary = _summarize(dispositions)
    return {
        "holdings": holdings,
        "dispositions": dispositions,
        "summary": summary,
        "warnings": warnings,
    }


def _summarize(dispositions: list[dict]) -> dict:
    by_year: dict[int, dict] = {}
    for d in dispositions:
        year = int(d["date"][:4])
        acc = by_year.setdefault(
            year,
            {
                "tax_year": year,
                "dispositions": 0,
                "proceeds": Decimal(0),
                "acb": Decimal(0),
                "outlays": Decimal(0),
                "capital_gain": Decimal(0),
                "superficial_loss_denied": Decimal(0),
            },
        )
        acc["dispositions"] += 1
        acc["proceeds"] += Decimal(str(d["proceeds"]))
        acc["acb"] += Decimal(str(d["acb"]))
        acc["outlays"] += Decimal(str(d["outlays"]))
        acc["capital_gain"] += Decimal(str(d["capital_gain"]))
        acc["superficial_loss_denied"] += Decimal(str(d["superficial_loss_denied"]))

    years = []
    for year in sorted(by_year):
        acc = by_year[year]
        net = acc["capital_gain"]
        years.append(
            {
                "tax_year": year,
                "dispositions": acc["dispositions"],
                "total_proceeds": _money(acc["proceeds"]),
                "total_acb": _money(acc["acb"]),
                "total_outlays": _money(acc["outlays"]),
                "net_capital_gain": _money(net),
                "taxable_capital_gain": _money(net * INCLUSION_RATE) if net > 0 else 0.0,
                "superficial_loss_denied": _money(acc["superficial_loss_denied"]),
            }
        )
    return {"by_tax_year": years, "inclusion_rate": float(INCLUSION_RATE)}
