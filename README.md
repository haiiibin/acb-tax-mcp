# acb-tax-mcp

[![CI](https://github.com/haiiibin/acb-tax-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/haiiibin/acb-tax-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/acb-tax-mcp)](https://pypi.org/project/acb-tax-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/acb-tax-mcp)](https://pypi.org/project/acb-tax-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> An [MCP](https://modelcontextprotocol.io) server that computes Canadian **adjusted cost base (ACB)** and **capital gains** from your trade history: average-cost tracking, per-disposition gains, and **superficial-loss** detection, returned as structured JSON.

Ask your assistant *"what are my capital gains for 2024?"* or *"did I trigger any superficial losses?"* and it runs the CRA rules over your transactions instead of you wrestling a spreadsheet.

> ⚠️ **This is a calculation aid, not tax advice.** Verify every number before you file, and consult a professional for anything non-trivial. See [Limitations](#limitations).

Works with **Claude Desktop**, **Claude Code**, **Cursor**, or any MCP-compatible client.

---

## Features

| Tool | What it does |
|---|---|
| `calculate_acb` | Full calculation: current holdings (shares, total ACB, ACB per share), every disposition with proceeds/ACB/outlays/gain, per-year summaries, and warnings. |
| `acb_summary` | Just current holdings and their book cost (handy for unrealized gains against a market price). |
| `capital_gains_report` | A Schedule-3-style report for one tax year: each disposition plus totals, net capital gain, and taxable gain (50% inclusion). |
| `check_superficial_losses` | Flags losses caught by the 30-day rule, with the denied (deferred) amount per event. |

Implements the CRA **average-cost method** (all shares of a security pool into one ACB; gains are against the average, not FIFO) and the **superficial-loss rule** (loss denied and deferred into the ACB of substitute shares bought within 30 days before or after the sale). Commissions and per-trade **CAD FX conversion** are handled.

---

## Install

Requires Python 3.10+.

```bash
uv tool install acb-tax-mcp      # or:  pip install acb-tax-mcp
```

Run from source without installing:

```bash
git clone https://github.com/haiiibin/acb-tax-mcp
cd acb-tax-mcp
uv run acb-tax-mcp
```

## Configure your client

### Claude Desktop

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "acb-tax": {
      "command": "acb-tax-mcp"
    }
  }
}
```

### Claude Code

```bash
claude mcp add acb-tax -- acb-tax-mcp
```

---

## Transactions

Give the tools a list of transactions (or a path to a `.csv` / `.json` file).

| Field | Required | Notes |
|---|---|---|
| `date` | yes | `YYYY-MM-DD` |
| `action` | yes | `buy` or `sell` |
| `security` | yes | ticker / symbol (pooled by this key) |
| `shares` | yes | positive number |
| `price` | yes | price per share, in the trade currency |
| `commission` | no | trade commission (default 0) |
| `currency` | no | e.g. `USD` (default `CAD`) |
| `fx_rate` | no | trade currency to CAD, e.g. `1.35` for USD (default 1) |
| `note` | no | free text |

CSV uses the same column names as a header row.

---

## Usage

- *"Calculate the ACB and capital gains for the trades in `~/trades.csv`."*
- *"What's my capital-gains report for 2024?"*
- *"Did any of these sales trigger a superficial loss?"*
- *"What's my current book cost for XEQT?"*

### Example

```jsonc
// calculate_acb with:
// buy 100 XYZ @ $10, buy 100 XYZ @ $20, sell 100 XYZ @ $25
{
  "holdings": [
    { "security": "XYZ", "shares": 100.0, "total_acb": 1500.0, "acb_per_share": 15.0 }
  ],
  "dispositions": [
    { "date": "2024-03-01", "security": "XYZ", "shares_sold": 100.0,
      "proceeds": 2500.0, "acb": 1500.0, "capital_gain": 1000.0,
      "is_superficial_loss": false }
  ],
  "summary": {
    "by_tax_year": [
      { "tax_year": 2024, "net_capital_gain": 1000.0, "taxable_capital_gain": 500.0 }
    ],
    "inclusion_rate": 0.5
  }
}
```

### Superficial loss example

Buy 100 @ $10, sell 100 @ $8 (a $200 loss), then rebuy 100 @ $8 nine days later:

```jsonc
{ "gain_before_superficial": -200.0, "superficial_loss_denied": 200.0,
  "capital_gain": 0.0, "is_superficial_loss": true }
```

The $200 loss is denied and added to the ACB of the repurchased shares (new ACB per share becomes $10), so it is recovered on a future sale.

---

## Limitations

Read these before relying on the output.

- **Average-cost, per identical property.** Feed *all* trades of the same security across your accounts together, since the CRA rule pools identical property at the taxpayer level. The tool pools by the `security` key you provide.
- **Superficial losses** use the standard least-of-three test with a single forward pass. Deeply chained or overlapping superficial losses can need case-by-case professional judgment.
- **Not yet handled:** return of capital, reinvested/notional distributions (ETF phantom distributions), stock splits, options, and other corporate actions. These affect ACB and are on the roadmap.
- **FX** must be supplied per transaction (use the transaction-date rate). The tool does not fetch exchange rates.
- Registered accounts (TFSA/RRSP) do not have capital gains; this tool is for **non-registered (taxable)** accounts.
- **Not tax advice.**

---

## Development

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
```

## License

MIT. See [LICENSE](LICENSE).
