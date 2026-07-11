"""Transaction model and parsing.

A transaction is a single buy or sell. Monetary amounts use :class:`decimal.Decimal`
so ACB and capital gains are computed to the cent without binary-float drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

VALID_ACTIONS = {"buy", "sell"}


def _to_decimal(value, name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name!r} is not a valid number: {value!r}") from exc


def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date {value!r}; use ISO format YYYY-MM-DD.")


@dataclass
class Transaction:
    """A single buy or sell, with amounts in its trade currency.

    ``fx_rate`` converts the trade currency to CAD (e.g. 1.35 for a USD trade).
    The CRA requires ACB and gains in CAD, so foreign trades must carry the
    transaction-date exchange rate.
    """

    date: date
    action: str
    security: str
    shares: Decimal
    price: Decimal
    commission: Decimal = Decimal(0)
    currency: str = "CAD"
    fx_rate: Decimal = Decimal(1)
    note: str = ""

    @property
    def cad_book_cost(self) -> Decimal:
        """Total cost added to ACB on a buy (price*shares + commission), in CAD."""
        return (self.shares * self.price + self.commission) * self.fx_rate

    @property
    def cad_proceeds(self) -> Decimal:
        """Net proceeds of a sale (price*shares - commission), in CAD."""
        return (self.shares * self.price - self.commission) * self.fx_rate

    @property
    def cad_outlays(self) -> Decimal:
        """Commission on the trade, in CAD (an outlay/expense of disposition)."""
        return self.commission * self.fx_rate


def parse_transaction(raw: dict) -> Transaction:
    """Validate and coerce one transaction dict into a :class:`Transaction`."""
    if not isinstance(raw, dict):
        raise ValueError(f"Each transaction must be an object, got {type(raw).__name__}.")

    action = str(raw.get("action", "")).strip().lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f"'action' must be 'buy' or 'sell', got {raw.get('action')!r}.")

    security = str(raw.get("security", "")).strip().upper()
    if not security:
        raise ValueError("'security' is required and cannot be empty.")

    shares = _to_decimal(raw.get("shares"), "shares")
    if shares <= 0:
        raise ValueError(f"'shares' must be positive, got {shares}.")

    price = _to_decimal(raw.get("price"), "price")
    if price < 0:
        raise ValueError(f"'price' cannot be negative, got {price}.")

    commission = _to_decimal(raw.get("commission", 0), "commission")
    fx_rate = _to_decimal(raw.get("fx_rate", 1), "fx_rate")
    if fx_rate <= 0:
        raise ValueError(f"'fx_rate' must be positive, got {fx_rate}.")

    currency = str(raw.get("currency", "CAD")).strip().upper() or "CAD"

    return Transaction(
        date=_to_date(raw.get("date")),
        action=action,
        security=security,
        shares=shares,
        price=price,
        commission=commission,
        currency=currency,
        fx_rate=fx_rate,
        note=str(raw.get("note", "")),
    )


def parse_transactions(items) -> list[Transaction]:
    if not isinstance(items, (list, tuple)):
        raise ValueError("Transactions must be a list of transaction objects.")
    out = []
    for i, raw in enumerate(items):
        try:
            out.append(parse_transaction(raw))
        except ValueError as exc:
            raise ValueError(f"Transaction #{i + 1}: {exc}") from exc
    return out
