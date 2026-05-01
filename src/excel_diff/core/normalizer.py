import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class NormConfig:
    lowercase: bool = True
    remove_accents: bool = True
    expand_units: bool = True
    collapse_whitespace: bool = True
    strip_quantities: bool = True  # remove "1 litro", "5 quilograma" etc. from match key


UNIT_MAP: list[tuple[str, str]] = [
    (r'\b(\d+)\s*litros?\b', r'\1 litro'),
    (r'\b(\d+)\s*l\b', r'\1 litro'),
    (r'\b(\d+)\s*kg\b', r'\1 quilograma'),
    (r'\b(\d+)\s*quilogramas?\b', r'\1 quilograma'),
    (r'\b(\d+)\s*g\b', r'\1 grama'),
    (r'\b(\d+)\s*gramas?\b', r'\1 grama'),
    (r'\b(\d+)\s*ml\b', r'\1 mililitro'),
    (r'\b(\d+)\s*mililitros?\b', r'\1 mililitro'),
    (r'\bpcts?\b', 'pacote'),
    (r'\bpacotes?\b', 'pacote'),
    (r'\buns?\b', 'unidade'),
    (r'\bunidades?\b', 'unidade'),
    (r'\bdz\b', 'duzia'),
    (r'\bduzias?\b', 'duzia'),
]

_COMPILED_UNIT_MAP = [(re.compile(pat, re.IGNORECASE), repl) for pat, repl in UNIT_MAP]

# After expand_units, remove quantity+unit tokens like "1 litro", "500 grama"
_QTY_UNIT_RE = re.compile(
    r'\b\d+\s*(litro|quilograma|grama|mililitro|pacote|unidade|duzia)s?\b',
    re.IGNORECASE,
)


def remove_accents(text: str) -> str:
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def expand_units(text: str) -> str:
    for pattern, replacement in _COMPILED_UNIT_MAP:
        text = pattern.sub(replacement, text)
    return text


def normalize(text: str, config: NormConfig | None = None) -> str:
    if config is None:
        config = NormConfig()
    if not isinstance(text, str):
        text = str(text) if text is not None else ''
    if config.lowercase:
        text = text.lower()
    if config.remove_accents:
        text = remove_accents(text)
    if config.expand_units:
        text = expand_units(text)
    if config.strip_quantities:
        text = _QTY_UNIT_RE.sub('', text)
    if config.collapse_whitespace:
        text = re.sub(r'\s+', ' ', text).strip()
    return text
