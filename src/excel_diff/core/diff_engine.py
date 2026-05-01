from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .loader import detect_key_column, load_file
from .matcher import match_rows
from .normalizer import NormConfig


@dataclass
class MatchedPair:
    row_a: dict
    row_b: dict
    score: float
    key_a: str
    key_b: str


@dataclass
class DiffResult:
    only_in_a: list[dict]
    only_in_b: list[dict]
    matched: list[MatchedPair]
    threshold: float
    file_a_name: str
    file_b_name: str
    headers_a: list[str] = field(default_factory=list)
    headers_b: list[str] = field(default_factory=list)
    key_col_a: str = ''
    key_col_b: str = ''


def run_diff(
    path_a: str | Path,
    path_b: str | Path,
    threshold: float = 75.0,
    key_col_a: str | None = None,
    key_col_b: str | None = None,
    config: NormConfig | None = None,
) -> DiffResult:
    headers_a, rows_a = load_file(path_a)
    headers_b, rows_b = load_file(path_b)

    if config is None:
        config = NormConfig()

    col_a = key_col_a if key_col_a else detect_key_column(headers_a)
    col_b = key_col_b if key_col_b else detect_key_column(headers_b)

    only_in_a, only_in_b, matched_raw = match_rows(
        rows_a, rows_b, col_a, col_b, threshold, config
    )

    matched = [
        MatchedPair(row_a=ra, row_b=rb, score=score, key_a=col_a, key_b=col_b)
        for ra, rb, score in matched_raw
    ]

    return DiffResult(
        only_in_a=only_in_a,
        only_in_b=only_in_b,
        matched=matched,
        threshold=threshold,
        file_a_name=Path(path_a).name,
        file_b_name=Path(path_b).name,
        headers_a=headers_a,
        headers_b=headers_b,
        key_col_a=col_a,
        key_col_b=col_b,
    )
