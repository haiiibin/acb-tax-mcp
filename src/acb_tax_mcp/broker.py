"""Normalize a raw broker-activity export into the transaction shape.

Broker CSVs rarely match the documented ``date/action/security/...`` headers:
columns are named differently per broker ("Trade Date", "Activity Type",
"Symbol", "Quantity"...) and trade rows are mixed in with dividends, deposits
and fees. This module maps common header aliases, keeps only buy/sell rows
(reinvested distributions count as buys, since DRIP shares add to ACB), and
returns transactions ready for :func:`acb_tax_mcp.acb.compute`, plus a per-row
account of everything it skipped so nothing disappears silently.
"""

from __future__ import annotations

from acb_tax_mcp.models import parse_transaction

# Header aliases per canonical field, checked in order: the first alias present
# in the export wins (e.g. "trade date" is preferred over "settlement date").
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "trade date", "transaction date", "activity date", "settlement date"),
    "action": ("action", "activity", "activity type", "transaction type", "type", "side", "buy/sell"),
    "security": ("security", "symbol", "ticker", "stock", "instrument"),
    "shares": ("shares", "quantity", "qty", "units", "number of shares", "no. of shares"),
    "price": ("price", "price per share", "unit price", "average price", "avg price", "execution price"),
    "commission": ("commission", "commissions", "commission & fees", "fees", "fee"),
    "currency": ("currency", "ccy", "currency code"),
    "fx_rate": ("fx_rate", "fx rate", "exchange rate", "fx"),
    "note": ("note", "description", "memo", "details"),
}

_REQUIRED = ("date", "action", "security", "shares", "price")
_BUY_WORDS = ("buy", "bought", "purchase", "reinvest", "drip")
_SELL_WORDS = ("sell", "sold")


def _clean_number(value):
    """Strip broker number formatting: thousands commas, $, (123.45) negatives."""
    if not isinstance(value, str):
        return value
    v = value.strip().replace(",", "").replace("$", "")
    if v.startswith("(") and v.endswith(")"):
        v = "-" + v[1:-1]
    return v


def _magnitude(value):
    """Drop the sign: exports often use signed quantities/commissions, but the
    action column already carries the direction."""
    v = _clean_number(value)
    if isinstance(v, str):
        return v.lstrip("-")
    if isinstance(v, (int, float)):
        return abs(v)
    return v


def _map_columns(headers: set[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in headers:
                mapping[field] = alias
                break
    return mapping


def _classify_action(raw: str) -> str | None:
    text = raw.strip().lower()
    if any(w in text for w in _SELL_WORDS):
        return "sell"
    if any(w in text for w in _BUY_WORDS):
        return "buy"
    return None


def normalize(rows) -> dict:
    """Map broker rows to clean transactions; report every skipped row."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("Expected a non-empty list of row objects from the broker export.")

    norm_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Each row must be an object, got {type(row).__name__}.")
        norm_rows.append({str(k or "").strip().lower(): v for k, v in row.items()})

    headers: set[str] = set()
    for row in norm_rows:
        headers.update(row.keys())
    mapping = _map_columns(headers)

    missing = [f for f in _REQUIRED if f not in mapping]
    if missing:
        raise ValueError(
            f"Could not identify columns for: {', '.join(missing)}. "
            f"Headers found: {sorted(h for h in headers if h)}. "
            "Rename the columns or pass transactions in the documented shape directly."
        )

    transactions: list[dict] = []
    skipped: list[dict] = []
    drip_rows = 0

    for i, row in enumerate(norm_rows, start=1):
        action_raw = str(row.get(mapping["action"]) or "").strip()
        action = _classify_action(action_raw)
        if action is None:
            skipped.append(
                {
                    "row": i,
                    "reason": f"not a buy/sell trade (action was {action_raw!r})",
                    "security": str(row.get(mapping["security"]) or "").strip() or None,
                }
            )
            continue
        if action == "buy" and any(w in action_raw.lower() for w in ("reinvest", "drip")):
            drip_rows += 1

        candidate = {
            "date": row.get(mapping["date"]),
            "action": action,
            "security": row.get(mapping["security"]),
            "shares": _magnitude(row.get(mapping["shares"])),
            "price": _clean_number(row.get(mapping["price"])),
        }
        if "commission" in mapping:
            candidate["commission"] = _magnitude(row.get(mapping["commission"]))
        if "currency" in mapping:
            candidate["currency"] = row.get(mapping["currency"])
        if "fx_rate" in mapping:
            candidate["fx_rate"] = _clean_number(row.get(mapping["fx_rate"]))
        if "note" in mapping:
            candidate["note"] = row.get(mapping["note"])

        try:
            t = parse_transaction(candidate)
        except ValueError as exc:
            skipped.append(
                {
                    "row": i,
                    "reason": str(exc),
                    "security": str(row.get(mapping["security"]) or "").strip() or None,
                }
            )
            continue

        transactions.append(
            {
                "date": t.date.isoformat(),
                "action": t.action,
                "security": t.security,
                "shares": float(t.shares),
                "price": float(t.price),
                "commission": float(t.commission),
                "currency": t.currency,
                "fx_rate": float(t.fx_rate),
                "note": t.note,
            }
        )

    warnings: list[str] = []
    if drip_rows:
        warnings.append(
            f"{drip_rows} reinvestment/DRIP row(s) were treated as buys; "
            "reinvested distributions add to ACB at the reinvestment price."
        )
    non_cad = {t["currency"] for t in transactions if t["currency"] != "CAD" and t["fx_rate"] == 1.0}
    if non_cad:
        warnings.append(
            f"Trades in {', '.join(sorted(non_cad))} have no fx_rate; supply the "
            "transaction-date CAD exchange rate before computing ACB or the numbers will be wrong."
        )

    return {
        "transactions": transactions,
        "skipped": skipped,
        "column_mapping": mapping,
        "counts": {
            "rows": len(norm_rows),
            "trades": len(transactions),
            "skipped": len(skipped),
        },
        "warnings": warnings,
    }
