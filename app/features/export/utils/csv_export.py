"""CSV serialization helpers for the export feature.

Pure functions (no DB, no Google) shared by the CSV download path.
Excel + Google Sheets interop: UTF-8 with BOM, comma delimiter,
QUOTE_MINIMAL quoting, CRLF line endings.
"""

import csv
import io
import re
from typing import List


def rows_to_csv_bytes(rows: List[List[str]]) -> bytes:
    """Serialize row-matrix (as built by ``build_rows``) to CSV bytes."""
    buf = io.StringIO(newline="")
    writer = csv.writer(
        buf,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        doublequote=True,
        lineterminator="\r\n",
    )
    writer.writerows(rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def build_csv_filename(form_title: str) -> str:
    """Slugified ``<title>-responses.csv`` filename for Content-Disposition."""
    slug = re.sub(r"[^a-z0-9]+", "-", form_title.strip().lower()).strip("-")
    if not slug:
        slug = "form"
    return f"{slug[:50].strip('-') or 'form'}-responses.csv"
