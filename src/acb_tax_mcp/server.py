"""MCP server exposing the ACB / capital-gains tools.

Tool docstrings are plain triple-quoted strings (never f-strings) so ``__doc__``
is set and FastMCP can read them as the descriptions the LLM sees. The shared
transaction-shape note is injected into each docstring *before* the tool is
registered, because FastMCP captures ``__doc__`` at registration time.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from acb_tax_mcp import acb, loaders

mcp = FastMCP("acb-tax")

_TX_SHAPE = (
    "Each transaction is an object: date (YYYY-MM-DD), action ('buy' or 'sell'), "
    "security (ticker/symbol), shares, price (per share), and optionally commission, "
    "currency, fx_rate (trade-currency to CAD, e.g. 1.35 for USD), and note."
)


def _resolve(transactions, csv_path) -> list[dict]:
    if csv_path:
        return loaders.load_transactions_file(csv_path)
    if transactions is None:
        raise ValueError(
            "Provide either 'transactions' (a list of transaction objects) or 'csv_path'."
        )
    if not isinstance(transactions, list):
        raise ValueError("'transactions' must be a list of transaction objects.")
    return transactions


def calculate_acb(transactions: list[dict[str, Any]] | None = None, csv_path: str | None = None) -> dict:
    """Compute adjusted cost base and capital gains for a set of trades (Canadian rules).

    Runs the full calculation and returns: current holdings (shares, total ACB,
    ACB per share) per security; every disposition with proceeds, ACB, outlays,
    the gain before and after the superficial-loss rule, and whether it was a
    superficial loss; per-tax-year summaries with net and taxable capital gain;
    and any warnings.

    Uses the CRA average-cost method (all shares of a security pool into one ACB;
    gains are computed against the average, not FIFO). Pass trades either inline
    as 'transactions' or as a file path in 'csv_path' (CSV or JSON). {tx_shape}

    This is a calculation aid, not tax advice; verify results before filing.
    """
    return acb.compute(_resolve(transactions, csv_path))


def acb_summary(transactions: list[dict[str, Any]] | None = None, csv_path: str | None = None) -> dict:
    """Show current holdings: shares, total ACB and ACB per share for each security.

    A lighter view than calculate_acb when you only want the current book cost of
    what is still held (for example to compute an unrealized gain against a market
    price). Accepts inline 'transactions' or a 'csv_path'. {tx_shape}
    """
    result = acb.compute(_resolve(transactions, csv_path))
    return {"holdings": result["holdings"], "warnings": result["warnings"]}


def capital_gains_report(
    tax_year: int,
    transactions: list[dict[str, Any]] | None = None,
    csv_path: str | None = None,
) -> dict:
    """Produce a capital-gains report for a single tax year (Schedule 3 style).

    Returns every disposition dated in 'tax_year' with proceeds, ACB, outlays and
    the allowable capital gain/loss, plus totals: total proceeds, total ACB, net
    capital gain, and the taxable capital gain (net gain times the 50% inclusion
    rate). Superficial losses are already applied. Accepts inline 'transactions'
    or a 'csv_path'. {tx_shape}

    This is a calculation aid, not tax advice; verify results before filing.
    """
    result = acb.compute(_resolve(transactions, csv_path))
    rows = [d for d in result["dispositions"] if d["date"][:4] == str(tax_year)]
    year_summary = next(
        (y for y in result["summary"]["by_tax_year"] if y["tax_year"] == tax_year), None
    )
    return {
        "tax_year": tax_year,
        "dispositions": rows,
        "summary": year_summary,
        "inclusion_rate": result["summary"]["inclusion_rate"],
        "warnings": result["warnings"],
    }


def check_superficial_losses(
    transactions: list[dict[str, Any]] | None = None, csv_path: str | None = None
) -> dict:
    """Flag superficial losses under the CRA 30-day (61-day window) rule.

    Scans dispositions for losses where the same security was bought within 30
    days before or after the sale and still held at the end of that window. For
    each, reports the security, date, the denied (deferred) loss amount and the
    allowable portion. The denied amount is added to the ACB of the substitute
    shares. Accepts inline 'transactions' or a 'csv_path'. {tx_shape}
    """
    result = acb.compute(_resolve(transactions, csv_path))
    flagged = [d for d in result["dispositions"] if d["is_superficial_loss"]]
    total_denied = round(sum(d["superficial_loss_denied"] for d in flagged), 2)
    return {
        "superficial_loss_count": len(flagged),
        "total_denied_loss": total_denied,
        "events": flagged,
        "warnings": result["warnings"],
    }


# Patch the shared note into each docstring, THEN register (FastMCP reads
# __doc__ at registration time).
for _fn in (calculate_acb, acb_summary, capital_gains_report, check_superficial_losses):
    if _fn.__doc__ and "{tx_shape}" in _fn.__doc__:
        _fn.__doc__ = _fn.__doc__.replace("{tx_shape}", _TX_SHAPE)
    mcp.tool()(_fn)


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
