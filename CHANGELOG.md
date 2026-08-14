# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-08-14

### Added

- New `schedule3_summary` tool: aggregates dispositions into one row per
  security in the Schedule 3 "publicly traded shares" column shape (number of
  shares, gross proceeds of disposition, adjusted cost base, outlays and
  expenses, gain or loss after the superficial-loss rule), with acquisition
  years, per-column totals, an optional `tax_year` filter, and the list of
  years that have dispositions.
- `CONTRIBUTING.md` (dev setup, Decimal/CRA correctness rules, dual-SDK
  testing notes), `CODE_OF_CONDUCT.md`, `SECURITY.md`, and GitHub issue
  templates for bug reports and feature requests.

### Changed

- Releases now publish to the official MCP Registry automatically on tag via
  GitHub OIDC, alongside the existing PyPI trusted publishing.

## [0.3.0] - 2026-07-28

### Added

- MCP SDK 2.x support: the server now imports `MCPServer` on SDK 2.x and falls
  back to `FastMCP` on SDK 1.x, and the dependency pin widens to
  `mcp>=1.2.0,<3`. Verified against both SDK lines.

## [0.2.1] - 2026-07-28

### Fixed

- Pin `mcp>=1.2.0,<2`. MCP Python SDK 2.0 (released 2026-07-27) removes the
  `mcp.server.fastmcp` import path (`FastMCP` became
  `mcp.server.mcpserver.MCPServer`), so fresh installs resolving `mcp==2.0.0`
  crashed on startup with `ModuleNotFoundError`. Migration to SDK v2 is
  planned separately.

## [0.2.0] - 2026-07-27

### Added

- New tool `unrealized_gains`: current holdings' ACB against market prices you
  supply, with per-position and total unrealized gain in dollars and percent.
  Foreign-quoted securities take a `{"price": ..., "fx_rate": ...}` pair; held
  securities without a price are reported in `missing_prices` and excluded from
  totals.
- New tool `normalize_broker_csv`: turns a raw broker activity export into
  transactions the other tools accept. Maps common column aliases ("Trade
  Date", "Activity Type", "Symbol", "Quantity", ...), keeps only buy/sell rows
  (reinvestment/DRIP rows count as buys), cleans `$1,200` / `(9.95)` / signed
  quantity formats, and reports every skipped row with a reason.
- Python 3.13 in the CI test matrix and package classifiers.

### Changed

- CI now runs `ruff check` as a lint job; ruff configuration pinned in
  `pyproject.toml`.

## [0.1.2] - 2026-07-21

### Added

- Published to the official [MCP Registry](https://registry.modelcontextprotocol.io)
  as `io.github.haiiibin/acb-tax-mcp` (`server.json`).
- Glama listing metadata (`glama.json`) and score badge.
- `Dockerfile` (stdio) for containerized runs.

## [0.1.1] - 2026-07-11

### Fixed

- Blank optional CSV cells (commission, fx_rate, currency, note) no longer
  crash parsing or silently coerce to zero.
- ISO datetime strings (`2024-01-01T09:30:00`) are accepted as dates, as
  produced by spreadsheet/broker exports.

### Added

- Loud warning when foreign-currency trades carry no `fx_rate`, instead of
  silently computing CAD-wrong numbers.
- GitHub Actions CI (test matrix py3.10 to py3.12).

## [0.1.0] - 2026-07-10

### Added

- Initial release: `calculate_acb`, `acb_summary`, `capital_gains_report`,
  `check_superficial_losses`.
- CRA average-cost ACB engine with superficial-loss detection (61-day window,
  least-of-three test) and per-trade CAD FX conversion.

[0.3.0]: https://github.com/haiiibin/acb-tax-mcp/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/haiiibin/acb-tax-mcp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/haiiibin/acb-tax-mcp/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
[0.1.1]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
[0.1.0]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
