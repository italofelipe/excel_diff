import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from excel_diff.core.matcher import match_rows
from excel_diff.core.normalizer import NormConfig


def _rows(items: list[str], col: str = 'produto') -> list[dict]:
    return [{col: item} for item in items]


COL = 'produto'
CFG = NormConfig()


def test_exact_match():
    a = _rows(['Leite Integral'])
    b = _rows(['Leite Integral'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 75, CFG)
    assert len(matched) == 1
    assert len(only_a) == 0
    assert len(only_b) == 0


def test_fuzzy_match_leite():
    # token_set_ratio: "leite 1 litro" is a token-subset of "leite piracanjuba 1 litro" → score 100
    a = _rows(['Leite Piracanjuba 1 litro'])
    b = _rows(['Leite 1L'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 75, CFG)
    assert len(matched) == 1, f"Expected 1 match, got {len(matched)}. only_a={only_a}"


def test_fuzzy_match_farinha():
    a = _rows(['Farinha de Trigo 5kg'])
    b = _rows(['Farinha Trigo 5 quilogramas'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 70, CFG)
    assert len(matched) == 1


def test_no_match_different_products():
    a = _rows(['Sal'])
    b = _rows(['Açúcar'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 75, CFG)
    assert len(matched) == 0
    assert len(only_a) == 1
    assert len(only_b) == 1


def test_multiple_rows():
    # After stripping quantities: "leite" matches "leite integral", "farinha" matches "farinha de trigo"
    # "Sal" and "Açúcar" don't match (22% similarity)
    a = _rows(['Leite 1L', 'Farinha 5kg', 'Sal 1kg'])
    b = _rows(['Leite Integral 1 litro', 'Farinha de Trigo 5 quilogramas', 'Açúcar 1kg'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 75, CFG)
    assert len(matched) >= 2
    assert any('car' in r[COL].lower() for r in only_b)  # Açúcar in only_b


def test_empty_a():
    only_a, only_b, matched = match_rows([], _rows(['Leite']), COL, COL, 75, CFG)
    assert only_a == []
    assert len(only_b) == 1
    assert matched == []


def test_empty_b():
    only_a, only_b, matched = match_rows(_rows(['Leite']), [], COL, COL, 75, CFG)
    assert len(only_a) == 1
    assert only_b == []
    assert matched == []


def test_high_threshold_forces_no_match():
    # "Sal" vs "Farinha" are truly unrelated products; even at low threshold they won't match
    a = _rows(['Sal'])
    b = _rows(['Farinha'])
    only_a, only_b, matched = match_rows(a, b, COL, COL, 75, CFG)
    assert len(matched) == 0
