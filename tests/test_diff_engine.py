import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import openpyxl
from excel_diff.core.diff_engine import run_diff


def _make_xlsx(rows: list[list], headers: list[str]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    tmp.close()
    return tmp.name


def test_run_diff_basic():
    path_a = _make_xlsx([['Leite Piracanjuba 1 litro', 10], ['Farinha 5kg', 5]], ['produto', 'quantidade'])
    path_b = _make_xlsx([['Leite 1L', 8], ['Açúcar 1kg', 3]], ['produto', 'quantidade'])

    result = run_diff(path_a, path_b, threshold=75)

    assert result.file_a_name.endswith('.xlsx')
    assert result.file_b_name.endswith('.xlsx')
    # Leite Piracanjuba matches Leite 1L via token_set_ratio; Açúcar has no match
    assert len(result.matched) >= 1
    acucar_in_only_b = any('car' in str(r.get('produto', '')).lower() for r in result.only_in_b)
    assert acucar_in_only_b, f"only_in_b: {result.only_in_b}"

    os.unlink(path_a)
    os.unlink(path_b)


def test_run_diff_detects_key_column():
    path_a = _make_xlsx([['Leite', 1]], ['produto', 'qtd'])
    path_b = _make_xlsx([['Leite Integral', 1]], ['produto', 'qtd'])
    result = run_diff(path_a, path_b, threshold=70)
    assert result.key_col_a == 'produto'
    assert result.key_col_b == 'produto'
    os.unlink(path_a)
    os.unlink(path_b)
