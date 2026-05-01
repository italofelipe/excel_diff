import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from excel_diff.core.loader import load_file, detect_key_column


def _write_csv(content: str, encoding: str = 'utf-8') -> str:
    tmp = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding=encoding)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_csv_comma_delimiter():
    path = _write_csv('produto,quantidade\nLeite,10\nFarinha,5\n')
    headers, rows = load_file(path)
    os.unlink(path)
    assert headers == ['produto', 'quantidade']
    assert len(rows) == 2
    assert rows[0]['produto'] == 'Leite'


def test_csv_semicolon_delimiter():
    path = _write_csv('produto;quantidade\nLeite;10\nFarinha;5\n')
    headers, rows = load_file(path)
    os.unlink(path)
    assert headers == ['produto', 'quantidade']
    assert rows[1]['produto'] == 'Farinha'
    assert rows[1]['quantidade'] == '5'


def test_csv_tab_delimiter():
    path = _write_csv('produto\tquantidade\nLeite\t10\n')
    headers, rows = load_file(path)
    os.unlink(path)
    assert headers == ['produto', 'quantidade']
    assert rows[0]['quantidade'] == '10'


def test_csv_utf8_bom():
    # utf-8-sig encoding adds the BOM automatically; don't add it in the string too
    content = 'produto;quantidade\nLeite;10\n'
    path = _write_csv(content, encoding='utf-8-sig')
    headers, rows = load_file(path)
    os.unlink(path)
    assert 'produto' in headers
    assert rows[0]['produto'] == 'Leite'


def test_csv_cp1252_encoding():
    content = 'produto;quantidade\nAçúcar;5\nFarinha;3\n'
    path = _write_csv(content, encoding='cp1252')
    headers, rows = load_file(path)
    os.unlink(path)
    assert len(rows) == 2


def test_csv_skips_empty_rows():
    path = _write_csv('produto,quantidade\nLeite,10\n\n\nFarinha,5\n')
    headers, rows = load_file(path)
    os.unlink(path)
    assert len(rows) == 2


def test_csv_mixed_with_xlsx(tmp_path):
    import openpyxl
    # Create xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['produto', 'quantidade'])
    ws.append(['Leite 1L', 8])
    xlsx_path = str(tmp_path / 'b.xlsx')
    wb.save(xlsx_path)

    # Create csv
    csv_path = _write_csv('produto;quantidade\nLeite Piracanjuba 1 litro;10\n')

    from excel_diff.core.diff_engine import run_diff
    result = run_diff(csv_path, xlsx_path, threshold=75)

    os.unlink(csv_path)
    assert len(result.matched) == 1, f'Expected 1 match, got {result.matched}'
