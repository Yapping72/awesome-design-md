"""Turns a list of row-dicts into a CSV string body for a download response."""

import csv
import io
from typing import Any


def rows_to_csv(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
