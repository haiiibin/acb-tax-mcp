# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

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

[0.2.0]: https://github.com/haiiibin/acb-tax-mcp/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
[0.1.1]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
[0.1.0]: https://github.com/haiiibin/acb-tax-mcp/releases/tag/v0.1.2
