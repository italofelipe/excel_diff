import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from excel_diff.core.normalizer import normalize, expand_units, NormConfig

_NO_STRIP = NormConfig(strip_quantities=False)


def test_lowercase():
    assert normalize('Leite Integral', NormConfig(remove_accents=False, expand_units=False, strip_quantities=False)) == 'leite integral'


def test_remove_accents():
    assert normalize('Açúcar Refinado', NormConfig(expand_units=False, strip_quantities=False)) == 'acucar refinado'


def test_expand_unit_l():
    result = expand_units('Leite 1L'.lower())
    assert '1 litro' in result


def test_expand_unit_kg():
    result = expand_units('Farinha 5kg'.lower())
    assert '5 quilograma' in result


def test_expand_unit_g():
    result = expand_units('Sal 500g'.lower())
    assert '500 grama' in result


def test_expand_unit_ml():
    result = expand_units('Óleo 200ml'.lower())
    assert '200 mililitro' in result


def test_strip_quantities_removes_qty_unit():
    # Default config strips "1 litro", "5 quilograma" etc.
    result = normalize('Leite 1L')
    assert '1 litro' not in result
    assert 'leite' in result


def test_strip_quantities_false_preserves_units():
    result = normalize('Leite 1L', _NO_STRIP)
    assert '1 litro' in result


def test_leite_piracanjuba_both_resolve_to_leite():
    # After stripping quantities, both resolve to just the product name
    a = normalize('Leite Piracanjuba 1 litro')
    b = normalize('Leite 1L')
    assert 'leite' in a
    assert 'leite' in b


def test_collapse_whitespace():
    result = normalize('Farinha   de   Trigo', NormConfig(remove_accents=False, expand_units=False, strip_quantities=False))
    assert result == 'farinha de trigo'


def test_none_input():
    assert normalize(None) == ''


def test_numeric_input():
    result = normalize(123)
    assert result == '123'
