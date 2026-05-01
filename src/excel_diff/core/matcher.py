from __future__ import annotations

from rapidfuzz import fuzz, process

from .normalizer import NormConfig, normalize


def _build_index(rows: list[dict], key_col: str, config: NormConfig) -> list[tuple[str, dict]]:
    result = []
    for row in rows:
        raw = str(row.get(key_col, ''))
        norm = normalize(raw, config)
        result.append((norm, row))
    return result


def match_rows(
    rows_a: list[dict],
    rows_b: list[dict],
    key_col_a: str,
    key_col_b: str,
    threshold: float,
    config: NormConfig | None = None,
) -> tuple[list[dict], list[dict], list[tuple[dict, dict, float]]]:
    """
    Returns (only_in_a, only_in_b, matched_pairs).
    matched_pairs is a list of (row_a, row_b, score).
    """
    if config is None:
        config = NormConfig()

    index_b = _build_index(rows_b, key_col_b, config)
    keys_b = [item[0] for item in index_b]

    matched_b_indices: set[int] = set()
    only_in_a: list[dict] = []
    matched: list[tuple[dict, dict, float]] = []

    for row_a in rows_a:
        raw_a = str(row_a.get(key_col_a, ''))
        norm_a = normalize(raw_a, config)

        if not norm_a or not keys_b:
            only_in_a.append(row_a)
            continue

        result = process.extractOne(norm_a, keys_b, scorer=fuzz.token_set_ratio)
        if result is None:
            only_in_a.append(row_a)
            continue

        best_key, score, idx = result
        if score >= threshold:
            matched.append((row_a, index_b[idx][1], score))
            matched_b_indices.add(idx)
        else:
            only_in_a.append(row_a)

    only_in_b = [index_b[i][1] for i in range(len(index_b)) if i not in matched_b_indices]
    return only_in_a, only_in_b, matched
