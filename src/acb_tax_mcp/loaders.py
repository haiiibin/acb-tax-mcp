"""Load a transaction list from a CSV or JSON file.

CSV headers (case-insensitive): date, action, security, shares, price,
commission, currency, fx_rate, note. JSON is a list of transaction objects with
the same keys.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path


def resolve_path(path) -> Path:
    p = Path(os.path.expanduser(str(path))).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"No such file: {p}")
    if p.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a transactions file: {p}")
    return p.resolve()


def load_transactions_file(path) -> list[dict]:
    p = resolve_path(path)
    ext = p.suffix.lower()
    if ext == ".json":
        with p.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "transactions" in data:
            data = data["transactions"]
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of transactions.")
        return data
    if ext in (".csv", ".txt", ".tsv"):
        delimiter = "\t" if ext == ".tsv" else ","
        with p.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            rows = []
            for row in reader:
                rows.append({(k or "").strip().lower(): v for k, v in row.items()})
        return rows
    raise ValueError(
        f"Unsupported transactions file {ext!r}; use .csv, .tsv or .json."
    )
