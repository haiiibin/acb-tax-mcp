# Contributing

Thanks for your interest in improving acb-tax-mcp. Bug reports, feature ideas,
and pull requests are all welcome.

## Development setup

```bash
git clone https://github.com/haiiibin/acb-tax-mcp
cd acb-tax-mcp
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running checks

```bash
pytest -q          # test suite
ruff check .       # lint (config lives in pyproject.toml)
```

Both must pass before a PR can merge. CI also runs the suite on Python 3.10
through 3.13.

## Correctness rules for tax math

- All money math uses `Decimal`; never introduce floats into ACB, proceeds,
  or gain calculations. Round only at the reporting boundary.
- Behavior must follow published CRA rules (average-cost ACB, the
  30-days-before/after superficial-loss window). Cite the rule you are
  implementing in the PR description; if a rule is ambiguous, surface a
  warning in the output rather than guessing silently.
- The output is a calculation aid, not tax advice; keep that framing in docs
  and tool descriptions.

## MCP SDK compatibility

The server supports both MCP SDK 1.x (`mcp.server.fastmcp.FastMCP`) and 2.x
(`mcp.server.mcpserver.MCPServer`) through the import shim in
`src/acb_tax_mcp/server.py`. If you touch server wiring, run the tests against
both majors; CI's `test-mcp1` job pins `mcp<2` to guard the fallback path, and
the regular matrix exercises the current SDK.

## Pull request guidelines

- Keep changes focused; one concern per PR.
- Add or update tests for any behavior change, including edge cases around
  the superficial-loss window and multi-currency transactions.
- Update `CHANGELOG.md` under `[Unreleased]`.
- New tools need a docstring (it becomes the tool description shown to LLMs)
  and a row in the README tool table.

## Reporting bugs

Please use the bug-report issue template. A minimal anonymized transaction
list that reproduces the problem makes fixes much faster; never post real
account numbers, names, or full statements.
