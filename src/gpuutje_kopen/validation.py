"""Listing validation using exact word-token matching for GPU correctness.

Every word in a GPU search query must appear as an exact token in the listing
title.  Compound words like "RTX4070Ti" are split on letter↔digit and
camelCase boundaries so "RTX", "4070", "TI" are all available as tokens.
Among full matches the query with the most words wins (most specific).
"""

import re
from .db import GPU, load_gpu_list

_GPU_LIST: list[GPU] = []
_GPU_BY_ID: dict[str, GPU] = {}

_SPLIT_RE = re.compile(r'[\s\-_/,;:()!@#$%^&*\[\]{}|\\<>.+]+')
_SUBTOKEN_RE = re.compile(r'[A-Z]+[a-z]*|[a-z]+|[0-9]+')


def _ensure_loaded():
    global _GPU_LIST, _GPU_BY_ID
    if not _GPU_LIST:
        _GPU_LIST = load_gpu_list()
        _GPU_BY_ID = {g.id: g for g in _GPU_LIST}


def reload_gpu_cache():
    global _GPU_LIST, _GPU_BY_ID
    _GPU_LIST = load_gpu_list()
    _GPU_BY_ID = {g.id: g for g in _GPU_LIST}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into uppercase tokens.

    Splits on whitespace / punctuation to get word-level tokens, then also
    splits each compound word on letter↔digit and camelCase boundaries.
    Both the original word and its sub-tokens are kept so that:

        "RTX4070TiSuper"  → {"RTX4070TISUPER", "RTX", "4070", "TI", "SUPER"}
        "L4 GPU"          → {"L4", "L", "4", "GPU"}
        "3080ti"          → {"3080TI", "3080", "TI"}
    """
    tokens: set[str] = set()
    for part in _SPLIT_RE.split(text):
        if not part:
            continue
        tokens.add(part.upper())
        sub = _SUBTOKEN_RE.findall(part)
        if len(sub) > 1:
            tokens.update(s.upper() for s in sub)
    return tokens


def _query_match(query: str, title_tokens: set[str]) -> int:
    """Return the word count if ALL words of *query* appear in *title_tokens*, else 0."""
    words = query.upper().split()
    if not words:
        return 0
    for w in words:
        if w not in title_tokens:
            return 0
    return len(words)


def find_best_gpu_match(title: str) -> tuple[str | None, int]:
    """Find the GPU whose search query best matches the title.

    Returns ``(gpu_id, matched_word_count)`` or ``(None, 0)``.
    """
    _ensure_loaded()
    if not title:
        return None, 0

    title_tokens = _tokenize(title)
    best_id: str | None = None
    best_words = 0

    for gpu in _GPU_LIST:
        for query in gpu.search_queries:
            count = _query_match(query, title_tokens)
            if count > best_words:
                best_id = gpu.id
                best_words = count

    return best_id, best_words


def validate_listing(
    gpu_id: str, title: str, threshold: int = 70,
) -> tuple[bool, str | None, float]:
    """Validate whether a listing matches the expected GPU.

    Returns ``(is_valid, corrected_gpu_id, match_word_count)``.
    *threshold* is accepted for API compatibility but ignored.
    """
    _ensure_loaded()
    if not title:
        return False, None, 0

    best_match, best_words = find_best_gpu_match(title)

    if best_match is None or best_words < 1:
        return False, None, 0

    if best_match == gpu_id:
        return True, None, float(best_words)

    # Best match differs — check whether the original GPU also matches
    title_tokens = _tokenize(title)
    original_words = 0
    original_gpu = _GPU_BY_ID.get(gpu_id)
    if original_gpu:
        for query in original_gpu.search_queries:
            count = _query_match(query, title_tokens)
            if count > original_words:
                original_words = count

    # Correct to the better match if it is strictly more specific
    if best_words > original_words:
        return True, best_match, float(best_words)

    # Original matches equally well — keep it
    if original_words >= 1:
        return True, None, float(original_words)

    return False, None, float(best_words)
