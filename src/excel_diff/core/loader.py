from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path

import openpyxl

PREFERRED_KEY_COLS = [
    'produto', 'descricao', 'descricção', 'descrição', 'item',
    'nome', 'ingrediente', 'material', 'insumo',
]

_CSV_ENCODINGS = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
_CSV_DELIMITERS = [';', ',', '\t', '|']


def _normalize_header(h: str) -> str:
    text = str(h).lower().strip()
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def detect_key_column(headers: list[str]) -> str:
    norm = {_normalize_header(h): h for h in headers}
    for candidate in PREFERRED_KEY_COLS:
        if candidate in norm:
            return norm[candidate]
    return headers[0] if headers else ''


# ── XLSX ─────────────────────────────────────────────────────────────────────

def _find_header_row(rows: list[tuple]) -> int:
    """Return the index of the first row that looks like a header (mostly non-empty strings)."""
    for i, row in enumerate(rows):
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) >= max(2, len(row) * 0.5):
            return i
    return 0


def _load_xlsx(path: str | Path, sheet_index: int = 0) -> tuple[list[str], list[dict]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[sheet_index]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return [], []

    header_idx = _find_header_row(rows)
    raw_headers = rows[header_idx]
    headers = [str(h).strip() if h is not None else f'Coluna_{i+1}'
               for i, h in enumerate(raw_headers)]

    data: list[dict] = []
    for row in rows[header_idx + 1:]:
        if all(v is None or str(v).strip() == '' for v in row):
            continue
        record = {header: (value if value is not None else '')
                  for header, value in zip(headers, row)}
        data.append(record)

    return headers, data


# ── CSV ───────────────────────────────────────────────────────────────────────

def _detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter using first non-empty line."""
    first_line = next((l for l in sample.splitlines() if l.strip()), '')
    for delim in _CSV_DELIMITERS:
        try:
            dialect = csv.Sniffer().sniff(first_line, delimiters=delim)
            if dialect.delimiter == delim:
                return delim
        except csv.Error:
            pass
    # fallback: count occurrences in first line
    return max(_CSV_DELIMITERS, key=lambda d: first_line.count(d))


def _strip_field_quotes(value: str) -> str:
    """Strip the doubled-outer-quote wrapping: '""VALUE""' → 'VALUE'."""
    v = value.strip()
    # Strip leading and trailing " characters
    v = v.strip('"')
    # Unescape doubled inner quotes
    v = v.replace('""', '"')
    return v


def _needs_quote_stripping(rows_sample: list[list[str]]) -> bool:
    """Return True if data rows use the ""VALUE"" double-quote wrapping format."""
    for row in rows_sample:
        if not row:
            continue
        quoted = sum(
            1 for cell in row
            if cell.startswith('"') or cell.endswith('"') or cell.startswith('""')
        )
        if quoted >= max(1, len(row) * 0.5):
            return True
    return False


def _load_csv(path: str | Path) -> tuple[list[str], list[dict]]:
    raw: str | None = None
    for enc in _CSV_ENCODINGS:
        try:
            raw = Path(path).read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if raw is None:
        raise ValueError(f'Não foi possível decodificar o arquivo CSV: {path}')

    delimiter = _detect_delimiter(raw)

    # First pass: read WITHOUT quoting to detect format
    reader_raw = csv.reader(io.StringIO(raw), delimiter=delimiter, quotechar='\x00')
    raw_rows = [row for row in reader_raw if any(c.strip() for c in row)]

    if not raw_rows:
        return [], []

    headers_raw = raw_rows[0]
    sample_data = raw_rows[1:6]
    needs_strip = _needs_quote_stripping(sample_data)

    def clean(v: str) -> str:
        v = v.strip()
        if needs_strip:
            return _strip_field_quotes(v)
        return v

    headers = [clean(h) or f'Coluna_{i+1}' for i, h in enumerate(headers_raw)]

    data: list[dict] = []
    for row in raw_rows[1:]:
        record = {headers[i]: clean(row[i]) if i < len(row) else ''
                  for i in range(len(headers))}
        if all(not v for v in record.values()):
            continue
        data.append(record)

    return headers, data


# ── Public API ────────────────────────────────────────────────────────────────

def load_file(path: str | Path, sheet_index: int = 0) -> tuple[list[str], list[dict]]:
    if Path(path).suffix.lower() == '.csv':
        return _load_csv(path)
    return _load_xlsx(path, sheet_index)
