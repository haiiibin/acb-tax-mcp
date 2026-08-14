# Security Policy

## Supported versions

Only the latest release on PyPI receives fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately
via [GitHub private vulnerability reporting](https://github.com/haiiibin/acb-tax-mcp/security/advisories/new)
or email haibiny123@gmail.com. You can expect an initial response within a few
days.

## Scope notes

This server operates on transaction data the host explicitly passes to it (or
CSV files it is pointed at) and performs no network calls at runtime. It
processes potentially sensitive financial records, so reports about data
leaking into logs or error messages are particularly welcome.
